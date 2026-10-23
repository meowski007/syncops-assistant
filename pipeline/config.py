"""Configuration and settings for the SyncOps ETL pipeline and data quality layer."""

import os
from pathlib import Path
from dataclasses import dataclass

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DEFAULT_DB_PATH = DATA_DIR / "syncops.db"
REPORTS_DIR = BASE_DIR / "reports" / "data_quality"

@dataclass
class PipelineConfig:
    db_path: Path = DEFAULT_DB_PATH
    raw_table: str = "raw_sync_events"
    clean_table: str = "clean_sync_events"
    runs_table: str = "pipeline_runs"
    rejected_table: str = "pipeline_rejected_records"
    reports_dir: Path = REPORTS_DIR
    
    # PII Masking: Read from environment; fallback to clearly-labeled dev salt
    pii_salt: str = os.environ.get("PII_SALT") or os.environ.get("PII_HMAC_KEY") or "DEVELOPMENT_ONLY_SALT_NOT_FOR_PRODUCTION"
    is_production_salt: bool = bool(os.environ.get("PII_SALT") or os.environ.get("PII_HMAC_KEY"))
    
    # Thresholds for validation
    max_future_seconds_allowed: int = 3600  # 1 hour clock skew tolerance
    max_latency_ms: float = 30000.0  # 30 seconds max realistic sync latency
    max_payload_bytes: int = 10 * 1024 * 1024  # 10 MB max payload size

config = PipelineConfig()
