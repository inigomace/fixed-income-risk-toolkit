from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional, Sequence, Tuple, Union

import numpy as np

try:
    from scipy.optimize import least_squares
except ImportError as e:
    raise ImportError(
        "scipy is required for NSS calibration. "
        "Install with: pip install scipy"
    ) from e

from firisk.curve.nss import NSSParams, nss_yield
from firisk.utils.dates import normalize_tenor, tenor_to_years, sort_tenors


# ----------------------------
# Defaults aligned to your project scope
# ----------------------------

DEFAULT_TENORS: Sequence[str] = (
    "3M", "6M", "1Y", "2Y", "3Y", "5Y", "7Y", "10Y"
)


# ----------------------------
# Fit stats container
# ----------------------------

@dataclass(frozen=True)
class NSSFitStats:
    rmse: float
    max_abs_error: float
    n_points: int
    success: bool
    cost: float
    message: str

    # Optional diagnostics
    fitted_yields: Optional[np.ndarray] = None
    observed_yields: Optional[np.ndarray] = None
    maturities_years: Optional[np.ndarray] = None
    tenors: Optional[List[str]] = None


# ----------------------------
# Public API
# ----------------------------

def calibrate_nss(
    tenors: Sequence[str],
    observed_yields: Sequence[float],
    *,
    initial_guess: Optional[Sequence[float]] = None,
    bounds: Optional[Tuple[Sequence[float], Sequence[float]]] = None,
    drop_na: bool = True,
) -> Tuple[NSSParams, NSSFitStats]:
    """
    Calibrate NSS parameters to an observed yield snapshot.

    Parameters
    ----------
    tenors:
        Tenor strings like ["3M","6M","1Y","2Y",...].
    observed_yields:
        Yields in decimal form aligned with tenors.
    initial_guess:
        Optional explicit 6-vector:
            [beta0, beta1, beta2, beta3, tau1, tau2]
    bounds:
        Optional (lower, upper) bounds for least squares.
    drop_na:
        If True, drop any tenor points with NaN yields.

    Returns
    -------
    (NSSParams, NSSFitStats)
    """
    if len(tenors) != len(observed_yields):
        raise ValueError("tenors and observed_yields must have the same length.")

    # Normalize tenors
    tenors_norm = [normalize_tenor(t) for t in tenors]

    # Convert to numeric
    y = np.asarray(observed_yields, dtype=float)

    # Optionally drop NaNs
    if drop_na:
        mask = np.isfinite(y)
        tenors_norm = [t for t, m in zip(tenors_norm, mask) if m]
        y = y[mask]

    if len(tenors_norm) < 4:
        raise ValueError(
            "Not enough valid tenor points to fit NSS. "
            "Provide at least 4 non-NaN yields."
        )

    # Convert tenors to maturities in years
    mats = np.array([tenor_to_years(t) for t in tenors_norm], dtype=float)

    # Sort by maturity (for stable guesses/diagnostics)
    order = np.argsort(mats)
    mats = mats[order]
    y = y[order]
    tenors_norm = [tenors_norm[i] for i in order]

    # Default initial guess
    if initial_guess is None:
        # beta0 ~ longest maturity yield (anchor the long end)
        beta0 = float(y[-1])
        beta1 = -0.02
        beta2 = 0.02
        beta3 = 0.01
        tau1 = 1.0
        tau2 = 3.0
        x0 = np.array([beta0, beta1, beta2, beta3, tau1, tau2], dtype=float)
    else:
        if len(initial_guess) != 6:
            raise ValueError("initial_guess must be a length-6 sequence.")
        x0 = np.asarray(initial_guess, dtype=float)

    # Default bounds (reasonable, not too tight)
    if bounds is None:
        lower = np.array([-0.05, -0.50, -0.50, -0.50, 1e-3, 1e-3], dtype=float)
        upper = np.array([ 0.20,  0.50,  0.50,  0.50, 20.0, 20.0], dtype=float)
    else:
        lower = np.asarray(bounds[0], dtype=float)
        upper = np.asarray(bounds[1], dtype=float)
        if lower.shape[0] != 6 or upper.shape[0] != 6:
            raise ValueError("bounds must provide two length-6 sequences.")

    # Residual function
    def residuals(x: np.ndarray) -> np.ndarray:
        b0, b1, b2, b3, t1, t2 = x
        model = nss_yield(mats, b0, b1, b2, b3, t1, t2)
        return model - y

    # Fit
    res = least_squares(
        residuals,
        x0=x0,
        bounds=(lower, upper),
        method="trf",
        max_nfev=5000,
    )

    params = NSSParams.from_array(res.x)

    fitted = nss_yield(mats, params.beta0, params.beta1, params.beta2, params.beta3, params.tau1, params.tau2)
    err = fitted - y

    rmse = float(np.sqrt(np.mean(err ** 2)))
    max_abs = float(np.max(np.abs(err)))

    stats = NSSFitStats(
        rmse=rmse,
        max_abs_error=max_abs,
        n_points=int(len(y)),
        success=bool(res.success),
        cost=float(res.cost),
        message=str(res.message),
        fitted_yields=fitted,
        observed_yields=y,
        maturities_years=mats,
        tenors=list(tenors_norm),
    )

    return params, stats


