from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

import pandas as pd

from firisk.curve.curve_object import NSSCurve
from firisk.instruments.cashflows import Cashflow, generate_fixed_coupon_cashflows
from firisk.utils.dates import year_fraction_act_365


@dataclass(frozen=True)
class FixedCouponBond:
    """
    Fixed-coupon bullet bond.

    This is a deliberately clean and limited implementation:
      - No embedded options
      - No inflation linking
      - No amortization

    Assumptions:
      - ACT/365 timing
      - Discounting via NSSCurve's continuous-comp DF
    """
    maturity_date: pd.Timestamp
    coupon_rate: float
    notional: float = 100.0
    frequency: int = 2

    def cashflows(self, settlement_date) -> List[Cashflow]:
        return generate_fixed_coupon_cashflows(
            settlement_date=settlement_date,
            maturity_date=self.maturity_date,
            coupon_rate=self.coupon_rate,
            notional=self.notional,
            frequency=self.frequency
        )

    def price(self, curve: NSSCurve, settlement_date) -> float:
        """
        Price the bond by discounting future cashflows.

        PV = sum( CF_i * DF(t_i) )

        where t_i is year fraction from settlement to cashflow date.
        """
        settle = pd.Timestamp(settlement_date)
        cfs = self.cashflows(settle)

        pv = 0.0
        for cf in cfs:
            t = year_fraction_act_365(settle, cf.date)
            if t <= 0:
                continue
            df = curve.discount_factor(t)
            pv += cf.amount * df

        return float(pv)
