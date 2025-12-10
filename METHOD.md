# METHODS.md — Fixed Income Risk Toolkit

This document describes the modeling choices, formulas, and implementation logic used in this project. The goal is to be clear, consistent, and reproducible rather than exhaustive or fully production-grade.

---

## 1. Scope of the Toolkit

This toolkit implements a compact fixed-income risk pipeline built around:

1) A single sovereign yield curve dataset (U.S. Treasury-style tenors).  
2) A parametric curve model (Nelson–Siegel–Svensson).  
3) Fixed-coupon bullet bond pricing.  
4) Risk measures:
   - key-rate DV01 / PVBP  
   - curve stress tests  
   - historical VaR  
   - Monte Carlo VaR  
5) Portfolio aggregation.

The implementation is intended as an educational and interview-ready demonstration of rates/risk mechanics.

---

## 2. Data Conventions

### 2.1 Yield Inputs

The yield history is represented as a table:

- **Index:** dates  
- **Columns:** standard tenors (project default)

Current default tenors used throughout the risk stack:

- `3M, 6M, 1Y, 2Y, 3Y, 5Y, 7Y, 10Y`

### 2.2 Yield Units

All yields in the codebase are treated as **decimals**, not percent:

- 4.50% → `0.045`

This is enforced by loader validation and assumed by all curve/risk functions.

---

## 3. Nelson–Siegel–Svensson (NSS) Yield Curve

### 3.1 Model Form

The NSS model represents a smooth yield curve using 6 parameters:

$$
y(t)=
\beta_0
+ \beta_1\,L_1(t,\tau_1)
+ \beta_2\,S_1(t,\tau_1)
+ \beta_3\,S_2(t,\tau_2)
$$

where:

$$
L_1(t,\tau)=\frac{1-e^{-t/\tau}}{t/\tau}
$$

$$
S_1(t,\tau)=L_1(t,\tau)-e^{-t/\tau}
$$

$$
S_2(t,\tau)=\frac{1-e^{-t/\tau}}{t/\tau}-e^{-t/\tau}
$$

Parameters:

- **β0**: long-term level  
- **β1**: short-end slope component  
- **β2, β3**: curvature components  
- **τ1, τ2**: shape/decay controls

### 3.2 Interpretation of Output

The model is used to produce:

- **model-implied yields** at arbitrary maturities  
- **discount factors** for pricing

---

## 4. Calibration (Curve Fitting)

### 4.1 Objective

Fit NSS parameters to an observed yield snapshot at a given date.

### 4.2 Method

We solve a least-squares problem:

$$
\min_{\theta}\sum_{i=1}^{N}
\left(
y_{\text{NSS}}(t_i;\theta)-y_{\text{obs}}(t_i)
\right)^2
$$

where:

- $\theta=(\beta_0,\beta_1,\beta_2,\beta_3,\tau_1,\tau_2)$  
- $t_i$ are maturities implied by the tenor list

### 4.3 Numerical Choices

- Optimizer: `scipy.optimize.least_squares`  
- Bounds:
  - $\tau_1,\tau_2>0$  
  - broad ranges on β parameters to avoid over-constraining

### 4.4 Fit Quality

The calibration returns diagnostics including:

- RMSE  
- maximum absolute fitting error  
- optimizer success flag and message

---

## 5. Curve Object and Discounting

### 5.1 NSSCurve

`NSSCurve` is a lightweight wrapper around fitted parameters that exposes:

- `yield_at(t)`  
- `discount_factor(t)`  
- `yields_for_tenors([...])`

### 5.2 Discount Factor Assumption

Discounting uses **continuous compounding**:

$$
DF(t)=e^{-y(t)\,t}
$$

This is a clean modeling simplification that keeps pricing consistent across:

- DV01  
- stress testing  
- VaR

---

## 6. Fixed-Coupon Bullet Bond Pricing

### 6.1 Instrument Type

The instrument layer implements:

- **Fixed-coupon bullet bonds**
  - periodic coupons  
  - full principal repayment at maturity  
  - no optionality

### 6.2 Cashflows

For notional $N$, coupon rate $c$, frequency $f$:

Coupon per period:

$$
CF_{\text{coupon}}=\frac{N\,c}{f}
$$

Final cashflow includes principal:

$$
CF_{\text{final}}=\frac{N\,c}{f}+N
$$

### 6.3 Time Measurement

A simplified day-count is used:

- **ACT/365**

Year fraction:

$$
t=\frac{\text{days between settlement and payment}}{365}
$$

### 6.4 Pricing Formula

$$
PV=\sum_i CF_i\,DF(t_i)
$$

---

## 7. Key-Rate DV01 / PVBP

### 7.1 Purpose

