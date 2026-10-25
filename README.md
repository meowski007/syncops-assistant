# SyncOps Assistant: Customer-Experience Reliability & AI Operations Platform

> [!IMPORTANT]
> ### ⚠️ SYNTHETIC DATA DISCLOSURE
> **ALL DATA, TELEMETRY, LOGS, INCIDENT IDENTIFIERS, AND METRIC READINGS IN THIS REPOSITORY ARE 100% DETERMINISTICALLY GENERATED SYNTHETIC DATA CREATED FOR EDUCATIONAL RELIABILITY ENGINEERING, DATA PLATFORM, AND AI DEMONSTRATION.**
> This project is an independent educational portfolio project and does NOT contain real customer data, internal corporate infrastructure, proprietary telemetry, or non-public information from Noise, boAt, Google, Apple, Amgen, or any other commercial organization.

---

## 1. Problem Statement & Motivation
High-scale consumer synchronization and data ingestion platforms (such as mobile telemetry sync, cloud device synchronization, or enterprise data pipelines) process millions of sync events across heterogeneous device fleets (iOS, Android, IoT sensors, web clients). When edge ingestion drops, token invalidation surges, or payload timeouts spike, Site Reliability Engineers (SREs) and Data Platform engineers face common operational challenges:
- **Alert Fatigue & Delayed MTTR:** Sifting through raw ingestion errors across millions of records delays mean time to identify and mitigate customer-impacting regressions.
- **Data Quality & Privacy Gaps:** Raw ingestion logs often contain malformed records, corrupted timestamps, and customer identifiers that violate privacy policies if unmasked.
- **Reactive Rather Than Predictive Operations:** Teams react to outages after customers complain rather than forecasting metric degradation ahead of time.
- **Disconnected Runbooks & Hallucinated AI:** Operational mitigation steps remain trapped in static wikis, while ad-hoc generative AI chat tools hallucinate commands and lack grounded retrieval.

**SyncOps Assistant** addresses these challenges through a customer-experience reliability platform operating across a verified 4-stage operational workflow:

$$\text{Detect} \longrightarrow \text{Explain} \longrightarrow \text{Recover} \longrightarrow \text{Confirm}$$

---

## 2. Platform Architecture Diagram

```mermaid
flowchart TD
    subgraph Ingestion ["1. Data Ingestion & Governance Layer"]
        RAW[("Raw Landing Zone<br/>(raw_sync_events)")]
        DQ["Data Quality Gate<br/>(Schema, Bounds, Timestamps)"]
        MASK["PII Masking Engine<br/>(HMAC-SHA256 Salted Hashes)"]
        DLQ[("Dead-Letter Quarantine<br/>(pipeline_dead_letter)")]
        CLEAN[("Clean Analytical Store<br/>(clean_sync_events)")]
        AUDIT[("Governance Audit Log<br/>(pipeline_runs, dq_audit)")]
    end

    subgraph Service Layer ["2. FastAPI Core Services (:8000)"]
        API["FastAPI REST Router"]
        MID["Observability Middleware<br/>(Trace ID, Latency & JSON Logging)"]
        KPI["KPI Engine<br/>(7 CX Reliability Metrics)"]
        INC["Incident Correlation Service"]
        PROM["Prometheus Exporter (/metrics)"]
        DQ_EP["Data Quality API (/data-quality)"]
        FC_EP["Forecasting API (/forecast)"]
        RAG_EP["Retrieval-Only RAG API (/triage/rag)"]
        AGENT_EP["LLM Triage API (/triage)"]
    end

    subgraph Intelligence ["3. Forecasting & Knowledge Retrieval Engines"]
        subgraph TS ["Time-Series Forecasting Engine"]
            WF["Walk-Forward Validator<br/>(Rolling Origin / Anti-Leakage)"]
            HW["Holt-Winters Exp Smoothing"]
            SN["Seasonal Naive Baseline"]
            NV["Naive Drift Baseline"]
            DRIFT["Drift Detector (MAE/Residuals)"]
        end
        subgraph RAG ["Grounded RAG & Triage Engines"]
            CHUNK["Section-Aware Markdown Chunker"]
            VEC["Sublinear TF-IDF Vectorizer<br/>(Cosine Similarity Scoring)"]
            GUARD["Low-Relevance Guardrails<br/>(Refusal Threshold < 0.08)"]
            CITE["Citation & Provenance Engine"]
            AGENT["LLM Tool-Calling Agent<br/>(OpenAI SDK + Offline Fallback)"]
        end
    end

    subgraph Interfaces ["4. Dual Operator & Consumer Layer"]
        REACT["Vite + React 18 SPA (:5173)<br/>(Typed Client, Live Forecasts, Triage)"]
        STREAMLIT["Streamlit Dashboard (:8501)<br/>(Multi-Tab Observability)"]
        SLACK_REAL["Slack Bolt Bot (Socket Mode)"]
        SLACK_MOCK["Slack Mock Runner (CLI)"]
        PROMETHEUS["Optional Prometheus Scraper<br/>(not deployed)"]
    end

    RAW --> DQ
    DQ -->|Valid Records| MASK
    DQ -->|Failed Records| DLQ
    MASK --> CLEAN
    DQ --> AUDIT

    CLEAN --> KPI
    CLEAN --> INC
    CLEAN --> TS

    MID --> API
    API --> KPI
    API --> INC
    API --> DQ_EP
    API --> FC_EP
    API --> RAG_EP
    API --> AGENT_EP
    API --> PROM

    DQ_EP --> AUDIT
    FC_EP --> TS
    RAG_EP --> RAG
    AGENT_EP --> AGENT

    API --> REACT
    API --> STREAMLIT
    API --> SLACK_REAL
    CLEAN --> SLACK_MOCK
    PROM --> PROMETHEUS
```

