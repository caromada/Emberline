"""CONUS Albers (EPSG:5070) so distance parameters are honest meters."""
import pandas as pd
from pyproj import Transformer
from shapely.ops import transform as shp_transform

_FWD = Transformer.from_crs("EPSG:4326", "EPSG:5070", always_xy=True)
_INV = Transformer.from_crs("EPSG:5070", "EPSG:4326", always_xy=True)


def add_projected(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out["x"], out["y"] = _FWD.transform(df["longitude"].values, df["latitude"].values)
    return out


def to_lonlat_geom(geom):
    return shp_transform(_INV.transform, geom)


def to_lonlat_xy(x: float, y: float) -> tuple[float, float]:
    return _INV.transform(x, y)
