"""Model training, artifact serialization, and evaluation report generation."""

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
import pandas as pd
import numpy as np

# Ensure UTF-8 output on Windows consoles
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

from forecasting.data import build_daily_sync_timeseries, build_daily_incident_timeseries
from forecasting.models import (
    NaiveForecastModel,
    SeasonalNaiveForecastModel,
    ExponentialSmoothingForecastModel,
)
from forecasting.evaluate import compare_all_models
from pipeline.config import config
from app.logging_config import logger

ARTIFACTS_DIR = Path(__file__).resolve().parent / "artifacts"
REPORTS_DIR = Path(__file__).resolve().parent.parent / "reports" / "forecasting"

def train_and_evaluate_forecasting(
    db_path: Path | str | None = None,
    horizon: int = 3,
    save_artifacts: bool = True
) -> dict[str, Any]:
    """
    Executes end-to-end model training, chronological walk-forward evaluation,
    artifact versioning, and Markdown report generation for both targets:
    1. Daily Sync Failure Rate
    2. Daily Incident Volume
    """
    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    
    now_str = datetime.now(timezone.utc).isoformat()
    now_tag = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")

    # 1. Target 1: Failure Rate
    df_sync = build_daily_sync_timeseries(db_path=db_path)
    s_failure = df_sync["failure_rate"] if not df_sync.empty else pd.Series(dtype=float)
    
    # Target 2: Incident Volume
    df_inc = build_daily_incident_timeseries(db_path=db_path)
    s_incidents = df_inc["incident_count"] if not df_inc.empty else pd.Series(dtype=float)

    # 2. Walk-forward comparisons
    min_train = min(4, max(2, len(s_failure) - horizon))
    min_train_inc = min(3, max(2, len(s_incidents) - horizon)) if len(s_incidents) > horizon else 1
    
    cmp_failure = compare_all_models(s_failure, target_name="failure_rate", horizon=horizon, min_train_size=min_train)
    cmp_incidents = compare_all_models(s_incidents, target_name="incident_volume", horizon=horizon, min_train_size=min_train_inc)

    # 3. Fit Best Models on Full History
    best_fail_model_name = cmp_failure["best_model"]
    best_inc_model_name = cmp_incidents["best_model"]
    
    model_factories = {
        "naive": lambda: NaiveForecastModel(),
        "seasonal_naive": lambda: SeasonalNaiveForecastModel(seasonal_period=7),
        "exponential_smoothing": lambda: ExponentialSmoothingForecastModel(seasonal_period=7),
    }

    final_fail_model = model_factories[best_fail_model_name]()
    final_fail_model.fit(s_failure)
    point_fail, low_fail, up_fail = final_fail_model.predict(horizon=horizon)
    # Clamp failure rates to valid [0.0, 100.0] interval
    low_fail = np.clip(low_fail, 0.0, 100.0)
    up_fail = np.clip(up_fail, 0.0, 100.0)
    point_fail = np.clip(point_fail, 0.0, 100.0)

    final_inc_model = model_factories[best_inc_model_name]()
    final_inc_model.fit(s_incidents)
    point_inc, low_inc, up_inc = final_inc_model.predict(horizon=horizon)
    low_inc = np.clip(low_inc, 0.0, None)
    up_inc = np.clip(up_inc, 0.0, None)
    point_inc = np.clip(point_inc, 0.0, None)

    # 4. Save Versioned Metadata Artifacts
    metadata = {
        "version": f"v_{now_tag}",
        "created_at": now_str,
        "horizon_days": horizon,
        "failure_rate": {
            "selected_model": best_fail_model_name,
            "validation_metrics": cmp_failure["models"].get(best_fail_model_name, {}),
            "all_models_compared": cmp_failure["models"],
            "training_history_length": len(s_failure),
            "last_observed_value": float(s_failure.iloc[-1]) if not s_failure.empty else 0.0,
            "forecast_point": [round(float(v), 2) for v in point_fail],
            "forecast_lower": [round(float(v), 2) for v in low_fail],
            "forecast_upper": [round(float(v), 2) for v in up_fail],
        },
        "incident_volume": {
            "selected_model": best_inc_model_name,
            "validation_metrics": cmp_incidents["models"].get(best_inc_model_name, {}),
            "all_models_compared": cmp_incidents["models"],
            "training_history_length": len(s_incidents),
            "last_observed_value": float(s_incidents.iloc[-1]) if not s_incidents.empty else 0.0,
            "forecast_point": [round(float(v), 2) for v in point_inc],
            "forecast_lower": [round(float(v), 2) for v in low_inc],
            "forecast_upper": [round(float(v), 2) for v in up_inc],
        },
        "disclosure": "SYNTHETIC_DATA_METHODOLOGY_DEMONSTRATION"
    }

    if save_artifacts:
        meta_file = ARTIFACTS_DIR / f"forecast_metadata_{now_tag}.json"
        meta_file.write_text(json.dumps(metadata, indent=2), encoding="utf-8")
        # Also maintain a latest pointer
        latest_file = ARTIFACTS_DIR / "forecast_metadata_latest.json"
        latest_file.write_text(json.dumps(metadata, indent=2), encoding="utf-8")
        logger.info(f"Forecasting metadata saved to {meta_file}")

    # 5. Generate Markdown Comparison Report
    md_report_file = REPORTS_DIR / "forecast_evaluation_report.md"
    generate_forecast_markdown_report(metadata, md_report_file)

    return metadata

