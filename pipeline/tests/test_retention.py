import json

from emberline.run import prune_state
from emberline.store import LocalStore


def _state():
    rec = lambda fid, last, merged=None: {  # noqa: E731
        "fire_id": fid, "first_seen": "2026-08-01", "last_seen": last,
        "merged_into": merged}
    return {
        "records": [rec("F1", "2026-09-28"),            # live
                    rec("F2", "2026-09-18"),            # retired, remembered
                    rec("F3", "2026-08-01"),            # forgotten
                    rec("F4", "2026-09-28", "F1")],     # merged away
        "history": {fid: [{"date": "x"}] for fid in ("F1", "F2", "F3", "F4")},
        "events": [["merge", "F4", "F1", "2026-09-28"],
                   ["merge", "F9", "F8", "2026-08-01"]],
        "next_serial": 42,
    }


def test_prune_state_keeps_only_live_geometry():
    s = _state()
    prune_state(s, "2026-09-28", retire_days=7, forget_days=30)
    assert [r["fire_id"] for r in s["records"]] == ["F1", "F2", "F4"]
    assert set(s["history"]) == {"F1"}
    assert s["events"] == [["merge", "F4", "F1", "2026-09-28"]]
    assert s["next_serial"] == 42  # ids are never reused


def test_store_prune_bounds_files_and_index(tmp_path):
    store = LocalStore(str(tmp_path))
    days = [f"2026-09-{d:02d}" for d in range(1, 11)]
    for d in days:
        store.write_geojson("perimeters", d, [])
        store.write_geojson("detections", d, [])
        store.update_index(d)
    store.prune(keep_perimeter_days=3, keep_detection_days=5)
    assert sorted(p.stem for p in (tmp_path / "perimeters").glob("*.geojson")) == days[-3:]
    assert len(list((tmp_path / "detections").glob("*.geojson"))) == 5
    assert json.loads((tmp_path / "index.json").read_text())["dates"] == days[-3:]
