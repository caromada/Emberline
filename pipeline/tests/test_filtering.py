import pandas as pd

from emberline.filtering import drop_low_confidence


def test_drops_only_low_confidence():
    df = pd.DataFrame({"confidence": ["l", "n", "h", "L", "n"], "frp": [1, 2, 3, 4, 5]})
    out = drop_low_confidence(df)
    assert list(out["frp"]) == [2, 3, 5]
