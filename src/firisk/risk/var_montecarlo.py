from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Mapping, Optional, Sequence

import numpy as np

from firisk.curve.calibration import calibrate_nss
from firisk.curve.curve_object import NSSCurve
from firisk.utils.dates import normalize_tenor, sort_tenors


DEFAULT_VAR_TENORS: Sequence[str] = (
    "3M", "6M", "1Y", "2Y", "3Y", "5Y", "7Y", "10Y"
)


@dataclass(frozen=True)
class MonteCarloVaRResult:
    base_price: float
    base_date: object
    settlement_date: object
    tenors: List[str]
    lookback_days: int
    n_sims: int
    seed: int
    pnl: np.ndarray
    var_by_level: Dict[float, float]


def _as_yield_vector(yields_by_tenor: Mapping[str, float], tenors: Sequence[str]) -> np.ndarray:
    return np.array([float(yields_by_tenor[t]) for t in tenors], dtype=float)


def _fit_and_price(bond, yields_by_tenor: Mapping[str, float], tenors: Sequence[str], settlement_date):
    obs = _as_yield_vector(yields_by_tenor, tenors)
    params, _ = calibrate_nss(tenors, obs)
    curve = NSSCurve.from_params(params)
    return float(bond.price(curve, settlement_date=settlement_date))


def compute_monte_carlo_var_with_settlement(
    bond,
    yield_df,
    settlement_date,
    *,
    base_date=None,
    tenors: Optional[Sequence[str]] = None,
    lookback_days: int = 252,
    n_sims: int = 5000,
    seed: int = 42,
    confidence_levels: Sequence[float] = (0.95, 0.99),
) -> MonteCarloVaRResult:
    """
    Monte Carlo VaR using full revaluation:

    1) Estimate covariance matrix of daily tenor changes from history.
    2) Simulate multivariate normal yield shocks.
    3) Apply shocks to the base curve snapshot.
    4) Refit NSS and reprice bond per simulation.
    5) Compute VaR from the simulated P&L distribution.

    VaR reported as a positive number (loss magnitude).
    """
    if tenors is None:
        tenors = DEFAULT_VAR_TENORS

    tenors = sort_tenors([normalize_tenor(t) for t in tenors])

    missing = [t for t in tenors if t not in yield_df.columns]
    if missing:
        raise ValueError(f"Yield DataFrame missing required tenors: {missing}")

    if base_date is None:
        base_date = yield_df.index.max()

    # History window ending at base_date
    df_sub = yield_df.loc[:base_date].copy()
    if lookback_days is not None and lookback_days > 0:
        df_sub = df_sub.tail(lookback_days + 1)

    if len(df_sub) < 2:
        raise ValueError("Not enough history for Monte Carlo VaR with the chosen lookback window.")

    base_row = df_sub.loc[base_date, tenors].to_dict()

    # Base price
    base_price = _fit_and_price(bond, base_row, tenors, settlement_date)

    # Estimate covariance of daily changes
    changes = df_sub[tenors].diff().dropna()
    cov = np.cov(changes.values.T)

    # Numerical stability: ensure PSD-ish
    # Add tiny ridge if needed
    eps = 1e-12
    cov = cov + np.eye(len(tenors)) * eps

    rng = np.random.default_rng(seed)
    shocks = rng.multivariate_normal(
        mean=np.zeros(len(tenors)),
        cov=cov,
        size=int(n_sims)
    )

    pnl = np.empty(int(n_sims), dtype=float)

    for i in range(int(n_sims)):
        shocked = dict(base_row)
        for j, t in enumerate(tenors):
            shocked[t] = float(shocked[t]) + float(shocks[i, j])

        p_shocked = _fit_and_price(bond, shocked, tenors, settlement_date)
        pnl[i] = p_shocked - base_price

    var_by_level: Dict[float, float] = {}
    for cl in confidence_levels:
        q = np.quantile(pnl, 1.0 - float(cl))
        var_by_level[float(cl)] = float(max(0.0, -q))

    return MonteCarloVaRResult(
        base_price=base_price,
        base_date=base_date,
        settlement_date=settlement_date,
        tenors=list(tenors),
        lookback_days=int(min(lookback_days, len(df_sub) - 1)),
        n_sims=int(n_sims),
        seed=int(seed),
        pnl=pnl,
        var_by_level=var_by_level,
    )