def generate_forecast_markdown_report(metadata: dict[str, Any], output_path: Path) -> None:
    """Generates an interview-ready Markdown evaluation report for time series forecasting."""
    fail_data = metadata["failure_rate"]
    inc_data = metadata["incident_volume"]
    
    def format_table(model_dict: dict[str, Any], best_name: str) -> str:
        rows = []
        for name, m in model_dict.items():
            is_best = " ⭐ (Selected)" if name == best_name else ""
            if "error" in m:
                rows.append(f"| `{name}`{is_best} | N/A | N/A | N/A | {m['error']} |")
            else:
                rows.append(f"| `{name}`{is_best} | {m.get('mae', 0.0):.3f} | {m.get('rmse', 0.0):.3f} | {m.get('smape', 0.0):.2f}% | {m.get('evaluated_points', 0)} pts |")
        return "\n".join(rows)

    report_md = f"""# Time-Series Forecasting Evaluation & Backtesting Report

> **SYNTHETIC DISCLOSURE:** Time-series telemetry and forecast models are demonstrated on synthetic data to validate SRE backtesting methodology, walk-forward validation, and zero-leakage ML engineering.

---

### 1. Executive Summary & Methodology
- **Validation Protocol:** Chronological Rolling-Origin Walk-Forward Validation.
- **Data Leakage Guarantee:** Strict temporal splitting. Zero future lookahead bias. Models at origin $t$ are fitted strictly on observations prior to $t$.
- **Forecast Horizon:** {metadata['horizon_days']} days ahead.
- **Evaluation Metrics:** MAE (Mean Absolute Error), RMSE (Root Mean Squared Error), sMAPE (Symmetric Mean Absolute Percentage Error, zero-denominator safe).

---

### 2. Target 1: Daily Sync Failure Rate (%)
- **Selected Champion Model:** `{fail_data['selected_model']}`
- **Historical Data Points:** {fail_data['training_history_length']} daily observations.
- **Last Observed Failure Rate:** {fail_data['last_observed_value']:.2f}%

| Model Architecture | MAE (Lower is better) | RMSE | sMAPE (%) | Evaluated Splits |
| :--- | :--- | :--- | :--- | :--- |
{format_table(fail_data['all_models_compared'], fail_data['selected_model'])}

---

### 3. Target 2: Daily Incident Volume (Incidents / Day)
- **Selected Champion Model:** `{inc_data['selected_model']}`
- **Historical Data Points:** {inc_data['training_history_length']} daily observations.
- **Last Observed Incident Volume:** {inc_data['last_observed_value']:.1f}

| Model Architecture | MAE | RMSE | sMAPE (%) | Evaluated Splits |
| :--- | :--- | :--- | :--- | :--- |
{format_table(inc_data['all_models_compared'], inc_data['selected_model'])}

---

### 4. Prediction Intervals & Empirical Uncertainty
- **Interval Methodology:** Empirical residual quantiles (2.5% to 97.5%) scaled by forecast step uncertainty.
- **Boundary Clamping:** Failure rate intervals are clamped to realistic bounds [0.0%, 100.0%]. Incident counts are bounded at >= 0.0.
- **Limitations:** Empirical residual intervals represent historical dispersion under stationary conditions and are not a theoretical guarantee against black-swan operational disruptions.
"""
    output_path.write_text(report_md, encoding="utf-8")
    logger.info(f"Forecast evaluation markdown report written to {output_path}")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Train and evaluate SyncOps time series forecasting.")
    parser.add_argument("--horizon", type=int, default=3, help="Forecast horizon in days")
    args = parser.parse_args()
    
    print("=" * 65)
    print("SYNCOPS TIME-SERIES FORECASTING & CHRONOLOGICAL EVALUATION")
    print("=" * 65)
    res = train_and_evaluate_forecasting(horizon=args.horizon)
    print(f"✓ Failure Rate Best Model: {res['failure_rate']['selected_model']}")
    print(f"  Validation MAE: {res['failure_rate']['validation_metrics'].get('mae')}")
    print(f"✓ Incident Volume Best Model: {res['incident_volume']['selected_model']}")
    print(f"  Validation MAE: {res['incident_volume']['validation_metrics'].get('mae')}")
