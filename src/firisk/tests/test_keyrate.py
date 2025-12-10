import pandas as pd
import numpy as np

from firisk.curve.nss import NSSParams
from firisk.curve.curve_object import NSSCurve
from firisk.instruments.bond import FixedCouponBond
from firisk.risk.keyrate import compute_keyrate_dv01_with_settlement


def test_keyrate_dv01_runs_and_returns_all_tenors():
    # Simple synthetic-ish yields (decimal)
    yields = {
        "3M": 0.05,
        "6M": 0.05,
        "1Y": 0.048,
        "2Y": 0.047,
        "3Y": 0.046,
        "5Y": 0.045,
        "7Y": 0.044,
        "10Y": 0.043,
    }

    bond = FixedCouponBond(
        maturity_date=pd.Timestamp("2030-01-01"),
        coupon_rate=0.045,
        notional=100,
        frequency=2
    )

    settlement = pd.Timestamp("2022-12-30")

    res = compute_keyrate_dv01_with_settlement(
        bond, yields, settlement_date=settlement, bump_bp=1.0
    )

    assert np.isfinite(res.base_price)
    assert set(res.keyrate_dv01.keys()) == set(yields.keys())
