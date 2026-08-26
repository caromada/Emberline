import numpy as np
import pandas as pd

from emberline.clustering import cluster_detections


def _df(points):
    return pd.DataFrame(points, columns=["x", "y"])


def test_two_separated_fires_and_noise():
    rng = np.random.default_rng(7)
    fire_a = rng.normal([0, 0], 400, (20, 2))
    fire_b = rng.normal([50_000, 0], 400, (20, 2))
    lone = np.array([[200_000, 200_000]])
    df = _df(np.vstack([fire_a, fire_b, lone]))
    out = cluster_detections(df, eps_m=1500, min_samples=3)
    assert out["cluster"].nunique() == 2
    assert len(out) == 40  # noise point dropped


def test_empty_frame():
    out = cluster_detections(_df(np.empty((0, 2))), eps_m=1500, min_samples=3)
    assert out.empty
