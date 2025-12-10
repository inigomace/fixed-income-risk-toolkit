import numpy as np
import pandas as pd

from firisk.instruments.bond import FixedCouponBond
from firisk.risk.stress import run_stress_tests_with_settlement


def _sample_yield_curve() -> dict:
    # Simple, plausible, gently downward-sloping curve in decimals
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


def test_parallel_stress_has_negative_pnl_for_long_bond():
    yields = _sample_yield_curve()

    bond = FixedCouponBond(
        maturity_date=pd.Timestamp("2035-01-01"),
        coupon_rate=0.045,
        notional=100,
        frequency=2,
    )

    settlement = pd.Timestamp("2025-01-01")

    res = run_stress_tests_with_settlement(
        bond,
        yields,
        settlement_date=settlement,
        shock_bp=25.0,  # +25bp parallel / long-end-ish shocks
    )

    assert np.isfinite(res.base_price)

    assert "parallel" in res.scenarios
    par = res.scenarios["parallel"]

    assert np.isfinite(par.price)
    # For a plain vanilla long bond, higher yields should reduce price
    assert par.pnl < 0.0
