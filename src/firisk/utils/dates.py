from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Iterable, List, Sequence, Tuple, Union, Optional

import pandas as pd


# ----------------------------
# Tenor parsing
# ----------------------------

_TENOR_RE = re.compile(r"^\s*(\d+)\s*([MmYy])\s*$")


def normalize_tenor(tenor: str) -> str:
    """
    Normalize a tenor string to canonical form.

    Examples:
        "3m" -> "3M"
        " 10Y " -> "10Y"
    """
    t = tenor.strip()
    m = _TENOR_RE.match(t)
    if not m:
        raise ValueError(f"Invalid tenor format: '{tenor}' (expected like '3M', '1Y').")
    n = int(m.group(1))
    unit = m.group(2).upper()
    return f"{n}{unit}"


def tenor_to_years(tenor: str) -> float:
    """
    Convert a tenor string into a year fraction.

    Rules:
        M => months => n/12
        Y => years  => n
    """
    t = normalize_tenor(tenor)
    n = int(t[:-1])
    unit = t[-1]

    if unit == "M":
        return n / 12.0
    if unit == "Y":
        return float(n)

    # Should never reach here due to regex
    raise ValueError(f"Unsupported tenor unit in '{tenor}'.")


def sort_tenors(tenors: Iterable[str]) -> List[str]:
    """
    Sort tenor strings by ascending maturity.

    Returns normalized tenors.
    """
    normed = [normalize_tenor(t) for t in tenors]
    return sorted(normed, key=tenor_to_years)


def enforce_tenor_order(
    columns: Sequence[str],
    required: Optional[Sequence[str]] = None
) -> List[str]:
    """
    Validate that required tenors exist and return columns in canonical sorted order.

    Parameters
    ----------
    columns:
        Column names from a DataFrame.
    required:
        Required tenors. If provided, will error on missing.

    Returns
    -------
    List[str]
        Sorted/normalized tenor column list.
    """
    norm_cols = [normalize_tenor(c) for c in columns]

    if required is not None:
        req_norm = [normalize_tenor(r) for r in required]
        missing = [r for r in req_norm if r not in norm_cols]
        if missing:
            raise ValueError(f"Missing required tenor columns: {missing}")

    return sort_tenors(norm_cols)


# ----------------------------
# Date helpers
# ----------------------------

def to_datetime_index(
    df: pd.DataFrame,
    date_col: str = "date"
) -> pd.DataFrame:
    """
    Ensure df is indexed by a DatetimeIndex.

    Accepts:
        - existing DatetimeIndex
        - a date column containing parseable strings

    Returns a copy.
    """
    out = df.copy()

    if isinstance(out.index, pd.DatetimeIndex):
        return out

    if date_col not in out.columns and "Date" in out.columns:
        out = out.rename(columns={"Date": date_col})

    if date_col not in out.columns:
        raise ValueError(f"Expected a '{date_col}' or 'Date' column.")

    out[date_col] = pd.to_datetime(out[date_col], errors="coerce")
    if out[date_col].isna().any():
        bad = out.loc[out[date_col].isna(), date_col].head(10).tolist()
        raise ValueError(f"Unparseable dates. Examples: {bad}")

    out = out.set_index(date_col).sort_index()
    return out


def year_fraction_act_365(start: Union[str, pd.Timestamp], end: Union[str, pd.Timestamp]) -> float:
    """
    ACT/365 year fraction.
    """
    s = pd.Timestamp(start)
    e = pd.Timestamp(end)
    delta_days = (e - s).days
    return delta_days / 365.0
