"""Central tunables. Every number that affects output quality lives here."""
from dataclasses import dataclass
import os

CONUS_BBOX = "-125,24,-66,50"  # west,south,east,north


@dataclass(frozen=True)
class Config:
    firms_key: str | None = None
    sources: tuple[str, ...] = ("VIIRS_SNPP_NRT", "VIIRS_NOAA20_NRT")
    bbox: str = CONUS_BBOX
    day_range: int = 2                 # days of FIRMS history per fetch
    eps_m: float = 1500.0              # DBSCAN neighborhood (meters, EPSG:5070)
    min_samples: int = 3
    hull_ratio: float = 0.25           # concave_hull ratio; swept 0.25-0.7 against
                                       # n=20 NIFC perimeters >=1000 ha: 0.25 -> 40%
                                       # median area error, 0.7 (near-convex) -> 48%
    pixel_buffer_m: float = 187.5      # half a 375 m VIIRS pixel
    iou_threshold: float = 0.10        # min IoU to call two perimeters the same fire
    max_gap_days: int = 3              # cloud-cover tolerance before a fire ID retires
    static_window_days: int = 90
    static_day_fraction: float = 0.60  # >60% of window days burning => industrial source
    cell_size_m: float = 375.0
    data_dir: str = "data"

    @classmethod
    def from_env(cls) -> "Config":
        return cls(firms_key=os.environ.get("FIRMS_MAP_KEY"))
