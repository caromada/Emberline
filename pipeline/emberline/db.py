"""Optional PostGIS mirror of the local store. No-op unless DATABASE_URL is set."""
import json
import os
import pathlib


def sync(data_dir: str) -> None:
    url = os.environ.get("DATABASE_URL")
    if not url:
        return
    import psycopg  # imported lazily so local dev never needs a database

    root = pathlib.Path(data_dir)
    state = json.loads((root / "state.json").read_text())
    day = json.loads((root / "index.json").read_text())["dates"][-1]
    perims = json.loads((root / "perimeters" / f"{day}.geojson").read_text())
    dets = json.loads((root / "detections" / f"{day}.geojson").read_text())
    schema = (pathlib.Path(__file__).resolve().parents[1] / "schema.sql").read_text()

    with psycopg.connect(url) as conn, conn.cursor() as cur:
        cur.execute(schema)
        for r in state["records"]:
            cur.execute(
                """INSERT INTO fires VALUES (%s,%s,%s,%s)
                   ON CONFLICT (fire_id) DO UPDATE
                   SET last_seen=EXCLUDED.last_seen, merged_into=EXCLUDED.merged_into""",
                (r["fire_id"], r["first_seen"], r["last_seen"], r["merged_into"]))
        for f in perims["features"]:
            p = f["properties"]
            cur.execute(
                """INSERT INTO perimeters (fire_id, date, geom, area_ha, frp_sum)
                   VALUES (%s,%s, ST_Multi(ST_GeomFromGeoJSON(%s)), %s, %s)
                   ON CONFLICT (fire_id, date) DO UPDATE
                   SET geom=EXCLUDED.geom, area_ha=EXCLUDED.area_ha,
                       frp_sum=EXCLUDED.frp_sum""",
                (p["fire_id"], p["date"], json.dumps(f["geometry"]),
                 p["area_ha"], p["frp_sum"]))
        cur.execute("DELETE FROM detections WHERE acq_date=%s", (day,))
        for f in dets["features"]:
            cur.execute(
                "INSERT INTO detections (acq_date, geom, frp)"
                " VALUES (%s, ST_GeomFromGeoJSON(%s), %s)",
                (f["properties"]["date"], json.dumps(f["geometry"]),
                 f["properties"]["frp"]))
