"""
Demo: Curve stress tests (parallel / steepener / flattener)

Run from Spyder or terminal.

This script:
1) Locates a yields.csv file
2) Loads a yield history
3) Uses the latest curve snapshot
4) Builds a sample fixed-coupon bond
5) Runs parallel / steepener / flattener stress tests
6) Prints a small summary table and saves it as CSV
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from firisk.data.loaders import load_yield_history
from firisk.instruments.bond import FixedCouponBond
from firisk.risk.stress import run_stress_tests_with_settlement


def resolve_yields_path() -> Path:
    """
    Tries common project locations for yields.csv.

    Priority:
    1) data/raw/yields.csv
    2) src/firisk/data/yields.csv
    """
    root = Path(__file__).resolve().parent.parent

    candidates = [
        root / "data" / "yields.csv",
    ]

    for p in candidates:
        if p.exists():
            return p

    msg = "Could not find yields.csv. Tried:\n" + "\n".join(str(c) for c in candidates)
    raise FileNotFoundError(msg)


def main():
    csv_path = resolve_yields_path()
    print(f"Using yields file: {csv_path}")

    df = load_yield_history(csv_path)

    latest = df.index.max()
    yields_row = df.loc[latest].to_dict()

    print(f"Latest curve date: {latest.date()}")
    print("Tenors:", list(df.columns))

    bond = FixedCouponBond(
        maturity_date=pd.Timestamp("2030-01-01"),
        coupon_rate=0.045,
        notional=100,
        frequency=2,
    )

    res = run_stress_tests_with_settlement(
        bond,
        yields_row,
        settlement_date=latest,
        shock_bp=25.0,  # 25bp = 0.25%
    )

    # Build a summary DataFrame
    rows = []
    for name, s in res.scenarios.items():
        rows.append(
            {
                "scenario": name,
                "price": s.price,
                "pnl": s.pnl,
            }
        )

    df_out = pd.DataFrame(rows).set_index("scenario")
    df_out.loc["BASE", "price"] = res.base_price

    print("\nStress test results (shock = +25bp):")
    print(df_out)

    out_path = Path(__file__).resolve().parent / "stress_test_output.csv"
    df_out.to_csv(out_path)
    print(f"\nSaved stress test summary to: {out_path}")


if __name__ == "__main__":
    main()
