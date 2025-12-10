from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Sequence, Union, overload

import numpy as np

# Optional import: depends on your Step 2 utils
# If you haven't created these yet, you can comment these two lines
# and only use maturity_years-based functions for now.
from firisk.utils.dates import normalize_tenor, tenor_to_years


ArrayLike = Union[float, int, Sequence[float], np.ndarray]


# ----------------------------
# Parameter container
# ----------------------------

@dataclass(frozen=True)
class NSSParams:
    """
    Nelson–Siegel–Svensson parameters.

    y(t) = β0
         + β1 * L1(t, τ1)
         + β2 * S1(t, τ1)
         + β3 * S2(t, τ2)

    Where:
      L1 is the "level/long" loading
      S1 and S2 are "slope/curvature" style loadings.
    """
    beta0: float
    beta1: float
    beta2: float
    beta3: float
    tau1: float
    tau2: float

    def as_array(self) -> np.ndarray:
        return np.array([self.beta0, self.beta1, self.beta2, self.beta3, self.tau1, self.tau2], dtype=float)

    @staticmethod
    def from_array(x: Sequence[float]) -> "NSSParams":
        if len(x) != 6:
            raise ValueError("NSSParams.from_array expects length-6 sequence.")
        b0, b1, b2, b3, t1, t2 = map(float, x)
        return NSSParams(b0, b1, b2, b3, t1, t2)


# ----------------------------
# Internal numeric helpers
# ----------------------------

def _to_1d_float_array(x: ArrayLike) -> np.ndarray:
    arr = np.asarray(x, dtype=float)
    if arr.ndim == 0:
        arr = arr.reshape(1)
    return arr.ravel()


def _assert_positive(name: str, arr: np.ndarray) -> None:
    if np.any(~np.isfinite(arr)):
        raise ValueError(f"{name} contains non-finite values.")
    if np.any(arr <= 0):
        raise ValueError(f"{name} must be strictly positive.")


def _safe_loading_factor(x: np.ndarray) -> np.ndarray:
    """
    Compute (1 - exp(-x)) / x with a stable series expansion for small x.

    For small x:
        (1 - e^{-x}) / x ≈ 1 - x/2 + x^2/6 - x^3/24

    This avoids numerical issues as x -> 0.
    """
    x = np.asarray(x, dtype=float)
    out = np.empty_like(x)

    small = np.abs(x) < 1e-8
    large = ~small

    # series expansion for small x
    xs = x[small]
    out[small] = 1.0 - xs / 2.0 + (xs ** 2) / 6.0 - (xs ** 3) / 24.0

    # standard formula for the rest
    xl = x[large]
    out[large] = (1.0 - np.exp(-xl)) / xl

    return out


# ----------------------------
# Core NSS loadings
# ----------------------------

def nss_loadings(
    maturity_years: ArrayLike,
    tau1: float,
    tau2: float
) -> np.ndarray:
    """
    Return the 3 NSS loading vectors evaluated at maturities.

    Returns an array of shape (n, 3) with columns:
      L1(t, tau1)
      S1(t, tau1)
      S2(t, tau2)

    Where:
      L1 = (1 - e^{-t/tau1}) / (t/tau1)
      S1 = L1 - e^{-t/tau1}
      S2 = (1 - e^{-t/tau2}) / (t/tau2) - e^{-t/tau2}
    """
    t = _to_1d_float_array(maturity_years)
    _assert_positive("maturity_years", t)

    tau1 = float(tau1)
    tau2 = float(tau2)
    if not np.isfinite(tau1) or tau1 <= 0:
        raise ValueError("tau1 must be strictly positive.")
    if not np.isfinite(tau2) or tau2 <= 0:
        raise ValueError("tau2 must be strictly positive.")

    x1 = t / tau1
    x2 = t / tau2

    L1 = _safe_loading_factor(x1)
    e1 = np.exp(-x1)
    e2 = np.exp(-x2)

    S1 = L1 - e1
    L2 = _safe_loading_factor(x2)
    S2 = L2 - e2

    return np.column_stack([L1, S1, S2])


# ----------------------------
# Core NSS yield function
# ----------------------------

@overload
def nss_yield(
    maturity_years: float,
    beta0: float, beta1: float, beta2: float, beta3: float,
    tau1: float, tau2: float
) -> float:
    ...


@overload
def nss_yield(
    maturity_years: ArrayLike,
    beta0: float, beta1: float, beta2: float, beta3: float,
    tau1: float, tau2: float
) -> np.ndarray:
    ...


def nss_yield(
    maturity_years: ArrayLike,
    beta0: float, beta1: float, beta2: float, beta3: float,
    tau1: float, tau2: float
):
    """
    Compute NSS model yields for given maturities in years.

    Model:
      y(t) = β0
           + β1 * L1(t, τ1)
           + β2 * S1(t, τ1)
           + β3 * S2(t, τ2)

    Inputs/outputs are in decimal yield terms.
    """
    t = _to_1d_float_array(maturity_years)
    _assert_positive("maturity_years", t)

    load = nss_loadings(t, tau1=tau1, tau2=tau2)  # (n,3)
    L1 = load[:, 0]
    S1 = load[:, 1]
    S2 = load[:, 2]

    b0 = float(beta0)
    b1 = float(beta1)
    b2 = float(beta2)
    b3 = float(beta3)

    y = b0 + b1 * L1 + b2 * S1 + b3 * S2

    # Return scalar if scalar input
    arr_in = np.asarray(maturity_years)
    if arr_in.ndim == 0:
        return float(y[0])
    return y


def nss_yield_from_params(maturity_years: ArrayLike, params: NSSParams):
    """
    Convenience wrapper using NSSParams.
    """
    return nss_yield(
        maturity_years,
        params.beta0, params.beta1, params.beta2, params.beta3,
        params.tau1, params.tau2
    )


# ----------------------------
# Tenor-based helpers
# ----------------------------

def nss_yield_for_tenors(
    tenors: Iterable[str],
    beta0: float, beta1: float, beta2: float, beta3: float,
    tau1: float, tau2: float
) -> np.ndarray:
    """
    Compute NSS yields for a list of tenor strings like ["3M","1Y","10Y"].

    Returns yields in the same order as input.
    """
    tenors_norm = [normalize_tenor(t) for t in tenors]
    mats = np.array([tenor_to_years(t) for t in tenors_norm], dtype=float)
    return nss_yield(mats, beta0, beta1, beta2, beta3, tau1, tau2)


def nss_yield_for_tenors_from_params(
    tenors: Iterable[str],
    params: NSSParams
) -> np.ndarray:
    """
    Convenience wrapper using NSSParams.
    """
    return nss_yield_for_tenors(
        tenors,
        params.beta0, params.beta1, params.beta2, params.beta3,
        params.tau1, params.tau2
    )
