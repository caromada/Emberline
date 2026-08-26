import pandas as pd

from emberline.static_mask import build_static_mask, drop_static_sources


def _detections(x, y, n_days, start="2026-05-01"):
    dates = pd.date_range(start, periods=n_days).strftime("%Y-%m-%d")
    return pd.DataFrame({"x": x, "y": y, "acq_date": dates})


def test_flare_masked_fire_kept():
    flare = _detections(100.0, 100.0, 80)          # 80 of 90 days => masked
    fire = _detections(500_000.0, 500_000.0, 10)   # real fire => kept
    df = pd.concat([flare, fire], ignore_index=True)
    mask = build_static_mask(df, window_days=90, day_fraction=0.60, cell_size_m=375.0)
    out = drop_static_sources(df, mask, cell_size_m=375.0)
    assert set(out["x"]) == {500_000.0}
    assert len(mask) == 1
