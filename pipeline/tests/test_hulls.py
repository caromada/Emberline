import numpy as np
import pandas as pd
from shapely.geometry import MultiPoint

from emberline.hulls import build_perimeters


def _v_shaped_cluster():
    # two 6km arms meeting at origin, detections scattered ~120m off-axis the
    # way real 375m VIIRS samples land (perfectly collinear points are a
    # degenerate case for Delaunay-based concave hulls and never occur)
    rng = np.random.default_rng(0)
    t = np.arange(0, 6000, 150.0)
    arm1 = np.column_stack([t, t * 0.15]) + rng.normal(0, 120, (len(t), 2))
    arm2 = np.column_stack([t * 0.5, t]) + rng.normal(0, 120, (len(t), 2))
    pts = np.vstack([arm1, arm2])
    return pd.DataFrame({"x": pts[:, 0], "y": pts[:, 1], "cluster": 0, "frp": 10.0})


def test_concave_beats_convex():
    df = _v_shaped_cluster()
    perims = build_perimeters(df, hull_ratio=0.35, pixel_buffer_m=187.5)
    convex = MultiPoint(list(zip(df["x"], df["y"]))).convex_hull.buffer(187.5)
    assert perims[0]["geom"].area < 0.7 * convex.area  # >=30% tighter
    assert perims[0]["n_detections"] == len(df)
    assert perims[0]["frp_sum"] == float(df["frp"].sum())


def test_area_hectares_positive_and_valid():
    df = _v_shaped_cluster()
    p = build_perimeters(df, hull_ratio=0.35, pixel_buffer_m=187.5)[0]
    assert p["geom"].is_valid and p["area_ha"] > 0
