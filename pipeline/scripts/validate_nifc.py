"""Accuracy vs official perimeters. Produces the README table.

Pairs our latest perimeters with overlapping NIFC/WFIGS perimeters (IoU > 0.05
in EPSG:5070) and reports per-fire IoU + signed area error, plus the median
absolute error. Also snapshots the official perimeters for the compare layer.

Usage: python pipeline/scripts/validate_nifc.py [--data-dir data]
"""
import argparse
import json
import pathlib
import statistics
import sys

from pyproj import Transformer
from shapely.geometry import shape
from shapely.ops import transform as shp_transform

sys.path.insert(0, str(pathlib.Path(__file__).parents[1]))
from emberline.nifc import fetch_current_perimeters

_FWD = Transformer.from_crs("EPSG:4326", "EPSG:5070", always_xy=True)


def to_5070(geom):
    # official WFIGS polygons are routinely self-intersecting; repair first
    import shapely
    return shapely.make_valid(shp_transform(_FWD.transform, shapely.make_valid(geom)))


SEASON_DAYS = 120


def update_season(root: pathlib.Path, day: str, rows: list) -> dict:
    """Upsert today's per-incident scores into a season-to-date record.

    A fire is only scoreable while it is still burning, so a table of today's
    matches shrinks toward nothing as the season winds down. Each incident is
    scored at its most completely observed moment: the comparison where our
    tracked footprint was largest. Later comparisons tend to see only a remnant
    after a detection gap retires the fire's IDs, which measures tracking
    continuity rather than perimeter accuracy. The selection uses only our own
    area, never agreement with the official shape, so it cannot cherry-pick.
    """
    from datetime import date as _date

    path = root / "validation_history.json"
    season = json.loads(path.read_text()) if path.exists() else {}
    for ids, incident, our_ha, nifc_ha, iou, err, _first in rows:
        prev = season.get(incident)
        if incident and incident != "?" and (prev is None or our_ha >= prev["our_ha"]):
            season[incident] = {"ids": ids, "our_ha": round(our_ha, 1),
                                "nifc_ha": round(nifc_ha, 1), "iou": round(iou, 3),
                                "err": round(err, 1), "date": day}
    today = _date.fromisoformat(day)
    season = {k: v for k, v in season.items()
              if (today - _date.fromisoformat(v["date"])).days <= SEASON_DAYS}
    path.write_text(json.dumps(season, indent=1, sort_keys=True))
    return season


def render(season: dict) -> list[str]:
    rows = sorted(season.items(), key=lambda kv: -kv[1]["nifc_ha"])
    lines = [f"Season to date (last {SEASON_DAYS} days): each incident scored at its most completely"
             " observed moment, the comparison where Emberline's tracked footprint was largest.",
             "",
             "| NIFC incident | Emberline fire IDs | our ha | NIFC ha | IoU | area err | measured |",
             "|---|---|---:|---:|---:|---:|---|"]
    for name, r in rows:
        lines.append(f"| {name} | {r['ids']} | {r['our_ha']:.0f} | {r['nifc_ha']:.0f}"
                     f" | {r['iou']:.2f} | {r['err']:+.0f}% | {r['date']} |")
    errors = [abs(r["err"]) for _, r in rows]
    large = [abs(r["err"]) for _, r in rows if r["nifc_ha"] >= 1000]
    if not errors:
        return lines + ["", "No overlapping official perimeters recorded yet."]
    lines.append(f"\n**Median |area error|, all incidents: {statistics.median(errors):.0f}%** (n={len(errors)})")
    if large:
        lines.append(f"\n**Incidents ≥ 1,000 ha: median |area error| {statistics.median(large):.0f}%**"
                     f" (n={len(large)}) · below that, the 375 m sensor footprint dominates"
                     f" the area of small burns")
    return lines


