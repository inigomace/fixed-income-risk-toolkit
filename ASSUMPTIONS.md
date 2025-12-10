# ASSUMPTIONS.md — Fixed Income Risk Toolkit

This document lists the practical modeling and implementation assumptions used in this project.
The goal is consistency and interview-ready clarity rather than full production realism.

---

## 1. Market Data

- The toolkit uses a **single sovereign curve** to keep the narrative simple.
- The dataset is treated as **U.S. Treasury-style par yields** by standard tenor.
- The default tenor set used across the toolkit is:

  - 3M, 6M, 1Y, 2Y, 3Y, 5Y, 7Y, 10Y

- The yield history is structured as:

  - **index:** dates  
  - **columns:** tenors  
  - **values:** yields

---

## 2. Units and Standardization

- **Yields are stored as decimals** (not percent).

  - Example: 4.50% → 0.045

- This convention is assumed everywhere:
  - curve calibration  
  - bond pricing  
  - DV01  
  - stress testing  
  - VaR

- Any input data that is in percent must be converted before use.

---

## 3. Yield Curve Model

- The curve model is **Nelson–Siegel–Svensson (NSS)**.
- Calibration uses **least squares** to fit NSS parameters to the observed tenor snapshot.
- The fitted NSS curve is treated as:
  - a smooth approximation of the tenor curve
  - sufficient for educational pricing/risk demos

---

## 4. Discounting

- Discount factors are derived from the NSS-implied yield curve.
- A simplified discounting convention is used:

  - **Continuous compounding**

- This is a modeling convenience to ensure a clean and consistent pipeline.

---

## 5. Instruments

- The instrument layer supports:
  - **Fixed-coupon bullet bonds**
- Assumptions:
  - no embedded options  
  - no inflation linkage  
  - no floating-rate coupons  
  - principal repaid at maturity  

---

## 6. Day Count and Time

- A simplified day-count convention is used:

  - **ACT/365**

- This choice is applied uniformly across pricing and risk.

---

## 7. DV01 / PVBP

- PVBP and DV01 are computed using **bump-and-reprice**.
- Key-rate DV01:
  - each tenor is bumped independently by a default:

    - **+1 bp**

  - the NSS curve is **recalibrated** after each bump
  - portfolio and bond pricing is rerun to compute sensitivity

---

## 8. Stress Testing

- Three standard scenario types are implemented:
  - **parallel**
  - **steepener**
  - **flattener**

- Default shock size:

  - **25 bp**

- Shocks are applied to **observed tenor yields**, then:
  - NSS is recalibrated
  - instruments/portfolio are repriced
  - P&L is computed as stressed price minus base price

---

## 9. Value at Risk (VaR)

### 9.1 Historical VaR
- Uses a non-parametric approach based on:
  - historical daily changes in tenor yields
- Default lookback:

  - **252 trading days**

- Uses **full revaluation**:
  - apply historical tenor shocks to the base curve
  - recalibrate NSS
  - reprice to generate P&L distribution

### 9.2 Monte Carlo VaR
- Uses a simple multivariate normal model of tenor yield changes.
- The covariance matrix is estimated from:
  - historical daily changes
- Default simulations:

  - **2,000–5,000** (demo-dependent)

- Uses **full revaluation**:
  - simulate tenor shocks
  - recalibrate NSS
  - reprice

### 9.3 Confidence Levels
- Default confidence levels:

  - **95% and 99%**

---

## 10. Portfolio Aggregation

- The portfolio is a minimal container of:
  - (instrument, quantity)
- Portfolio PV is:

  - sum of quantity-weighted instrument PVs

- The portfolio implements a bond-like interface:
  - `price(curve, settlement_date)`
- This allows reuse of the same risk engines at:
  - bond level  
  - portfolio level  

---

## 11. What This Toolkit Does NOT Model

These are intentionally excluded to keep the scope interview-sized:

- bootstrapping from real coupon instruments  
- bid/ask spreads and liquidity  
- funding curves / OIS discounting  
- convexity adjustments  
- credit risk  
- optionality and callable structures  
- regulatory VaR frameworks  

---

## 12. Intended Use

This toolkit is designed to demonstrate:

- clean Python structuring  
- parametric yield curve calibration  
- consistent bond pricing  
- practical risk measurement workflows  
- reproducible research via tests and demos  

It is not intended as a production risk system.
