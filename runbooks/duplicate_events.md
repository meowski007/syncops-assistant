# SRE Runbook: Duplicate Synchronization Events & Idempotency Anomalies

## Overview
- **Category:** `DUPLICATE_EVENTS` / `SCHEMA_MISMATCH`
- **Severity Classification:** SEV3 (Elevated duplicates without database corruption) / SEV2 (Duplicate write loops)
- **Service:** Clean Ingestion Layer & Deduplication Gateway
- **Synthetic Flag:** SYNTHETIC DATA & SCENARIO FOR EDUCATIONAL USE

---

## 1. Symptoms & Detection
- Alert `DuplicateSyncEventRateElevated`: Duplicate event ratio exceeds 3.0% of incoming batch volume.
- Unique constraint violations detected in staging layer (`raw_sync_events`).
- Customer accounts reporting duplicated telemetry points or flickering state.

## 2. Immediate Diagnostic Checklist
1. **Analyze Client UUID Generation:**
   - Verify whether client app builds are reusing static event UUIDs across separate upload retries.
2. **Inspect Content Fingerprints:**
   - Compare SHA-256 content fingerprints of duplicate pairs to confirm if payloads are identical or distinct.
3. **Check Network Replay Gateways:**
   - Look for mobile carrier network proxy retries replaying HTTP POST requests.

## 3. Mitigation Steps
1. **Enforce Ingestion Deduplication Window:**
   - Configure gateway Redis cache with a 24-hour sliding bloom filter for event UUIDs.
2. **Activate Transactional UPSERTs:**
   - Ensure clean storage tables use idempotent `INSERT OR IGNORE` with unique constraints on event ID.
3. **Notify Client SDK Team:**
   - Flag non-RFC compliant UUID generator implementations in legacy mobile client versions.

## 4. Rollback Strategy
- If deduplication caching causes dropped valid events, revert deduplication filter TTL to 1 hour.

## 5. Verification & Recovery Confirmation
- Query `clean_sync_events` and confirm zero duplicate primary keys exist.
- Verify `skipped_duplicates` counter matches expected replayed batch volume.
