"""Persistent heat sources (gas flares, refineries, steel mills) trip VIIRS on
nearly every pass forever. Any 375 m cell hot on >60% of days in a trailing
90-day window is not a wildfire.
"""
import numpy as np
import pandas as pd


def _cells(df: pd.DataFrame, cell_size_m: float) -> pd.Series:
    cx = np.floor(df["x"].values / cell_size_m).astype("int64")
    cy = np.floor(df["y"].values / cell_size_m).astype("int64")
    return pd.Series(list(zip(cx, cy)), index=df.index)


def build_static_mask(history: pd.DataFrame, window_days: int, day_fraction: float,
                      cell_size_m: float) -> set[tuple[int, int]]:
    if history.empty:
        return set()
    df = history.copy()
    df["cell"] = _cells(df, cell_size_m)
    days_hot = df.groupby("cell")["acq_date"].nunique()
    return set(days_hot[days_hot / window_days > day_fraction].index)


def drop_static_sources(df: pd.DataFrame, mask: set, cell_size_m: float) -> pd.DataFrame:
    if df.empty or not mask:
        return df
    keep = ~_cells(df, cell_size_m).isin(mask)
    return df[keep].reset_index(drop=True)
