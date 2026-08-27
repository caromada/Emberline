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

The pipeline snapshots WFIGS perimeters on every run and scores itself: each fire's cumulative footprint (union of its whole perimeter history, in an equal-area projection) is matched to the overlapping official perimeter by IoU, and the per-fire table with signed area errors lands in [`data/validation.md`](data/validation.md), refreshed every ingest.

Current numbers from live data: **median absolute area error of ~40% against official perimeters for fires ≥ 1,000 ha**, with well-observed fires much tighter (Three Queens +2%, Deer Creek +3%); the exact figure refreshes with every ingest in [`data/validation.md`](data/validation.md). Two known biases dominate the tail, and both are physics rather than bugs: below ~1,000 ha the 375 m sensor footprint inflates small burns, and fires that were already burning before the tracking window opened have unobserved history and read low. The hull concavity parameter was tuned by sweeping it against these official perimeters: ratio 0.25 scores 40% median error, while a near-convex 0.7 scores 48%.

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

**Convex hulls are wrong, and everyone uses them anyway.** A fire burning up two canyon arms produces a convex hull that swallows the unburned ridge between them. On a two-armed test cluster, the concave hull comes in at ~27 % of the convex hull's area — the convex version overstates the fire by nearly 4×. The concavity parameter was then tuned against real official perimeters: sweeping it over n=20 NIFC fires ≥ 1,000 ha, the tightest setting (0.25) scores 40 % median area error while a near-convex setting (0.7) scores 48 % — the same direction the geometry predicts. A half-pixel (187.5 m) buffer turns point samples into detection footprints. One found edge case: perfectly collinear detections degenerate the Delaunay triangulation the hull is built on — real detections are never collinear, but the tests cover it anyway.

**Cluster identity across time.** DBSCAN labels mean nothing from one run to the next, but "this fire grew 780 ha" requires knowing today's cluster 7 is yesterday's cluster 4. Emberline matches perimeters by intersection-over-union with greedy 1:1 assignment, then handles the messy cases explicitly: two fires that merge collapse into the **older** ID with a recorded merge event; a fire hidden by a day of cloud cover matches again for up to 3 days before its ID retires; a small fast-moving day-one fire can legitimately fail its IoU match — that shows up as an ID break, which is the honest failure mode.

**False positives are forever.** VIIRS flags gas flares, refineries, and steel mills on every single pass. Without a filter, the map grows a permanent "wildfire" over every oil field in Kern County. Emberline builds a static-source mask: any 375 m grid cell hot on more than 60 % of days in a trailing 90-day window is industrial, not wildfire, and its detections are dropped before clustering.

## Run it locally

The repo ships with live data (refreshed every 3 h by the ingest workflow), and the frontend needs zero credentials. Without a FIRMS key you can still exercise the whole pipeline offline — `make demo` synthesizes an 8-day fire season and runs it through every stage:

```bash
python3 -m venv .venv && .venv/bin/pip install -r pipeline/requirements.txt
cd pipeline && ../.venv/bin/pytest          # 21 tests
cd .. && make demo                          # regenerate demo data
cd web && npm install && npm run dev        # http://localhost:3000
```

## Deploy your own

1. Get a free FIRMS map key: https://firms.modaps.eosdis.nasa.gov/api/area/
2. Add a repo secret `FIRMS_MAP_KEY` (and optionally `DATABASE_URL` for the PostGIS mirror — schema in `pipeline/schema.sql`)
3. In repo **Settings → Pages**, set the source to **GitHub Actions**
4. The `deploy` workflow publishes `web/` to GitHub Pages on every push; the `ingest` workflow runs every 3 h, fetches the latest detections, commits refreshed `data/`, and re-triggers the deploy

## Repository layout

```
pipeline/   Python ingest: clustering, hulls, identity, metrics (fully unit-tested)
data/       per-day GeoJSON snapshots + fire registry (the API surface)
web/        Next.js + MapLibre + deck.gl frontend
.github/    3-hour ingest cron
```