def calibrate_nss_from_series(
    series,
    *,
    tenors: Optional[Sequence[str]] = None,
    **kwargs
) -> Tuple[NSSParams, NSSFitStats]:
    """
    Convenience wrapper allowing a pandas Series-like object.

    If `tenors` is not provided, uses series.index.
    """
    try:
        import pandas as pd  # local import to avoid hard dependency here
    except Exception:
        pd = None  # noqa: N806

    if tenors is None:
        if hasattr(series, "index"):
            tenors = list(series.index)
        else:
            raise ValueError("tenors must be provided if series has no index.")

    values = list(series.values) if hasattr(series, "values") else list(series)
    return calibrate_nss(tenors, values, **kwargs)


def calibrate_nss_for_date(
    yield_df,
    date=None,
    *,
    tenors: Optional[Sequence[str]] = None,
    **kwargs
) -> Tuple[NSSParams, NSSFitStats]:
    """
    Calibrate NSS for a specific date from a yield history DataFrame.

    Parameters
    ----------
    yield_df:
        DataFrame indexed by dates with tenor columns.
    date:
        A date-like index key. If None, uses latest date.
    tenors:
        Optional explicit tenor list. If None, uses yield_df.columns.
    kwargs:
        Passed to calibrate_nss.

    Returns
    -------
    (NSSParams, NSSFitStats)
    """
    if tenors is None:
        tenors = list(yield_df.columns)

    if date is None:
        date = yield_df.index.max()

    row = yield_df.loc[date]

    # Support row being Series
    values = row.values if hasattr(row, "values") else row

    return calibrate_nss(tenors, values, **kwargs)


def calibrate_nss_latest(
    yield_df,
    *,
    tenors: Optional[Sequence[str]] = None,
    **kwargs
) -> Tuple[NSSParams, NSSFitStats]:
    """
    Simple convenience helper for the most recent curve snapshot.
    """
    return calibrate_nss_for_date(yield_df, date=None, tenors=tenors, **kwargs)


# ----------------------------
# Optional tiny utility
# ----------------------------

def guess_initial_nss(
    tenors: Sequence[str],
    observed_yields: Sequence[float],
) -> np.ndarray:
    """
    Exposed helper for building a reasonable starting point.
    """
    tenors_norm = [normalize_tenor(t) for t in tenors]
    mats = np.array([tenor_to_years(t) for t in tenors_norm], dtype=float)
    y = np.asarray(observed_yields, dtype=float)

    mask = np.isfinite(y)
    mats = mats[mask]
    y = y[mask]

    if len(y) == 0:
        return np.array([0.03, -0.02, 0.02, 0.01, 1.0, 3.0], dtype=float)

    order = np.argsort(mats)
    mats = mats[order]
    y = y[order]

    beta0 = float(y[-1])
    beta1 = -0.02
    beta2 = 0.02
    beta3 = 0.01
    tau1 = 1.0
    tau2 = 3.0

    return np.array([beta0, beta1, beta2, beta3, tau1, tau2], dtype=float)
