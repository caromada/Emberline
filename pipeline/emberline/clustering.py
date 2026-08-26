"""Spatial clustering of detections into candidate fires."""
import pandas as pd
from sklearn.cluster import DBSCAN


def cluster_detections(df: pd.DataFrame, eps_m: float, min_samples: int) -> pd.DataFrame:
    if df.empty:
        return df.assign(cluster=pd.Series(dtype="int64"))
    labels = DBSCAN(eps=eps_m, min_samples=min_samples).fit(df[["x", "y"]].values).labels_
    out = df.copy()
    out["cluster"] = labels
    return out[out["cluster"] >= 0].reset_index(drop=True)
