from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, List, Optional, Sequence, Union

import numpy as np

from firisk.curve.nss import NSSParams, nss_yield, nss_yield_from_params
from firisk.utils.dates import normalize_tenor, tenor_to_years, sort_tenors


ArrayLike = Union[float, int, Sequence[float], np.ndarray]


@dataclass(frozen=True)
class NSSCurve:
    """
    A lightweight, reusable NSS curve object.

    This class is intentionally small and dependency-light so it can be used by:
      - bond pricing
      - key-rate DV01 / PVBP
      - stress scenarios
      - VaR engines

    Assumptions (document in ASSUMPTIONS.md):
      - Yields are in decimal (e.g., 0.045 not 4.5)
      - Discount factors are computed using continuous comp:
            DF(t) = exp(-y(t) * t)
        This is a standard, clean modeling choice for educational risk engines.
    """
    beta0: float
    beta1: float
    beta2: float
    beta3: float
    tau1: float
    tau2: float

    # ----------------------------
    # Constructors
    # ----------------------------

    @classmethod
    def from_params(cls, params: NSSParams) -> "NSSCurve":
        return cls(
            beta0=params.beta0,
            beta1=params.beta1,
            beta2=params.beta2,
            beta3=params.beta3,
            tau1=params.tau1,
            tau2=params.tau2,
        )

    def to_params(self) -> NSSParams:
        return NSSParams(
            beta0=float(self.beta0),
            beta1=float(self.beta1),
            beta2=float(self.beta2),
            beta3=float(self.beta3),
            tau1=float(self.tau1),
            tau2=float(self.tau2),
        )

    # ----------------------------
    # Core curve outputs
    # ----------------------------

    def yield_at(self, maturity_years: ArrayLike):
        """
        Model-implied yield at maturity t (in years).

        Returns float if input is scalar, else numpy array.
        """
        return nss_yield(
            maturity_years,
            self.beta0, self.beta1, self.beta2, self.beta3,
            self.tau1, self.tau2
        )

    # Alias (some people prefer 'zero_rate')
    zero_rate = yield_at

    def discount_factor(self, maturity_years: ArrayLike):
        """
        Continuous-comp discount factor for maturity t in years.

        DF(t) = exp(-y(t) * t)
        """
        t = np.asarray(maturity_years, dtype=float)
        y = np.asarray(self.yield_at(t), dtype=float)

        # Handle scalar-vs-array consistency
        df = np.exp(-y * t)

        if t.ndim == 0:
            return float(df)
        return df

    def forward_rate_simple(
        self,
        t1: float,
        t2: float
    ) -> float:
        """
        Simple forward rate implied by discount factors between two maturities.

        This is optional but handy for future extensions.

        f(t1,t2) ~ (ln DF(t1) - ln DF(t2)) / (t2 - t1)
        """
        t1 = float(t1)
        t2 = float(t2)
        if t1 <= 0 or t2 <= 0 or t2 <= t1:
            raise ValueError("Require 0 < t1 < t2 for forward rate.")

        df1 = self.discount_factor(t1)
        df2 = self.discount_factor(t2)

        return (np.log(df1) - np.log(df2)) / (t2 - t1)

    # ----------------------------
    # Tenor-based convenience
    # ----------------------------

    def yields_for_tenors(self, tenors: Iterable[str]) -> np.ndarray:
        """
        Compute model yields for a list of tenor strings.

        Input order is preserved.
        """
        tenors_norm = [normalize_tenor(t) for t in tenors]
        mats = np.array([tenor_to_years(t) for t in tenors_norm], dtype=float)
        return np.asarray(self.yield_at(mats), dtype=float)

    def discount_factors_for_tenors(self, tenors: Iterable[str]) -> np.ndarray:
        """
        Compute discount factors for a list of tenor strings.
        """
        tenors_norm = [normalize_tenor(t) for t in tenors]
        mats = np.array([tenor_to_years(t) for t in tenors_norm], dtype=float)
        return np.asarray(self.discount_factor(mats), dtype=float)

    # ----------------------------
    # Grids / plotting helpers
    # ----------------------------

    def curve_grid(
        self,
        maturities_years: Sequence[float]
    ) -> np.ndarray:
        """
        Return yields for an explicit maturity grid (in years).
        """
        mats = np.asarray(maturities_years, dtype=float)
        return np.asarray(self.yield_at(mats), dtype=float)

    def default_tenor_snapshot(
        self,
        tenors: Optional[Sequence[str]] = None
    ) -> dict:
        """
        Convenience method to produce a dict of {tenor: yield}
        for your canonical curve snapshot.
        """
        if tenors is None:
            # Keep your current stable tenor set
            tenors = ["3M", "6M", "1Y", "2Y", "3Y", "5Y", "7Y", "10Y"]

        tenors_norm = [normalize_tenor(t) for t in tenors]
        ys = self.yields_for_tenors(tenors_norm)
        return {t: float(y) for t, y in zip(tenors_norm, ys)}