def write_compare_layer(root: pathlib.Path, day: str, features: list[dict]) -> None:
    """Snapshot the official perimeters for the map's NIFC toggle.

    Only perimeters that touch one of our fires are kept (the full CONUS layer
    is ~20 MB), simplified to ~50 m, and only the latest snapshot is retained:
    the frontend never reads older ones and each copy would live in git forever.
    """
    import shapely
    from shapely.geometry import mapping

    slim = []
    for g in features:
        geom = shapely.make_valid(shape(g["geometry"])).simplify(
            0.0005, preserve_topology=True)
        geom = shapely.set_precision(geom, 1e-5)
        if geom.is_empty:
            continue
        slim.append({"type": "Feature", "geometry": mapping(geom),
                     "properties": {"name": g["properties"].get("poly_IncidentName")}})
    out_dir = root / "nifc"
    out_dir.mkdir(exist_ok=True)
    for old in out_dir.glob("*.geojson"):
        old.unlink()
    (out_dir / f"{day}.geojson").write_text(
        json.dumps({"type": "FeatureCollection", "features": slim},
                   separators=(",", ":")))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-dir", default="data")
    args = ap.parse_args()
    root = pathlib.Path(args.data_dir)
    dates = json.loads((root / "index.json").read_text())["dates"]
    ours = json.loads((root / "perimeters" / f"{dates[-1]}.geojson").read_text())
    if not ours["features"]:
        print("no perimeters to validate")
        return

    # query only around our fires: the CONUS-wide layer blows the transfer limit
    from shapely.geometry import GeometryCollection
    extent = GeometryCollection(
        [shape(f["geometry"]) for f in ours["features"]]).bounds
    pad = 0.5
    bbox = (f"{extent[0] - pad},{extent[1] - pad},"
            f"{extent[2] + pad},{extent[3] + pad}")
    nifc = fetch_current_perimeters(bbox)

    theirs_5070 = [(g, to_5070(shape(g["geometry"]))) for g in nifc["features"]]

    # NIFC perimeters are CUMULATIVE burned area; a single day of detections is
    # only the active front. Compare the union of each fire's whole perimeter
    # history (stored in EPSG:5070 in the registry) against the official shape.
    import shapely
    from shapely.ops import unary_union

    # incident-centric: one incident can be covered by several of our fire IDs
    # (splits across swath gaps), so our estimate of an incident's footprint is
    # the union of every tracked fire that touches it
    state = json.loads((root / "state.json").read_text())
    footprints = []
    for f in ours["features"]:
        fid = f["properties"]["fire_id"]
        hist = state["history"].get(fid, [])
        if not hist:
            continue
        geom = shapely.make_valid(
            unary_union([shapely.make_valid(shape(h["geom"])) for h in hist]))
        first_seen = next((r["first_seen"] for r in state["records"]
                           if r["fire_id"] == fid), dates[0])
        footprints.append((fid, geom, first_seen))

    rows = []
    names: dict[str, str] = {}
    compare_layer = []
    for g, official in theirs_5070:
        ob = official.bounds
        mine_parts = [
            (fid, geom, first) for fid, geom, first in footprints
            if not (geom.bounds[0] > ob[2] or geom.bounds[2] < ob[0]
                    or geom.bounds[1] > ob[3] or geom.bounds[3] < ob[1])
            and geom.intersects(official)
        ]
        if not mine_parts:
            continue
        compare_layer.append(g)
        mine = shapely.make_valid(unary_union([geom for _, geom, _ in mine_parts]))
        inter = mine.intersection(official).area
        iou = inter / mine.union(official).area if inter else 0.0
        if iou <= 0.05:
            continue
        err = (mine.area - official.area) / official.area * 100
        ids = "+".join(fid for fid, _, _ in mine_parts[:3])
        earliest = min(first for _, _, first in mine_parts)
        incident = g["properties"].get("poly_IncidentName", "?")
        rows.append((ids, incident,
                     mine.area / 10_000, official.area / 10_000, iou, err,
                     earliest))
        if incident and incident != "?":
            for fid, _, _ in mine_parts:
                names[fid] = incident
    (root / "names.json").write_text(json.dumps(names, separators=(",", ":")))
    write_compare_layer(root, dates[-1], compare_layer)
    season = update_season(root, dates[-1], rows)
    lines = render(season)
    out = "\n".join(lines)
    (root / "validation.md").write_text(out + "\n")
    print(out)


if __name__ == "__main__":
    main()
