import pandas as pd
import numpy as np
from strategies.strategy_base import Strategy

class RSIPairStrategy(Strategy):
    """
    SPY/RSP Pair Trading Strategy
    - Short whichever ETF has RSI > 70
    - Long the other ETF
    - Reverse when opposite signal triggers
    """
    
    def __init__(self, rsi_period=14, rsi_threshold=70, position_size=50.0):
        """
        Args:
            rsi_period: RSI lookback period (default 14)
            rsi_threshold: RSI level to trigger trades (default 70)
            position_size: Dollar amount per position (default $50)
        """
        self.rsi_period = rsi_period
        self.rsi_threshold = rsi_threshold
        self.position_size = position_size
        
    def calculate_rsi(self, prices, period=14):
        """Calculate RSI indicator"""
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi
    
    def add_indicators(self, df):
        """Add RSI indicator to dataframe"""
        df['rsi'] = self.calculate_rsi(df['Close'], self.rsi_period)
        return df
    
    def generate_signals(self, df):
        """
        Generate trading signals:
        signal = 1: Long position
        signal = -1: Short position
        signal = 0: No position
        """
        df['signal'] = 0
        
        # Short when RSI > threshold
        df.loc[df['rsi'] > self.rsi_threshold, 'signal'] = -1
        
        # Long when RSI < (100 - threshold) 
        df.loc[df['rsi'] < (100 - self.rsi_threshold), 'signal'] = 1
        
        # Forward fill to maintain position
        df['position'] = df['signal'].replace(0, np.nan).ffill().fillna(0)
        
        # Set target quantity
        df['target_qty'] = self.position_size
        
        return df
class VRPAdaptivePairStrategy(Strategy):
    """
    RSP/SPY Mean Reversion with Volatility Risk Premium (VRP) Overlay.
   
    This strategy should be run on RSP data. It requires SPY and VIX
    data to be merged into the input DataFrame.
    """

    def __init__(
        self,
        rsi_period: int = 14,
        rsi_threshold: float = 70.0,
        position_size: float = 100.0,
        vrp_window: int = 21
    ):
        self.rsi_period = rsi_period
        self.rsi_threshold = rsi_threshold
        self.position_size = position_size
        self.vrp_window = vrp_window

    def add_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        # 1. RSI for Relative Strength (RSP vs SPY)
        # Note: Assumes columns 'Close' (RSP) and 'Close_SPY' exist
        for col, name in [('Close', 'rsp'), ('Close_SPY', 'spy')]:
            delta = df[col].diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=self.rsi_period).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=self.rsi_period).mean()
            rs = gain / loss
            df[f'rsi_{name}'] = 100 - (100 / (1 + rs))

        # 2. VRP Calculation: (VIX - Annualized Realized Vol of SPY)
        # Assumes 'Close_VIX' exists in df
        spy_returns = df['Close_SPY'].pct_change()
        realized_vol = spy_returns.rolling(self.vrp_window).std() * np.sqrt(252) * 100
        df['vrp'] = df['Close_VIX'] - realized_vol
       
        # 3. VRP Z-Score (Regime Detection)
        df['vrp_z'] = (df['vrp'] - df['vrp'].rolling(63).mean()) / df['vrp'].rolling(63).std()
       
        return df

    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        df['signal'] = 0
       
        # Define Regimes
        # Safe = VRP is positive/normal; Panic = VRP is crashing
        panic_threshold = -1.5
        is_safe = df['vrp_z'] > panic_threshold
        is_harvest = df['vrp_z'] > 0 # High conviction
       
        # RSI Logic: If SPY is overbought (>70), we want to be Short SPY / Long RSP
        # In this primary-ticker model, signal=1 means Long RSP (and implied Short SPY)
        buy_rsp = (df['rsi_spy'] > self.rsi_threshold) & is_safe
        sell_rsp = (df['rsi_rsp'] > self.rsi_threshold) & is_safe
       
        # Assign Signals
        df.loc[buy_rsp, 'signal'] = 1
        df.loc[sell_rsp, 'signal'] = -1
       
        # Position Logic (Carry the signal forward)
        df['position'] = df['signal'].replace(0, np.nan).ffill().fillna(0)
       
        # Adaptive Sizing: Scale size based on VRP regime
        df['target_qty'] = self.position_size  # Base size
       
        # Reduce size by 50% if VRP is fragile (0 > Z > -1.5)
        df.loc[df['vrp_z'] <= 0, 'target_qty'] = self.position_size * 0.5
       
        # Emergency Exit: If VRP enters Panic Zone, flatten everything
        df.loc[~is_safe, 'position'] = 0
        df.loc[~is_safe, 'target_qty'] = 0
       
        return df
