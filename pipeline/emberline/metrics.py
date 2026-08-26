"""Growth and spread metrics from a fire's perimeter history (projected meters)."""
import math
from datetime import date

_WINDS = ["N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE",
          "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW"]


def bearing_deg(dx: float, dy: float) -> float:
    return math.degrees(math.atan2(dx, dy)) % 360.0


def compass_16(bearing: float) -> str:
    return _WINDS[int((bearing % 360) / 22.5 + 0.5) % 16]


def compute_growth(history: list[dict]) -> dict:
    none = {"growth_24h_ha": None, "speed_km_day": None,
            "bearing_deg": None, "direction": None}
    if len(history) < 2:
        return none
    prev, cur = history[-2], history[-1]
    days = (date.fromisoformat(cur["date"]) - date.fromisoformat(prev["date"])).days
    if days <= 0:
        return none
    dx, dy = cur["cx"] - prev["cx"], cur["cy"] - prev["cy"]
    dist_km = math.hypot(dx, dy) / 1000.0
    b = bearing_deg(dx, dy)
    return {
        "growth_24h_ha": (cur["area_ha"] - prev["area_ha"]) / days,
        "speed_km_day": dist_km / days,
        "bearing_deg": b,
        "direction": compass_16(b),
    }
