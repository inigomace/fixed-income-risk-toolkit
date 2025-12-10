"""
Demo: Monte Carlo VaR (full revaluation)
"""

from __future__ import annotations

from pathlib import Path
import pandas as pd

from firisk.data.loaders import load_yield_history
from firisk.instruments.bond import FixedCouponBond
from firisk.risk.var_montecarlo import compute_monte_carlo_var_with_settlement


def resolve_yields_path() -> Path:
    root = Path(__file__).resolve().parent.parent
    candidates = [
        root / "data" / "yields.csv",
    ]
    for p in candidates:
        if p.exists():
            return p
    raise FileNotFoundError("Could not find yields.csv in standard locations.")


def main():
    csv_path = resolve_yields_path()
    print(f"Using yields file: {csv_path}")

    df = load_yield_history(csv_path)
    latest = df.index.max()

    bond = FixedCouponBond(
        maturity_date=pd.Timestamp("2030-01-01"),
        coupon_rate=0.045,
        notional=100,
        frequency=2,
    )

    res = compute_monte_carlo_var_with_settlement(
        bond,
        df,
        settlement_date=latest,
        base_date=latest,
        lookback_days=252,
        n_sims=5000,
        seed=42,
        confidence_levels=(0.95, 0.99),
    )

    print("\nMonte Carlo VaR (loss magnitude):")
    for cl, v in res.var_by_level.items():
        print(f"{int(cl*100)}% VaR: {v:.4f}")

    out = Path(__file__).resolve().parent / "montecarlo_var_output.csv"
    pd.Series(res.var_by_level, name="VaR").to_csv(out)
    print(f"\nSaved VaR summary to: {out}")


if __name__ == "__main__":
    main()
