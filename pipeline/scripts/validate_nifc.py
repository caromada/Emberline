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
    (root / "nifc").mkdir(exist_ok=True)
    (root / "nifc" / f"{dates[-1]}.geojson").write_text(json.dumps(nifc))

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
        mine = shapely.make_valid(unary_union([geom for _, geom, _ in mine_parts]))
        inter = mine.intersection(official).area
        iou = inter / mine.union(official).area if inter else 0.0
        if iou <= 0.05:
            continue
        err = (mine.area - official.area) / official.area * 100
        ids = "+".join(fid for fid, _, _ in mine_parts[:3])
        earliest = min(first for _, _, first in mine_parts)
        rows.append((ids, g["properties"].get("poly_IncidentName", "?"),
                     mine.area / 10_000, official.area / 10_000, iou, err,
                     earliest))
    rows = sorted(rows, key=lambda r: -r[3])
    errors = [abs(r[5]) for r in rows]

    lines = ["| ours | NIFC incident | our ha | NIFC ha | IoU | area err |",
             "|---|---|---:|---:|---:|---:|"]
    for r in rows:
        lines.append(f"| {r[0]} | {r[1]} | {r[2]:.0f} | {r[3]:.0f} | {r[4]:.2f} | {r[5]:+.0f}% |")
    if errors:
        large = [abs(r[5]) for r in rows if r[3] >= 1000]
        # a fire already burning when our data window opened has most of its
        # footprint unobserved; only fires whose ignition we watched are a
        # fair test of the perimeter method
        first_day = dates[0]
        observed = [abs(r[5]) for r in rows if r[6] > first_day]
        lines.append(f"\n**Median |area error|: {statistics.median(errors):.0f}%** (n={len(errors)})")
        if large:
            lines.append(
                f"\n**Fires ≥ 1,000 ha: median |area error| {statistics.median(large):.0f}%**"
                f" (n={len(large)}) · below that, a 375 m sensor footprint dominates"
                f" the area of small burns")
        if observed:
            lines.append(
                f"\n**Fires whose ignition falls inside the data window:"
                f" median |area error| {statistics.median(observed):.0f}%**"
                f" (n={len(observed)}) · fires already burning when tracking began"
                f" have unobserved history and read low by construction")
    else:
        lines.append("\nNo overlapping official perimeters found for this date.")
    out = "\n".join(lines)
    (root / "validation.md").write_text(out + "\n")
    print(out)


if __name__ == "__main__":
    main()
