# SRE Runbook: Queue Backlog & Dead-Letter Queue (DLQ) Spikes

## Overview
- **Category:** `QUEUE_BACKLOG` / `RETRY_STORM`
- **Severity Classification:** SEV2 (DLQ ingestion > 1,000 msgs/min) / SEV3 (Moderate queue growth)
- **Service:** Asynchronous Event Broker & Dead-Letter Queue
- **Synthetic Flag:** SYNTHETIC DATA & SCENARIO FOR EDUCATIONAL USE

---

## 1. Symptoms & Detection
- Alert `IngestionQueueBacklogHigh`: Unprocessed message count in ingestion queue exceeds 50,000 items.
- Dead-letter queue (`pipeline_rejected_records`) receives unexpected surge of unparseable event payloads.
- Processing lag causes delayed customer-facing sync status indicators.

## 2. Immediate Diagnostic Checklist
1. **Analyze Dead-Letter Reasons:**
   - Sample the top 10 error strings in `pipeline_rejected_records` to isolate validation failures.
2. **Inspect Consumer Worker Health:**
   - Check if downstream consumers are failing healthchecks and restarting in crash loops.
3. **Verify Downstream Rate Limits:**
   - Check if database writes or downstream microservices are rate-limiting queue consumers.

## 3. Mitigation Steps
1. **Quarantine Poisoned Message Batches:**
   - Route unparseable payloads directly to dead-letter storage without blocking queue head-of-line processing.
2. **Increase Consumer Concurrency:**
   - Scale worker pods to drain queue backlog.
3. **Adjust Prefetch Limits:**
   - Reduce worker prefetch limit to prevent out-of-memory errors on worker nodes.

## 4. Rollback Strategy
- If an erroneous schema change broke worker deserializers, roll back the worker deployment immediately.

## 5. Verification & Recovery Confirmation
- Queue depth drops to nominal baseline (< 500 messages).
- Dead-letter rate drops to 0 records per minute under steady-state load.
