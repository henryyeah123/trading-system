#!/usr/bin/env python3
"""
LIVE RSP/VGT Pair Trading Strategy
Optimized parameters: 65/30/50, 90% capital
"""

import time
import pandas as pd
import numpy as np
from datetime import datetime, timezone
from pipeline.alpaca import get_rest

# OPTIMIZED PARAMETERS
RSI_ENTRY_HIGH = 65
RSI_ENTRY_LOW = 30
RSI_EXIT = 50
CAPITAL_USAGE = 0.90
LOOKBACK_BARS = 100

def calculate_rsi(prices, period=14):
    """Calculate RSI"""
    delta = prices.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

print("="*60)
print("LIVE RSP/VGT PAIR TRADING STRATEGY")
print("="*60)
print(f"RSI Entry High: {RSI_ENTRY_HIGH}")
print(f"RSI Entry Low:  {RSI_ENTRY_LOW}")
print(f"RSI Exit:       {RSI_EXIT}")
print(f"Capital Usage:  {CAPITAL_USAGE*100:.0f}%")
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

def get_ratio_rsi():
    """Get RSP/VGT ratio RSI"""
    rsp_bars = api.get_bars('RSP', '1Hour', limit=LOOKBACK_BARS).df
    vgt_bars = api.get_bars('VGT', '1Hour', limit=LOOKBACK_BARS).df
    
    common_idx = rsp_bars.index.intersection(vgt_bars.index)
    rsp_bars = rsp_bars.loc[common_idx]
    vgt_bars = vgt_bars.loc[common_idx]
    
    ratio = rsp_bars['close'] / vgt_bars['close']
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

def enter_trade(position_type, ratio_rsi):
    global current_position
    try:
        account_value = get_account_value()
        position_size = account_value * CAPITAL_USAGE / 2
        
        rsp_price = get_current_price('RSP')
        vgt_price = get_current_price('VGT')
        
        if not rsp_price or not vgt_price:
            return
        
        rsp_qty = int(position_size / rsp_price)
        vgt_qty = int(position_size / vgt_price)
        
        if position_type == 'short_rsp_long_vgt':
            # Short RSP, Long VGT
            api.submit_order(symbol='RSP', qty=rsp_qty, side='sell', type='market', time_in_force='day')
            api.submit_order(symbol='VGT', qty=vgt_qty, side='buy', type='market', time_in_force='day')
            print(f"\n[{datetime.now(timezone.utc)}] ENTERED: SHORT RSP / LONG VGT")
            
        elif position_type == 'long_rsp_short_vgt':
            # Long RSP, Short VGT
            api.submit_order(symbol='RSP', qty=rsp_qty, side='buy', type='market', time_in_force='day')
            api.submit_order(symbol='VGT', qty=vgt_qty, side='sell', type='market', time_in_force='day')
            print(f"\n[{datetime.now(timezone.utc)}] ENTERED: LONG RSP / SHORT VGT")
        
        print(f"  RSI: {ratio_rsi:.2f}")
        print(f"  Size: ${position_size*2:,.0f}")
        current_position = position_type
        
    except Exception as e:
        print(f"Error entering trade: {e}")

# Main loop
print("\nStarting live trading loop...")
print("Press Ctrl+C to stop\n")

try:
    while True:
        now = datetime.now(timezone.utc)
        ratio_rsi = get_ratio_rsi()
        
        if ratio_rsi is None:
            print(f"[{now}] Waiting for data...")
            time.sleep(300)
            continue
        
        print(f"[{now}] Ratio RSI: {ratio_rsi:.2f} | Position: {current_position or 'None'}")
        
        # Exit logic
        if current_position == 'short_rsp_long_vgt' and ratio_rsi < RSI_EXIT:
            print(f"  → EXIT SIGNAL (RSI < {RSI_EXIT})")
            close_all_positions()
            
        elif current_position == 'long_rsp_short_vgt' and ratio_rsi > (100 - RSI_EXIT):
            print(f"  → EXIT SIGNAL (RSI > {100 - RSI_EXIT})")
            close_all_positions()
        
        # Entry logic
        elif current_position is None:
            if ratio_rsi > RSI_ENTRY_HIGH:
                print(f"  → ENTRY SIGNAL: RSI > {RSI_ENTRY_HIGH}")
                enter_trade('short_rsp_long_vgt', ratio_rsi)
                
            elif ratio_rsi < RSI_ENTRY_LOW:
                print(f"  → ENTRY SIGNAL: RSI < {RSI_ENTRY_LOW}")
                enter_trade('long_rsp_short_vgt', ratio_rsi)
        
        # Check every 5 minutes
        time.sleep(300)
        
except KeyboardInterrupt:
    print("\n\nStopping strategy...")
    close_all_positions()
    print("✓ Strategy stopped")
