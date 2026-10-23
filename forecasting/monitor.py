"""Forecast drift monitoring and residual tracking service."""

from typing import Any
import numpy as np
import pandas as pd

from app.logging_config import logger

def check_forecast_drift(
    recent_actuals: list[float] | np.ndarray,
    recent_predictions: list[float] | np.ndarray,
    baseline_mae: float,
    threshold_multiplier: float = 1.5,
    min_samples: int = 3
) -> dict[str, Any]:
    """
    Monitors recent forecast residuals against reference validation MAE.
    
    METHODOLOGY NOTE:
    This provides an operational heuristic warning when recent error exceeds
    threshold_multiplier * baseline_mae. It is an alerting aid, not a formal
    Kolmogorov-Smirnov or Page-Hinkley concept drift test.
    """
    act = np.array(recent_actuals, dtype=float)
    pred = np.array(recent_predictions, dtype=float)
    
    if len(act) < min_samples:
        return {
            "drift_detected": False,
            "status": "INSUFFICIENT_HISTORY",
            "message": f"Sample count ({len(act)}) below minimum threshold ({min_samples}).",
            "recent_mae": None,
            "baseline_mae": baseline_mae
        }
        
    recent_mae = float(np.mean(np.abs(act - pred)))
    error_ratio = round(recent_mae / max(1e-4, baseline_mae), 2)
    is_drifted = (recent_mae > (baseline_mae * threshold_multiplier))
    
    status_str = "DRIFT_ALERT" if is_drifted else "STABLE"
    if is_drifted:
        logger.warning(
            f"Forecast drift warning: Recent MAE {recent_mae:.3f} exceeds reference {baseline_mae:.3f} (ratio {error_ratio}x)."
        )

    return {
        "drift_detected": is_drifted,
        "status": status_str,
        "recent_mae": round(recent_mae, 3),
        "baseline_mae": round(baseline_mae, 3),
        "error_ratio": error_ratio,
        "samples_evaluated": len(act),
        "threshold_multiplier": threshold_multiplier
    }
