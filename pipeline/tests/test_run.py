import json
import pathlib

import numpy as np
import pandas as pd

from emberline.config import Config
from emberline.firms import parse_firms_csv
from emberline.run import run_for_date


def _synthetic_csv(tmp_path):
    rows = []
    rng = np.random.default_rng(3)
    for day, (n, spread) in enumerate([(12, 0.004), (25, 0.009), (45, 0.016)]):
        d = f"2026-08-{20 + day:02d}"
        pts = rng.normal([40.65, -122.38], spread, (n, 2))
        for lat, lon in pts:
            rows.append([lat, lon, 345.0, d, "0912", "N", "VIIRS", "n", "2.0NRT", 15.0, "N"])
    df = pd.DataFrame(rows, columns=["latitude", "longitude", "bright_ti4", "acq_date",
                                     "acq_time", "satellite", "instrument", "confidence",
                                     "version", "frp", "daynight"])
    path = tmp_path / "detections.csv"
    df.to_csv(path, index=False)
    return path


def test_three_day_run(tmp_path):
    csv = _synthetic_csv(tmp_path)
    detections = parse_firms_csv(csv.read_text())
    cfg = Config(data_dir=str(tmp_path / "data"))
    for d in ["2026-08-20", "2026-08-21", "2026-08-22"]:
        run_for_date(cfg, d, detections)

    data = pathlib.Path(cfg.data_dir)
    fires = json.loads((data / "fires.json").read_text())
    assert len(fires["fires"]) == 1
    fire = fires["fires"][0]
    assert fire["fire_id"] == "F0001"
    assert fire["first_seen"] == "2026-08-20" and fire["last_seen"] == "2026-08-22"
    assert fire["area_ha"] > 0 and fire["growth_24h_ha"] > 0
    assert fire["cumulative_ha"] >= fire["area_ha"]  # union of history covers today
    assert len(fire["history"]) == 3 and len(fire["track"]) == 3

    perim = json.loads((data / "perimeters" / "2026-08-22.geojson").read_text())
    assert perim["features"][0]["properties"]["fire_id"] == "F0001"
    assert (data / "detections" / "2026-08-22.geojson").exists()
    assert "2026-08-20" in json.loads((data / "index.json").read_text())["dates"]
