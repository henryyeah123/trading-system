#!/usr/bin/env python3
"""Download VIX data for sentiment filtering."""

import pandas as pd
from pipeline.alpaca import get_rest, save_bars, clean_market_data, _parse_timeframe, _normalize_bars, _to_rfc3339

api = get_rest()

# Define date range: 2024-01-01 to 2025-12-31
start = pd.Timestamp("2024-01-01", tz="UTC")
end = pd.Timestamp("2025-12-31", tz="UTC")

print(f"Downloading VIX data from {start.date()} to {end.date()}")

# Download VIX
print("\nDownloading VIX...")
vix_bars = api.get_bars(
    "VIX",
    _parse_timeframe("1Day"),
    start=_to_rfc3339(start),
    end=_to_rfc3339(end),
    limit=10000,
    feed="iex"
).df
vix_df = _normalize_bars(vix_bars, "VIX")
print(f"Got {len(vix_df)} VIX bars")

vix_raw = save_bars(vix_df, "VIX", "1Day", "stock")
vix_clean = clean_market_data(vix_raw)
print(f"Saved to: {vix_clean}")

print("\n✅ VIX download complete!")
