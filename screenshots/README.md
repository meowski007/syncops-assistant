# Screenshots & Visual Interface Walkthrough

This directory contains placeholders and visual documentation for the **SyncOps Assistant** dashboard and SRE investigation views.

---

### 1. Customer-Experience Core KPIs & Health Banner
- **File:** `01_kpi_overview.png` (Placeholder)
- **Description:** Displays the synthetic data disclosure banner, the 7 core reliability KPIs (Sync Success Rate, Recovery Rate, MTTR, Repeat Failure Rate, Support Tickets Filed, Self-Service Resolution Rate, and Sync Feature Adoption Rate), and the calculation window filter.
- **How to capture manually:**
  1. Start the API: `.venv\Scripts\uvicorn app.main:app --port 8000`
  2. Start the dashboard: `.venv\Scripts\streamlit run dashboard/app.py`
  3. Open `http://localhost:8501` in your browser.
  4. Capture the top section with KPI metric cards.

---

### 2. Failure Distribution & Severity Analytics
- **File:** `02_failure_distribution.png` (Placeholder)
- **Description:** Interactive Plotly charts illustrating sync error categorizations (e.g. `PAYLOAD_TIMEOUT`, `AUTH_EXPIRED`, `FIRMWARE_UNSUPPORTED`) and incident severity breakdown (`SEV1` through `SEV4`).
- **How to capture manually:**
  1. Scroll down to the "Failure Category Distribution" and "Incident Severity & Status Distribution" sections.
  2. Capture both charts side-by-side.

---

### 3. SRE Incident Triage & Runbook Correlation
- **File:** `03_incident_triage_investigation.png` (Placeholder)
- **Description:** Live demonstration of the autonomous SRE triage agent. Shows incident `INC-2026-1001`, correlated cohort telemetry, empirical evidence list, and recommended mitigation actions extracted from `payload_timeout_guide.md`.
- **How to capture manually:**
  1. Select `INC-2026-1001` in the incident dropdown.
  2. Click **"Run SRE Incident Triage"**.
  3. Capture the resulting green confirmation box, summary, likely root cause, evidence points, and referenced runbooks.

---

### 4. Local Slack Mock Mode
- **File:** `04_slack_mock_terminal.png` (Placeholder)
- **Description:** Terminal output of `python -m app.slack.mock` showing simulated `/syncstatus`, `/incidents`, mention triage, and threshold-triggered alerts with cooldown.
- **How to capture manually:**
  1. Run `.venv\Scripts\python -m app.slack.mock` in Windows PowerShell.
  2. Capture the formatted simulated Slack blocks in the terminal.