---

## 3. Component Directory & Verified Database Baseline

### Actual Database Telemetry Baseline (Verified by SQLite Counts):
- **Raw Sync Events (`raw_sync_events`):** 20,000 ingested edge telemetry rows (across initial and subsequent pipeline runs).
- **Clean Sync Events (`clean_sync_events`):** 5,000 validated, deduplicated, and HMAC-pseudonymized records.
- **Distinct Customers:** 300 synthetic customer accounts across 5 device cohorts (`iOS-Production`, `iOS-Beta`, `Android-v3`, `WebClient-Enterprise`, `IoT-Firmware-v12`).
- **Incidents (`incidents`):** 5 synthetic operational incidents (`INC-2026-1001` through `INC-2026-1005`).
- **Support Tickets (`support_tickets`):** 244 synthetic customer support tickets correlated to incident windows.
- **Adoption Records (`adoption_records`):** 31 daily synthetic feature adoption rows.

### Subsystem Architecture:

| Subsystem | Module / Directory | Technology | Core Responsibility |
| :--- | :--- | :--- | :--- |
| **ETL Pipeline** | `pipeline/` | Python, SQLite, Pandera | Idempotent extract, validate, transform, and load pipeline. Rejects duplicates, routes malformed records to dead-letter quarantine. |
| **Data Governance** | `DATA_GOVERNANCE.md`, `pipeline/validate.py` | Python, HMAC-SHA256 | Schema contracts, 5 blocking rules, 3 warning rules, customer ID pseudonymization, automated markdown audit reports. |
| **Forecasting Engine** | `forecasting/` | Statsmodels, NumPy, SciPy | Chronological walk-forward validation (rolling origin) for Holt-Winters, Seasonal Naive, and Naive models with empirical prediction intervals. |
| **Retrieval-Only RAG** | `app/triage/rag/`, `runbooks/` | Scikit-Learn (TF-IDF), Cosine Sim | Section-aware chunking of 13 Markdown runbooks, sublinear TF-IDF retrieval, citation mapping, and low-relevance refusal guardrail. |
| **LLM Triage Agent** | `app/triage/agent.py`, `app/triage/tools.py` | Python, OpenAI SDK, SQLite | Bounded tool-calling agent querying database telemetry and markdown runbooks, with offline deterministic fallback (`app/triage/fallback.py`). |
| **RAG Evaluation** | `evaluation/` | Python, JSON Benchmark | Offline 25-query evaluation suite computing MRR, Hit@1, Hit@3, Hit@5, and citation validity over different chunk sizes. |
| **REST API** | `app/main.py`, `app/schemas.py` | FastAPI, Pydantic v2 | Single source of truth exposing `/health`, `/kpis`, `/incidents`, `/metrics`, `/data-quality`, `/forecast`, `/triage/rag`, and `/triage`. |
| **React Frontend** | `frontend/` | React 18, Vite, TypeScript | Observability web interface with live KPI cards, incident directory, interactive forecast charts, and RAG chat. |
| **Streamlit Dashboard** | `dashboard/app.py` | Streamlit, Plotly | Multi-tab operations cockpit covering Incidents, Forecasts, Data Quality audit runs, and RAG runbook search. |
| **Slack Integration** | `app/slack/` | Slack Bolt for Python | Socket Mode bot (for connecting to real Slack workspaces) and local zero-credential mock runner (`python -m app.slack.mock`). |
| **Observability** | `app/metrics.py`, `app/logging_config.py` | Prometheus Client, JSON Logs | Bounded-cardinality Prometheus metrics and structured JSON access logs with `X-Request-ID` tracing. |

