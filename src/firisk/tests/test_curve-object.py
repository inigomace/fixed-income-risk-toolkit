from firisk.curve.curve_object import NSSCurve
from firisk.curve.nss import NSSParams

params = NSSParams(
    beta0=0.04,
    beta1=-0.02,
    beta2=0.01,
    beta3=0.005,
    tau1=1.5,
    tau2=4.0
)

curve = NSSCurve.from_params(params)

print(curve.yield_at(1.0))  # 1Y
print(curve.yields_for_tenors(["3M", "1Y", "5Y", "10Y"]))
print(curve.discount_factor([0.25, 1, 5, 10]))
print(curve.default_tenor_snapshot())
