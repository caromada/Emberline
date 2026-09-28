"""NASA FIRMS area API: fetch and parse VIIRS detections."""
import io
import time

import pandas as pd
import requests

BASE = "https://firms.modaps.eosdis.nasa.gov/api/area/csv"


def area_url(key: str, source: str, bbox: str, day_range: int, date: str | None = None) -> str:
    url = f"{BASE}/{key}/{source}/{bbox}/{day_range}"
    return f"{url}/{date}" if date else url


def parse_firms_csv(text: str) -> pd.DataFrame:
    df = pd.read_csv(io.StringIO(text))
    if df.empty:
        return df
    hhmm = df["acq_time"].astype(int).astype(str).str.zfill(4)
    df["acq_datetime"] = pd.to_datetime(
        df["acq_date"] + " " + hhmm.str[:2] + ":" + hhmm.str[2:]
    )
    return df


def get_with_retry(url: str, timeout: int = 120, attempts: int = 4,
                   backoff_s: float = 20.0, **kwargs) -> requests.Response:
    """GET that rides out transient network failures and 5xx responses.

    CI runners intermittently can't reach the FIRMS host at all; a short
    backoff almost always clears it, where failing the run would just skip a
    3-hour cycle.
    """
    for attempt in range(attempts):
        try:
            resp = requests.get(url, timeout=timeout, **kwargs)
            if resp.status_code < 500 or attempt == attempts - 1:
                return resp
        except (requests.ConnectionError, requests.Timeout):
            if attempt == attempts - 1:
                raise
        time.sleep(backoff_s * (attempt + 1))
    raise AssertionError("unreachable")


def fetch_detections(key, sources, bbox, day_range, date=None, timeout=120) -> pd.DataFrame:
    frames = []
    for source in sources:
        # NRT archives only reach back a few days and the API 400s past that;
        # fall back to shorter windows per source rather than failing the run
        for dr in sorted({d for d in (day_range, 5, 3, 2) if d <= day_range}, reverse=True):
            resp = get_with_retry(area_url(key, source, bbox, dr, date), timeout=timeout)
            if resp.status_code == 400 and dr > 2:
                continue
            resp.raise_for_status()
            frames.append(parse_firms_csv(resp.text))
            break
    frames = [f for f in frames if not f.empty]
    if not frames:
        return pd.DataFrame()
    return pd.concat(frames, ignore_index=True).drop_duplicates(
        subset=["latitude", "longitude", "acq_date", "acq_time", "satellite"]
    )
