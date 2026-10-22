import sqlite3
from pathlib import Path
from contextlib import contextmanager
from typing import Generator
from app.config import settings
from app.logging_config import logger

SCHEMA_SQL = """
-- Synthetic Customers
CREATE TABLE IF NOT EXISTS customers (
    id TEXT PRIMARY KEY,
    cohort TEXT NOT NULL,
    created_at TEXT NOT NULL,
    device_type TEXT NOT NULL,
    app_version TEXT NOT NULL
);

-- Synthetic Synchronization Events
CREATE TABLE IF NOT EXISTS sync_events (
    id TEXT PRIMARY KEY,
    customer_id TEXT NOT NULL,
    timestamp TEXT NOT NULL,
    status TEXT NOT NULL CHECK(status IN ('SUCCESS', 'FAILURE')),
    failure_category TEXT,
    latency_ms REAL NOT NULL,
    payload_size_bytes INTEGER NOT NULL,
    retry_count INTEGER NOT NULL DEFAULT 0,
    FOREIGN KEY (customer_id) REFERENCES customers (id)
);

-- Synthetic Incidents
CREATE TABLE IF NOT EXISTS incidents (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    severity TEXT NOT NULL CHECK(severity IN ('SEV1', 'SEV2', 'SEV3', 'SEV4')),
    status TEXT NOT NULL CHECK(status IN ('DETECTED', 'INVESTIGATING', 'MITIGATED', 'RESOLVED')),
    start_time TEXT NOT NULL,
    recovery_time TEXT,
    affected_cohort TEXT NOT NULL,
    failure_category TEXT NOT NULL,
    root_cause_summary TEXT
);

-- Synthetic Support Tickets
CREATE TABLE IF NOT EXISTS support_tickets (
    id TEXT PRIMARY KEY,
    customer_id TEXT NOT NULL,
    incident_id TEXT,
    timestamp TEXT NOT NULL,
    category TEXT NOT NULL,
    resolved_via_self_service INTEGER NOT NULL CHECK(resolved_via_self_service IN (0, 1)),
    resolution_time_minutes REAL,
    FOREIGN KEY (customer_id) REFERENCES customers (id),
    FOREIGN KEY (incident_id) REFERENCES incidents (id)
);

-- Synthetic Adoption Records
CREATE TABLE IF NOT EXISTS adoption_records (
    date TEXT PRIMARY KEY,
    daily_active_users INTEGER NOT NULL,
    total_registered_users INTEGER NOT NULL,
    sync_feature_adopted_users INTEGER NOT NULL
);

-- Indexes for high-throughput SRE timeseries and filter queries
CREATE INDEX IF NOT EXISTS idx_sync_events_timestamp ON sync_events(timestamp);
CREATE INDEX IF NOT EXISTS idx_sync_events_customer ON sync_events(customer_id);
CREATE INDEX IF NOT EXISTS idx_sync_events_status ON sync_events(status);
CREATE INDEX IF NOT EXISTS idx_sync_events_failure_cat ON sync_events(failure_category);
CREATE INDEX IF NOT EXISTS idx_incidents_status ON incidents(status);
CREATE INDEX IF NOT EXISTS idx_incidents_severity ON incidents(severity);
CREATE INDEX IF NOT EXISTS idx_incidents_start_time ON incidents(start_time);
CREATE INDEX IF NOT EXISTS idx_support_tickets_incident ON support_tickets(incident_id);
CREATE INDEX IF NOT EXISTS idx_support_tickets_timestamp ON support_tickets(timestamp);
"""

def get_db_path() -> Path:
    """Returns the resolved database path, ensuring parent directories exist."""
    path = Path(settings.DATABASE_PATH).resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    return path

@contextmanager
def get_db(db_path: str | Path | None = None) -> Generator[sqlite3.Connection, None, None]:
    """Context manager yielding an SQLite connection with Row factory enabled."""
    target_path = Path(db_path) if db_path else get_db_path()
    conn = sqlite3.connect(str(target_path), timeout=10.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    try:
        yield conn
    finally:
        conn.close()

def init_db(db_path: str | Path | None = None) -> None:
    """Initializes the database schema if tables do not exist."""
    target_path = Path(db_path) if db_path else get_db_path()
    target_path.parent.mkdir(parents=True, exist_ok=True)
    with get_db(target_path) as conn:
        conn.executescript(SCHEMA_SQL)
        conn.commit()
    logger.info("Database schema initialized.", extra={"database_path": str(target_path)})

def check_db_health(db_path: str | Path | None = None) -> dict:
    """Returns database connectivity status and table record counts."""
    target_path = Path(db_path) if db_path else get_db_path()
    if not target_path.exists():
        return {"connected": False, "exists": False, "record_counts": {}}
    try:
        with get_db(target_path) as conn:
            counts = {}
            for table in ("customers", "sync_events", "incidents", "support_tickets", "adoption_records"):
                cursor = conn.execute(f"SELECT COUNT(*) FROM {table}")
                counts[table] = cursor.fetchone()[0]
            return {"connected": True, "exists": True, "record_counts": counts}
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        return {"connected": False, "exists": True, "error": str(e), "record_counts": {}}
