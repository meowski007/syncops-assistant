"""
Deterministic Synthetic Data Seeder for SyncOps Assistant.
DISCLOSURE: ALL DATA GENERATED IS STRICTLY SYNTHETIC AND DESIGNED FOR
EDUCATIONAL SRE AND CUSTOMER-EXPERIENCE RELIABILITY ANALYSIS.
DOES NOT CONTAIN REAL CUSTOMER DATA OR INTERNAL CORPORATE TELEMETRY.
"""

import argparse
import random
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from app.database import get_db, init_db, get_db_path
from app.logging_config import logger

RANDOM_SEED = 42

COHORTS = [
    "iOS-Production",
    "iOS-Beta",
    "Android-v3",
    "WebClient-Enterprise",
    "IoT-Firmware-v12",
]

DEVICE_TYPES = {
    "iOS-Production": ["iPhone15,2", "iPhone14,3", "iPad13,1"],
    "iOS-Beta": ["iPhone15,3", "iPhone16,1"],
    "Android-v3": ["Pixel7", "GalaxyS23", "Pixel8Pro"],
    "WebClient-Enterprise": ["Chrome-macOS", "Safari-macOS", "Edge-Windows"],
    "IoT-Firmware-v12": ["SmartHub-v12", "SensorNode-v12"],
}

APP_VERSIONS = {
    "iOS-Production": ["4.12.0", "4.12.1"],
    "iOS-Beta": ["4.13.0-rc1", "4.13.0-rc2"],
    "Android-v3": ["3.8.4", "3.8.5"],
    "WebClient-Enterprise": ["2.4.0"],
    "IoT-Firmware-v12": ["12.1.0"],
}

FAILURE_CATEGORIES = [
    "AUTH_EXPIRED",
    "PAYLOAD_TIMEOUT",
    "SCHEMA_MISMATCH",
    "RATE_LIMITED",
    "DATABASE_LOCK",
    "FIRMWARE_UNSUPPORTED",
]

INCIDENTS = [
    {
        "id": "INC-2026-1001",
        "title": "Sync payload timeout spikes on iOS Production batch upload",
        "severity": "SEV1",
        "status": "INVESTIGATING",
        "start_offset_hours": 3,
        "recovery_offset_hours": None,
        "affected_cohort": "iOS-Production",
        "failure_category": "PAYLOAD_TIMEOUT",
        "root_cause_summary": "Upstream payload decompression buffer exhaustion during peak client telemetry batch upload.",
    },
    {
        "id": "INC-2026-1002",
        "title": "BLE firmware buffer truncation during sync burst",
        "severity": "SEV2",
        "status": "RESOLVED",
        "start_offset_hours": 48,
        "recovery_offset_hours": 46.5,  # Recovered in 1.5h (90 mins)
        "affected_cohort": "IoT-Firmware-v12",
        "failure_category": "FIRMWARE_UNSUPPORTED",
        "root_cause_summary": "Firmware 12.1.0 BLE MTU negotiation failure during concurrent multi-packet sync bursts.",
    },
    {
        "id": "INC-2026-1003",
        "title": "OAuth token refresh failure after cert rotation",
        "severity": "SEV3",
        "status": "RESOLVED",
        "start_offset_hours": 96,
        "recovery_offset_hours": 95.2,  # Recovered in 0.8h (48 mins)
        "affected_cohort": "Android-v3",
        "failure_category": "AUTH_EXPIRED",
        "root_cause_summary": "Identity provider rotated leaf certificate without propagating intermediate cert to token validator.",
    },
    {
        "id": "INC-2026-1004",
        "title": "Enterprise batch sync ingress rate limit saturation",
        "severity": "SEV2",
        "status": "MITIGATED",
        "start_offset_hours": 24,
        "recovery_offset_hours": 22.0,  # Mitigated in 2.0h (120 mins)
        "affected_cohort": "WebClient-Enterprise",
        "failure_category": "RATE_LIMITED",
        "root_cause_summary": "Automated ETL export from three enterprise tenants triggered token-bucket egress threshold simultaneously.",
    },
    {
        "id": "INC-2026-1005",
        "title": "Proto field deprecation caused schema mismatch in Beta cohort",
        "severity": "SEV4",
        "status": "RESOLVED",
        "start_offset_hours": 120,
        "recovery_offset_hours": 119.5,  # Recovered in 0.5h (30 mins)
        "affected_cohort": "iOS-Beta",
        "failure_category": "SCHEMA_MISMATCH",
        "root_cause_summary": "Deprecated field in protobuf schema v2.4 dropped by edge gateway parser.",
    },
]

