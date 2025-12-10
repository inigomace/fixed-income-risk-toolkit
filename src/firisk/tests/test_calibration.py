import matplotlib.pyplot as plt
from pathlib import Path
from firisk.data.loaders import load_yield_history
from firisk.curve.calibration import calibrate_nss_latest
from firisk.utils.dates import tenor_to_years

ROOT = Path(__file__).resolve().parents[3]  # project root

df = load_yield_history(ROOT / "src" / "firisk" / "data" / "yields.csv")
params, stats = calibrate_nss_latest(df)

tenors = stats.tenors
mats = stats.maturities_years
obs = stats.observed_yields
fit = stats.fitted_yields

plt.figure()
plt.plot(mats, obs, marker="o", label="Observed")
plt.plot(mats, fit, marker="x", label="Fitted")
plt.xticks(mats, tenors)
plt.title("NSS Fit: Observed vs Fitted")
plt.ylabel("Yield (decimal)")
plt.grid(True)
plt.legend()
plt.show()
