"""Orchestrator: one call per (config, date) — from cron or backfill."""
import argparse
from dataclasses import replace

import pandas as pd
from shapely.geometry import Point, shape

from .clustering import cluster_detections
from .config import Config
from .filtering import drop_low_confidence
from .firms import fetch_detections, parse_firms_csv
from .hulls import build_perimeters
from .identity import FireRecord, match_day
from .metrics import compute_growth
from .projection import add_projected, to_lonlat_geom, to_lonlat_xy
from .static_mask import build_static_mask, drop_static_sources
from .store import LocalStore, feature


def load_detections(cfg: Config, input_csv: str | None) -> pd.DataFrame:
    if input_csv:
        with open(input_csv) as fh:
            return parse_firms_csv(fh.read())
    return fetch_detections(cfg.firms_key, cfg.sources, cfg.bbox, cfg.day_range)


def run_for_date(cfg: Config, day: str, detections: pd.DataFrame) -> None:
    store = LocalStore(cfg.data_dir)
    state = store.load_state()

    history = detections[detections["acq_date"] <= day]  # trailing window for the mask
    df = drop_low_confidence(detections[detections["acq_date"] == day])
    if df.empty:
        store.update_index(day)
        return

    df = add_projected(df)
    mask = build_static_mask(add_projected(drop_low_confidence(history)),
                             cfg.static_window_days, cfg.static_day_fraction,
                             cfg.cell_size_m)
    df = drop_static_sources(df, mask, cfg.cell_size_m)
    df = cluster_detections(df, cfg.eps_m, cfg.min_samples)
    if df.empty:
        store.update_index(day)
        return
    perims = build_perimeters(df, cfg.hull_ratio, cfg.pixel_buffer_m)

    prev = [
        (FireRecord(**r), shape(state["history"][r["fire_id"]][-1]["geom"]))
        for r in state["records"]
        if r["fire_id"] in state["history"]
    ]
    result = match_day(prev, [p["geom"] for p in perims], today=day,
                       iou_threshold=cfg.iou_threshold,
                       max_gap_days=cfg.max_gap_days,
                       next_serial=state["next_serial"])

    merged_away = {r.fire_id for r in result.records if r.merged_into}
    perim_features, fires_summary = [], []
    for fid, p in zip(result.assignments, perims):
        hist = [h for h in state["history"].get(fid, []) if h["date"] != day]  # rerun-safe
        hist.append({"date": day, "area_ha": p["area_ha"],
                     "cx": p["centroid_xy"][0], "cy": p["centroid_xy"][1],
                     "geom": p["geom"].__geo_interface__})
        state["history"][fid] = hist
        growth = compute_growth(hist)
        rec = next(r for r in result.records if r.fire_id == fid)
        lon, lat = to_lonlat_xy(*p["centroid_xy"])
        props = {"fire_id": fid, "date": day, "area_ha": round(p["area_ha"], 1),
                 "frp_sum": round(p["frp_sum"], 1), "n_detections": p["n_detections"],
                 "first_seen": rec.first_seen, "last_seen": rec.last_seen,
                 "centroid": [round(lon, 5), round(lat, 5)],
                 "history": [{"date": h["date"], "area_ha": round(h["area_ha"], 1)}
                             for h in hist],
                 "track": [list(to_lonlat_xy(h["cx"], h["cy"])) for h in hist],
                 **{k: (round(v, 2) if isinstance(v, float) else v)
                    for k, v in growth.items()}}
        perim_features.append(feature(to_lonlat_geom(p["geom"]), props))
        fires_summary.append(props)

    det_features = [
        feature(Point(r.longitude, r.latitude),
                {"frp": float(r.frp), "date": day,
                 "daynight": getattr(r, "daynight", "N")})
        for r in df.itertuples()
    ]

    state["records"] = [vars(r) for r in result.records]
    state["next_serial"] = result.next_serial
    state["events"].extend(list(e) for e in result.events)

    store.write_geojson("perimeters", day, perim_features)
    store.write_geojson("detections", day, det_features)
    active = [f for f in fires_summary if f["fire_id"] not in merged_away]
    store.write_fires_summary(sorted(active, key=lambda f: f["area_ha"], reverse=True))
    store.save_state(state)
    store.update_index(day)


def main() -> None:
    ap = argparse.ArgumentParser(description="Emberline ingest")
    ap.add_argument("--date", help="YYYY-MM-DD (default: latest in feed)")
    ap.add_argument("--input-csv", help="offline CSV instead of FIRMS API")
    ap.add_argument("--backfill", action="store_true",
                    help="run every date present in the input")
    ap.add_argument("--data-dir", default="data")
    ap.add_argument("--static-window-days", type=int,
                    help="override the trailing window for the static-source mask"
                         " (useful for short offline datasets)")
    ap.add_argument("--day-range", type=int,
                    help="days of FIRMS history to fetch per run (max 10)")
    args = ap.parse_args()

    cfg = replace(Config.from_env(), data_dir=args.data_dir)
    if args.static_window_days:
        cfg = replace(cfg, static_window_days=args.static_window_days)
    if args.day_range:
        cfg = replace(cfg, day_range=min(args.day_range, 10))
    df = load_detections(cfg, args.input_csv)
    if df.empty:
        raise SystemExit("no detections returned")
    dates = sorted(df["acq_date"].unique())
    targets = dates if args.backfill else [args.date or dates[-1]]
    for day in targets:
        run_for_date(cfg, day, df)
        print(f"ingested {day}")


if __name__ == "__main__":
    main()
