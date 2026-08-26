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
