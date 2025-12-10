from firisk.data.loaders import load_yield_history
from firisk.curve.calibration import calibrate_nss_latest
from firisk.curve.curve_object import NSSCurve
from firisk.instruments.bond import FixedCouponBond
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]  # project root

df = load_yield_history(ROOT / "src" / "firisk" / "data" / "yields.csv")
params, stats = calibrate_nss_latest(df)

curve = NSSCurve.from_params(params)

bond = FixedCouponBond(
    maturity_date=pd.Timestamp("2030-01-01"),
    coupon_rate=0.045,
    notional=100,
    frequency=2
)

print("Bond price:", bond.price(curve, settlement_date=df.index.max()))
