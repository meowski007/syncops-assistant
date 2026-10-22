# SRE Runbook: Payload Timeout and Ingestion Gateway Latency

## Overview
- **Category:** `PAYLOAD_TIMEOUT` / `RATE_LIMITED`
- **Severity Classification:** SEV1 (High volume customer sync failures) / SEV2 (Intermittent timeouts)
- **Service:** Batch Ingestion Gateway & Decompression Workers
- **Synthetic Flag:** SYNTHETIC DATA & SCENARIO FOR EDUCATIONAL USE

---

## 1. Symptoms & Detection
- Alert `PayloadTimeoutSpike`: Sync attempts timing out after 5,000ms threshold.
- Ingestion worker CPU utilization pinned at 100%.
- Latency p95 and p99 exceeding 3,000ms on client batch telemetry uploads.

## 2. Immediate Diagnostic Checklist
1. **Analyze Client Payload Sizes:**
   - Check if clients in cohorts such as `iOS-Production` or `WebClient-Enterprise` are sending uncompressed payloads > 50KB.
2. **Inspect Upstream Decompression Buffer:**
   - Look for buffer allocation errors, garbage collection pauses, or thread starvation in ingestion services.
3. **Verify Rate Limiter Behavior:**
   - Confirm whether rate limiter token buckets are saturated or if backend connection pools are exhausted.

## 3. Mitigation Steps
1. **Increase Gateway Timeout & Concurrency:**
   - Temporarily increase connection timeout from 5.0s to 10.0s to permit in-flight payload completion.
2. **Horizontal Auto-Scaling:**
   - Increase replica count on batch ingestion pods by 100% to relieve CPU and buffer pressure.
3. **Adaptive Client Throttling:**
   - Instruct clients via response headers to back off batch sync upload frequency using exponential backoff with full jitter.

## 4. Rollback Strategy
- If caused by a newly deployed decompression library or ingestion binary, rollback container image to previous release tag.

## 5. Verification & Recovery Confirmation
- Monitor `avg_latency_ms` on `sync_events`: Ensure p95 drops below 400ms.
- Check that timeout error rate returns to < 0.1%.
- Ensure memory and CPU consumption on ingestion workers stabilizes below 70%.
