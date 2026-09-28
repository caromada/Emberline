import pathlib

from emberline.firms import area_url, parse_firms_csv

FIXTURE = pathlib.Path(__file__).parent / "fixtures" / "firms_sample.csv"


def test_parse_firms_csv_columns_and_datetime():
    df = parse_firms_csv(FIXTURE.read_text())
    assert len(df) == 4
    assert {"latitude", "longitude", "frp", "confidence", "acq_date"} <= set(df.columns)
    assert str(df["acq_datetime"].iloc[0]) == "2026-08-20 09:12:00"


def test_area_url():
    url = area_url("KEY123", "VIIRS_SNPP_NRT", "-125,24,-66,50", 2)
    assert url == (
        "https://firms.modaps.eosdis.nasa.gov/api/area/csv/"
        "KEY123/VIIRS_SNPP_NRT/-125,24,-66,50/2"
    )


def test_get_with_retry_recovers_from_network_blip(monkeypatch):
    import requests

    from emberline import firms

    calls = {"n": 0}

    class Ok:
        status_code = 200

    def flaky_get(url, timeout, **kw):
        calls["n"] += 1
        if calls["n"] < 3:
            raise requests.ConnectionError("Network is unreachable")
        return Ok()

    monkeypatch.setattr(firms.requests, "get", flaky_get)
    monkeypatch.setattr(firms.time, "sleep", lambda s: None)
    assert firms.get_with_retry("https://example.test").status_code == 200
    assert calls["n"] == 3


def test_get_with_retry_gives_up_eventually(monkeypatch):
    import pytest
    import requests

    from emberline import firms

    def dead_get(url, timeout, **kw):
        raise requests.ConnectionError("Network is unreachable")

    monkeypatch.setattr(firms.requests, "get", dead_get)
    monkeypatch.setattr(firms.time, "sleep", lambda s: None)
    with pytest.raises(requests.ConnectionError):
        firms.get_with_retry("https://example.test", attempts=3)
