CREATE EXTENSION IF NOT EXISTS postgis;

CREATE TABLE IF NOT EXISTS fires (
  fire_id     text PRIMARY KEY,
  first_seen  date NOT NULL,
  last_seen   date NOT NULL,
  merged_into text REFERENCES fires(fire_id)
);

CREATE TABLE IF NOT EXISTS perimeters (
  fire_id  text REFERENCES fires(fire_id),
  date     date NOT NULL,
  geom     geometry(MultiPolygon, 4326) NOT NULL,
  area_ha  double precision NOT NULL,
  frp_sum  double precision NOT NULL,
  PRIMARY KEY (fire_id, date)
);
CREATE INDEX IF NOT EXISTS perimeters_geom_gix ON perimeters USING gist (geom);

CREATE TABLE IF NOT EXISTS detections (
  id       bigserial PRIMARY KEY,
  acq_date date NOT NULL,
  geom     geometry(Point, 4326) NOT NULL,
  frp      real NOT NULL
);
CREATE INDEX IF NOT EXISTS detections_date_ix ON detections (acq_date);
CREATE INDEX IF NOT EXISTS detections_geom_gix ON detections USING gist (geom);
