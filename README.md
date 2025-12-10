# Fixed Income Risk Toolkit (NSS Yield Curve, DV01 & VaR)

A small fixed-income risk engine built in Python and Jupyter that:

- Calibrates **Nelson–Siegel–Svensson (NSS)** yield curves
- Prices fixed-coupon government bonds and portfolios
- Computes **key-rate DV01 / PVBP** by tenor bucket
- Runs **parallel / steepener / flattener** curve stress scenarios
- Estimates **historical** and **Monte Carlo VaR**
- Ships as a **reproducible Git/Jupyter pipeline** with tests and a methods note

Designed as a learning project and portfolio piece for rates / risk / quant internship applications.

---

## 1. Features

- **Yield Curve Modeling**
  - Nelson–Siegel–Svensson (NSS) parametric curve
  - Single-date and time-series calibration
  - Fitted parameters and fit error diagnostics saved to disk

- **Instrument & Portfolio Layer**
  - Fixed-coupon bullet bonds (e.g. Treasuries)
  - Cashflow generation and discounting from the NSS curve
  - Simple portfolio abstraction with per-instrument PV breakdown

- **Risk Sensitivities**
  - Parallel DV01 / PVBP
  - **Key-rate DV01** by tenor bucket (e.g. 2Y, 5Y, 10Y, 30Y)
  - Bump-and-reprice methodology with clear bump size conventions

- **Curve Stress Testing**
  - Configurable **parallel shifts**
  - **Steepener** and **flattener** scenarios with tunable shock sizes
  - Portfolio P&L under each scenario with intuitive plots

- **Value at Risk (VaR)**
  - **Historical VaR**: non-parametric, based on past curve moves
  - **Monte Carlo VaR**: multivariate normal shocks to key-rate yields
  - 95% and 99% VaR with reproducible random seeds

- **Engineering Hygiene**
  - Modular `src/` layout
  - Unit tests with `pytest`
  - Optional `pre-commit` hooks (`black`, `ruff`)
  - CI workflow (GitHub Actions) to run tests and lint on push

---

## 2. Tech Stack

- **Language:** Python (3.10+ recommended)
- **Core libraries:** `numpy`, `pandas`, `scipy`, `matplotlib`
- **Dev tooling:** `pytest`, `black`, `ruff`, `pre-commit`
- **Interface:** Jupyter notebooks for analysis and visualization

---

## 3. Project Structure

```text
.
├─ README.md
├─ pyproject.toml        # Project + dependency config (or requirements.txt)
├─ src/
│  └─ firisk/
│     ├─ data/
│     │  ├─ sources.py      # Data source abstractions (e.g. local CSV)
│     │  └─ loaders.py      # Load + validate yield history
│     ├─ curve/
│     │  ├─ nss.py          # NSS model functions
│     │  ├─ calibration.py  # Single-date & time-series calibration
│     │  └─ curve_object.py # NSSCurve class: yields, zeros, discount factors
│     ├─ instruments/
│     │  ├─ cashflows.py    # Fixed coupon cashflow generation
│     │  └─ bond.py         # FixedCouponBond and pricing
│     ├─ portfolio/
│     │  ├─ portfolio.py    # Portfolio container + PV
│     │  └─ config.py       # Read portfolio configs (CSV/YAML)
│     ├─ risk/
│     │  ├─ keyrate.py      # Key-rate DV01 / PVBP
│     │  ├─ stress.py       # Parallel, steepener, flattener scenarios
│     │  ├─ var_historical.py   # Historical VaR
│     │  └─ var_montecarlo.py   # Monte Carlo VaR
│     └─ utils/
│        ├─ dates.py        # Tenor parsing, year fractions
│        ├─ math.py         # Helper math functions
│        └─ validation.py   # Input validation helpers
├─ notebooks/
│  ├─ 01_data_and_portfolio.ipynb
│  ├─ 02_nss_calibration_single_date.ipynb
│  ├─ 03_nss_calibration_timeseries.ipynb
│  ├─ 04_bond_pricing_sanity.ipynb
│  ├─ 05_keyrate_dv01.ipynb
│  ├─ 06_stress_tests.ipynb
│  └─ 07_var_methods.ipynb
├─ data/
│  ├─ raw/        # e.g. raw yield history CSV (small sample for reproducibility)
│  └─ processed/  # cleaned yields, fitted NSS parameters, example portfolio
├─ docs/
│  ├─ METHODS.md      # Modeling choices and formulas
│  ├─ ASSUMPTIONS.md  # Day-count, frequency, data caveats
│  └─ MODEL_LIMITS.md # Known limitations + future improvements
├─ tests/
│  ├─ test_nss.py
│  ├─ test_calibration.py
│  ├─ test_curve_object.py
│  ├─ test_bond.py
│  ├─ test_keyrate.py
│  ├─ test_stress.py
│  └─ test_var.py
├─ .github/workflows/ci.yml
├─ .pre-commit-config.yaml
└─ Makefile
