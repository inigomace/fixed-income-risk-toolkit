from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Mapping, Optional, Sequence, Tuple

import numpy as np

from firisk.curve.calibration import calibrate_nss
from firisk.curve.curve_object import NSSCurve
from firisk.utils.dates import normalize_tenor, sort_tenors


DEFAULT_VAR_TENORS: Sequence[str] = (
    "3M", "6M", "1Y", "2Y", "3Y", "5Y", "7Y", "10Y"
)


@dataclass(frozen=True)
class HistoricalVaRResult:
    base_price: float
    base_date: object
    settlement_date: object
    tenors: List[str]
    lookback_days: int
    pnl: np.ndarray
    var_by_level: Dict[float, float]


def _as_yield_vector(yields_by_tenor: Mapping[str, float], tenors: Sequence[str]) -> np.ndarray:
    return np.array([float(yields_by_tenor[t]) for t in tenors], dtype=float)


def _fit_and_price(bond, yields_by_tenor: Mapping[str, float], tenors: Sequence[str], settlement_date):
    obs = _as_yield_vector(yields_by_tenor, tenors)
    params, _ = calibrate_nss(tenors, obs)
    curve = NSSCurve.from_params(params)
    return float(bond.price(curve, settlement_date=settlement_date))


def compute_historical_var_with_settlement(
    bond,
    yield_df,
    settlement_date,
    *,
    base_date=None,
    tenors: Optional[Sequence[str]] = None,
    lookback_days: int = 252,
    confidence_levels: Sequence[float] = (0.95, 0.99),
) -> HistoricalVaRResult:
    """
    Historical simulation VaR using full revaluation:

    1) Choose base_date (default: latest).
    2) Take base curve yields at base_date.
    3) Compute historical daily changes for the chosen tenors.
    4) Apply each historical change vector to today's/base yields.
    5) Refit NSS and reprice bond.
    6) Build P&L distribution and VaR.

    VaR reported as a positive number (loss magnitude).
    """
    if tenors is None:
        tenors = DEFAULT_VAR_TENORS

    tenors = sort_tenors([normalize_tenor(t) for t in tenors])

    # Validate columns exist
    missing = [t for t in tenors if t not in yield_df.columns]
    if missing:
        raise ValueError(f"Yield DataFrame missing required tenors: {missing}")

    if base_date is None:
        base_date = yield_df.index.max()

    # Slice lookback window ending at base_date
    df_sub = yield_df.loc[:base_date].copy()
    if lookback_days is not None and lookback_days > 0:
        df_sub = df_sub.tail(lookback_days + 1)  # +1 to allow diff

    if len(df_sub) < 2:
        raise ValueError("Not enough history for historical VaR with the chosen lookback window.")

    base_row = df_sub.loc[base_date, tenors].to_dict()

    # Base price
    base_price = _fit_and_price(bond, base_row, tenors, settlement_date)

    # Historical daily changes
    changes = df_sub[tenors].diff().dropna()

    pnl_list = []
    for _, delta in changes.iterrows():
        shocked = dict(base_row)
        for t in tenors:
            shocked[t] = float(shocked[t]) + float(delta[t])

        p_shocked = _fit_and_price(bond, shocked, tenors, settlement_date)
        pnl_list.append(p_shocked - base_price)

    pnl = np.array(pnl_list, dtype=float)

    var_by_level: Dict[float, float] = {}
    # VaR is a loss quantile: take negative tail of P&L
    # e.g., 95% VaR => 5th percentile of P&L, report positive magnitude of loss
    for cl in confidence_levels:
        q = np.quantile(pnl, 1.0 - float(cl))
        var_by_level[float(cl)] = float(max(0.0, -q))

    return HistoricalVaRResult(
        base_price=base_price,
        base_date=base_date,
        settlement_date=settlement_date,
        tenors=list(tenors),
        lookback_days=int(min(lookback_days, len(df_sub) - 1)),
        pnl=pnl,
        var_by_level=var_by_level,
    )
