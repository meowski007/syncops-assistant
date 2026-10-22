# SRE Runbook: Synchronization Pipeline Failures

## Overview
- **Category:** `SYNC_FAILURE` / `SCHEMA_MISMATCH` / `DATABASE_LOCK`
- **Severity Classification:** SEV1 (global sync drop > 10%) / SEV2 (cohort degradation)
- **Service:** Sync Ingress & Data Pipeline Engine
- **Synthetic Flag:** SYNTHETIC DATA & SCENARIO FOR EDUCATIONAL USE

---

## 1. Symptoms & Detection
- Alert `SyncSuccessRateDegraded`: Sync success rate drops below 95% over a 15-minute rolling window.
- Spikes in HTTP 500 or 504 on `/api/v1/sync` ingestion gateway.
- Customers reporting stuck upload progress or retry loops.

## 2. Immediate Diagnostic Checklist
1. **Identify Affected Cohort:**
   - Execute query on `sync_events` grouped by cohort and `failure_category`.
   - Inspect whether failures are localized to a specific app version or OS build.
2. **Examine Database Lock Contention:**
   - Check write transaction duration on core shard storage.
   - Look for deadlocks or slow commit times exceeding 2,500ms.
3. **Inspect Schema Compatibility:**
   - Verify if a recent protobuf or JSON schema rollout deprecated fields still transmitted by legacy clients.

## 3. Mitigation Steps
1. **Enable Graceful Client Throttling:**
   - Issue dynamic configuration flag `sync_jitter_interval_ms=15000` to distribute retry storms.
2. **Drain Stalled Worker Queues:**
   - Scale consumer workers or pause non-critical batch synchronization jobs to prioritize interactive customer sync.
3. **Schema Rollback:**
   - If schema mismatch is detected, redeploy edge gateway schema compatibility layer to permit optional legacy fields.

## 4. Rollback Strategy
- Revert the latest edge gateway deployment to the previous stable release.
- Flush edge cache and invalidation layers.

## 5. Verification & Recovery Confirmation
- Monitor `/kpis` endpoint: Ensure `sync_success_rate` returns above 98% for at least two consecutive 15-minute evaluation windows.
- Verify that `repeat_failure_rate` drops below 2.0%.
- Confirm zero active SEV1 or SEV2 alerts in Prometheus monitoring.
