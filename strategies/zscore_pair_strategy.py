import numpy as np
import pandas as pd

from strategies.strategy_base import Strategy


class ZScorePairStrategy(Strategy):
    """
    SPY/RSP mean-reversion strategy based on z-score of the SPY/RSP ratio.

    Expected input columns:
      - Close: SPY close
      - rsp_close: RSP close (aligned timestamps)

    Signals:
      - z_score > entry_z: SHORT SPY, LONG RSP (signal = -1)
      - z_score < -entry_z: LONG SPY, SHORT RSP (signal = +1)
      - abs(z_score) < exit_z: CLOSE position (position = 0)
    """

    def __init__(self, lookback: int = 60, entry_z: float = 2.0, exit_z: float = 0.5, position_size: float = 10.0):
        if lookback < 2:
            raise ValueError("lookback must be at least 2.")
        if entry_z <= 0:
            raise ValueError("entry_z must be positive.")
        if exit_z < 0:
            raise ValueError("exit_z must be non-negative.")
        if exit_z >= entry_z:
            raise ValueError("exit_z must be less than entry_z.")
        if position_size <= 0:
            raise ValueError("position_size must be positive.")
        self.lookback = lookback
        self.entry_z = entry_z
        self.exit_z = exit_z
        self.position_size = position_size

    def add_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        if "rsp_close" not in df.columns:
            raise ValueError("ZScorePairStrategy requires a 'rsp_close' column with RSP prices.")

        ratio = df["Close"] / df["rsp_close"]
        mean = ratio.rolling(self.lookback).mean()
        std = ratio.rolling(self.lookback).std()
        z = (ratio - mean) / std.replace(0.0, np.nan)

        df["ratio"] = ratio
        df["ratio_mean"] = mean
        df["ratio_std"] = std
        df["z_score"] = z.replace([np.inf, -np.inf], np.nan).fillna(0.0)
        return df

    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        df["signal"] = 0

        short_spy = df["z_score"] > self.entry_z
        long_spy = df["z_score"] < -self.entry_z

        df.loc[short_spy, "signal"] = -1
        df.loc[long_spy, "signal"] = 1

        df["position"] = df["signal"].replace(0, np.nan).ffill().fillna(0)
        exit_mask = df["z_score"].abs() < self.exit_z
        df.loc[exit_mask, "position"] = 0

        df["target_qty"] = df["position"].abs() * self.position_size

        # Optional per-leg guidance for pair execution.
        df["spy_signal"] = df["position"]
        df["rsp_signal"] = -df["position"]
        df["spy_target_qty"] = df["target_qty"]
        df["rsp_target_qty"] = df["position"].abs() * self.position_size
        return df