Key-rate DV01 measures sensitivity of price to a **1 bp move in a specific tenor**, holding all other quoted tenors unchanged.

### 7.2 Bump-and-Reprice Method

For each tenor $k$:

1) Start with observed yields $y_{\text{obs}}$.  
2) Create a shocked set:

$$
y'_{\text{obs},k}=y_{\text{obs},k}+0.0001
$$

3) Recalibrate NSS to $y'_{\text{obs}}$.  
4) Reprice instrument/portfolio.  
5) Compute:

$$
\text{KRDV01}_k = PV_k^{+1\text{bp}} - PV_{\text{base}}
$$

### 7.3 Sign Convention

- If rates rise, bond prices typically fall.  
- Therefore KRDV01 values are typically **negative** for long positions.

---

## 8. Curve Stress Testing

### 8.1 Goal

Evaluate portfolio P&L under structured, larger shocks.

### 8.2 Scenarios

All scenarios are applied to the **observed tenor yields**, then NSS is recalibrated.

#### 8.2.1 Parallel

$$
y'_i = y_i + s
$$

#### 8.2.2 Steepener (simple linear weighting)

Long-end rates rise more than short-end:

$$
y'_i = y_i + w_i\,s
$$

with:

- $w_i$ increasing from 0 (shortest tenor) to 1 (longest tenor)

#### 8.2.3 Flattener (inverse weighting)

Short-end rates rise more than long-end:

$$
y'_i = y_i + (1-w_i)\,s
$$

### 8.3 Output

For each scenario:

$$
\text{P\&L} = PV_{\text{stressed}} - PV_{\text{base}}
$$

---

## 9. Value at Risk (VaR)

This toolkit implements **full revaluation VaR**, meaning:

- we shock yields  
- recalibrate NSS  
- reprice the instrument/portfolio

### 9.1 Historical VaR

#### 9.1.1 Method

1) Choose a base date (default: latest).  
2) Extract the base yields vector $y_0$.  
3) Compute historical daily changes:

$$
\Delta y_t = y_t - y_{t-1}
$$

4) Create shocked curves:

$$
y'_t = y_0 + \Delta y_t
$$

5) Refit NSS for each $y'_t$.  
6) Reprice to get a P&L distribution.

#### 9.1.2 VaR Estimation

For confidence level $c$:

$$
VaR_c = \max\left(0,\,-Q_{1-c}(\text{P\&L})\right)
$$

Reported VaR is a **positive loss magnitude**.

### 9.2 Monte Carlo VaR

#### 9.2.1 Method

1) Estimate covariance of daily tenor changes from history.  
2) Simulate shocks:

$$
\Delta y \sim \mathcal{N}(0,\Sigma)
$$

3) Apply:

$$
y' = y_0 + \Delta y
$$

4) Refit NSS and reprice for each simulation.  
5) Compute VaR from the simulated P&L distribution.

---

## 10. Portfolio Aggregation

### 10.1 Structure

The portfolio holds a list of positions:

- (instrument, quantity)

### 10.2 PV

$$
PV_{\text{portfolio}} = \sum_i q_i\,PV_i
$$

### 10.3 Risk Reuse

The portfolio class implements:

- `price(curve, settlement_date)`

This allows the portfolio to plug into the same risk engines used for a single bond.

---

## 11. Validation and Testing Philosophy

The test suite focuses on:

- numerical sanity  
- shape consistency  
- regression protection for refactors

Examples:

- discount factors behave sensibly for positive curves  
- calibration completes with finite parameters  
- key-rate DV01 returns all requested tenors  
- stress scenarios return finite PV and P&L  
- VaR functions produce a non-empty P&L distribution

---

## 12. Known Simplifications and Limitations

This toolkit intentionally simplifies several real-world elements:

- ACT/365 used universally  
- continuous-comp discounting for simplicity  
- no bootstrapping of zero curves from instruments  
- no inflation-linked or callable structures  
- no transaction costs, liquidity effects, or bid/ask  
- VaR assumes stability of historical relationships

These choices are appropriate for a compact educational risk engine and can be extended in future iterations.

---

## 13. Reproducibility

- A small yield sample is included in:

  - `src/firisk/data/yields.csv`

- Demo scripts in:

  - `src/firisk/scripts/`

  reproduce:

  - bond pricing  
  - key-rate DV01  
  - stress tests  
  - historical VaR  
  - Monte Carlo VaR  
  - portfolio risk summaries

---

## 14. Summary

This project demonstrates a clean end-to-end rates risk workflow:

**yield history → NSS fit → curve object → bond PV → DV01 → stress → VaR → portfolio aggregation**

The implementation is designed to be simple, testable, and easy to explain in an internship interview setting.
