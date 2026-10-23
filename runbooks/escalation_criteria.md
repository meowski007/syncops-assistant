# SRE Runbook: Incident Escalation Criteria & On-Call Handoff

## Overview
- **Category:** `ESCALATION_CRITERIA` / `OPERATIONAL_GOVERNANCE`
- **Scope:** Universal protocol governing on-call escalation, commander handoff, and stakeholder communication.
- **Synthetic Flag:** SYNTHETIC DATA & SCENARIO FOR EDUCATIONAL USE

---

## 1. Purpose
Defines objective thresholds and communication pathways for escalating incidents beyond primary on-call engineers to specialized teams and leadership.

## 2. Quantitative Escalation Triggers

| Trigger Condition | Action Required | Escalation Target |
| :--- | :--- | :--- |
| **MTTR > 60 mins on SEV1** | Hand over primary investigation to dedicated Incident Commander (IC). | Senior SRE On-Call Lead |
| **Sync Success Rate < 85%** | Declare Major Platform Outage; assemble war room. | Core Services Engineering Leadership |
| **Widespread Auth Invalidation** | Page Identity Security & Token Architecture team. | Identity Platform On-Call |
| **Fleet BLE Sync Blocked** | Page Hardware & Firmware Systems team. | Device Firmware Engineering Lead |
| **Data Quality Rejection > 25%** | Halt downstream analytical consumers; page Data Platform. | Data Engineering On-Call |

## 3. Communication Cadence
- **SEV1 Incidents:** Status updates published to `#syncops-alerts` and status dashboard every **15 minutes**.
- **SEV2 Incidents:** Status updates published every **30 minutes**.
- **SEV3 / SEV4 Incidents:** Updates posted upon state change (`DETECTED` -> `INVESTIGATING` -> `MITIGATED` -> `RESOLVED`).

## 4. Post-Incident Review (PIR) Protocol
- Any SEV1 or SEV2 incident mandates a blameless Post-Incident Review document within **48 hours** of resolution.
- PIR must document: Timeline of events, Root Cause Analysis (5 Whys), What Went Well, What Went Wrong, Where We Got Lucky, and Action Items with JIRA owners.
