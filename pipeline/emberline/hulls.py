"""Perimeter estimation.

Convex hulls overstate two-armed fires badly (they bridge unburned terrain
between arms), so we use shapely's concave hull and then buffer by half a
VIIRS pixel to represent detection footprint rather than point samples.
"""
import pandas as pd
import shapely
from shapely.geometry import MultiPoint


def build_perimeters(df: pd.DataFrame, hull_ratio: float, pixel_buffer_m: float) -> list[dict]:
    perimeters = []
    for cluster_id, grp in df.groupby("cluster"):
        mp = MultiPoint(list(zip(grp["x"], grp["y"])))
        hull = shapely.concave_hull(mp, ratio=hull_ratio)
        geom = shapely.make_valid(hull.buffer(pixel_buffer_m))
        perimeters.append(
            {
                "cluster": int(cluster_id),
                "geom": geom,
                "area_ha": geom.area / 10_000.0,
                "frp_sum": float(grp["frp"].sum()),
                "n_detections": int(len(grp)),
                "centroid_xy": (geom.centroid.x, geom.centroid.y),
            }
        )
    return perimeters
