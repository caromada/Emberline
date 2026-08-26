import pandas as pd
from shapely.geometry import Point

from emberline.projection import add_projected, to_lonlat_geom


def test_roundtrip():
    df = pd.DataFrame({"longitude": [-122.38], "latitude": [40.65]})
    out = add_projected(df)
    assert {"x", "y"} <= set(out.columns)
    back = to_lonlat_geom(Point(out["x"].iloc[0], out["y"].iloc[0]))
    assert abs(back.x - -122.38) < 1e-6 and abs(back.y - 40.65) < 1e-6


def test_meters_scale():
    # ~0.01 deg longitude at 40N is ~850m; projected distance must be in that range
    df = add_projected(
        pd.DataFrame({"longitude": [-122.38, -122.37], "latitude": [40.65, 40.65]})
    )
    dx = abs(df["x"].iloc[1] - df["x"].iloc[0])
    assert 700 < dx < 1000
