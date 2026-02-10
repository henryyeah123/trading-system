#!/usr/bin/env python3
"""
Aggressive Pair Trading - 90% Capital, Stop Loss Protection
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

def calculate_rsi(prices, period=14):
    """Calculate RSI indicator"""
    delta = prices.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    return rsi

# Load 5-minute data
print("Loading SPY and RSP 5-minute data...")
spy_df = pd.read_csv('data/SPY_5Min_stock_alpaca_clean.csv', index_col='Datetime', parse_dates=True)
rsp_df = pd.read_csv('data/RSP_5Min_stock_alpaca_clean.csv', index_col='Datetime', parse_dates=True)

# Align dates
common_dates = spy_df.index.intersection(rsp_df.index)
spy_df = spy_df.loc[common_dates]
rsp_df = rsp_df.loc[common_dates]

print(f"Loaded {len(spy_df)} 5-minute bars")

# Calculate ratio and RSI
print("Calculating SPY/RSP ratio and RSI...")
spy_df['ratio'] = spy_df['Close'] / rsp_df['Close']
spy_df['ratio_rsi'] = calculate_rsi(spy_df['ratio'], period=14)

# Drop NaN
valid_idx = spy_df['ratio_rsi'].notna()
spy_df = spy_df[valid_idx]
rsp_df = rsp_df[valid_idx]

print(f"Valid data points: {len(spy_df)}")

# Strategy parameters
RSI_OVERBOUGHT = 70
RSI_OVERSOLD = 30
CAPITAL_USAGE = 0.90  # Use 90% of capital per trade
STOP_LOSS_PCT = 0.02  # Exit if position loses 2%

# Initialize portfolio
portfolio = {
    'cash': 100000,
    'spy_shares': 0,
    'rsp_shares': 0,
    'equity': [],
    'dates': [],
    'trades': [],
    'entry_value': 0
}

current_position = None

print("\nRunning AGGRESSIVE pair trading strategy...")
print(f"Capital Usage: {CAPITAL_USAGE*100}%")
print(f"Stop Loss: {STOP_LOSS_PCT*100}%")
print("="*60)

for date in spy_df.index:
    spy_price = spy_df.loc[date, 'Close']
    rsp_price = rsp_df.loc[date, 'Close']
    ratio_rsi = spy_df.loc[date, 'ratio_rsi']
    
    # Calculate portfolio value
    portfolio_value = portfolio['cash'] + \
                      portfolio['spy_shares'] * spy_price + \
                      portfolio['rsp_shares'] * rsp_price
    
    portfolio['equity'].append(portfolio_value)
    portfolio['dates'].append(date)
    
    # Check stop loss if in position
    if current_position is not None:
        position_pnl = portfolio_value - portfolio['entry_value']
        loss_pct = position_pnl / portfolio['entry_value']
        
        if loss_pct < -STOP_LOSS_PCT:
            # STOP LOSS HIT
            portfolio['cash'] += portfolio['spy_shares'] * spy_price
            portfolio['cash'] += portfolio['rsp_shares'] * rsp_price
            
            portfolio['trades'].append(
                f"{date}: STOP LOSS | Loss={loss_pct*100:.2f}% | PnL: ${position_pnl:.2f}"
            )
            
            portfolio['spy_shares'] = 0
            portfolio['rsp_shares'] = 0
            current_position = None
            portfolio['entry_value'] = 0
            continue
    
    # Trading logic
    if current_position is None:
        # Entry signals - use 90% of capital
        position_size = portfolio_value * CAPITAL_USAGE / 2  # Split between SPY and RSP
        
        if ratio_rsi > RSI_OVERBOUGHT:
            # Short SPY, Long RSP
            spy_shares = -(position_size // spy_price)
            rsp_shares = position_size // rsp_price
            
            portfolio['spy_shares'] = spy_shares
            portfolio['rsp_shares'] = rsp_shares
            portfolio['cash'] -= (rsp_shares * rsp_price)
            portfolio['cash'] += (-spy_shares * spy_price)
            portfolio['entry_value'] = portfolio_value
            
            current_position = 'short_spy_long_rsp'
            portfolio['trades'].append(
                f"{date}: SHORT SPY @ ${spy_price:.2f}, LONG RSP @ ${rsp_price:.2f} | "
                f"Ratio_RSI={ratio_rsi:.1f} | Size=${position_size*2:,.0f}"
            )
            
        elif ratio_rsi < RSI_OVERSOLD:
            # Long SPY, Short RSP
            spy_shares = position_size // spy_price
            rsp_shares = -(position_size // rsp_price)
            
            portfolio['spy_shares'] = spy_shares
            portfolio['rsp_shares'] = rsp_shares
            portfolio['cash'] -= (spy_shares * spy_price)
            portfolio['cash'] += (-rsp_shares * rsp_price)
            portfolio['entry_value'] = portfolio_value
            
            current_position = 'long_spy_short_rsp'
            portfolio['trades'].append(
                f"{date}: LONG SPY @ ${spy_price:.2f}, SHORT RSP @ ${rsp_price:.2f} | "
                f"Ratio_RSI={ratio_rsi:.1f} | Size=${position_size*2:,.0f}"
            )
    
    else:
        # Exit on mean reversion
        should_exit = False
        
        if current_position == 'short_spy_long_rsp' and ratio_rsi < 50:
            should_exit = True
        elif current_position == 'long_spy_short_rsp' and ratio_rsi > 50:
            should_exit = True
        
        if should_exit:
            portfolio['cash'] += portfolio['spy_shares'] * spy_price
            portfolio['cash'] += portfolio['rsp_shares'] * rsp_price
            
            position_pnl = portfolio_value - portfolio['entry_value']
            portfolio['trades'].append(
                f"{date}: CLOSE | Ratio_RSI={ratio_rsi:.1f} | PnL: ${position_pnl:.2f}"
            )
            
            portfolio['spy_shares'] = 0
            portfolio['rsp_shares'] = 0
            current_position = None
            portfolio['entry_value'] = 0

# Results
final_value = portfolio['equity'][-1]
total_pnl = final_value - 100000
total_trades = len([t for t in portfolio['trades'] if 'SHORT' in t or 'LONG' in t])
stop_losses = len([t for t in portfolio['trades'] if 'STOP LOSS' in t])

print("\n" + "="*60)
print("AGGRESSIVE STRATEGY RESULTS")
print("="*60)
print(f"Starting Capital: $100,000")
print(f"Final Portfolio Value: ${final_value:,.2f}")
print(f"Total PnL: ${total_pnl:,.2f}")
print(f"Return: {(total_pnl/100000)*100:.2f}%")
print(f"Total Trades: {total_trades}")
print(f"Stop Losses Hit: {stop_losses}")
print(f"\nCapital Usage: {CAPITAL_USAGE*100}% per trade")
print(f"Stop Loss: {STOP_LOSS_PCT*100}%")
print("\nLast 20 Trades:")
for trade in portfolio['trades'][-20:]:
    print(f"  {trade}")

# Plot
plt.figure(figsize=(14, 7))
plt.plot(portfolio['dates'], portfolio['equity'], linewidth=2)
plt.axhline(y=100000, color='r', linestyle='--', label='Starting Capital')
plt.xlabel('Date')
plt.ylabel('Portfolio Value ($)')
plt.title('AGGRESSIVE SPY/RSP Pair Trading - 90% Capital + Stop Loss')
plt.legend()
plt.grid(True, alpha=0.3)
plt.tight_layout()
plt.show()

print("\n" + "="*60)
