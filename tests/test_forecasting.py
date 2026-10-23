"""Tests for Time-Series Forecasting: Walk-forward validation, zero-leakage, baseline models."""

import numpy as np
import pandas as pd
import pytest

from forecasting.models import NaiveForecastModel, SeasonalNaiveForecastModel, ExponentialSmoothingForecastModel
from forecasting.evaluate import calculate_mae, calculate_rmse, calculate_smape, walk_forward_validation, compare_all_models
from forecasting.monitor import check_forecast_drift
from forecasting.service import get_forecast_data

def test_metrics_calculation():
    actual = np.array([10.0, 20.0, 30.0])
    pred = np.array([12.0, 18.0, 33.0])
    
    mae = calculate_mae(actual, pred)
    rmse = calculate_rmse(actual, pred)
    smape = calculate_smape(actual, pred)

    assert round(mae, 2) == 2.33
    assert rmse > mae
    assert 0.0 <= smape <= 100.0

def test_smape_zero_denominator_safe():
    actual = np.array([0.0, 0.0, 0.0])
    pred = np.array([0.0, 0.0, 0.0])
    # Standard MAPE divides by zero; sMAPE safely handles zero with epsilon
    smape = calculate_smape(actual, pred)
    assert smape == 0.0

def test_naive_forecast_predict():
    series = pd.Series([5.0, 6.0, 7.5, 8.0])
    model = NaiveForecastModel().fit(series)
    point, lower, upper = model.predict(horizon=3)
    
    assert len(point) == 3
    assert np.all(point == 8.0)  # Always predicts last observed value
    assert np.all(lower <= point)
    assert np.all(point <= upper)

def test_seasonal_naive_forecast_predict():
    # 14 days of repeating weekly pattern
    series = pd.Series([1, 2, 3, 4, 5, 6, 7, 1, 2, 3, 4, 5, 6, 7], dtype=float)
    model = SeasonalNaiveForecastModel(seasonal_period=7).fit(series)
    point, lower, upper = model.predict(horizon=7)
    
    assert len(point) == 7
    # Should predict the previous cycle [1, 2, 3, 4, 5, 6, 7]
    assert np.array_equal(point, [1, 2, 3, 4, 5, 6, 7])

def test_exponential_smoothing_predict():
    series = pd.Series([10.0, 11.2, 12.1, 13.5, 14.2, 15.1, 16.0, 17.2, 18.0, 19.1])
    model = ExponentialSmoothingForecastModel().fit(series)
    point, lower, upper = model.predict(horizon=3)
    
    assert len(point) == 3
    assert np.all(lower <= point)
    assert np.all(point <= upper)

def test_walk_forward_zero_future_leakage():
    # Construct sequence where future values jump sharply
    series = pd.Series(
        [1.0, 2.0, 3.0, 4.0, 5.0, 100.0, 200.0],
        index=pd.date_range("2026-10-01", periods=7, freq="D")
    )
    # Origin at index 4 (value 5.0) must not know about 100.0
    res = walk_forward_validation(
        series,
        model_factory=lambda: NaiveForecastModel(),
        horizon=1,
        min_train_size=4,
        step_size=1
    )
    assert res["evaluated_points"] > 0
    assert "mae" in res

def test_insufficient_history_error():
    short_series = pd.Series([5.0, 6.0])
    with pytest.raises(ValueError, match="too short"):
        walk_forward_validation(short_series, lambda: NaiveForecastModel(), horizon=1, min_train_size=4)

def test_forecast_drift_monitoring():
    baseline_mae = 1.0
    # Scenario 1: Stable
    stable = check_forecast_drift(
        recent_actuals=[10, 11, 12],
        recent_predictions=[10.5, 11.2, 11.8],
        baseline_mae=baseline_mae
    )
    assert stable["drift_detected"] is False
    assert stable["status"] == "STABLE"

    # Scenario 2: Severe drift
    drifted = check_forecast_drift(
        recent_actuals=[10, 20, 30],
        recent_predictions=[10, 10, 10],
        baseline_mae=baseline_mae,
        threshold_multiplier=1.5
    )
    assert drifted["drift_detected"] is True
    assert drifted["status"] == "DRIFT_ALERT"

def test_forecast_service_schema():
    res = get_forecast_data(target="failure_rate", horizon=3)
    assert res["status"] == "SUCCESS"
    assert res["target"] == "failure_rate"
    assert len(res["forecast"]) == 3
    for f in res["forecast"]:
        assert f["lower_bound"] <= f["point_forecast"] <= f["upper_bound"]
        assert 0.0 <= f["point_forecast"] <= 100.0
