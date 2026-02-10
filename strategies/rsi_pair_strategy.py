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
