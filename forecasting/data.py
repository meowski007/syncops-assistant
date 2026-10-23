"""Time series data extraction, daily aggregation, and alignment."""

import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
import pandas as pd
import numpy as np

from pipeline.config import config
from app.logging_config import logger

def build_daily_sync_timeseries(db_path: Path | str | None = None) -> pd.DataFrame:
    """
    Extracts synchronization events and aggregates them into a strictly regular
    daily time series with missing date imputation and zero-denominator protection.
    
    Returns DataFrame with DatetimeIndex and columns:
    - total_syncs: int
    - failed_syncs: int
    - failure_rate: float (percentage 0.0 - 100.0)
    - has_traffic: bool
    """
    target_path = Path(db_path) if db_path else config.db_path
    conn = sqlite3.connect(str(target_path))
    conn.row_factory = sqlite3.Row
    
    # Check if clean_sync_events exists, otherwise fallback to sync_events
    cur = conn.cursor()
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='clean_sync_events'")
    table_name = "clean_sync_events" if cur.fetchone() else "sync_events"
    
    query = f"""
        SELECT 
            substr(timestamp, 1, 10) as event_date,
            COUNT(*) as total_syncs,
            SUM(CASE WHEN status = 'FAILURE' THEN 1 ELSE 0 END) as failed_syncs
        FROM {table_name}
        GROUP BY substr(timestamp, 1, 10)
        ORDER BY event_date ASC
    """
    df = pd.read_sql_query(query, conn)
    conn.close()

    if df.empty:
        # Return empty dataframe with correct schema
        empty_df = pd.DataFrame(columns=["total_syncs", "failed_syncs", "failure_rate", "has_traffic"])
        empty_df.index = pd.DatetimeIndex([], name="date")
        return empty_df

    df["event_date"] = pd.to_datetime(df["event_date"])
    df.set_index("event_date", inplace=True)
    df.index.name = "date"

    # Fill calendar gaps to guarantee strict daily frequency
    full_date_range = pd.date_range(start=df.index.min(), end=df.index.max(), freq="D", name="date")
    df = df.reindex(full_date_range)

    # Safe handling of zero-denominator days
    df["has_traffic"] = df["total_syncs"].notna() & (df["total_syncs"] > 0)
    df["total_syncs"] = df["total_syncs"].fillna(0).astype(int)
    df["failed_syncs"] = df["failed_syncs"].fillna(0).astype(int)

    # Calculate failure rate: If no traffic, interpolate or use rolling median rather than assuming 0.0% failure
    def calc_rate(row):
        if row["total_syncs"] > 0:
            return round((row["failed_syncs"] / row["total_syncs"]) * 100.0, 2)
        return np.nan

    df["failure_rate"] = df.apply(calc_rate, axis=1)
    
    # If any days had zero traffic, forward fill failure rate to avoid artificial drops
    df["failure_rate"] = df["failure_rate"].ffill().bfill().fillna(0.0)

    return df

def build_daily_incident_timeseries(db_path: Path | str | None = None) -> pd.DataFrame:
    """
    Extracts incidents and aggregates them into a strictly regular daily count time series.
    """
    target_path = Path(db_path) if db_path else config.db_path
    conn = sqlite3.connect(str(target_path))
    
    query = """
        SELECT 
            substr(start_time, 1, 10) as incident_date,
            COUNT(*) as incident_count
        FROM incidents
        GROUP BY substr(start_time, 1, 10)
        ORDER BY incident_date ASC
    """
    df = pd.read_sql_query(query, conn)
    conn.close()

    if df.empty:
        empty_df = pd.DataFrame(columns=["incident_count"])
        empty_df.index = pd.DatetimeIndex([], name="date")
        return empty_df

    df["incident_date"] = pd.to_datetime(df["incident_date"])
    df.set_index("incident_date", inplace=True)
    df.index.name = "date"

    # Fill missing dates with 0 incidents
    full_date_range = pd.date_range(start=df.index.min(), end=df.index.max(), freq="D", name="date")
    df = df.reindex(full_date_range)
    df["incident_count"] = df["incident_count"].fillna(0).astype(int)

    return df
