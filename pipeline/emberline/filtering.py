"""Detection quality filters. VIIRS confidence is categorical: l / n / h."""
import pandas as pd


def drop_low_confidence(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df
    return df[df["confidence"].astype(str).str.lower() != "l"].reset_index(drop=True)
