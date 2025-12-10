import pandas as pd
import numpy as np

from firisk.curve.curve_object import NSSCurve
from firisk.curve.nss import NSSParams
from firisk.instruments.bond import FixedCouponBond


def test_bond_price_is_finite():
    params = NSSParams(
        beta0=0.04, beta1=-0.02, beta2=0.01, beta3=0.005,
        tau1=1.5, tau2=4.0
    )
    curve = NSSCurve.from_params(params)

    bond = FixedCouponBond(
        maturity_date=pd.Timestamp("2030-01-01"),
        coupon_rate=0.04,
        notional=100,
        frequency=2
    )

    price = bond.price(curve, settlement_date="2025-01-01")
    assert np.isfinite(price)
    assert price > 0
