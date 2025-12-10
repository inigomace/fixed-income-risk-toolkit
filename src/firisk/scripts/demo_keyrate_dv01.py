"""
Demo: Key-rate DV01 using NSS recalibration

Run from Spyder or terminal.

This script:
1) Loads a yield history CSV
2) Selects the latest date
3) Builds a sample fixed-coupon bond
4) Computes key-rate DV01 for your 3M–10Y tenor set

Expected to work even if your working directory is not the repo root.
"""

from __future__ import annotations

from pathlib import Path
import pandas as pd

from firisk.data.loaders import load_yield_history
from firisk.instruments.bond import FixedCouponBond
from firisk.risk.keyrate import compute_keyrate_dv01_with_settlement


def resolve_yields_path() -> Path:
    """
    Tries common project locations for yields.csv.

    Priority:
    1) Repo-level data/raw/yields.csv
    2) Package-contained src/firisk/data/yields.csv
    """
    # scripts/ lives at repo root in the intended layout
    root = Path(__file__).resolve().parent.parent

    candidates = [
        root / "data" / "yields.csv"
    ]

    for p in candidates:
        if p.exists():
            return p

    # If nothing found, raise a helpful error
    msg = "Could not find yields.csv. Tried:\n" + "\n".join(str(c) for c in candidates)
    raise FileNotFoundError(msg)


def main():
    # 1) Locate data
    csv_path = resolve_yields_path()
    print(f"Using yields file: {csv_path}")

    # 2) Load clean yield history
    df = load_yield_history(csv_path)

    # 3) Pick latest date
    latest = df.index.max()
    yields_row = df.loc[latest].to_dict()

    print(f"Latest curve date: {latest.date()}")
    print("Tenors:", list(df.columns))

    # 4) Define a sample bond
    bond = FixedCouponBond(
        maturity_date=pd.Timestamp("2030-01-01"),
        coupon_rate=0.045,
        notional=100,
        frequency=2
    )

    # 5) Compute key-rate DV01
    res = compute_keyrate_dv01_with_settlement(
        bond,
        yields_row,
        settlement_date=latest,
        bump_bp=1.0
    )

    # 6) Display results nicely
    kr = (
        pd.Series(res.keyrate_dv01, name="KeyRateDV01")
        .to_frame()
        .assign(BumpedPrice=pd.Series(res.bumped_prices))
    )

    kr.loc["BASE"] = [None, res.base_price]  # add base price row

    print("\nKey-rate DV01 results (price change for +1bp):")
    print(kr)

    # 7) Optional: save output for your notebook/README
    out_dir = Path(__file__).resolve().parent
    out_path = out_dir / "keyrate_dv01_output.csv"
    kr.to_csv(out_path)
    print(f"\nSaved results to: {out_path}")


if __name__ == "__main__":
    main()
