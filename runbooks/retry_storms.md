# SRE Runbook: Client Retry Storms & Thundering Herd

## Overview
- **Category:** `RETRY_STORM` / `RATE_LIMITED`
- **Severity Classification:** SEV2 (Global retry amplification > 3x) / SEV3 (Localized fleet retries)
- **Service:** Edge Ingress & Gateway Rate Limiter
- **Synthetic Flag:** SYNTHETIC DATA & SCENARIO FOR EDUCATIONAL USE

---

## 1. Symptoms & Detection
- Alert `ClientRetryStormActive`: Total ingestion requests surge 300% without commensurate increase in unique daily active users.
- `retry_count` distribution shifts: > 15% of sync events exhibit `retry_count >= 3`.
- Ingress HTTP 429 Too Many Requests responses spike above 5.0% of total edge traffic.

## 2. Immediate Diagnostic Checklist
1. **Analyze Retry Interval Distribution:**
   - Verify if clients are using fixed interval retries instead of exponential backoff with full jitter.
2. **Inspect Upstream Gateway Health:**
   - Determine if a transient downstream 500 error on sync shard ingestion triggered simultaneous client retries.
3. **Verify Rate Limiter Token Bucket Status:**
   - Confirm whether rate limiter token buckets are starved across specific IP ranges or customer cohorts.

## 3. Mitigation Steps
1. **Enable Dynamic Ingress Jitter Flags:**
   - Dispatch edge response header `Retry-After: 30` with randomized jitter window [15s, 45s].
2. **Shed Non-Critical Sync Traffic:**
   - Temporarily enable shedding on background analytics telemetry to prioritize interactive customer sync.
3. **Expand Ingress Gateway Capacity:**
   - Scale edge gateway instances by 50% to absorb concurrent connection attempts without TCP connection drops.

## 4. Rollback Strategy
- Gradually lower `Retry-After` thresholds in increments of 5 seconds once ingress CPU drops below 65%.

## 5. Verification & Recovery Confirmation
- Verify that `retry_count` returns to normal baseline (< 2% with retry >= 2).
- Confirm edge HTTP 429 responses return to < 0.1%.
- Ensure sync success rate stabilizes above 98.0% for 30 consecutive minutes.
