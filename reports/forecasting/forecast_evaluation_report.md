# Time-Series Forecasting Evaluation & Backtesting Report

> **SYNTHETIC DISCLOSURE:** Time-series telemetry and forecast models are demonstrated on synthetic data to validate SRE backtesting methodology, walk-forward validation, and zero-leakage ML engineering.

---

### 1. Executive Summary & Methodology
- **Validation Protocol:** Chronological Rolling-Origin Walk-Forward Validation.
- **Data Leakage Guarantee:** Strict temporal splitting. Zero future lookahead bias. Models at origin $t$ are fitted strictly on observations prior to $t$.
- **Forecast Horizon:** 3 days ahead.
- **Evaluation Metrics:** MAE (Mean Absolute Error), RMSE (Root Mean Squared Error), sMAPE (Symmetric Mean Absolute Percentage Error, zero-denominator safe).

---

### 2. Target 1: Daily Sync Failure Rate (%)
- **Selected Champion Model:** `exponential_smoothing`
- **Historical Data Points:** 8 daily observations.
- **Last Observed Failure Rate:** 5.21%

| Model Architecture | MAE (Lower is better) | RMSE | sMAPE (%) | Evaluated Splits |
| :--- | :--- | :--- | :--- | :--- |
| `naive` | 1.098 | 1.407 | 19.52% | 6 pts |
| `seasonal_naive` | 1.098 | 1.407 | 19.52% | 6 pts |
| `exponential_smoothing` ⭐ (Selected) | 0.968 | 1.068 | 16.10% | 6 pts |

---

### 3. Target 2: Daily Incident Volume (Incidents / Day)
- **Selected Champion Model:** `naive`
- **Historical Data Points:** 6 daily observations.
- **Last Observed Incident Volume:** 1.0

| Model Architecture | MAE | RMSE | sMAPE (%) | Evaluated Splits |
| :--- | :--- | :--- | :--- | :--- |
| `naive` ⭐ (Selected) | 1.000 | 1.000 | 200.00% | 3 pts |
| `seasonal_naive` | 1.000 | 1.000 | 200.00% | 3 pts |
| `exponential_smoothing` | 1.833 | 1.878 | 200.00% | 3 pts |

---

### 4. Prediction Intervals & Empirical Uncertainty
- **Interval Methodology:** Empirical residual quantiles (2.5% to 97.5%) scaled by forecast step uncertainty.
- **Boundary Clamping:** Failure rate intervals are clamped to realistic bounds [0.0%, 100.0%]. Incident counts are bounded at >= 0.0.
- **Limitations:** Empirical residual intervals represent historical dispersion under stationary conditions and are not a theoretical guarantee against black-swan operational disruptions.