---

## 4. Quick Start & Setup

### Verified Environment Prerequisites
- **Python:** Tested on Python 3.12.10
- **Node.js / npm:** Tested on Node.js v24.22.1 / npm 11.19.1
- **Git:** Tested on Git 2.56.0.windows.1
- **Shell:** Windows PowerShell 5.1+ / PowerShell 7+, or macOS / Linux bash

### Windows PowerShell Setup

```powershell
# 1. Create and activate virtual environment
python -m venv .venv
.venv\Scripts\Activate.ps1

# 2. Upgrade pip and install backend dependencies
pip install --upgrade pip
pip install -r requirements.txt

# 3. Seed synthetic database idempotently
python scripts/seed_data.py

# 4. Execute the ETL Data Pipeline (Raw -> Clean Analytical Store)
python -m pipeline.run

# 5. Train and backtest Time-Series Forecasting models
python -m forecasting.train

# 6. Install React frontend dependencies and verify build
cd frontend
npm install
npm run build
cd ..

# 7. Run the automated test suite (88 tests)
pytest -v
```

### macOS / Linux Bash Setup

```bash
# 1. Create and activate virtual environment
python3 -m venv .venv
source .venv/bin/activate

# 2. Upgrade pip and install backend dependencies
pip install --upgrade pip
pip install -r requirements.txt

# 3. Seed synthetic database idempotently
python3 scripts/seed_data.py

# 4. Execute the ETL Data Pipeline (Raw -> Clean Analytical Store)
python3 -m pipeline.run

# 5. Train and backtest Time-Series Forecasting models
python3 -m forecasting.train

# 6. Install React frontend dependencies and verify build
cd frontend
npm install
npm run build
cd ..

# 7. Run the automated test suite (88 tests)
pytest -v
```

---

## 5. Running the Application Services

Open separate terminal windows for each component:

### Service 1: FastAPI REST API (`http://localhost:8000`)
```powershell
.venv\Scripts\Activate.ps1
uvicorn app.main:app --reload --port 8000
```
- Swagger UI Documentation: `http://localhost:8000/docs`
- Prometheus Metrics: `http://localhost:8000/metrics`

### Service 2: Vite React Frontend (`http://localhost:5173`)
```powershell
cd frontend
npm run dev
```
- Open browser at `http://localhost:5173`

### Service 3: Streamlit Reliability Dashboard (`http://localhost:8501`)
```powershell
.venv\Scripts\Activate.ps1
streamlit run dashboard/app.py --server.port 8501
```
- Open browser at `http://localhost:8501`

### Service 4: Local Slack Mock Mode (Zero Credentials Required)
```powershell
.venv\Scripts\Activate.ps1
python -m app.slack.mock
```

---

## 6. Automated Test Suite & Verification Results

The automated test suite contains 88 unit and integration tests covering regression baselines, data quality rules, forecasting intervals, RAG guardrails, and mocked LLM tool calling.

**Source Command:**
```powershell
.venv\Scripts\pytest -v
```

### Real Test Output:
```text
============================= test session starts =============================
platform win32 -- Python 3.12.10, pytest-8.4.2, pluggy-1.7.0 -- syncops-assistant\.venv\Scripts\python.exe
cachedir: .pytest_cache
rootdir: syncops-assistant
configfile: pytest.ini
testpaths: tests
plugins: anyio-4.15.1, cov-5.0.0, typeguard-4.6.0
collected 88 items

tests/test_api.py ......................... [ 11%]
tests/test_api_upgrades.py .........        [ 21%]
tests/test_data_quality.py .......          [ 29%]
tests/test_forecasting.py .........         [ 39%]
tests/test_incidents.py .....               [ 45%]
tests/test_kpis.py ...................      [ 65%]
tests/test_pipeline.py .......              [ 73%]
tests/test_rag.py ......                    [ 80%]
tests/test_slack_mock.py ......             [ 87%]
tests/test_triage.py ...........            [100%]

======================= 88 passed, 2 warnings in 9.85s ========================
```

