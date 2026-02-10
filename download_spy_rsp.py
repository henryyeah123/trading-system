#!/usr/bin/env python3
"""Download SPY and RSP daily data for backtesting."""

from pipeline.alpaca import fetch_stock_bars, save_bars, clean_market_data

# Download SPY daily data (2024-2025)
print("Downloading SPY daily data...")
spy_df = fetch_stock_bars(
    symbol="SPY",
    timeframe="1Day",
    limit=500,  # ~2 years of daily bars
    feed="iex"
)
print(f"Downloaded {len(spy_df)} SPY bars")

# Save and clean SPY
spy_raw = save_bars(spy_df, "SPY", "1Day", "stock")
print(f"Saved raw data to: {spy_raw}")
spy_clean = clean_market_data(spy_raw)
print(f"Cleaned data saved to: {spy_clean}")

# Download RSP daily data
print("\nDownloading RSP daily data...")
rsp_df = fetch_stock_bars(
    symbol="RSP",
    timeframe="1Day",
    limit=500,
    feed="iex"
)
print(f"Downloaded {len(rsp_df)} RSP bars")

# Save and clean RSP
rsp_raw = save_bars(rsp_df, "RSP", "1Day", "stock")
print(f"Saved raw data to: {rsp_raw}")
rsp_clean = clean_market_data(rsp_raw)
print(f"Cleaned data saved to: {rsp_clean}")

print("\n✅ Download complete!")

