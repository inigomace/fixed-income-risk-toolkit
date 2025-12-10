from firisk.utils.dates import normalize_tenor, tenor_to_years, sort_tenors

def test_normalize_tenor():
    assert normalize_tenor("3m") == "3M"
    assert normalize_tenor("10Y") == "10Y"

def test_tenor_to_years():
    assert tenor_to_years("3M") == 0.25
    assert tenor_to_years("6M") == 0.5
    assert tenor_to_years("1Y") == 1.0

def test_sort_tenors():
    assert sort_tenors(["10Y", "3M", "2Y"]) == ["3M", "2Y", "10Y"]
