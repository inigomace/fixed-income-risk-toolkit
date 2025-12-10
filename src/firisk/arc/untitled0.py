from pathlib import Path
import pandas as pd
import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
csv_path = ROOT / "data" / "raw" / "yields.csv"

TENORS = ["3M", "6M", "1Y", "2Y", "3Y", "5Y", "7Y", "10Y"]

df = pd.read_csv(csv_path)

# 1) Remove Excel artifact columns
df = df.loc[:, ~df.columns.str.match(r"^Unnamed")]

# 2) Accept either Date or date
if "date" in df.columns:
    date_col = "date"
elif "Date" in df.columns:
    date_col = "Date"
else:
    raise ValueError(f"No date column found. Columns: {list(df.columns)}")

# 3) Keep only what you need
missing = [t for t in TENORS if t not in df.columns]
if missing:
    raise ValueError(f"Missing expected tenor columns: {missing}")

df = df[[date_col] + TENORS].copy()

# 4) Parse mixed MDY dates with two-pass explicit formats
# 4) Parse mixed dates with explicit multi-pass formats
s = df[date_col].astype(str).str.strip()

# MDY passes
m1 = pd.to_datetime(s, format="%m/%d/%Y", errors="coerce")
m2 = pd.to_datetime(s, format="%m/%d/%y", errors="coerce")

# DMY passes (fallback)
d1 = pd.to_datetime(s, format="%d/%m/%Y", errors="coerce")
d2 = pd.to_datetime(s, format="%d/%m/%y", errors="coerce")

df[date_col] = m1.fillna(m2).fillna(d1).fillna(d2)

if df[date_col].isna().any():
    bad = s[df[date_col].isna()].head(20).tolist()
    raise ValueError(f"Unparseable dates remain. Examples: {bad}")


# 5) Coerce numeric
for c in TENORS:
    df[c] = pd.to_numeric(df[c], errors="coerce")

# 6) Detect percent vs decimal and standardize to decimal
max_abs = np.nanmax(np.abs(df[TENORS].values))
if np.isfinite(max_abs) and max_abs > 1.0:
    df[TENORS] = df[TENORS] / 100.0

# 7) Round
df[TENORS] = df[TENORS].round(4)

# 8) Sort
df = df.sort_values(date_col)

# 9) Rename to canonical 'date'
if date_col == "Date":
    df = df.rename(columns={"Date": "date"})
    date_col = "date"

# 10) Write back clean raw file
df.to_csv(csv_path, index=False, date_format="%Y-%m-%d", float_format="%.4f")

# 11) Print clean diagnostics
print("Cleaned raw yields written to:", csv_path)
print(df.head())
print(df.columns)
print(df[date_col].min(), df[date_col].max())
print(df[TENORS].max().max())
