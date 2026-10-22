# SRE Runbook: Recovery Confirmation & Post-Incident Verification

## Overview
- **Category:** `RECOVERY_CONFIRMATION`
- **Scope:** Universal Standard Operating Procedure across all incident severities
- **Phase:** **Detect → Explain → Recover → Confirm** (Phase 4: Confirm)
- **Synthetic Flag:** SYNTHETIC DATA & SCENARIO FOR EDUCATIONAL USE

---

## 1. Purpose
This runbook defines the mandatory verification protocol required before an incident can transition from `INVESTIGATING` / `MITIGATED` to `RESOLVED`.
Premature closure without rigorous metric confirmation leads to recurring incidents and repeat customer failures.

## 2. Standard 4-Step Confirmation Protocol

### Step 1: Metric Stability Window
- The primary service KPI (e.g. `sync_success_rate`) must remain within the acceptable Service Level Objective (SLO >= 98.0%) for a minimum of **30 consecutive minutes** under regular production traffic volume.

### Step 2: Cohort Verification
- Check the specific cohort telemetry (`affected_cohort`) using the `/incidents/{id}` endpoint or dashboard drill-down.
- Confirm that error rates for the impacted cohort have returned to baseline parity with unaffected cohorts.

### Step 3: Customer Sentiment & Ticket Decay
- Observe incoming customer support tickets. The volume of new tickets with the relevant failure category must decrease by at least 90% from peak incident levels.

### Step 4: Observability Drain
- Review Prometheus metrics (`syncops_http_errors_total` and `syncops_synthetic_sync_success_rate`).
- Ensure no secondary alerts or flapping alerts are registered.

## 3. Incident State Transition
1. Document the exact mitigation time and root cause summary.
2. Calculate and record the final MTTR (Time to Recover).
3. Update incident status to `RESOLVED` in the incident repository.
4. Schedule an internal blameless Post-Incident Review (PIR) if severity was SEV1 or SEV2.
