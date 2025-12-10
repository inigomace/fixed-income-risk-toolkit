from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Sequence
import warnings

from firisk.utils.dates import normalize_tenor, sort_tenors, to_datetime_index, tenor_to_years

import pandas as pd


# ----------------------------
# Canonical tenor universe
# ----------------------------
TENOR_ORDER: Sequence[str] = (
    "3M", "6M", "1Y", "2Y", "3Y", "5Y", "7Y", "10Y"
)

TENOR_TO_YEARS = {
    "3M": 0.25,
    "6M": 0.50,
    "1Y": 1.0,
    "2Y": 2.0,
    "3Y": 3.0,
    "5Y": 5.0,
    "7Y": 7.0,
    "10Y": 10.0,
}


@dataclass(frozen=True)
class YieldValidationConfig:
    """
    Validation configuration for yield history tables.

    This project standardizes yields to DECIMAL form:
        4.50% -> 0.0450

    We purposely keep this strict to avoid silent downstream risk errors.
    """
    required_tenors: Sequence[str] = TENOR_ORDER

    # Accept either "date" or "Date" stored in raw file
    date_column: str = "date"

    allow_extra_columns: bool = False

    # Missing-value policy:
    # - "ffill": forward-fill (practical for daily rates)
    # - "drop": drop any rows with missing values
    # - "error": fail if any missing values exist
    missing_policy: str = "ffill"

    # Warn if more than this fraction of a column is missing pre-fill
    missing_warn_fraction: float = 0.05


# ----------------------------
# Public API
# ----------------------------
def load_yield_history(
    path: str | Path,
    config: Optional[YieldValidationConfig] = None
) -> pd.DataFrame:
    """
    Load and validate yield history from CSV.

    Returns a clean DataFrame with:
      - DatetimeIndex
      - columns in canonical tenor order
      - numeric yields in decimal form
    """
    config = config or YieldValidationConfig()
    path = Path(path)

    if not path.exists():
        raise FileNotFoundError(f"Yield history file not found: {path}")

    df = pd.read_csv(path)
    return validate_yield_table(df, config=config)


def validate_yield_table(
    df: pd.DataFrame,
    config: Optional[YieldValidationConfig] = None
) -> pd.DataFrame:
    """
    Validate and clean a raw yield table.

    Validation includes:
      - Drop Excel artifact columns (Unnamed: x)
      - Standardize date column name
      - Parse dates robustly
      - Remove duplicate dates
      - Enforce required tenor columns
      - Sort columns by canonical tenor order
      - Convert to numeric
      - Standardize percent/decimal per-cell
      - Apply missing value rule
    """
    config = config or YieldValidationConfig()
    df = df.copy()

    # 1) Drop Excel artifact columns
    df = df.loc[:, ~df.columns.astype(str).str.match(r"^Unnamed")]

    # 2) Normalize date column name if needed
    if config.date_column not in df.columns and "Date" in df.columns:
        df = df.rename(columns={"Date": config.date_column})

    # 3) Parse date and set index
    df = _set_datetime_index(df, date_col=config.date_column)

    # 4) Sort index, remove duplicates
    df = df.sort_index()
    if df.index.duplicated().any():
        warnings.warn("Duplicate dates detected. Keeping last occurrence per date.")
        df = df[~df.index.duplicated(keep="last")]

    # 5) Confirm required tenor columns exist
    missing = [t for t in config.required_tenors if t not in df.columns]
    if missing:
        raise ValueError(f"Missing required tenor columns: {missing}")

    # 6) Keep only required columns unless extras allowed
    if not config.allow_extra_columns:
        df = df.loc[:, list(config.required_tenors)]

    # 7) Reorder columns to canonical tenor order
    ordered = [t for t in TENOR_ORDER if t in df.columns]
    # If allow_extra_columns=True, append extras after required ordered
    if config.allow_extra_columns:
        extras = [c for c in df.columns if c not in ordered]
        df = df.loc[:, ordered + extras]
    else:
        df = df.loc[:, ordered]

    # 8) Coerce numeric yields
    df = df.apply(pd.to_numeric, errors="coerce")

    # 9) Missing diagnostics (pre-fill)
    missing_frac = df.isna().mean()
    warn_cols = missing_frac[missing_frac > config.missing_warn_fraction]
    if len(warn_cols) > 0:
        warnings.warn(
            "High missing fraction detected in columns (pre-fill):\n"
            f"{warn_cols.sort_values(ascending=False)}"
        )

    # 10) Standardize units per-cell
    # If a value looks like percent (e.g., 4.5, 7.8), convert it to decimal.
    # If it already looks like decimal (e.g., 0.045), keep it.
    for col in config.required_tenors:
        s = df[col]
        df[col] = s.where(s.abs() <= 1.0, s / 100.0)

    # 11) Apply missing-value policy
    if config.missing_policy == "ffill":
        df = df.ffill()
    elif config.missing_policy == "drop":
        df = df.dropna()
    elif config.missing_policy == "error":
        if df.isna().any().any():
            raise ValueError("Missing values detected and missing_policy='error'.")
    else:
        raise ValueError(f"Unknown missing_policy: {config.missing_policy}")

    # 12) Final sanity checks
    if df.index.duplicated().any():
        raise AssertionError("Duplicate dates remain after cleaning.")

    # Ensure ordering exactly matches your canonical tenors
    expected_cols = list(TENOR_ORDER)
    if not config.allow_extra_columns and list(df.columns) != expected_cols:
        raise AssertionError(
            f"Column order mismatch.\nExpected: {expected_cols}\nGot: {list(df.columns)}"
        )

    return df


# ----------------------------
# Helpers
# ----------------------------
def _set_datetime_index(df: pd.DataFrame, date_col: str) -> pd.DataFrame:
    """
    Accept a date column in several possible formats and set as DatetimeIndex.

    Supports:
      - ISO: YYYY-MM-DD
      - MDY: 01/17/1990, 1/17/90
      - DMY: 17/01/1990, 17/01/90

    This is intentionally defensive even if your raw file is already cleaned.
    """
    if isinstance(df.index, pd.DatetimeIndex):
        return df

    if date_col not in df.columns:
        raise ValueError(
            f"Yield table must have a DatetimeIndex or a '{date_col}' column."
        )

    s = df[date_col].astype(str).str.strip()

    # Try explicit formats in a safe order
    p_iso = pd.to_datetime(s, format="%Y-%m-%d", errors="coerce")

    p_mdy_4 = pd.to_datetime(s, format="%m/%d/%Y", errors="coerce")
    p_mdy_2 = pd.to_datetime(s, format="%m/%d/%y", errors="coerce")

    p_dmy_4 = pd.to_datetime(s, format="%d/%m/%Y", errors="coerce")
    p_dmy_2 = pd.to_datetime(s, format="%d/%m/%y", errors="coerce")

    parsed = p_iso.fillna(p_mdy_4).fillna(p_mdy_2).fillna(p_dmy_4).fillna(p_dmy_2)

    # Last-resort generic parse attempts
    if parsed.isna().any():
        generic_mdy = pd.to_datetime(s, dayfirst=False, errors="coerce")
        generic_dmy = pd.to_datetime(s, dayfirst=True, errors="coerce")
        parsed = parsed.fillna(generic_mdy).fillna(generic_dmy)

    if parsed.isna().any():
        bad = s[parsed.isna()].head(20).tolist()
        raise ValueError(f"Unparseable dates remain. Examples: {bad}")

    df = df.copy()
    df[date_col] = parsed
    df = df.set_index(date_col)

    return df
