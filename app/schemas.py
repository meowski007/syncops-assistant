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
