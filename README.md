# Emberline

**Live wildfire perimeter tracking derived from raw satellite thermal detections — updated every 3 hours, no humans in the loop.**

<!-- hero: 12s GIF of the time scrub goes here
![Emberline time scrub](docs/media/scrub.gif)
-->

Official wildfire perimeters lag by hours to days because someone has to draw them. Emberline draws them automatically: it ingests VIIRS 375 m thermal detections from NASA FIRMS, clusters them into fires, fits concave-hull perimeters, tracks each fire's identity from day to day, and computes how fast every fire is growing and which direction it's moving. A toggle overlays the official NIFC perimeter next to Emberline's so you can judge the method against ground truth on any fire.

**Live map:** `https://<your-username>.github.io/emberline/` _(after first Pages deploy)_

## What it shows

- **Perimeters** — concave hulls over clustered detections, one polygon per fire per day
- **Growth** — `4,210 ha, +780 ha in 24 h` per fire, from day-over-day perimeter area
- **Spread vectors** — a tapered arrow from each fire's historical centroid to its current one; length encodes km/day
- **Time slider** — scrub the fire's whole history; perimeters and arrows update in place
- **Official comparison** — NIFC/WFIGS interagency perimeters as a fade-in overlay

## Accuracy vs. official perimeters

The pipeline snapshots WFIGS perimeters on every run and scores itself (IoU and signed area error per fire, matched by intersection-over-union in an equal-area projection). The current table lives in [`data/validation.md`](data/validation.md) and is refreshed by the ingest workflow.

> The repo currently ships with a synthetic demo dataset so the frontend runs with zero setup. The accuracy table becomes meaningful after the first real FIRMS ingest (see **Going live** below).

## Architecture

```
GitHub Actions cron (every 3 h)
        │
        ▼
  Python ingest (pipeline/)
    fetch FIRMS CSV (VIIRS SNPP + NOAA-20, CONUS bbox)
    drop low-confidence detections
    drop persistent heat sources (static-source mask)
    reproject EPSG:4326 → EPSG:5070 (CONUS Albers, meters)
    DBSCAN cluster (eps 1500 m, min_samples 3)
    concave hull per cluster + half-pixel buffer
    match clusters to known fires by IoU (merges, splits, cloud gaps)
    compute area, 24 h growth, centroid displacement, bearing
        │
        ▼
  data/ — per-day GeoJSON snapshots + fire registry (committed each run)
  PostGIS mirror (optional, DATABASE_URL)
        │
        ▼
  Next.js + MapLibre GL + deck.gl (web/) — time slider, spread arrows,
  FRP-ramp detections, NIFC comparison layer
```

## What was hard

**Convex hulls are wrong, and everyone uses them anyway.** A fire burning up two canyon arms produces a convex hull that swallows the unburned ridge between them. On a two-armed test cluster, the concave hull comes in at ~27 % of the convex hull's area — the convex version overstates the fire by nearly 4×. Emberline uses `shapely.concave_hull` with the ratio parameter held in one config constant, tuned against official perimeters, plus a half-pixel (187.5 m) buffer so point samples become detection footprints. One found edge case: perfectly collinear detections degenerate the Delaunay triangulation the hull is built on — real detections are never collinear, but the tests now cover it.

**Cluster identity across time.** DBSCAN labels mean nothing from one run to the next, but "this fire grew 780 ha" requires knowing today's cluster 7 is yesterday's cluster 4. Emberline matches perimeters by intersection-over-union with greedy 1:1 assignment, then handles the messy cases explicitly: two fires that merge collapse into the **older** ID with a recorded merge event; a fire hidden by a day of cloud cover matches again for up to 3 days before its ID retires; a small fast-moving day-one fire can legitimately fail its IoU match — that shows up as an ID break, which is the honest failure mode.

**False positives are forever.** VIIRS flags gas flares, refineries, and steel mills on every single pass. Without a filter, the map grows a permanent "wildfire" over every oil field in Kern County. Emberline builds a static-source mask: any 375 m grid cell hot on more than 60 % of days in a trailing 90-day window is industrial, not wildfire, and its detections are dropped before clustering.

## Run it locally

Zero credentials needed — a synthetic 8-day fire season ships with the repo:

```bash
python3 -m venv .venv && .venv/bin/pip install -r pipeline/requirements.txt
cd pipeline && ../.venv/bin/pytest          # 21 tests
cd .. && make demo                          # regenerate demo data
cd web && npm install && npm run dev        # http://localhost:3000
```

## Going live

1. Get a free FIRMS map key: https://firms.modaps.eosdis.nasa.gov/api/area/
2. Add a repo secret `FIRMS_MAP_KEY` (and optionally `DATABASE_URL` for the PostGIS mirror — schema in `pipeline/schema.sql`)
3. In repo **Settings → Pages**, set the source to **GitHub Actions**
4. The `deploy` workflow publishes `web/` to GitHub Pages on every push; the `ingest` workflow runs every 3 h, commits refreshed `data/`, and re-triggers the deploy
5. To replace the demo dataset with real detections: `rm -rf data`, commit, and run the `ingest` workflow once manually

## Repository layout

```
pipeline/   Python ingest: clustering, hulls, identity, metrics (fully unit-tested)
data/       per-day GeoJSON snapshots + fire registry (the API surface)
web/        Next.js + MapLibre + deck.gl frontend
.github/    3-hour ingest cron
```
