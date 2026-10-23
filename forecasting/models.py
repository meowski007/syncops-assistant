"""Forecasting models implementation: Naive, Seasonal Naive, and Exponential Smoothing."""

from typing import Any
import numpy as np
import pandas as pd
from statsmodels.tsa.holtwinters import ExponentialSmoothing

class ForecastingModel:
    """Base interface for time series forecasting models."""
    name: str = "base"

    def fit(self, series: pd.Series) -> "ForecastingModel":
        raise NotImplementedError

    def predict(self, horizon: int, alpha: float = 0.05) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        """
        Generates point forecasts and empirical prediction intervals.
        Returns: (point_forecast, lower_bound, upper_bound)
        """
        raise NotImplementedError

class NaiveForecastModel(ForecastingModel):
    """
    Naive baseline: Forecasts all future periods using the most recently observed value.
    Formula: y_hat[t + h] = y[t]
    """
    name = "naive"

    def __init__(self):
        self.last_value: float = 0.0
        self.residuals: np.ndarray = np.array([])

    def fit(self, series: pd.Series) -> "NaiveForecastModel":
        if series.empty:
            raise ValueError("Cannot fit Naive model on empty series.")
        vals = series.to_numpy(dtype=float)
        self.last_value = float(vals[-1])
        # In-sample residuals for naive: diff between successive values
        if len(vals) > 1:
            self.residuals = vals[1:] - vals[:-1]
        else:
            self.residuals = np.array([0.0])
        return self

    def predict(self, horizon: int, alpha: float = 0.05) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        point = np.full(horizon, self.last_value, dtype=float)
        resid_std = float(np.std(self.residuals)) if len(self.residuals) > 1 else (0.1 * abs(self.last_value) if self.last_value != 0 else 1.0)
        if resid_std == 0:
            resid_std = 0.1 * abs(self.last_value) if self.last_value != 0 else 1.0
        # z-score: ~1.96 for alpha=0.05
        z = 1.96 if alpha <= 0.05 else 1.645
        margin = z * resid_std * np.sqrt(np.arange(1, horizon + 1))
        lower = point - margin
        upper = point + margin
        return point, lower, upper

class SeasonalNaiveForecastModel(ForecastingModel):
    """
    Seasonal Naive baseline: Forecasts future periods using values from the previous seasonal cycle.
    Formula: y_hat[t + h] = y[t + h - m] (where m is seasonal period, default 7 days).
    Gracefully falls back to standard naive if history length < seasonal_period.
    """
    name = "seasonal_naive"

    def __init__(self, seasonal_period: int = 7):
        self.seasonal_period = seasonal_period
        self.history: np.ndarray = np.array([])
        self.residuals: np.ndarray = np.array([])

    def fit(self, series: pd.Series) -> "SeasonalNaiveForecastModel":
        if series.empty:
            raise ValueError("Cannot fit Seasonal Naive model on empty series.")
        self.history = series.to_numpy(dtype=float)
        m = self.seasonal_period
        if len(self.history) > m:
            self.residuals = self.history[m:] - self.history[:-m]
        elif len(self.history) > 1:
            self.residuals = self.history[1:] - self.history[:-1]
        else:
            self.residuals = np.array([0.0])
        return self

    def predict(self, horizon: int, alpha: float = 0.05) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        n = len(self.history)
        m = self.seasonal_period
        
        point = np.zeros(horizon, dtype=float)
        for h in range(horizon):
            if n >= m:
                # Value from previous cycle
                idx = (n - m) + (h % m)
                point[h] = self.history[idx]
            else:
                # Fallback to last observed value if history < m
                point[h] = self.history[-1]

        resid_std = float(np.std(self.residuals)) if len(self.residuals) > 1 else (0.1 * abs(np.mean(point)) if np.mean(point) != 0 else 1.0)
        if resid_std == 0:
            resid_std = 0.1 * abs(np.mean(point)) if np.mean(point) != 0 else 1.0
        z = 1.96 if alpha <= 0.05 else 1.645
        margin = z * resid_std * np.sqrt(np.arange(1, horizon + 1))
        lower = point - margin
        upper = point + margin

        return point, lower, upper

class ExponentialSmoothingForecastModel(ForecastingModel):
    """
    Statistical Model: Holt-Winters Exponential Smoothing.
    Captures level and trend; incorporates additive seasonality if history permits (>= 2 * seasonal_periods).
    """
    name = "exponential_smoothing"

    def __init__(self, seasonal_period: int = 7):
        self.seasonal_period = seasonal_period
        self.fitted_model: Any = None
        self.residuals: np.ndarray = np.array([])
        self.last_value: float = 0.0

    def fit(self, series: pd.Series) -> "ExponentialSmoothingForecastModel":
        if len(series) < 3:
            raise ValueError("Exponential Smoothing requires at least 3 historical points.")
            
        vals = series.to_numpy(dtype=float)
        self.last_value = float(vals[-1])
        
        # Decide seasonal configuration based on available history length
        has_enough_for_season = (len(vals) >= 2 * self.seasonal_period)
        
        try:
            if has_enough_for_season:
                model = ExponentialSmoothing(
                    vals,
                    trend="add",
                    seasonal="add",
                    seasonal_periods=self.seasonal_period,
                    initialization_method="estimated"
                )
            else:
                # Simple Holt linear trend or simple exponential smoothing
                model = ExponentialSmoothing(
                    vals,
                    trend="add",
                    seasonal=None,
                    initialization_method="estimated"
                )
            self.fitted_model = model.fit(optimized=True)
            self.residuals = self.fitted_model.resid
        except Exception:
            # Fallback simple smoothing if optimization encounters numerical singularities
            model = ExponentialSmoothing(vals, trend=None, seasonal=None, initialization_method="estimated")
            self.fitted_model = model.fit(optimized=True)
            self.residuals = self.fitted_model.resid

        return self

    def predict(self, horizon: int, alpha: float = 0.05) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        if self.fitted_model is None:
            point = np.full(horizon, self.last_value, dtype=float)
            return point, point * 0.9, point * 1.1

        try:
            forecast_vals = self.fitted_model.forecast(horizon)
            point = np.array(forecast_vals, dtype=float)
        except Exception:
            point = np.full(horizon, self.last_value, dtype=float)

        resid_std = float(np.std(self.residuals)) if len(self.residuals) > 1 else (0.1 * abs(np.mean(point)) if np.mean(point) != 0 else 1.0)
        if resid_std == 0:
            resid_std = 0.1 * abs(np.mean(point)) if np.mean(point) != 0 else 1.0
        z = 1.96 if alpha <= 0.05 else 1.645
        margin = z * resid_std * np.sqrt(np.arange(1, horizon + 1))
        lower = point - margin
        upper = point + margin

        return point, lower, upper
