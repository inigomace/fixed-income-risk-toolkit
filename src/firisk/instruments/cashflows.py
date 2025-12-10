from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

import pandas as pd


@dataclass(frozen=True)
class Cashflow:
    date: pd.Timestamp
    amount: float


def _months_per_period(frequency: int) -> int:
    if frequency <= 0:
        raise ValueError("frequency must be positive.")
    months = 12 // frequency
    if 12 % frequency != 0:
        raise ValueError("frequency must divide 12 cleanly (e.g., 1,2,4,12).")
    return months


def build_coupon_schedule(
    settlement_date,
    maturity_date,
    frequency: int = 2
) -> List[pd.Timestamp]:
    """
    Build a simple coupon date schedule for a fixed-coupon bullet bond.

    Approach:
      - Step backwards from maturity in equal month jumps.
      - Keep dates strictly after settlement.
      - Return ascending list ending with maturity.

    This is a simplified schedule generator suitable for this project.
    """
    settle = pd.Timestamp(settlement_date)
    maturity = pd.Timestamp(maturity_date)

    if maturity <= settle:
        raise ValueError("maturity_date must be after settlement_date.")

    months = _months_per_period(frequency)

    dates = []
    d = maturity

    # Walk backward
    while d > settle:
        dates.append(d)
        d = d - pd.DateOffset(months=months)

    # Reverse to chronological order
    dates = sorted(set(dates))

    # Ensure maturity included
    if dates[-1] != maturity:
        dates.append(maturity)
        dates = sorted(set(dates))

    return dates


def generate_fixed_coupon_cashflows(
    settlement_date,
    maturity_date,
    coupon_rate: float,
    notional: float = 100.0,
    frequency: int = 2
) -> List[Cashflow]:
    """
    Generate future cashflows for a fixed-coupon bullet bond.

    Assumptions:
      - Coupon amount = notional * coupon_rate / frequency
      - Principal repaid fully at maturity
      - coupon_rate in decimal form (0.05 = 5%)

    Returns:
      List of Cashflow objects occurring after settlement_date.
    """
    schedule = build_coupon_schedule(settlement_date, maturity_date, frequency)

    cpn = float(notional) * float(coupon_rate) / frequency

    cfs: List[Cashflow] = []
    for dt in schedule:
        amt = cpn
        if pd.Timestamp(dt) == pd.Timestamp(maturity_date):
            amt += float(notional)
        cfs.append(Cashflow(pd.Timestamp(dt), float(amt)))

    return cfs
