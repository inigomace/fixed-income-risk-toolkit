from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Mapping, Optional, Sequence, List

import numpy as np

from firisk.curve.calibration import calibrate_nss
from firisk.curve.curve_object import NSSCurve
from firisk.utils.dates import normalize_tenor, sort_tenors, tenor_to_years


DEFAULT_STRESS_TENORS: Sequence[str] = (
    "3M", "6M", "1Y", "2Y", "3Y", "5Y", "7Y", "10Y"
)


@dataclass(frozen=True)
class StressScenarioResult:
    name: str
    shocked_yields: Dict[str, float]
    price: float
    pnl: float  # stressed price - base price


@dataclass(frozen=True)
class StressTestResult:
    base_price: float
    shock_bp: float
    tenors: List[str]
    scenarios: Dict[str, StressScenarioResult]


def _as_yield_vector(
    yields_by_tenor: Mapping[str, float],
    tenors: Sequence[str]
) -> np.ndarray:
    return np.array([float(yields_by_tenor[t]) for t in tenors], dtype=float)


def _fit_and_price(
    bond,
    yields_by_tenor: Mapping[str, float],
    tenors: Sequence[str],
    settlement_date,
) -> float:
    obs = _as_yield_vector(yields_by_tenor, tenors)
    params, _ = calibrate_nss(tenors, obs)
    curve = NSSCurve.from_params(params)
    return float(bond.price(curve, settlement_date=settlement_date))


def _parallel_shock(
    yields_by_tenor: Mapping[str, float],
    tenors: Sequence[str],
    shock_decimal: float,
) -> Dict[str, float]:
    return {t: float(yields_by_tenor[t]) + shock_decimal for t in tenors}


def _steepener_shock(
    yields_by_tenor: Mapping[str, float],
    tenors: Sequence[str],
    shock_decimal: float,
) -> Dict[str, float]:
    mats = np.array([tenor_to_years(t) for t in tenors], dtype=float)
    m_min = float(mats.min())
    m_max = float(mats.max())
    weights = np.ones_like(mats) if m_max == m_min else (mats - m_min) / (m_max - m_min)

    shocked: Dict[str, float] = {}
    for t, w in zip(tenors, weights):
        shocked[t] = float(yields_by_tenor[t]) + w * shock_decimal
    return shocked


def _flattener_shock(
    yields_by_tenor: Mapping[str, float],
    tenors: Sequence[str],
    shock_decimal: float,
) -> Dict[str, float]:
    mats = np.array([tenor_to_years(t) for t in tenors], dtype=float)
    m_min = float(mats.min())
    m_max = float(mats.max())
    weights = np.ones_like(mats) if m_max == m_min else (mats - m_min) / (m_max - m_min)

    shocked: Dict[str, float] = {}
    for t, w in zip(tenors, weights):
        shocked[t] = float(yields_by_tenor[t]) + (1.0 - w) * shock_decimal
    return shocked


def run_stress_tests_with_settlement(
    bond,
    yields_by_tenor: Mapping[str, float],
    settlement_date,
    *,
    stress_tenors: Optional[Sequence[str]] = None,
    shock_bp: float = 25.0,
) -> StressTestResult:
    if stress_tenors is None:
        stress_tenors = DEFAULT_STRESS_TENORS

    tenors = sort_tenors([normalize_tenor(t) for t in stress_tenors])

    missing = [t for t in tenors if t not in yields_by_tenor]
    if missing:
        raise ValueError(f"Missing tenors in yields_by_tenor: {missing}")

    base_price = _fit_and_price(bond, yields_by_tenor, tenors, settlement_date)

    shock_decimal = float(shock_bp) * 1e-4

    scenarios: Dict[str, StressScenarioResult] = {}

    y_parallel = _parallel_shock(yields_by_tenor, tenors, shock_decimal)
    p_parallel = _fit_and_price(bond, y_parallel, tenors, settlement_date)
    scenarios["parallel"] = StressScenarioResult(
        name="parallel",
        shocked_yields=y_parallel,
        price=p_parallel,
        pnl=p_parallel - base_price,
    )

    y_steep = _steepener_shock(yields_by_tenor, tenors, shock_decimal)
    p_steep = _fit_and_price(bond, y_steep, tenors, settlement_date)
    scenarios["steepener"] = StressScenarioResult(
        name="steepener",
        shocked_yields=y_steep,
        price=p_steep,
        pnl=p_steep - base_price,
    )

    y_flat = _flattener_shock(yields_by_tenor, tenors, shock_decimal)
    p_flat = _fit_and_price(bond, y_flat, tenors, settlement_date)
    scenarios["flattener"] = StressScenarioResult(
        name="flattener",
        shocked_yields=y_flat,
        price=p_flat,
        pnl=p_flat - base_price,
    )

    return StressTestResult(
        base_price=float(base_price),
        shock_bp=float(shock_bp),
        tenors=list(tenors),
        scenarios=scenarios,
    )
