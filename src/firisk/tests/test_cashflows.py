import pandas as pd
from firisk.instruments.cashflows import build_coupon_schedule, generate_fixed_coupon_cashflows


def test_schedule_includes_maturity():
    settle = pd.Timestamp("2020-01-01")
    maturity = pd.Timestamp("2025-01-01")
    sched = build_coupon_schedule(settle, maturity, frequency=2)

    assert sched[-1] == maturity
    assert all(d > settle for d in sched)


def test_cashflows_include_principal_at_maturity():
    settle = pd.Timestamp("2020-01-01")
    maturity = pd.Timestamp("2021-01-01")

    cfs = generate_fixed_coupon_cashflows(
        settle, maturity, coupon_rate=0.05, notional=100, frequency=2
    )

    assert any(cf.date == maturity and cf.amount > 100 for cf in cfs)
