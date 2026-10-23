# SRE Runbook: Database Connection Saturation & Storage Shard Exhaustion

## Overview
- **Category:** `DATABASE_LOCK` / `CONNECTION_EXHAUSTION`
- **Severity Classification:** SEV1 (Primary shard connection pool starvation) / SEV2 (Elevated lock wait times)
- **Service:** Core SQLite / Relational Storage Engine
- **Synthetic Flag:** SYNTHETIC DATA & SCENARIO FOR EDUCATIONAL USE

---

## 1. Symptoms & Detection
- Alert `DBConnectionPoolStarvation`: Available connections drop to zero; connection acquisition latency exceeds 5,000ms.
- API endpoints return HTTP 500 with `sqlite3.OperationalError: database is locked`.
- Elevated queue of blocked transactions on shard write locks.

## 2. Immediate Diagnostic Checklist
1. **Identify Long-Running Transactions:**
   - Execute query on active transactions exceeding 2,500ms duration.
2. **Check Index Health on Hot Tables:**
   - Verify index utilization on `clean_sync_events(date, status)` and `sync_events(timestamp)`.
3. **Verify WAL (Write-Ahead Logging) Mode:**
   - Ensure `PRAGMA journal_mode = WAL;` is enabled to allow concurrent reads during active writes.

## 3. Mitigation Steps
1. **Enable WAL Mode & Busy Timeout:**
   - Enforce `PRAGMA busy_timeout = 10000;` on all database client connections.
2. **Terminate Zombie Transaction Locks:**
   - Terminate hanging or stalled pipeline load connections.
3. **Route Read-Heavy Traffic to Read Replicas:**
   - Direct dashboard analytics queries to secondary read-only database connections.

## 4. Rollback Strategy
- Disconnect non-critical background ETL jobs to free connection pool headroom for real-time customer sync ingestion.

## 5. Verification & Recovery Confirmation
- Database connection acquisition latency p99 drops below 10ms.
- Zero locked database exceptions across 15 consecutive minutes of traffic.