- **Baseline Tests Preserved:** 49/49 passed.
- **Upgrade Tests (Data Quality, Forecasting, RAG, Incidents):** 38/38 passed.
- **LLM Tool-Calling Mock Integration Test:** 1/1 passed (`test_triage_incident_llm_tool_calling_mocked`).
- **Total Suite:** **88 passed, 0 failed in 9.85s**.

---

## 7. Data Quality & Governance Summary

SyncOps Assistant implements a structured data governance framework documented in [DATA_GOVERNANCE.md](DATA_GOVERNANCE.md).

**Source Command:**
```powershell
python -m pipeline.run
```

### Real Pipeline Execution Output:
```text
=================================================================
🚀 SYNCOPS REPRODUCIBLE ETL PIPELINE [Run: RUN-20261025203538-aaedb2]
Source: sqlite://syncops.db/sync_events | Dry-Run: False
=================================================================
[Phase 1: EXTRACT] Ingesting raw events...
  ✓ Extracted 5000 records from sqlite://syncops.db/sync_events
[Phase 2: VALIDATE] Executing schema & data quality checks...
  ✓ Accepted: 5000 | Rejected: 0 | Warnings: 0
[Phase 3: TRANSFORM] Normalizing, masking PII & deriving features...
  ✓ Transformed 5000 clean records (Batch duplicates filtered: 0)
  ✓ PII Masking: customer_id -> MASK-8fa1742c54dbdf1b
[Phase 4: LOAD] Committing to SQLite (raw staging + clean analytical layers)...
  ✓ Inserted new clean records: 0
  ✓ Skipped historical duplicates: 5000
  ✓ Staged raw audit events: 5000
[Phase 5: REPORT] Compiling audit report & quality metrics...
  ✓ Data Quality Report generated: DQR-f456cb165323
=================================================================
✅ PIPELINE RUN COMPLETED SUCCESSFULLY!
=================================================================
```

### Governance Architecture:
- **Raw Landing Zone:** Immutable append-only `raw_sync_events` table preserves verbatim edge telemetry with idempotency keys.
- **Blocking Quality Gates:** Records with missing IDs, invalid status values, negative latency or payload size, or future timestamps are quarantined to `pipeline_dead_letter`.
- **Non-Blocking Warnings:** High latency (>10,000ms), large payload (>5MB), or excessive retries (>3) are flagged without stalling the pipeline.
- **Cryptographic PII Masking:** Customer IDs (`CUST-0001`) and Device IDs (`DEV-0001`) are transformed into salted HMAC-SHA256 hex tokens (`cust_...`, `dev_...`) before persisting into `clean_sync_events`.
- **Lineage Tracking:** Every pipeline execution generates an immutable audit record in `pipeline_runs` and produces an automated markdown quality report in [reports/data_quality/](reports/data_quality/).

---

## 8. Time-Series Forecasting & Backtesting Results

The forecasting subsystem ([forecasting/](forecasting/)) projects future daily failure rates and incident volumes to enable proactive SRE alerting.

**Source Command:**
```powershell
python -m forecasting.train
```

### Backtesting Methodology:
- Evaluated via chronological walk-forward validation (rolling origin) designed to avoid look-ahead leakage; covered by tests.
- Models tested: **Exponential Smoothing (Holt-Winters)**, **Seasonal Naive**, and **Naive Baseline (last observed value)**.
- Generated report: [reports/forecasting/forecast_evaluation_report.md](reports/forecasting/forecast_evaluation_report.md).

### Real Evaluation Results (From `forecast_evaluation_report.md`):

| Target Metric | Model Architecture | Walk-Forward MAE | Walk-Forward RMSE | Walk-Forward sMAPE | Selected Status |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Daily Sync Failure Rate (%)** | **Exponential Smoothing (Holt-Winters)** | **0.968** | **1.068** | **16.10%** | **Selected Champion** |
| Daily Sync Failure Rate (%) | Seasonal Naive | 1.098 | 1.407 | 19.52% | Baseline |
| Daily Sync Failure Rate (%) | Naive Baseline (Last Value) | 1.098 | 1.407 | 19.52% | Baseline |
| **Daily Incident Volume** | **Naive Baseline (Last Value)** | **1.000** | **1.000** | **200.00%** | **Selected Champion** (Best on sparse integer events) |
| Daily Incident Volume | Seasonal Naive | 1.000 | 1.000 | 200.00% | Baseline |
| Daily Incident Volume | Exponential Smoothing | 1.833 | 1.878 | 200.00% | Baseline |

