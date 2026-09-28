# Emberline

![tests](https://github.com/caromada/Emberline/actions/workflows/test.yml/badge.svg) ![ingest](https://github.com/caromada/Emberline/actions/workflows/ingest.yml/badge.svg)

**Live wildfire perimeter tracking derived from raw satellite thermal detections — updated every 3 hours, no humans in the loop.**

### 🔥 [Open the live map → caromada.github.io/Emberline](https://caromada.github.io/Emberline/)

<!-- hero: 12s GIF of the time scrub goes here
![Emberline time scrub](docs/media/scrub.gif)
-->

Official wildfire perimeters lag by hours to days because someone has to draw them. Emberline draws them automatically: it ingests VIIRS 375 m thermal detections from NASA FIRMS, clusters them into fires, fits concave-hull perimeters, tracks each fire's identity from day to day, and computes how fast every fire is growing and which direction it's moving. A toggle overlays the official NIFC perimeter next to Emberline's so you can judge the method against ground truth on any fire.

**Live map:** https://caromada.github.io/Emberline/

## What it shows

- **Perimeters** — concave hulls over clustered detections, one polygon per fire per day
- **Growth** — `4,210 ha, +780 ha in 24 h` per fire, from day-over-day perimeter area
- **Spread vectors** — a tapered arrow from each fire's historical centroid to its current one; length encodes km/day
- **Time slider** — scrub the fire's whole history; the cumulative burned footprint grows under the active front
- **Official comparison** — NIFC/WFIGS interagency perimeters as a fade-in overlay, with matched incident names shown on Emberline's fires
- **Shareable state** — `?fire=F0165&date=2026-08-25` deep-links to a specific fire and day

## Accuracy vs. official perimeters

Every ingest compares each tracked fire's cumulative footprint (the union of its whole perimeter history, in an equal-area projection) against the overlapping official WFIGS perimeter, and records the result in a season-to-date table: [`validation.md` on the `data` branch](https://github.com/caromada/Emberline/blob/data/validation.md). Each incident is scored at its most completely observed moment, the comparison where Emberline's tracked footprint was largest. That selection uses only Emberline's own area, never agreement with the official shape, so it can't cherry-pick good results.

**Season to date: median absolute area error of 39% across 30 incidents ≥ 1,000 ha**, with well-tracked fires much tighter (Three Queens +2%, Deer Creek +3%). The hull concavity parameter was tuned against these official perimeters: a ratio of 0.25 scores 40% median error, while a near-convex 0.7 scores 48%.

Known limitations, in order of impact:
- **Tracking gaps.** A fire with no detections for more than 3 days (smoke, cloud, or a smoldering phase) retires its ID; when it flares back up it gets a new ID whose footprint starts from scratch. This, not the hull, drives most large under-reads.
- **Sensor footprint.** Below about 1,000 ha, the 375 m pixel size inflates small burns.
- **Pre-existing fires.** A fire already burning before tracking began has unobserved history and reads low.

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
  data branch — per-day GeoJSON snapshots + fire registry (one fresh commit per run)
  PostGIS mirror (optional, DATABASE_URL)
        │
        ▼
  Next.js + MapLibre GL + deck.gl (web/) — time slider, spread arrows,
  FRP-ramp detections, NIFC comparison layer
```

## What was hard

**Convex hulls are wrong, and everyone uses them anyway.** A fire burning up two canyon arms produces a convex hull that swallows the unburned ridge between them. On a two-armed test cluster, the concave hull comes in at ~27 % of the convex hull's area — the convex version overstates the fire by nearly 4×. The concavity parameter was then tuned against real official perimeters: sweeping it over n=20 NIFC fires ≥ 1,000 ha, the tightest setting (0.25) scores 40 % median area error while a near-convex setting (0.7) scores 48 % — the same direction the geometry predicts. A half-pixel (187.5 m) buffer turns point samples into detection footprints. One found edge case: perfectly collinear detections degenerate the Delaunay triangulation the hull is built on — real detections are never collinear, but the tests cover it anyway.

**Cluster identity across time.** DBSCAN labels mean nothing from one run to the next, but "this fire grew 780 ha" requires knowing today's cluster 7 is yesterday's cluster 4. Emberline matches perimeters by intersection-over-union with greedy 1:1 assignment, then handles the messy cases explicitly: two fires that merge collapse into the **older** ID with a recorded merge event; a fire hidden by a day of cloud cover matches again for up to 3 days before its ID retires; a small fast-moving day-one fire can legitimately fail its IoU match — that shows up as an ID break, which is the honest failure mode.

**False positives are forever.** VIIRS flags gas flares, refineries, and steel mills on every single pass. Without a filter, the map grows a permanent "wildfire" over every oil field in Kern County. Emberline builds a static-source mask: any 375 m grid cell hot on more than 60 % of days in a trailing 90-day window is industrial, not wildfire, and its detections are dropped before clustering.

## Run it locally

The live dataset lives on the `data` branch (refreshed every 3 h by the ingest workflow); `make data` pulls it down, and the frontend needs zero credentials. Without a FIRMS key you can still exercise the whole pipeline offline: `make demo` synthesizes an 8-day fire season and runs it through every stage.

```bash
python3 -m venv .venv && .venv/bin/pip install -r pipeline/requirements.txt
cd pipeline && ../.venv/bin/pytest          # 25 tests
cd .. && make data                          # live dataset (or: make demo)
cd web && npm install && npm run dev        # http://localhost:3000
```

## Deploy your own

1. Get a free FIRMS map key: https://firms.modaps.eosdis.nasa.gov/api/area/
2. Add a repo secret `FIRMS_MAP_KEY` (and optionally `DATABASE_URL` for the PostGIS mirror — schema in `pipeline/schema.sql`)
3. In repo **Settings → Pages**, set the source to **GitHub Actions**
4. The `deploy` workflow publishes `web/` to GitHub Pages on every push; the `ingest` workflow runs every 3 h, fetches the latest detections, publishes the refreshed dataset to the `data` branch as a single fresh commit (so it never accumulates history), and re-triggers the deploy

## Repository layout

```
pipeline/   Python ingest: clustering, hulls, identity, metrics (fully unit-tested)
web/        Next.js + MapLibre + deck.gl frontend
.github/    3-hour ingest cron
```
