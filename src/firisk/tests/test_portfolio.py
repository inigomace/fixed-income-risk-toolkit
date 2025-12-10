import numpy as np
import pandas as pd

from firisk.curve.calibration import calibrate_nss
from firisk.curve.curve_object import NSSCurve
from firisk.instruments.bond import FixedCouponBond
from firisk.portfolio.portfolio import Portfolio, Position


def _sample_yields():
    return {
        "3M": 0.050,
        "6M": 0.049,
        "1Y": 0.048,
        "2Y": 0.047,
        "3Y": 0.046,
        "5Y": 0.045,
        "7Y": 0.044,
        "10Y": 0.043,
    }


def test_portfolio_price_matches_sum_of_positions():
    yields = _sample_yields()
    tenors = list(yields.keys())
    obs = [yields[t] for t in tenors]

    params, _ = calibrate_nss(tenors, obs)
    curve = NSSCurve.from_params(params)

    settle = pd.Timestamp("2022-12-30")

    bond1 = FixedCouponBond(pd.Timestamp("2028-01-01"), 0.04)
    bond2 = FixedCouponBond(pd.Timestamp("2032-01-01"), 0.05)

    p1 = bond1.price(curve, settlement_date=settle)
    p2 = bond2.price(curve, settlement_date=settle)

    qty1 = 2.0
    qty2 = 3.0

    portfolio = Portfolio([
        Position(bond1, qty1),
        Position(bond2, qty2),
    ])

    pv_port = portfolio.price(curve, settlement_date=settle)
    pv_manual = qty1 * p1 + qty2 * p2

    assert np.isfinite(pv_port)
    assert abs(pv_port - pv_manual) < 1e-6
