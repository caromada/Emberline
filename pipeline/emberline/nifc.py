"""Official interagency perimeters (WFIGS) for validation and the compare layer."""
import requests

from .firms import get_with_retry

WFIGS_URL = (
    "https://services3.arcgis.com/T4QMspbfLg3qTGWY/arcgis/rest/services/"
    "WFIGS_Interagency_Perimeters_Current/FeatureServer/0/query"
)


def fetch_current_perimeters(bbox: str, timeout: int = 120) -> dict:
    west, south, east, north = bbox.split(",")
    params = {
        "where": "1=1",
        "geometry": f"{west},{south},{east},{north}",
        "geometryType": "esriGeometryEnvelope",
        "inSR": 4326,
        "spatialRel": "esriSpatialRelIntersects",
        "outFields": "poly_IncidentName,poly_GISAcres,poly_DateCurrent",
        "outSR": 4326,
        "geometryPrecision": 5,
        "f": "geojson",
    }
    last_err: Exception | None = None
    for _ in range(3):  # the service occasionally truncates large responses
        resp = get_with_retry(WFIGS_URL, timeout=timeout, params=params)
        resp.raise_for_status()
        try:
            return resp.json()
        except ValueError as err:
            last_err = err
    raise last_err
