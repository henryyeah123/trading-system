import time
import pandas as pd
import numpy as np
from datetime import datetime, timezone
from pipeline.alpaca import get_rest

def calculate_rsi(prices, period=14):
    """Calculate RSI"""
    delta = prices.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

# Strategy parameters
RSI_OVERBOUGHT = 70
RSI_OVERSOLD = 30
CAPITAL_USAGE = 0.90
LOOKBACK_BARS = 100
VRP_PANIC_THRESHOLD = -1.5 # The "Kill Switch" level

print("="*60)
print("LIVE SPY/RSP PAIR TRADING STRATEGY + VRP HEDGE")
print("="*60)

# Connect to Alpaca
api = get_rest()

# State tracking
current_position = None 

def get_account_value():
    account = api.get_account()
    return float(account.portfolio_value)

def get_current_price(symbol):
    bars = api.get_bars(symbol, '1Min', limit=1).df
    if not bars.empty:
        return bars['close'].iloc[-1]
    return None

def get_vrp_z_score():
    """Calculates the Volatility Risk Premium Z-Score"""
    try:
        # Fetch data for VRP (SPY for realized vol, VIXY as VIX proxy)
        spy_bars = api.get_bars('SPY', '1Day', limit=85).df
        # Note: If your Alpaca tier supports ^VIX, use that; otherwise VIXY/VXX
        vix_bars = api.get_bars('VIXY', '1Day', limit=85).df 
        
        returns = spy_bars['close'].pct_change()
        realized_vol = returns.rolling(21).std() * np.sqrt(252) * 100
        vrp = vix_bars['close'] - realized_vol
        
        vrp_mean = vrp.rolling(63).mean()
        vrp_std = vrp.rolling(63).std()
        
        z_score = (vrp.iloc[-1] - vrp_mean.iloc[-1]) / vrp_std.iloc[-1]
        return z_score
    except Exception as e:
        print(f"VRP Calculation Error: {e}")
        return 0.0 # Default to neutral if calculation fails

def get_ratio_rsi():
    spy_bars = api.get_bars('SPY', '5Min', limit=LOOKBACK_BARS).df
    rsp_bars = api.get_bars('RSP', '5Min', limit=LOOKBACK_BARS).df
    common_idx = spy_bars.index.intersection(rsp_bars.index)
    spy_bars = spy_bars.loc[common_idx]
    rsp_bars = rsp_bars.loc[common_idx]
    ratio = spy_bars['close'] / rsp_bars['close']
    rsi = calculate_rsi(ratio, period=14)
    return rsi.iloc[-1] if not rsi.empty else None

def close_all_positions():
    global current_position
    try:
        api.close_all_positions()
        print(f"[{datetime.now(timezone.utc)}] Closed all positions")
        current_position = None
    except Exception as e:
        print(f"Error closing positions: {e}")

def enter_trade(position_type, ratio_rsi, vrp_z):
    global current_position
    try:
        account_value = get_account_value()
        
        # ADAPTIVE SIZING: If VRP is weak (Z < 0), use half capital
        size_multiplier = 0.5 if vrp_z <= 0 else 1.0
        position_size = (account_value * CAPITAL_USAGE / 2) * size_multiplier
        
        spy_price = get_current_price('SPY')
        rsp_price = get_current_price('RSP')
        if not spy_price or not rsp_price: return
        
        spy_qty = int(position_size / spy_price)
        rsp_qty = int(position_size / rsp_price)
        
        if position_type == 'short_spy_long_rsp':
            api.submit_order(symbol='SPY', qty=spy_qty, side='sell', type='market', time_in_force='day')
            api.submit_order(symbol='RSP', qty=rsp_qty, side='buy', type='market', time_in_force='day')
        elif position_type == 'long_spy_short_rsp':
            api.submit_order(symbol='SPY', qty=spy_qty, side='buy', type='market', time_in_force='day')
            api.submit_order(symbol='RSP', qty=rsp_qty, side='sell', type='market', time_in_force='day')
            
        print(f"\n[{datetime.now(timezone.utc)}] ENTERED TRADE | VRP Z: {vrp_z:.2f} | Size: {size_multiplier*100}%")
        current_position = position_type
    except Exception as e:
        print(f"Error entering trade: {e}")

# Main loop
try:
    while True:
        now = datetime.now(timezone.utc)
        ratio_rsi = get_ratio_rsi()
        vrp_z = get_vrp_z_score()
        
        if ratio_rsi is None:
            time.sleep(300)
            continue
        
        print(f"[{now}] RSI: {ratio_rsi:.2f} | VRP Z: {vrp_z:.2f} | Pos: {current_position or 'None'}")
        
        # EMERGENCY EXIT: VRP Panic
        if current_position is not None and vrp_z <= VRP_PANIC_THRESHOLD:
            print(f"!!! VRP PANIC (Z={vrp_z:.2f}) - FLATTENING POSITIONS !!!")
            close_all_positions()

        # ENTRY LOGIC: Only if VRP is safe
        elif current_position is None and vrp_z > VRP_PANIC_THRESHOLD:
            if ratio_rsi > RSI_OVERBOUGHT:
                enter_trade('short_spy_long_rsp', ratio_rsi, vrp_z)
            elif ratio_rsi < RSI_OVERSOLD:
                enter_trade('long_spy_short_rsp', ratio_rsi, vrp_z)
        
        # EXIT LOGIC (Mean Reversion)
        elif current_position is not None:
            if (current_position == 'short_spy_long_rsp' and ratio_rsi < 50) or \
               (current_position == 'long_spy_short_rsp' and ratio_rsi > 50):
                close_all_positions()
        
        time.sleep(300)
except KeyboardInterrupt:
    close_all_positions()