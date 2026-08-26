from emberline.metrics import bearing_deg, compass_16, compute_growth


def test_bearing_north_and_east():
    assert bearing_deg(0, 1000) == 0.0
    assert bearing_deg(1000, 0) == 90.0


def test_compass():
    assert compass_16(0) == "N"
    assert compass_16(22.5) == "NNE"
    assert compass_16(202.5) == "SSW"


def test_compute_growth():
    history = [
        {"date": "2026-08-20", "area_ha": 1000.0, "cx": 0.0, "cy": 0.0},
        {"date": "2026-08-21", "area_ha": 1780.0, "cx": 800.0, "cy": 1900.0},
    ]
    g = compute_growth(history)
    assert round(g["growth_24h_ha"]) == 780
    assert round(g["speed_km_day"], 2) == 2.06
    assert g["direction"] == "NNE"


def test_single_snapshot_no_growth():
    g = compute_growth([{"date": "2026-08-20", "area_ha": 10.0, "cx": 0, "cy": 0}])
    assert g == {"growth_24h_ha": None, "speed_km_day": None,
                 "bearing_deg": None, "direction": None}
