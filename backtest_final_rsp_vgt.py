#!/usr/bin/env python3
"""
FINAL RSP/VGT Pair Trading Strategy
Optimized parameters: 65/30/50, 90% capital
Tested across 2020-2025
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

# OPTIMIZED PARAMETERS
RSI_ENTRY_HIGH = 65
RSI_ENTRY_LOW = 30
RSI_EXIT = 50
CAPITAL_USAGE = 0.90

print("="*70)
print("RSP/VGT PAIR TRADING STRATEGY - FINAL BACKTEST")
print("="*70)
print(f"Parameters:")
print(f"  RSI Entry High: {RSI_ENTRY_HIGH}")
print(f"  RSI Entry Low:  {RSI_ENTRY_LOW}")
print(f"  RSI Exit:       {RSI_EXIT}")
print(f"  Capital Usage:  {CAPITAL_USAGE*100:.0f}%")
print("="*70)

# Load data - try multiple sources to get full 2020-2025
rsp_dfs = []
vgt_dfs = []

data_sources = [
    ('data/RSP_1Day_stock_alpaca_clean.csv', 'data/VGT_1Day_stock_alpaca_clean.csv'),
    ('data/RSP_2022_2024_1Day_stock_alpaca_clean.csv', 'data/VGT_2022_2024_1Day_stock_alpaca_clean.csv'),
    ('data/RSP_2024_today_1Day_stock_alpaca_clean.csv', 'data/VGT_2024_today_1Day_stock_alpaca_clean.csv')
]

for rsp_file, vgt_file in data_sources:
    try:
        rsp = pd.read_csv(rsp_file, index_col='Datetime', parse_dates=True)
        vgt = pd.read_csv(vgt_file, index_col='Datetime', parse_dates=True)
        rsp_dfs.append(rsp)
        vgt_dfs.append(vgt)
    except:
        pass

# Combine all data
if rsp_dfs and vgt_dfs:
    rsp_df = pd.concat(rsp_dfs).sort_index()
    vgt_df = pd.concat(vgt_dfs).sort_index()
    
    # Remove duplicates
    rsp_df = rsp_df[~rsp_df.index.duplicated(keep='first')]
    vgt_df = vgt_df[~vgt_df.index.duplicated(keep='first')]
    
    print(f"\nLoaded data: {rsp_df.index[0].date()} to {rsp_df.index[-1].date()}")
    print(f"Total bars: {len(rsp_df)}")
else:
    print("ERROR: Could not load data")
    exit(1)

# Align data
common_idx = rsp_df.index.intersection(vgt_df.index)
rsp_df = rsp_df.loc[common_idx]
vgt_df = vgt_df.loc[common_idx]

# Calculate ratio and RSI
print("\nCalculating indicators...")
rsp_df['ratio'] = rsp_df['Close'] / vgt_df['Close']
rsp_df['ratio_rsi'] = calculate_rsi(rsp_df['ratio'], period=14)
rsp_df = rsp_df.dropna()
vgt_df = vgt_df.loc[rsp_df.index]

print(f"Valid data points: {len(rsp_df)}")

# Initialize portfolio
portfolio = {
    'cash': 100000,
    'rsp_shares': 0,
    'vgt_shares': 0,
    'equity': [],
    'dates': [],
    'trades': [],
    'entry_value': 0
}

current_position = None

print("\nRunning backtest...")
print("="*70)

for date in rsp_df.index:
    rsp_price = rsp_df.loc[date, 'Close']
    vgt_price = vgt_df.loc[date, 'Close']
    ratio_rsi = rsp_df.loc[date, 'ratio_rsi']
    
    # Calculate portfolio value
    portfolio_value = portfolio['cash'] + \
                      portfolio['rsp_shares'] * rsp_price + \
                      portfolio['vgt_shares'] * vgt_price
    
    portfolio['equity'].append(portfolio_value)
    portfolio['dates'].append(date)
    
    # Exit logic
    if current_position == 'short_rsp_long_vgt' and ratio_rsi < RSI_EXIT:
        portfolio['cash'] += portfolio['rsp_shares'] * rsp_price + portfolio['vgt_shares'] * vgt_price
        pnl = portfolio_value - portfolio['entry_value']
        
        portfolio['trades'].append(
            f"{date.date()}: EXIT | RSI={ratio_rsi:.1f} | PnL: ${pnl:.2f}"
        )
        
        portfolio['rsp_shares'] = 0
        portfolio['vgt_shares'] = 0
        current_position = None
        portfolio['entry_value'] = 0
        
    elif current_position == 'long_rsp_short_vgt' and ratio_rsi > (100 - RSI_EXIT):
        portfolio['cash'] += portfolio['rsp_shares'] * rsp_price + portfolio['vgt_shares'] * vgt_price
        pnl = portfolio_value - portfolio['entry_value']
        
        portfolio['trades'].append(
            f"{date.date()}: EXIT | RSI={ratio_rsi:.1f} | PnL: ${pnl:.2f}"
        )
        
        portfolio['rsp_shares'] = 0
        portfolio['vgt_shares'] = 0
        current_position = None
        portfolio['entry_value'] = 0
    
    # Entry logic
    if current_position is None:
        position_size = portfolio_value * CAPITAL_USAGE / 2
        
        if ratio_rsi > RSI_ENTRY_HIGH:
            # RSP expensive vs VGT → Short RSP, Long VGT
            rsp_shares = -(position_size // rsp_price)
            vgt_shares = position_size // vgt_price
            
            portfolio['rsp_shares'] = rsp_shares
            portfolio['vgt_shares'] = vgt_shares
            portfolio['cash'] -= (vgt_shares * vgt_price)
            portfolio['cash'] += (-rsp_shares * rsp_price)
            portfolio['entry_value'] = portfolio_value
            
            current_position = 'short_rsp_long_vgt'
            
            portfolio['trades'].append(
                f"{date.date()}: ENTER SHORT RSP/LONG VGT | RSI={ratio_rsi:.1f}"
            )
            
        elif ratio_rsi < RSI_ENTRY_LOW:
            # VGT expensive vs RSP → Long RSP, Short VGT
            rsp_shares = position_size // rsp_price
            vgt_shares = -(position_size // vgt_price)
            
            portfolio['rsp_shares'] = rsp_shares
            portfolio['vgt_shares'] = vgt_shares
            portfolio['cash'] -= (rsp_shares * rsp_price)
            portfolio['cash'] += (-vgt_shares * vgt_price)
            portfolio['entry_value'] = portfolio_value
            
            current_position = 'long_rsp_short_vgt'
            
            portfolio['trades'].append(
                f"{date.date()}: ENTER LONG RSP/SHORT VGT | RSI={ratio_rsi:.1f}"
            )

# Results
final_value = portfolio['equity'][-1]
total_pnl = final_value - 100000
total_trades = len([t for t in portfolio['trades'] if 'ENTER' in t])

print("\n" + "="*70)
print("FINAL RESULTS")
print("="*70)
print(f"Starting Capital:  $100,000")
print(f"Final Value:       ${final_value:,.2f}")
print(f"Total P&L:         ${total_pnl:,.2f}")
print(f"Total Return:      {(total_pnl/100000)*100:.2f}%")
print(f"Total Trades:      {total_trades}")
if total_trades > 0:
    print(f"Avg P&L per trade: ${total_pnl/total_trades:.2f}")

# Calculate Sharpe
returns = pd.Series(portfolio['equity']).pct_change().dropna()
if len(returns) > 0 and returns.std() > 0:
    sharpe = (returns.mean() / returns.std()) * np.sqrt(252)
    print(f"Sharpe Ratio:      {sharpe:.2f}")

print("\nLast 20 Trades:")
for trade in portfolio['trades'][-20:]:
    print(f"  {trade}")

# Plot
fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(16, 10), sharex=True)

# Equity curve
ax1.plot(portfolio['dates'], portfolio['equity'], linewidth=2, color='blue', label='Portfolio Value')
ax1.axhline(y=100000, color='r', linestyle='--', linewidth=1, label='Starting Capital')
ax1.set_ylabel('Portfolio Value ($)', fontsize=12)
ax1.set_title('RSP/VGT Pair Trading Strategy (Optimized)', fontsize=14, fontweight='bold')
ax1.legend()
ax1.grid(True, alpha=0.3)

# RSI
ax2.plot(rsp_df.index, rsp_df['ratio_rsi'], linewidth=1, color='purple', label='Ratio RSI')
ax2.axhline(y=RSI_ENTRY_HIGH, color='red', linestyle='--', linewidth=2, label=f'Entry High ({RSI_ENTRY_HIGH})')
ax2.axhline(y=RSI_ENTRY_LOW, color='green', linestyle='--', linewidth=2, label=f'Entry Low ({RSI_ENTRY_LOW})')
ax2.axhline(y=RSI_EXIT, color='gray', linestyle=':', linewidth=1, label=f'Exit ({RSI_EXIT})')
ax2.fill_between(rsp_df.index, RSI_ENTRY_HIGH, 100, alpha=0.2, color='red', label='Short RSP Zone')
ax2.fill_between(rsp_df.index, 0, RSI_ENTRY_LOW, alpha=0.2, color='green', label='Long RSP Zone')
ax2.set_ylabel('RSI', fontsize=12)
ax2.set_xlabel('Date', fontsize=12)
ax2.set_title('RSP/VGT Ratio RSI', fontsize=12)
ax2.legend(loc='upper right')
ax2.grid(True, alpha=0.3)
ax2.set_ylim(0, 100)

plt.tight_layout()
plt.savefig('rsp_vgt_final_backtest.png', dpi=150)
print("\n✓ Chart saved to: rsp_vgt_final_backtest.png")
plt.show()

print("="*70)
