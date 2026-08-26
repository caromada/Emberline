"""Synthesize a FIRMS-format CSV for local development (no API key needed).

Three fires with distinct life stories + a static industrial source:
  A: ignites day 1 near Redding, grows NNE ~2 km/day, develops two arms
  B: ignites day 4 in the Sierra foothills, fast circular growth
  C1/C2: neighbors from day 3 that merge on day 6
  S: gas-flare stand-in, the same pixels hot every single day (the static-source
     mask exists for exactly this signature; kept in the demo to show the
     raw point layer)
"""
import numpy as np
import pandas as pd

rng = np.random.default_rng(42)
DAYS = pd.date_range("2026-08-18", periods=8).strftime("%Y-%m-%d")
rows = []


def emit(lat, lon, day, frp, conf="n"):
    rows.append([round(lat, 5), round(lon, 5), round(340 + rng.normal(0, 6), 1), day,
                 f"{rng.integers(8, 11):02d}{rng.integers(0, 6)}2", "N", "VIIRS",
                 conf, "2.0NRT", round(max(frp, 0.5), 1), "N"])


def blob(clat, clon, sigma, n, day, frp_mu):
    pts = rng.normal([clat, clon], sigma, (n, 2))
    for lat, lon in pts:
        emit(lat, lon, day, rng.gamma(2.0, frp_mu / 2))


for i, day in enumerate(DAYS):
    # Fire A: NNE drift ~1.1 km/day, two arms after day 3
    alat, alon = 40.62 + i * 0.010, -122.40 + i * 0.004
    blob(alat, alon, 0.008 + i * 0.0022, 16 + i * 12, day, 14)
    if i >= 3:
        arm_len = 0.020 + 0.005 * i
        for t in np.linspace(0, arm_len, 10 + 2 * i):
            emit(alat + t + rng.normal(0, .002), alon - t * 0.55 + rng.normal(0, .002), day, 10)
            emit(alat + t * 0.6 + rng.normal(0, .002), alon + t * 0.9 + rng.normal(0, .002), day, 10)
    # Fire B from day 4
    if i >= 3:
        blob(39.30 + (i - 3) * 0.004, -120.85, 0.004 + (i - 3) * 0.005,
             8 + (i - 3) * 12, day, 22)
    # C pair from day 3, converging until they merge around day 6
    if i >= 2:
        gap = max(0.030 - (i - 2) * 0.009, 0.004)
        blob(41.05, -123.30 - gap / 2, 0.004 + (i - 2) * 0.003, 6 + (i - 2) * 5, day, 9)
        blob(41.05, -123.30 + gap / 2, 0.004 + (i - 2) * 0.003, 6 + (i - 2) * 5, day, 9)
    # Static source: same 3 pixels every single day
    for d_ in (0.0, 0.003, -0.003):
        emit(35.42 + d_, -119.05, day, 4.0)

df = pd.DataFrame(rows, columns=["latitude", "longitude", "bright_ti4", "acq_date",
                                 "acq_time", "satellite", "instrument", "confidence",
                                 "version", "frp", "daynight"])
df.to_csv("pipeline/scripts/demo_firms.csv", index=False)
print(f"wrote {len(df)} detections across {len(DAYS)} days")