def seed_database(db_path: str | Path | None = None, reset: bool = False) -> dict:
    """
    Seeds the SQLite database with deterministic synthetic data.
    If reset=True, clears existing tables before seeding.
    If reset=False and database already has records, returns existing counts idempotently.
    """
    random.seed(RANDOM_SEED)
    target_path = Path(db_path) if db_path else get_db_path()
    init_db(target_path)
    
    with get_db(target_path) as conn:
        # Check idempotency
        cursor = conn.execute("SELECT COUNT(*) FROM customers")
        existing_customers = cursor.fetchone()[0]
        
        if existing_customers > 0 and not reset:
            logger.info(
                "Database already contains records. Skipping seed to ensure idempotency. Use --reset to re-seed.",
                extra={"existing_customers": existing_customers}
            )
            counts = {}
            for table in ("customers", "sync_events", "incidents", "support_tickets", "adoption_records"):
                c = conn.execute(f"SELECT COUNT(*) FROM {table}")
                counts[table] = c.fetchone()[0]
            return counts

        if reset:
            logger.warning("Reset requested. Purging existing synthetic tables...")
            for table in ("support_tickets", "sync_events", "incidents", "customers", "adoption_records"):
                conn.execute(f"DELETE FROM {table}")
            conn.commit()

        now = datetime.now(timezone.utc)
        
        # 1. Generate Customers (300 deterministic customers)
        customers = []
        for i in range(1, 301):
            cust_id = f"CUST-{i:04d}"
            cohort = COHORTS[i % len(COHORTS)]
            device = random.choice(DEVICE_TYPES[cohort])
            version = random.choice(APP_VERSIONS[cohort])
            created_at = (now - timedelta(days=random.randint(15, 60))).isoformat()
            customers.append((cust_id, cohort, created_at, device, version))
            
        conn.executemany(
            "INSERT INTO customers (id, cohort, created_at, device_type, app_version) VALUES (?, ?, ?, ?, ?)",
            customers
        )
        
        # 2. Seed Structured Incidents
        incident_rows = []
        for inc in INCIDENTS:
            start_time = (now - timedelta(hours=inc["start_offset_hours"])).isoformat()
            recovery_time = (now - timedelta(hours=inc["recovery_offset_hours"])).isoformat() if inc["recovery_offset_hours"] else None
            incident_rows.append((
                inc["id"],
                inc["title"],
                inc["severity"],
                inc["status"],
                start_time,
                recovery_time,
                inc["affected_cohort"],
                inc["failure_category"],
                inc["root_cause_summary"]
            ))
            
        conn.executemany(
            """INSERT INTO incidents (id, title, severity, status, start_time, recovery_time, affected_cohort, failure_category, root_cause_summary)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            incident_rows
        )

        # 3. Generate Sync Events (5,000 deterministic events over past 7 days)
        sync_events = []
        active_inc_cohort = "iOS-Production"
        
        for i in range(1, 5001):
            event_id = f"EVT-{i:06d}"
            cust = random.choice(customers)
            cust_id, cust_cohort = cust[0], cust[1]
            
            # Timestamp uniformly spread over past 7 days (168 hours)
            event_time = now - timedelta(hours=random.uniform(0.1, 168.0))
            
            # Determine success/failure based on cohort and active incident window
            # If in iOS-Production within last 3 hours, higher failure rate (SEV1 active)
            is_recent_sev1_window = (cust_cohort == active_inc_cohort and (now - event_time).total_seconds() < 3 * 3600)
            
            if is_recent_sev1_window:
                is_success = random.random() < 0.60  # 40% failure rate during active incident
                failure_cat = "PAYLOAD_TIMEOUT" if not is_success else None
            else:
                is_success = random.random() < 0.955  # ~95.5% baseline success rate
                failure_cat = random.choice(FAILURE_CATEGORIES) if not is_success else None
                
            latency_ms = round(random.uniform(80.0, 450.0) if is_success else random.uniform(800.0, 5200.0), 2)
            payload_size = random.randint(1024, 65536)
            retry_count = 0 if is_success else random.choice([1, 2, 3])
            
            sync_events.append((
                event_id,
                cust_id,
                event_time.isoformat(),
                "SUCCESS" if is_success else "FAILURE",
                failure_cat,
                latency_ms,
                payload_size,
                retry_count
            ))
            
        conn.executemany(
            """INSERT INTO sync_events (id, customer_id, timestamp, status, failure_category, latency_ms, payload_size_bytes, retry_count)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            sync_events
        )

        # 4. Generate Support Tickets (linked to failures or self-service resolutions)
        support_tickets = []
        failed_events = [e for e in sync_events if e[3] == "FAILURE"]
        
        ticket_id_counter = 1
        for evt in failed_events[:250]: # Sample subset of failures generating tickets
            ticket_id = f"TCK-{ticket_id_counter:05d}"
            cust_id = evt[1]
            evt_time = datetime.fromisoformat(evt[2])
            ticket_time = (evt_time + timedelta(minutes=random.randint(5, 45))).isoformat()
            
            # Link to active incident if cohort matches
            linked_inc = "INC-2026-1001" if evt[4] == "PAYLOAD_TIMEOUT" else None
            
            # Self-service resolution probability
            resolved_self = 1 if random.random() < 0.38 else 0
            res_minutes = round(random.uniform(5.0, 30.0), 1) if resolved_self else round(random.uniform(60.0, 240.0), 1)
            
            support_tickets.append((
                ticket_id,
                cust_id,
                linked_inc,
                ticket_time,
                evt[4] or "SYNC_FAILURE",
                resolved_self,
                res_minutes
            ))
            ticket_id_counter += 1

        conn.executemany(
            """INSERT INTO support_tickets (id, customer_id, incident_id, timestamp, category, resolved_via_self_service, resolution_time_minutes)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            support_tickets
        )

        # 5. Generate Adoption Records (Past 30 days)
        adoption_records = []
        base_dau = 12000
        base_reg = 50000
        for d in range(30, -1, -1):
            date_str = (now - timedelta(days=d)).date().isoformat()
            dau = base_dau + (30 - d) * 120 + random.randint(-150, 150)
            total_reg = base_reg + (30 - d) * 350
            # Sync adoption gradually climbing from 74% to 84%
            adoption_ratio = 0.74 + (0.10 * (30 - d) / 30) + random.uniform(-0.01, 0.01)
            adopted_users = int(dau * adoption_ratio)
            adoption_records.append((date_str, dau, total_reg, adopted_users))

        conn.executemany(
            """INSERT INTO adoption_records (date, daily_active_users, total_registered_users, sync_feature_adopted_users)
               VALUES (?, ?, ?, ?)""",
            adoption_records
        )

        conn.commit()
        
        counts = {
            "customers": len(customers),
            "incidents": len(incident_rows),
            "sync_events": len(sync_events),
            "support_tickets": len(support_tickets),
            "adoption_records": len(adoption_records),
        }
        logger.info("Deterministic synthetic data seeded successfully.", extra=counts)
        return counts

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Seed SyncOps Assistant synthetic database.")
    parser.add_argument("--reset", action="store_true", help="Reset existing tables and re-seed.")
    parser.add_argument("--db", type=str, default=None, help="Path to SQLite database file.")
    args = parser.parse_args()
    
    print("=" * 60)
    print("SYNCOPS ASSISTANT: SYNTHETIC DATA SEEDER")
    print("DISCLOSURE: Telemetry is 100% synthetic for educational SRE analysis.")
    print("=" * 60)
    
    result = seed_database(db_path=args.db, reset=args.reset)
    print(f"Record counts: {result}")
