#!/usr/bin/env python3
"""Download historical SPY and RSP data with date ranges."""

import pandas as pd
from pipeline.alpaca import get_rest, save_bars, clean_market_data, _parse_timeframe, _normalize_bars, _to_rfc3339

api = get_rest()

# Define date range: 2024-01-01 to 2025-12-31
start = pd.Timestamp("2024-01-01", tz="UTC")
end = pd.Timestamp("2025-12-31", tz="UTC")

print(f"Downloading data from {start.date()} to {end.date()}")

# Download SPY
print("\nDownloading SPY...")
spy_bars = api.get_bars(
    "SPY",
    _parse_timeframe("1Day"),
    start=_to_rfc3339(start),
    end=_to_rfc3339(end),
    limit=10000,
    feed="iex"
).df
spy_df = _normalize_bars(spy_bars, "SPY")
print(f"Got {len(spy_df)} SPY bars")

spy_raw = save_bars(spy_df, "SPY", "1Day", "stock")
spy_clean = clean_market_data(spy_raw)
print(f"Saved to: {spy_clean}")

# Download RSP
print("\nDownloading RSP...")
rsp_bars = api.get_bars(
    "RSP",
    _parse_timeframe("1Day"),
    start=_to_rfc3339(start),
    end=_to_rfc3339(end),
    limit=10000,
    feed="iex"
).df
rsp_df = _normalize_bars(rsp_bars, "RSP")
print(f"Got {len(rsp_df)} RSP bars")

rsp_raw = save_bars(rsp_df, "RSP", "1Day", "stock")
rsp_clean = clean_market_data(rsp_raw)
print(f"Saved to: {rsp_clean}")

print("\n✅ Historical download complete!")
