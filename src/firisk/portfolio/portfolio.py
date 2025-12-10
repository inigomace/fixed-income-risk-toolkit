from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, List, Mapping, Optional, Sequence

import numpy as np

from firisk.curve.calibration import calibrate_nss
from firisk.curve.curve_object import NSSCurve
from firisk.utils.dates import normalize_tenor, sort_tenors

# Risk engines (already generic "bond-like" interfaces)
from firisk.risk.keyrate import compute_keyrate_dv01_with_settlement
from firisk.risk.stress import run_stress_tests_with_settlement
from firisk.risk.var_historical import compute_historical_var_with_settlement
from firisk.risk.var_montecarlo import compute_monte_carlo_var_with_settlement


@dataclass(frozen=True)
class Position:
    """
    A position in a single instrument.

    quantity interpretation:
      - number of bonds of the instrument's notional
      - e.g. quantity=10 means 10 bonds each with notional=100 (by default)
    """
    instrument: object
    quantity: float = 1.0


class Portfolio:
    """
    Very small portfolio container.

    Key design:
      - Implements price(curve, settlement_date),
        so it can be passed directly into risk engines
        designed for 'bond-like' objects.
    """

    def __init__(self, positions: Optional[Sequence[Position]] = None):
        self.positions: List[Position] = list(positions) if positions else []

    def add(self, instrument, quantity: float = 1.0) -> None:
        self.positions.append(Position(instrument=instrument, quantity=float(quantity)))

    # -----------------------------------------
    # Core pricing
    # -----------------------------------------

    def price(self, curve: NSSCurve, settlement_date) -> float:
        """
        Price portfolio given a curve.
        """
        total = 0.0
        for pos in self.positions:
            instr_price = float(pos.instrument.price(curve, settlement_date=settlement_date))
            total += float(pos.quantity) * instr_price
        return float(total)

    def price_from_yields(
        self,
        yields_by_tenor: Mapping[str, float],
        settlement_date,
        *,
        tenors: Optional[Sequence[str]] = None
    ) -> float:
        """
        Convenience method:
          yields snapshot -> calibrate NSS -> build curve -> price portfolio
        """
        if tenors is None:
            tenors = list(yields_by_tenor.keys())

        tenors_norm = sort_tenors([normalize_tenor(t) for t in tenors])

        missing = [t for t in tenors_norm if t not in yields_by_tenor]
        if missing:
            raise ValueError(f"Missing tenors in yields_by_tenor: {missing}")

        obs = np.array([float(yields_by_tenor[t]) for t in tenors_norm], dtype=float)

        params, _ = calibrate_nss(tenors_norm, obs)
        curve = NSSCurve.from_params(params)
        return self.price(curve, settlement_date=settlement_date)

    # -----------------------------------------
    # Portfolio-level wrappers around risk engines
    # -----------------------------------------

    def keyrate_dv01(
        self,
        yields_by_tenor: Mapping[str, float],
        settlement_date,
        *,
        key_tenors: Optional[Sequence[str]] = None,
        bump_bp: float = 1.0
    ):
        """
        Key-rate DV01 for the whole portfolio.

        Uses:
          compute_keyrate_dv01_with_settlement
        """
        return compute_keyrate_dv01_with_settlement(
            self,
            yields_by_tenor,
            settlement_date=settlement_date,
            key_tenors=key_tenors,
            bump_bp=bump_bp,
        )

    def stress_tests(
        self,
        yields_by_tenor: Mapping[str, float],
        settlement_date,
        *,
        stress_tenors: Optional[Sequence[str]] = None,
        shock_bp: float = 25.0
    ):
        """
        Parallel / steepener / flattener stress tests for the portfolio.
        """
        return run_stress_tests_with_settlement(
            self,
            yields_by_tenor,
            settlement_date=settlement_date,
            stress_tenors=stress_tenors,
            shock_bp=shock_bp,
        )

    def historical_var(
        self,
        yield_df,
        settlement_date,
        *,
        base_date=None,
        tenors: Optional[Sequence[str]] = None,
        lookback_days: int = 252,
        confidence_levels: Sequence[float] = (0.95, 0.99),
    ):
        """
        Historical VaR for portfolio.
        """
        return compute_historical_var_with_settlement(
            self,
            yield_df,
            settlement_date=settlement_date,
            base_date=base_date,
            tenors=tenors,
            lookback_days=lookback_days,
            confidence_levels=confidence_levels,
        )

    def monte_carlo_var(
        self,
        yield_df,
        settlement_date,
        *,
        base_date=None,
        tenors: Optional[Sequence[str]] = None,
        lookback_days: int = 252,
        n_sims: int = 5000,
        seed: int = 42,
        confidence_levels: Sequence[float] = (0.95, 0.99),
    ):
        """
        Monte Carlo VaR for portfolio.
        """
        return compute_monte_carlo_var_with_settlement(
            self,
            yield_df,
            settlement_date=settlement_date,
            base_date=base_date,
            tenors=tenors,
            lookback_days=lookback_days,
            n_sims=n_sims,
            seed=seed,
            confidence_levels=confidence_levels,
        )
