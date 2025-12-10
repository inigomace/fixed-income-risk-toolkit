import pandas as pd
import numpy as np

from firisk.instruments.bond import FixedCouponBond
from firisk.risk.var_historical import compute_historical_var_with_settlement
from firisk.risk.var_montecarlo import compute_monte_carlo_var_with_settlement


def _tiny_history():
    # Tiny synthetic dataset, just enough to ensure code runs
    dates = pd.date_range("2022-01-01", periods=10, freq="B")
    data = {
        "3M": np.linspace(0.02, 0.021, len(dates)),
        "6M": np.linspace(0.022, 0.023, len(dates)),
        "1Y": np.linspace(0.025, 0.026, len(dates)),
        "2Y": np.linspace(0.028, 0.029, len(dates)),
        "3Y": np.linspace(0.030, 0.031, len(dates)),
        "5Y": np.linspace(0.032, 0.033, len(dates)),
        "7Y": np.linspace(0.034, 0.035, len(dates)),
        "10Y": np.linspace(0.036, 0.037, len(dates)),
    }
    return pd.DataFrame(data, index=dates)


def test_historical_var_runs():
    df = _tiny_history()

    bond = FixedCouponBond(
        maturity_date=pd.Timestamp("2030-01-01"),
        coupon_rate=0.03,
        notional=100,
        frequency=2,
    )

    latest = df.index.max()

    res = compute_historical_var_with_settlement(
        bond,
        df,
        settlement_date=latest,
        base_date=latest,
        lookback_days=5,
        confidence_levels=(0.95,),
    )

    assert res.base_price > 0
    assert 0.95 in res.var_by_level
    assert len(res.pnl) > 0


def test_monte_carlo_var_runs():
    df = _tiny_history()

    bond = FixedCouponBond(
        maturity_date=pd.Timestamp("2030-01-01"),
        coupon_rate=0.03,
        notional=100,
        frequency=2,
    )

    latest = df.index.max()

    res = compute_monte_carlo_var_with_settlement(
        bond,
        df,
        settlement_date=latest,
        base_date=latest,
        lookback_days=5,
        n_sims=200,
        seed=1,
        confidence_levels=(0.95,),
    )

    assert res.base_price > 0
    assert 0.95 in res.var_by_level
    assert len(res.pnl) == 200