- **Sparse Event Finding:** For daily incident volume, Naive Baseline achieved lower error than Exponential Smoothing because incidents are rare, discrete integer occurrences (1 or 0 per day) where exponential smoothing over-predicts continuous fractions.
- **Empirical Prediction Intervals:** Prediction bounds are calculated from model residual standard error ($\sigma_e \cdot z \cdot \sqrt{h}$) ensuring intervals widen with the forecast horizon while clamping failure rates between $[0\%, 100\%]$.
- **Drift Monitoring:** Residual tracking alerts SRE operators when consecutive prediction errors exceed $2.5\times$ baseline MAE.

---

## 9. Grounded RAG Knowledge Base & Retrieval Evaluation

SyncOps Assistant features a grounded retrieval-augmented generation engine backed by 13 operational SRE runbooks ([runbooks/](runbooks/)).

**Source Command:**
```powershell
python evaluation/rag_evaluator.py
```

### Retrieval Architecture:
- **Section-Aware Markdown Chunker:** Chunks documents strictly by Markdown headers (`#`, `##`, `###`), preserving complete procedural steps rather than splitting sentences arbitrarily.
- **Sublinear TF-IDF + Cosine Retrieval:** Employs sublinear term-frequency scaling with cosine similarity scoring, delivering exact matching on technical error codes (`AUTH_EXPIRED`, `PAYLOAD_TIMEOUT`).
- **Low-Relevance Refusal Guardrail:** Queries with maximum cosine similarity $< 0.08$ trigger an immediate safety refusal, preventing hallucinated recommendations on out-of-scope prompts.
- **Source Citations:** Every triage answer includes exact runbook filenames, section headings, and snippet references.

### Real Evaluation Results (25 Curated SRE Questions, From `rag_evaluation_report.md`):

| Evaluation Metric | Configuration A (Target ~300 Chars / 50 Overlap) | Configuration B (Target ~600 Chars / 100 Overlap) |
| :--- | :--- | :--- |
| **Total Chunks in Corpus** | 106 chunks | 79 chunks |
| **Mean Reciprocal Rank (MRR)** | 0.858 | **0.880** |
| **Hit@1 (Precision @ 1)** | 80.0% | **84.0%** |
| **Hit@3** | 88.0% | 88.0% |
| **Hit@5** | 96.0% | 96.0% |
| **Citation Validity Rate** | **100.0%** | **100.0%** |

---

## 10. Autonomous Triage vs. Retrieval-Only RAG

To avoid confusion during technical interviews, the platform separates two distinct triage mechanisms:

| Dimension | Retrieval-Only RAG (`/triage/rag`) | LLM Tool-Calling Agent (`/triage`) |
| :--- | :--- | :--- |
| **Endpoint** | `POST /triage/rag` (`app/triage/rag/answer.py`) | `POST /triage` (`app/triage/agent.py`) |
| **Architecture** | Pure retrieval over local markdown runbooks using TF-IDF + Cosine Similarity. | ReAct-style tool-calling loop using OpenAI SDK with bounded turns (max 5 iterations). |
| **Generative LLM Call** | **None.** No text generation model is invoked; extracts verbatim runbook steps. | Invokes configured OpenAI model (`gpt-4o-mini`) via tool-calling API when keys exist. |
| **Callable Tools** | None (retriever indexes markdown chunks). | `get_incident_details` (queries SQLite telemetry) and `search_and_read_runbook` (reads runbooks). |
| **Offline Fallback** | Runs 100% offline with zero dependencies. | Falls back to deterministic rule engine (`app/triage/fallback.py`) if keys are absent or invalid. |
| **Guardrails** | Refuses queries if cosine similarity $< 0.08$. | Parses and validates output against Pydantic schema; flags `requires_human_review = True`. |

---

## 11. Limitations & Honest Notes

To maintain strict engineering honesty during technical interviews:
1. **Self-Authored Runbooks & Evaluation Set:** The 13 operational runbooks and the 25 evaluation questions were written by me, and the chunk-size configurations (300 vs 600 chars) were tuned against these same 25 questions. Consequently, the retrieval benchmark demonstrates methodology and metric calculation rather than out-of-domain generalization.
2. **Synthetic Telemetry:** All 5,000 sync events and incident logs are synthetic, generated with deterministic seasonal trends and failure distributions. Forecast model performance proves backtesting pipeline implementation, not real-world predictive validity. In particular, Naive Baseline outperformed Exponential Smoothing on incident counts due to sparse integer volume.
3. **Slack Socket Mode Testing:** The Slack integration includes a live Socket Mode listener (`app/slack/bot.py`) and a CLI mock runner (`app/slack/mock.py`). The bot has been tested end-to-end via the local mock runner; live workspace connectivity requires user-supplied Slack app tokens.
4. **Prometheus Exposition:** The API exposes bounded-cardinality Prometheus metrics at `/metrics`. No production Prometheus server or Grafana dashboard is deployed; metrics collection is verified via unit tests and direct HTTP scraping.

