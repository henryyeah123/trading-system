#!/usr/bin/env python3
"""
Download historical data for backtesting 2016-2020.

Usage:
    py download_backtest_2016_2020.py
    py download_backtest_2016_2020.py --symbol SPY

Then run the backtest:
    py run_backtest.py --csv data/AAPL_1Day_stock_alpaca_clean.csv --strategy ma --plot
"""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from pipeline.alpaca import (
    get_rest,
    save_bars,
    clean_market_data,
    _parse_timeframe,
    _normalize_bars,
    _to_rfc3339,
)

DATA_DIR = Path("data")
START = pd.Timestamp("2016-01-01", tz="UTC")
END = pd.Timestamp("2020-12-31", tz="UTC")
TIMEFRAME = "1Day"
LIMIT = 10000


def main() -> None:
    parser = argparse.ArgumentParser(description="Download 2016-2020 data for backtesting.")
    parser.add_argument("--symbol", default="AAPL", help="Symbol to download (default: AAPL)")
    parser.add_argument("--timeframe", default=TIMEFRAME, help="Bar size: 1Day, 1Hour, etc. (default: 1Day)")
    args = parser.parse_args()

    api = get_rest()
    symbol = args.symbol.upper()
    timeframe = args.timeframe

    print(f"Downloading {symbol} {timeframe} from {START.date()} to {END.date()}...")

    bars = api.get_bars(
        symbol,
        _parse_timeframe(timeframe),
        start=_to_rfc3339(START),
        end=_to_rfc3339(END),
        limit=LIMIT,
        feed="iex",
    ).df

    if bars is None or bars.empty:
        print("No data returned. Alpaca free data may not include 2016-2020 for this symbol.")
        print("Try a more recent range or check https://alpaca.markets/docs/market-data.")
        return

    df = _normalize_bars(bars, symbol)
    print(f"Got {len(df)} bars")

    raw_path = save_bars(df, symbol, timeframe, "stock")
    clean_path = clean_market_data(raw_path)

    print(f"Saved: {clean_path}")
    print("\nRun backtest with:")
    print(f"  py run_backtest.py --csv {clean_path} --strategy ma --plot")


if __name__ == "__main__":
    main()
