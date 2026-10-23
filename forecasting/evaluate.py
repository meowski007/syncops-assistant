"""Chronological walk-forward validation and evaluation metrics for forecasting."""

from typing import Any
import numpy as np
import pandas as pd

from forecasting.models import (
    ForecastingModel,
    NaiveForecastModel,
    SeasonalNaiveForecastModel,
    ExponentialSmoothingForecastModel,
)
from app.logging_config import logger

def calculate_mae(actual: np.ndarray, predicted: np.ndarray) -> float:
    """Mean Absolute Error."""
    return float(np.mean(np.abs(actual - predicted)))

def calculate_rmse(actual: np.ndarray, predicted: np.ndarray) -> float:
    """Root Mean Squared Error."""
    return float(np.sqrt(np.mean((actual - predicted) ** 2)))

def calculate_smape(actual: np.ndarray, predicted: np.ndarray, epsilon: float = 1e-8) -> float:
    """
    Symmetric Mean Absolute Percentage Error (sMAPE).
    Safe against zero denominators where standard MAPE fails:
    sMAPE = (100 / n) * sum( 2 * |actual - predicted| / (|actual| + |predicted| + eps) )
    """
    denominator = np.abs(actual) + np.abs(predicted) + epsilon
    numerator = 2.0 * np.abs(actual - predicted)
    return float(np.mean(numerator / denominator) * 100.0)

def compute_metrics(actual: np.ndarray, predicted: np.ndarray) -> dict[str, float]:
    """Computes standard SRE forecasting validation metrics."""
    if len(actual) == 0:
        return {"mae": 0.0, "rmse": 0.0, "smape": 0.0}
    return {
        "mae": round(calculate_mae(actual, predicted), 3),
        "rmse": round(calculate_rmse(actual, predicted), 3),
        "smape": round(calculate_smape(actual, predicted), 2),
    }

def walk_forward_validation(
    series: pd.Series,
    model_factory: Any,
    horizon: int = 1,
    min_train_size: int = 4,
    step_size: int = 1
) -> dict[str, Any]:
    """
    Executes chronological rolling-origin walk-forward validation.
    
    NO FUTURE LEAKAGE GUARANTEE:
    At each step t, the model is fit strictly on history[0:t].
    Forecasts are generated for [t : t + horizon] and compared against actuals[t : t + horizon].
    """
    n = len(series)
    if n <= min_train_size:
        raise ValueError(
            f"Series length ({n}) is too short for walk-forward validation with min_train_size={min_train_size}."
        )

    all_actuals = []
    all_predictions = []
    split_origins = []

    for origin in range(min_train_size, n - horizon + 1, step_size):
        train_slice = series.iloc[:origin]
        test_slice = series.iloc[origin : origin + horizon]
        
        # Fit model on training slice ONLY
        model: ForecastingModel = model_factory()
        model.fit(train_slice)
        
        point_forecasts, _, _ = model.predict(horizon=horizon)
        
        all_actuals.extend(test_slice.to_numpy(dtype=float))
        all_predictions.extend(point_forecasts)
        split_origins.append(str(train_slice.index[-1].date()))

    actuals_arr = np.array(all_actuals, dtype=float)
    preds_arr = np.array(all_predictions, dtype=float)
    
    metrics = compute_metrics(actuals_arr, preds_arr)
    metrics["evaluated_points"] = len(actuals_arr)
    metrics["origins_count"] = len(split_origins)
    metrics["horizon"] = horizon
    metrics["eval_window_start"] = str(series.index[min_train_size].date()) if n > min_train_size else None
    metrics["eval_window_end"] = str(series.index[-1].date())
    
    return metrics

def compare_all_models(
    series: pd.Series,
    target_name: str = "failure_rate",
    horizon: int = 1,
    min_train_size: int = 4
) -> dict[str, Any]:
    """
    Evaluates Naive, Seasonal Naive, and Exponential Smoothing on identical
    chronological walk-forward splits.
    """
    models = {
        "naive": lambda: NaiveForecastModel(),
        "seasonal_naive": lambda: SeasonalNaiveForecastModel(seasonal_period=7),
        "exponential_smoothing": lambda: ExponentialSmoothingForecastModel(seasonal_period=7),
    }

    comparison: dict[str, Any] = {}
    best_model_name = "naive"
    best_mae = float("inf")

    for name, factory in models.items():
        try:
            res = walk_forward_validation(
                series,
                model_factory=factory,
                horizon=horizon,
                min_train_size=min_train_size
            )
            comparison[name] = res
            if res["mae"] < best_mae:
                best_mae = res["mae"]
                best_model_name = name
        except Exception as e:
            logger.warning(f"Walk-forward validation for {name} failed: {e}")
            comparison[name] = {"error": str(e), "mae": 999.0, "rmse": 999.0, "smape": 999.0}

    return {
        "target": target_name,
        "best_model": best_model_name,
        "models": comparison,
        "horizon": horizon,
        "series_length": len(series)
    }
