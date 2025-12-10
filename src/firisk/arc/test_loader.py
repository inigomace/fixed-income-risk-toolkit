from pathlib import Path
from firisk.data.loaders import load_yield_history

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent

df = load_yield_history(ROOT / "data" / "yields.csv")

print(df.head())
print("Columns:", list(df.columns))
print("Date range:", df.index.min(), "->", df.index.max())
print("Max yield:", df.max().max())
print("Min yield:", df.min().min())
