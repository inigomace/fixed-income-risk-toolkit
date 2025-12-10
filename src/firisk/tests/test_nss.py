from firisk.curve.nss import nss_yield, NSSParams, nss_yield_for_tenors

# A reasonable-ish dummy parameter set
params = NSSParams(
    beta0=0.04,
    beta1=-0.02,
    beta2=0.01,
    beta3=0.005,
    tau1=1.5,
    tau2=4.0,
)

print(nss_yield(1.0, *params.as_array()[:4], params.tau1, params.tau2))  # 1Y
print(nss_yield([0.25, 0.5, 1, 2, 5, 10], *params.as_array()[:4], params.tau1, params.tau2))

print(nss_yield_for_tenors(["3M","6M","1Y","2Y","5Y","10Y"],
                           params.beta0, params.beta1, params.beta2, params.beta3,
                           params.tau1, params.tau2))
