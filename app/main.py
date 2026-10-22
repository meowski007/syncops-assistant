"""
SyncOps Assistant - FastAPI Core Application.
REST API for customer-experience reliability KPIs, incident investigation, and Prometheus telemetry.
"""

import time
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Annotated

from fastapi import FastAPI, HTTPException, Query, Request, Response, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse

from app.config import settings
from app.database import get_db, init_db, check_db_health, get_db_path
from app.incidents import list_incidents, get_incident_by_id
from app.kpis import compute_all_kpis
from app.logging_config import logger
from app.metrics import (
    HTTP_REQUESTS_TOTAL,
    HTTP_REQUEST_DURATION_SECONDS,
    HTTP_ERRORS_TOTAL,
    INCIDENT_OPERATIONS_TOTAL,
    SYNTHETIC_SYNC_SUCCESS_RATE_GAUGE,
    SYNTHETIC_ACTIVE_INCIDENTS_GAUGE,
    get_metrics_payload,
)
from app.schemas import (
    HealthResponse,
    KPIsResponse,
    IncidentSummary,
    IncidentDetail,
    TriageRequest,
    TriageResult,
)
from app.triage.agent import triage_incident

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle manager: initializes database and ensures baseline data on startup."""
    logger.info("SyncOps Assistant API initializing...")
    db_path = get_db_path()
    init_db(db_path)
    
    # Check if database has records; if not, run deterministic seed automatically
    health = check_db_health(db_path)
    if health.get("record_counts", {}).get("customers", 0) == 0:
        logger.info("Empty database detected on startup. Executing initial deterministic synthetic seed...")
        from scripts.seed_data import seed_database
        seed_database(db_path=db_path)
        
    logger.info("SyncOps Assistant API successfully started.", extra={"database": str(db_path)})
    yield
    logger.info("SyncOps Assistant API shutting down.")

app = FastAPI(
    title="SyncOps Assistant API",
    description="Customer-Experience Reliability & Incident Triage Platform API (Synthetic Telemetry for Educational SRE Use)",
    version="1.0.0",
    lifespan=lifespan,
)

# Enable CORS for Streamlit and local dashboard clients
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.middleware("http")
async def observability_middleware(request: Request, call_next):
    """
    SRE observability middleware:
    - Generates unique Request ID
    - Tracks latency via Prometheus histogram
    - Increments request and error counters with bounded cardinality
    - Emits structured JSON log
    """
    request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
    request.state.request_id = request_id
    
    start_time = time.perf_counter()
    endpoint = request.url.path
    method = request.method
    
    # Normalize endpoint path for bounded Prometheus labels
    normalized_path = endpoint
    if endpoint.startswith("/incidents/") and endpoint != "/incidents":
        normalized_path = "/incidents/{incident_id}"

    try:
        response: Response = await call_next(request)
        status_code = response.status_code
    except Exception as exc:
        status_code = 500
        HTTP_ERRORS_TOTAL.labels(method=method, endpoint=normalized_path, status_code="500").inc()
        logger.error(
            f"Unhandled exception processing {method} {endpoint}: {exc}",
            extra={"request_id": request_id, "endpoint": endpoint, "method": method, "status_code": 500}
        )
        raise exc
    finally:
        duration = time.perf_counter() - start_time
        duration_ms = round(duration * 1000.0, 2)
        
        # Record Prometheus metrics (bounded labels only)
        HTTP_REQUESTS_TOTAL.labels(method=method, endpoint=normalized_path, status_code=str(status_code)).inc()
        HTTP_REQUEST_DURATION_SECONDS.labels(method=method, endpoint=normalized_path).observe(duration)
        
        if status_code >= 400:
            HTTP_ERRORS_TOTAL.labels(method=method, endpoint=normalized_path, status_code=str(status_code)).inc()
            
        logger.info(
            f"{method} {endpoint} -> {status_code} ({duration_ms}ms)",
            extra={
                "request_id": request_id,
                "endpoint": endpoint,
                "method": method,
                "status_code": status_code,
                "duration_ms": duration_ms
            }
        )
        
    response.headers["X-Request-ID"] = request_id
    return response

# ==============================================================================
# REST Endpoints
# ==============================================================================

@app.get("/health", response_model=HealthResponse, tags=["Health"])
def get_health():
    """Returns application health status, database connectivity, and record counts."""
    health_info = check_db_health()
    return HealthResponse(
        status="healthy" if health_info.get("connected") else "degraded",
        database_connected=health_info.get("connected", False),
        record_counts=health_info.get("record_counts", {}),
        timestamp=datetime.now(timezone.utc).isoformat(),
        disclosure="ALL TELEMETRY IS SYNTHETIC FOR EDUCATIONAL USE"
    )

@app.get("/kpis", response_model=KPIsResponse, tags=["Metrics & KPIs"])
def get_kpis(
    window_hours: Annotated[int | None, Query(description="Calculation window in hours (e.g. 24, 168). Default all data.", ge=1)] = None
):
    """Computes all 7 customer-experience KPIs over the synthetic database."""
    with get_db() as conn:
        kpis = compute_all_kpis(conn, window_hours=window_hours)
        
    # Update Prometheus platform gauges
    try:
        SYNTHETIC_SYNC_SUCCESS_RATE_GAUGE.set(kpis["sync_success_rate"]["value"])
    except Exception:
        pass
        
    return kpis

@app.get("/incidents", response_model=list[IncidentSummary], tags=["Incidents"])
def get_incidents(
    status: Annotated[str | None, Query(description="Filter by incident status: DETECTED, INVESTIGATING, MITIGATED, RESOLVED")] = None,
    severity: Annotated[str | None, Query(description="Filter by severity: SEV1, SEV2, SEV3, SEV4")] = None,
    cohort: Annotated[str | None, Query(description="Filter by affected client cohort")] = None,
    limit: Annotated[int, Query(description="Maximum results to return", ge=1, le=200)] = 50,
    offset: Annotated[int, Query(description="Pagination offset", ge=0)] = 0,
):
    """Retrieves list of incidents with validated filtering."""
    with get_db() as conn:
        incs = list_incidents(
            conn,
            status=status,
            severity=severity,
            cohort=cohort,
            limit=limit,
            offset=offset
        )
    return incs

@app.get("/incidents/{incident_id}", response_model=IncidentDetail, tags=["Incidents"])
def get_incident(incident_id: str):
    """Retrieves a single incident by ID with correlated cohort telemetry and customer tickets."""
    with get_db() as conn:
        inc = get_incident_by_id(conn, incident_id)
        
    if not inc:
        logger.warning(f"Incident '{incident_id}' not found.")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Incident with ID '{incident_id}' was not found in the synthetic repository."
        )
        
    INCIDENT_OPERATIONS_TOTAL.labels(operation="query_detail", status="success").inc()
    return inc

@app.post("/triage", response_model=TriageResult, tags=["Triage"])
def post_triage(request: TriageRequest):
    """Runs automated SRE incident triage using LLM tool-calling or deterministic fallback."""
    result = triage_incident(
        incident_id=request.incident_id,
        force_fallback=request.force_fallback
    )
    return result

@app.get("/metrics", tags=["Observability"])
def get_metrics():
    """Prometheus scrapable metrics exposition endpoint."""
    payload, content_type = get_metrics_payload()
    return PlainTextResponse(content=payload.decode("utf-8"), media_type=content_type)
