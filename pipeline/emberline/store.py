"""Local file store: per-day GeoJSON snapshots + a fire registry.

Layout (all frontend-facing geometry in EPSG:4326):
  data/index.json                 {"dates": [...], "updated_at": "..."}
  data/state.json                 registry + per-fire history (internal, EPSG:5070 centroids)
  data/fires.json                 current summary per active fire (for panels)
  data/perimeters/<date>.geojson  perimeter polygons w/ metrics
  data/detections/<date>.geojson  raw detection points w/ frp
  data/nifc/<date>.geojson        official perimeter snapshots (compare layer)
"""
import json
import pathlib
from datetime import datetime, timezone

from shapely.geometry import mapping


class LocalStore:
    def __init__(self, data_dir: str):
        self.root = pathlib.Path(data_dir)
        (self.root / "perimeters").mkdir(parents=True, exist_ok=True)
        (self.root / "detections").mkdir(parents=True, exist_ok=True)
        (self.root / "nifc").mkdir(parents=True, exist_ok=True)

    def load_state(self) -> dict:
        p = self.root / "state.json"
        if p.exists():
            return json.loads(p.read_text())
        return {"records": [], "next_serial": 1, "history": {}, "events": []}

    def save_state(self, state: dict) -> None:
        self._write(self.root / "state.json", state)

    def write_geojson(self, kind: str, day: str, features: list[dict]) -> None:
        self._write(self.root / kind / f"{day}.geojson",
                    {"type": "FeatureCollection", "features": features})

    def write_fires_summary(self, fires: list[dict]) -> None:
        self._write(self.root / "fires.json", {"fires": fires, "updated_at": _now()})

    def update_index(self, day: str) -> None:
        p = self.root / "index.json"
        idx = json.loads(p.read_text()) if p.exists() else {"dates": []}
        if day not in idx["dates"]:
            idx["dates"] = sorted(idx["dates"] + [day])
        idx["updated_at"] = _now()
        self._write(p, idx)

    @staticmethod
    def _write(path: pathlib.Path, obj: dict) -> None:
        tmp = path.with_suffix(path.suffix + ".tmp")
        tmp.write_text(json.dumps(obj, separators=(",", ":"), default=float))
        tmp.replace(path)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def feature(geom_4326, props: dict) -> dict:
    return {"type": "Feature", "geometry": mapping(geom_4326), "properties": props}
