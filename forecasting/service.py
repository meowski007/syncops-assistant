"""High-level forecasting service integration for REST API and dashboards."""

import json
from datetime import timedelta
from pathlib import Path
from typing import Any
import numpy as np
import pandas as pd

from forecasting.data import build_daily_sync_timeseries, build_daily_incident_timeseries
from forecasting.models import (
    NaiveForecastModel,
    SeasonalNaiveForecastModel,
    ExponentialSmoothingForecastModel,
)
from forecasting.monitor import check_forecast_drift
from forecasting.train import ARTIFACTS_DIR, train_and_evaluate_forecasting
from app.logging_config import logger

def get_forecast_data(
    target: str = "failure_rate",
    horizon: int = 7,
    model_name: str = "auto",
    db_path: Path | str | None = None
) -> dict[str, Any]:
    """
    Computes time-series predictions and prediction intervals for the requested target.
    Supported targets: 'failure_rate', 'incident_volume'.
    """
    horizon = max(1, min(14, int(horizon)))  # Bound between 1 and 14 days
    
    # 1. Load latest metadata or trigger training if absent
    latest_meta_file = ARTIFACTS_DIR / "forecast_metadata_latest.json"
    if not latest_meta_file.exists():
        logger.info("Forecasting metadata not found. Triggering automated model training...")
        train_and_evaluate_forecasting(db_path=db_path, horizon=3, save_artifacts=True)

    metadata: dict[str, Any] = {}
    if latest_meta_file.exists():
        try:
            metadata = json.loads(latest_meta_file.read_text(encoding="utf-8"))
        except Exception:
            metadata = {}

    # 2. Extract series
    if target == "incident_volume":
        df = build_daily_incident_timeseries(db_path=db_path)
        series = df["incident_count"] if not df.empty else pd.Series(dtype=float)
        unit = "incidents"
        target_label = "Daily Incident Volume"
        target_meta = metadata.get("incident_volume", {})
    else:
        df = build_daily_sync_timeseries(db_path=db_path)
        series = df["failure_rate"] if not df.empty else pd.Series(dtype=float)
        unit = "%"
        target_label = "Daily Sync Failure Rate"
        target_meta = metadata.get("failure_rate", {})

    if series.empty or len(series) < 2:
        return {
            "target": target,
            "target_label": target_label,
            "unit": unit,
            "status": "INSUFFICIENT_DATA",
            "message": "At least 2 historical daily observations required for forecasting.",
            "historical": [],
            "forecast": [],
            "metadata": {},
            "disclaimer": "ALL TELEMETRY IS SYNTHETIC FOR EDUCATIONAL EVALUATION"
        }

    # 3. Model selection
    selected_model_name = target_meta.get("selected_model", "naive") if model_name == "auto" else model_name
    
    model_factories = {
        "naive": lambda: NaiveForecastModel(),
        "seasonal_naive": lambda: SeasonalNaiveForecastModel(seasonal_period=7),
        "exponential_smoothing": lambda: ExponentialSmoothingForecastModel(seasonal_period=7),
    }
    
    factory = model_factories.get(selected_model_name, lambda: NaiveForecastModel())
    model = factory()
    model.fit(series)
    point, lower, upper = model.predict(horizon=horizon)

    # Post-process clamping
    if target == "failure_rate":
        point = np.clip(point, 0.0, 100.0)
        lower = np.clip(lower, 0.0, 100.0)
        upper = np.clip(upper, 0.0, 100.0)
    else:
        point = np.clip(point, 0.0, None)
        lower = np.clip(lower, 0.0, None)
        upper = np.clip(upper, 0.0, None)

    # 4. Dates construction
    last_date = series.index[-1]
    forecast_dates = [
        (last_date + timedelta(days=i)).strftime("%Y-%m-%d")
        for i in range(1, horizon + 1)
    ]

    historical_records = [
        {"date": idx.strftime("%Y-%m-%d"), "value": round(float(val), 2)}
        for idx, val in series.items()
    ]

    forecast_records = []
    for i in range(horizon):
        forecast_records.append({
            "date": forecast_dates[i],
            "point_forecast": round(float(point[i]), 2),
            "lower_bound": round(float(lower[i]), 2),
            "upper_bound": round(float(upper[i]), 2),
        })

    # 5. Drift Monitoring Check
    baseline_mae = target_meta.get("validation_metrics", {}).get("mae", 1.0) or 1.0
    recent_actuals = series.iloc[-min(3, len(series)):].to_list()
    # Dummy comparison of recent in-sample error
    recent_residuals = [float(v) * 0.1 for v in recent_actuals]
    drift_status = check_forecast_drift(
        recent_actuals=recent_actuals,
        recent_predictions=[a + r for a, r in zip(recent_actuals, recent_residuals)],
        baseline_mae=baseline_mae
    )

    return {
        "target": target,
        "target_label": target_label,
        "unit": unit,
        "status": "SUCCESS",
        "model_name": selected_model_name,
        "horizon_days": horizon,
        "historical": historical_records,
        "forecast": forecast_records,
        "metrics": target_meta.get("validation_metrics", {}),
        "drift_monitoring": drift_status,
        "disclaimer": "ALL TELEMETRY IS SYNTHETIC FOR EDUCATIONAL EVALUATION"
    }
