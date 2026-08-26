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
    return shp_transform(_FWD.transform, geom)


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
    rows, errors = [], []
    for f in ours["features"]:
        mine = to_5070(shape(f["geometry"]))
        best, best_geom, best_iou = None, None, 0.0
        for g, geom in theirs_5070:
            inter = mine.intersection(geom).area
            iou = inter / mine.union(geom).area if inter else 0.0
            if iou > best_iou:
                best, best_geom, best_iou = g, geom, iou
        if best_iou > 0.05:
            err = (mine.area - best_geom.area) / best_geom.area * 100
            errors.append(abs(err))
            rows.append((f["properties"]["fire_id"],
                         best["properties"].get("poly_IncidentName", "?"),
                         f["properties"]["area_ha"], best_geom.area / 10_000,
                         best_iou, err))

    lines = ["| ours | NIFC incident | our ha | NIFC ha | IoU | area err |",
             "|---|---|---:|---:|---:|---:|"]
    for r in rows:
        lines.append(f"| {r[0]} | {r[1]} | {r[2]:.0f} | {r[3]:.0f} | {r[4]:.2f} | {r[5]:+.0f}% |")
    if errors:
        lines.append(f"\n**Median |area error|: {statistics.median(errors):.0f}%** (n={len(errors)})")
    else:
        lines.append("\nNo overlapping official perimeters found for this date.")
    out = "\n".join(lines)
    (root / "validation.md").write_text(out + "\n")
    print(out)


if __name__ == "__main__":
    main()
