"""
Pydantic Schemas for SyncOps Assistant REST API and LLM Triage Agent.
Enforces strict typing, validation, and serialization.
"""

from pydantic import BaseModel, Field
from typing import Any

# ==============================================================================
# Health & Status Schemas
# ==============================================================================
class HealthResponse(BaseModel):
    status: str = Field(default="healthy", description="Service health status")
    database_connected: bool
    record_counts: dict[str, int]
    timestamp: str
    disclosure: str = "ALL TELEMETRY IS SYNTHETIC FOR EDUCATIONAL USE"

# ==============================================================================
# KPI Schemas
# ==============================================================================
class KPIDetail(BaseModel):
    name: str
    value: float | int
    unit: str
    sample_size: int
    description: str
    extra: dict[str, Any] = Field(default_factory=dict)

class KPIsResponse(BaseModel):
    sync_success_rate: dict[str, Any]
    recovery_rate: dict[str, Any]
    time_to_recover: dict[str, Any]
    repeat_failure_rate: dict[str, Any]
    sync_related_support_tickets: dict[str, Any]
    self_service_resolution_rate: dict[str, Any]
    adoption_rate: dict[str, Any]
    window_hours: int | None = None
    calculated_at: str
    disclosure: str = "SYNTHETIC_DATA_ONLY"

# ==============================================================================
# Incident Schemas
# ==============================================================================
class IncidentSummary(BaseModel):
    id: str
    title: str
    severity: str
    status: str
    start_time: str
    recovery_time: str | None = None
    affected_cohort: str
    failure_category: str
    root_cause_summary: str | None = None

class IncidentDetail(IncidentSummary):
    cohort_telemetry: dict[str, Any] = Field(default_factory=dict)
    associated_tickets: list[dict[str, Any]] = Field(default_factory=list)

# ==============================================================================
# LLM Triage Schemas (Part 9)
# ==============================================================================
class TriageRequest(BaseModel):
    incident_id: str = Field(..., description="Target incident ID, e.g. INC-2026-1001")
    force_fallback: bool = Field(default=False, description="Force deterministic rule-based analysis without LLM")

class TriageResult(BaseModel):
    incident_id: str
    summary: str
    likely_cause: str
    suggested_next_step: str
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score between 0.0 and 1.0")
    evidence: list[str] = Field(default_factory=list)
    runbook_references: list[str] = Field(default_factory=list)
    requires_human_review: bool = True
    analysis_mode: str = Field(..., description="'llm_tool_calling' or 'deterministic_fallback'")
    disclaimer: str = "Advisory AI analysis over synthetic data. Human operator verification required."

# ==============================================================================
# RAG Triage Schemas (Upgrade 4)
# ==============================================================================
class RagTriageRequest(BaseModel):
    incident_id: str | None = Field(default=None, description="Optional target incident ID, e.g. INC-2026-1001")
    query: str | None = Field(default=None, description="Operational question or diagnostic query")
    min_score: float = Field(default=0.08, ge=0.0, le=1.0, description="Relevance cutoff threshold")
    top_k: int = Field(default=3, ge=1, le=10, description="Max runbook chunks to retrieve")

# ==============================================================================
# Forecasting Schemas (Upgrade 3)
# ==============================================================================
class ForecastPoint(BaseModel):
    date: str
    point_forecast: float
    lower_bound: float
    upper_bound: float

class ForecastHistoryPoint(BaseModel):
    date: str
    value: float

class ForecastResponse(BaseModel):
    target: str
    target_label: str
    unit: str
    status: str
    model_name: str
    horizon_days: int
    historical: list[ForecastHistoryPoint]
    forecast: list[ForecastPoint]
    metrics: dict[str, Any] = Field(default_factory=dict)
    drift_monitoring: dict[str, Any] = Field(default_factory=dict)
    disclaimer: str = "ALL TELEMETRY IS SYNTHETIC FOR EDUCATIONAL EVALUATION"

# ==============================================================================
# Data Quality Schemas (Upgrade 2)
# ==============================================================================
class DataQualitySummary(BaseModel):
    status: str
    last_run_id: str | None = None
    created_at: str | None = None
    total_records: int = 0
    accepted_records: int = 0
    rejected_records: int = 0
    warning_count: int = 0
    rejection_breakdown: dict[str, int] = Field(default_factory=dict)
    warning_breakdown: dict[str, int] = Field(default_factory=dict)
    report_markdown_path: str | None = None
    disclaimer: str = "SYNTHETIC_DATA_GOVERNANCE_METRICS"
