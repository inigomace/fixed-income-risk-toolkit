from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, List, Mapping, Optional, Sequence, Tuple, Union

import numpy as np

from firisk.curve.calibration import calibrate_nss
from firisk.curve.curve_object import NSSCurve
from firisk.utils.dates import normalize_tenor, sort_tenors


# Your current canonical tenor set
DEFAULT_KEY_TENORS: Sequence[str] = (
    "3M", "6M", "1Y", "2Y", "3Y", "5Y", "7Y", "10Y"
)


@dataclass(frozen=True)
class KeyRateResult:
    base_price: float
    bumped_prices: Dict[str, float]
    keyrate_dv01: Dict[str, float]  # price change for +1bp
    bump_bp: float
    tenors: List[str]


def _as_yield_vector(
    yields_by_tenor: Mapping[str, float],
    tenors: Sequence[str]
) -> np.ndarray:
    return np.array([float(yields_by_tenor[t]) for t in tenors], dtype=float)


def compute_keyrate_dv01(
    bond,
    yields_by_tenor: Mapping[str, float],
    *,
    key_tenors: Optional[Sequence[str]] = None,
    bump_bp: float = 1.0,
) -> KeyRateResult:
    """
    Compute key-rate DV01 via bump-and-reprice with NSS re-calibration.

    Parameters
    ----------
    bond:
        Any object with:
            price(curve, settlement_date) -> float
    yields_by_tenor:
        dict-like mapping, e.g. {"3M": 0.0521, "6M": 0.0519, ...}
        Must be decimals.
    key_tenors:
        Tenors to compute key-rate DV01 for.
        Defaults to your canonical set.
    bump_bp:
        Bump size in basis points.

    Returns
    -------
    KeyRateResult
    """
    if key_tenors is None:
        key_tenors = DEFAULT_KEY_TENORS

    # Normalize and enforce order
    key_tenors = sort_tenors([normalize_tenor(t) for t in key_tenors])

    # Ensure all required tenors exist in the input mapping
    missing = [t for t in key_tenors if t not in yields_by_tenor]
    if missing:
        raise ValueError(f"Missing tenors in yields_by_tenor: {missing}")

    # Vector form for calibration
    tenors = list(key_tenors)
    obs = _as_yield_vector(yields_by_tenor, tenors)

    # Baseline fit
    params_base, _ = calibrate_nss(tenors, obs)
    curve_base = NSSCurve.from_params(params_base)

    # Settlement date handling:
    # We assume bond has maturity/cashflow logic; use "today" conceptually.
    # In your notebooks you can pass an explicit settlement date.
    # Here we require the bond to accept settlement_date externally later if needed.
    # We'll default to None-style usage pattern; your bond class expects a date.
    #
    # For consistency with your FixedCouponBond:
    # you will call this function from a wrapper that supplies settlement_date.
    #
    # So we expose a second helper (below) for DataFrame-based use.

    raise_if_no_settlement = not hasattr(bond, "price")
    if raise_if_no_settlement:
        raise ValueError("bond must provide price(curve, settlement_date).")

    # We'll require the caller to pass a pre-bound lambda OR use the helper below.
    # So for the core function, we can't guess settlement_date safely.
    raise ValueError(
        "Use compute_keyrate_dv01_with_settlement(...) "
        "or pass a bond wrapper with settlement date bound."
    )


def compute_keyrate_dv01_with_settlement(
    bond,
    yields_by_tenor: Mapping[str, float],
    settlement_date,
    *,
    key_tenors: Optional[Sequence[str]] = None,
    bump_bp: float = 1.0,
) -> KeyRateResult:
    """
    Same as compute_keyrate_dv01 but explicit settlement_date.
    """
    if key_tenors is None:
        key_tenors = DEFAULT_KEY_TENORS

    key_tenors = sort_tenors([normalize_tenor(t) for t in key_tenors])
    tenors = list(key_tenors)

    missing = [t for t in tenors if t not in yields_by_tenor]
    if missing:
        raise ValueError(f"Missing tenors in yields_by_tenor: {missing}")

    obs = _as_yield_vector(yields_by_tenor, tenors)

    # Baseline
    params_base, _ = calibrate_nss(tenors, obs)
    curve_base = NSSCurve.from_params(params_base)
    base_price = float(bond.price(curve_base, settlement_date=settlement_date))

    bumped_prices: Dict[str, float] = {}
    keyrate: Dict[str, float] = {}

    bump_decimal = float(bump_bp) * 1e-4  # 1 bp = 0.0001

    # Bump each node, refit, reprice
    for t in tenors:
        bumped = dict(yields_by_tenor)
        bumped[t] = float(bumped[t]) + bump_decimal

        obs_b = _as_yield_vector(bumped, tenors)
        params_b, _ = calibrate_nss(tenors, obs_b)
        curve_b = NSSCurve.from_params(params_b)

        p_b = float(bond.price(curve_b, settlement_date=settlement_date))
        bumped_prices[t] = p_b
        keyrate[t] = p_b - base_price  # PV change for +1bp

    return KeyRateResult(
        base_price=base_price,
        bumped_prices=bumped_prices,
        keyrate_dv01=keyrate,
        bump_bp=float(bump_bp),
        tenors=tenors
    )
