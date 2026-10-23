# SRE Runbook: Delayed Event Processing & Pipeline Consumer Lag

## Overview
- **Category:** `PIPELINE_LAG` / `PAYLOAD_TIMEOUT`
- **Severity Classification:** SEV2 (Lag > 30 minutes across critical cohorts) / SEV3 (Minor batch lag)
- **Service:** Asynchronous Stream Ingestion & Processing Workers
- **Synthetic Flag:** SYNTHETIC DATA & SCENARIO FOR EDUCATIONAL USE

---

## 1. Symptoms & Detection
- Alert `SyncPipelineLagCritical`: Time delta between event generation timestamp and ingestion time exceeds 15 minutes.
- Worker queue length increases monotonically.
- End-to-end telemetry pipeline latency p99 exceeds 45,000ms.

## 2. Immediate Diagnostic Checklist
1. **Inspect Worker Consumer Group Offset:**
   - Identify whether consumer lag is concentrated on specific partition shards.
2. **Review Worker CPU and Memory Utilization:**
   - Look for garbage collection pauses or thread pool exhaustion in worker nodes.
3. **Check Downstream Database Write Latency:**
   - Verify if database lock waits are stalling worker acknowledgment commits.

## 3. Mitigation Steps
1. **Scale Consumer Replicas:**
   - Horizontally auto-scale consumer worker deployment from baseline to 200% capacity.
2. **Increase Batch Fetch Size:**
   - Optimize worker chunk size from 100 to 500 records per poll cycle.
3. **Partition Rebalancing:**
   - Force consumer group rebalance if an individual worker pod is stalled on a poisoned pill record.

## 4. Rollback Strategy
- If recent worker code changes introduced performance regression, roll back container tag to previous release.

## 5. Verification & Recovery Confirmation
- Consumer lag returns to < 30 seconds across all partitions.
- Event arrival-to-clean-layer duration stabilizes under 60 seconds.
