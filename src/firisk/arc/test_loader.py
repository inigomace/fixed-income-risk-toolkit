from pathlib import Path
from firisk.data.loaders import load_yield_history

ROOT = Path(__file__).resolve().parent.parent  # adjust if needed
df = load_yield_history(ROOT / "data" / "yields.csv")

expected = ["3M","6M","1Y","2Y","3Y","5Y","7Y","10Y"]

assert list(df.columns) == expected
assert df.index.duplicated().sum() == 0
assert df.index.is_monotonic_increasing
assert df.max().max() < 1.0  # confirms decimal

print("✅ Step 1 acceptance checks passed.")