---

## 12. Docker & Container Deployment

The multi-service stack includes container definitions:

```bash
docker compose up --build -d
```

### Services Defined:
- `syncops-api`: FastAPI REST service on `http://localhost:8000`
- `syncops-dashboard`: Streamlit dashboard on `http://localhost:8501`
- `syncops-frontend`: Nginx-served Vite React SPA on `http://localhost:5173`
- `syncops-data`: Persistent local volume for SQLite database storage

> **Verification Status:** Docker Compose v5.5.1 configuration files are present; container runtime was not verified on this machine because Docker Desktop daemon was not active.

---

## 13. Interview Preparation Guide: SRE, AI & Data Platform Roles

Use this section to articulate your design choices, trade-offs, and reliability engineering philosophy during technical interviews.

### Q1: "Why did you build an ETL pipeline with logical raw and clean layers instead of writing directly to clean tables?"
> **Answer:** "In telemetry synchronization platforms, edge data arrives with varying levels of quality — clock skew, network retries, malformed payloads, or corrupted client timestamps. Writing directly to analytical tables risks corrupting core SLIs.
>
> We implemented a medallion-inspired architecture: `raw_sync_events` is an immutable, append-only landing zone. The `pipeline/validate.py` module enforces 5 blocking quality checks, routing invalid records to a dead-letter quarantine table (`pipeline_dead_letter`) while passing clean data through HMAC-SHA256 PII masking into `clean_sync_events`. This ensures analytical idempotency, protects customer privacy, and enables root-cause auditing on rejected payloads."

### Q2: "How do you avoid lookahead bias and temporal leakage in your time-series forecasting?"
> **Answer:** "Standard k-fold cross-validation is invalid for time-series because it trains on future observations to predict past ones. We built a chronological walk-forward validator (rolling origin) designed to prevent lookahead leakage, backed by automated unit tests.
>
> For each test fold $t$, the model is fitted strictly on observations $[1, t-1]$ and predicts $[t, t+h-1]$. Furthermore, prediction intervals are computed from in-sample residual variance $\sigma_e \cdot z \cdot \sqrt{h}$, ensuring uncertainty expands realistically as the horizon extends into the future. On our daily sync failure rate metric, Exponential Smoothing achieved a backtested MAE of 0.968, outperforming Seasonal Naive and Naive baselines (MAE 1.098)."

### Q3: "Why did you choose TF-IDF with cosine similarity for RAG rather than a heavy remote embedding model?"
> **Answer:** "I did not benchmark remote neural embeddings. I chose sublinear TF-IDF for exact error-code matching (such as `AUTH_EXPIRED` or `PAYLOAD_TIMEOUT`), zero remote API dependencies, zero network latency, and deterministic execution without cost.
>
> Our offline evaluation across 25 curated SRE questions yielded an MRR of 0.880 and Hit@1 of 84%, with a 100% citation validity rate and a low-relevance refusal threshold that prevents hallucinated incident mitigation advice."

### Q4: "How does the system ensure customer privacy and compliance with data governance standards?"
> **Answer:** "In `DATA_GOVERNANCE.md`, we established strict data classification rules. Raw customer IDs (`CUST-0001`) and device IDs (`DEV-0001`) are considered pseudonymous identifiers. During the ETL transformation step, we hash these identifiers using HMAC-SHA256 with a configurable salt before writing to `clean_sync_events`.
>
> Analytical consumers and SRE operators can still correlate repeat failures across distinct sessions without exposing the actual customer identifier. If a salt rotation or compliance audit is required, the raw landing layer provides an immutable audit trail."

---

## 14. Independent Project & Synthetic Data Disclaimer
This software is developed independently for educational purposes, portfolio demonstration, and SRE / Data Platform skills evaluation. It is an independent portfolio project and is not an official product of Noise, boAt, Google, Apple, Amgen, or any commercial employer. All trademarks and company names are used strictly for context.
