"""
Demo: Portfolio PV + Key-Rate DV01 + Stress + VaR

This script:
1) Finds yields.csv
2) Loads yield history
3) Builds a small 2-bond portfolio
4) Runs:
   - portfolio PV
   - key-rate DV01
   - stress tests
   - historical VaR
   - Monte Carlo VaR

Designed to be Spyder-friendly.
"""

from __future__ import annotations

from pathlib import Path
import pandas as pd

from firisk.data.loaders import load_yield_history
from firisk.instruments.bond import FixedCouponBond
from firisk.portfolio.portfolio import Portfolio, Position


def resolve_yields_path() -> Path:
    here = Path(__file__).resolve()

    # Try walking upward to find standard layouts
    candidates = []
    for i in range(1, 7):
        root = here.parents[i]
        candidates.extend([
            root / "data" / "raw" / "yields.csv",
            root / "src" / "firisk" / "data" / "yields.csv",
        ])

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

    # Two simple example bonds
    bond1 = FixedCouponBond(
        maturity_date=pd.Timestamp("2028-01-01"),
        coupon_rate=0.040,
        notional=100,
        frequency=2
    )

    bond2 = FixedCouponBond(
        maturity_date=pd.Timestamp("2032-01-01"),
        coupon_rate=0.050,
        notional=100,
        frequency=2
    )

    # Quantities = number of bonds
    portfolio = Portfolio([
        Position(bond1, quantity=2.0),
        Position(bond2, quantity=3.0),
    ])

    # ----------------------------
    # PV
    # ----------------------------
    pv = portfolio.price_from_yields(yields_row, settlement_date=latest)
    print(f"\nPortfolio PV (approx): {pv:.4f}")

    # ----------------------------
    # Key-rate DV01
    # ----------------------------
    kr_res = portfolio.keyrate_dv01(
        yields_row,
        settlement_date=latest,
        bump_bp=1.0
    )

    kr_table = (
        pd.Series(kr_res.keyrate_dv01, name="KeyRateDV01")
        .to_frame()
        .assign(BumpedPrice=pd.Series(kr_res.bumped_prices))
    )
    kr_table.loc["BASE"] = [None, kr_res.base_price]

    print("\nPortfolio Key-rate DV01 (price change for +1bp):")
    print(kr_table)

    # ----------------------------
    # Stress
    # ----------------------------
    st_res = portfolio.stress_tests(
        yields_row,
        settlement_date=latest,
        shock_bp=25.0
    )

    st_rows = []
    for name, s in st_res.scenarios.items():
        st_rows.append({"scenario": name, "price": s.price, "pnl": s.pnl})

    st_table = pd.DataFrame(st_rows).set_index("scenario")
    st_table.loc["BASE", "price"] = st_res.base_price

    print("\nPortfolio Stress Tests (shock = +25bp):")
    print(st_table)

    # ----------------------------
    # Historical VaR
    # ----------------------------
    hv = portfolio.historical_var(
        df,
        settlement_date=latest,
        base_date=latest,
        lookback_days=252,
        confidence_levels=(0.95, 0.99)
    )

    print("\nHistorical VaR (loss magnitude):")
    for cl, v in hv.var_by_level.items():
        print(f"{int(cl*100)}% VaR: {v:.4f}")

    # ----------------------------
    # Monte Carlo VaR
    # ----------------------------
    mv = portfolio.monte_carlo_var(
        df,
        settlement_date=latest,
        base_date=latest,
        lookback_days=252,
        n_sims=2000,  # keep lighter for interactive runs
        seed=42,
        confidence_levels=(0.95, 0.99)
    )

    print("\nMonte Carlo VaR (loss magnitude):")
    for cl, v in mv.var_by_level.items():
        print(f"{int(cl*100)}% VaR: {v:.4f}")

    # Optional outputs for easy inspection
    out_dir = Path(__file__).resolve().parent
    kr_table.to_csv(out_dir / "portfolio_keyrate_dv01_output.csv")
    st_table.to_csv(out_dir / "portfolio_stress_output.csv")
    pd.Series(hv.var_by_level, name="HistoricalVaR").to_csv(out_dir / "portfolio_historical_var_output.csv")
    pd.Series(mv.var_by_level, name="MonteCarloVaR").to_csv(out_dir / "portfolio_montecarlo_var_output.csv")

    print(f"\nSaved outputs to: {out_dir}")


if __name__ == "__main__":
    main()
