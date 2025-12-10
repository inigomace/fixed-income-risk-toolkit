# Fixed Income Risk Toolkit (NSS Yield Curve, Bond Pricing, DV01 & VaR)

A compact fixed-income risk engine built in Python that:

- Calibrates **Nelson–Siegel–Svensson (NSS)** yield curves
- Prices **fixed-coupon government bonds**
- Computes **key-rate DV01 / PVBP**
- Runs **parallel / steepener / flattener** curve stress scenarios
- Estimates **historical** and **Monte Carlo VaR**
- Aggregates risk at the **portfolio** level
- Ships with **tests** and **demo scripts** for reproducible results

Designed as a learning project and portfolio piece for rates / risk / quant internship applications.

---

## 1. Features

### Yield Curve Modeling
- NSS parametric curve implementation
- Single-date calibration using real Treasury-style history
- Curve object exposing:
  - model yields
  - zero rates (model-implied)
  - discount factors

### Instruments
- Fixed-coupon bullet bond support
- Cashflow schedule generation
- Discounted PV pricing via the NSS curve

### Risk
- **Key-rate DV01 / PVBP**
  - bump-and-reprice by tenor
  - recalibrates NSS per bump
- **Curve stress testing**
  - parallel
  - steepener
  - flattener
- **VaR**
  - historical full revaluation
  - Monte Carlo full revaluation

### Portfolio
- Minimal portfolio container holding multiple bond positions
- Portfolio PV from yield snapshots
- Portfolio-level:
  - key-rate DV01
  - stress tests
  - historical VaR
  - Monte Carlo VaR

---

## 2. Methodology

- **Curve:** NSS fitted by least squares to observed tenor yields.
- **Pricing:** fixed-coupon bullet cashflows discounted using NSS-implied discount factors.
- **Key-rate DV01:** bump a single tenor by 1bp, refit NSS, reprice, and record price change.
- **Stress:** apply parallel/steepener/flattener shocks to tenor yields, refit NSS, reprice.
- **VaR:** full revaluation using historical tenor moves and multivariate-normal Monte Carlo shocks.
- **Portfolio:** aggregates bond PV and reuses the same risk engines through a shared pricing interface.

For implementation assumptions and defaults (tenors, day count, bump sizes, VaR lookbacks), see **ASSUMPTIONS.md**.

---

## 3. Tech Stack

- **Python:** 3.10+ recommended
- **Core:** `numpy`, `pandas`, `scipy`, `matplotlib`
- **Testing:** `pytest`

---

## 4. Project Structure

Current structure is package-first with demos and tests inside the `firisk` namespace:

```text
.
├─ README.md
├─ ASSUMPTIONS.md
├─ pyproject.toml
└─ src/
   └─ firisk/
      ├─ __init__.py
      ├─ arc/
      │  └─ test_loader.py              # dev scratch / experiments
      ├─ curve/
      │  ├─ __init__.py
      │  ├─ nss.py                      # NSS formula + helpers
      │  ├─ calibration.py              # least-squares calibration
      │  └─ curve_object.py             # NSSCurve class (yields + DFs)
      ├─ data/
      │  ├─ __init__.py
      │  ├─ loaders.py                  # load + validate yield history
      │  └─ yields.csv                  # small reproducible dataset
      ├─ instruments/
      │  ├─ __init__.py
      │  ├─ cashflows.py                # coupon schedule + CF generation
      │  └─ bond.py                     # FixedCouponBond pricing
      ├─ portfolio/
      │  ├─ __init__.py
      │  └─ portfolio.py                # Portfolio + Position
      ├─ risk/
      │  ├─ __init__.py
      │  ├─ keyrate.py                  # key-rate DV01 engine
      │  ├─ stress.py                   # curve scenario shocks
      │  ├─ var_historical.py           # historical VaR
      │  └─ var_montecarlo.py           # Monte Carlo VaR
      ├─ scripts/
      │  ├─ demo_bond_pricing.py
      │  ├─ demo_keyrate_dv01.py
      │  ├─ demo_stress_tests.py
      │  ├─ demo_var_historical.py
      │  ├─ demo_var_montecarlo.py
      │  ├─ demo_portfolio_risk.py
      │  ├─ keyrate_dv01_output.csv     # generated artifact
      │  ├─ stress_test_output.csv      # generated artifact
      │  └─ historical_var_output.csv   # generated artifact
      ├─ tests/
      │  ├─ test_dates.py
      │  ├─ test_nss.py
      │  ├─ test_calibration.py
      │  ├─ test_curve-object.py
      │  ├─ test_cashflows.py
      │  ├─ test_bond.py
      │  ├─ test_keyrate.py
      │  ├─ test_stress.py
      │  ├─ test_var.py
      │  └─ test_portfolio.py
      ├─ utils/
      │  ├─ __init__.py
      │  └─ dates.py                    # tenor parsing + ACT/365
      └─ fixed_income_risk_toolkit.egg-info/
