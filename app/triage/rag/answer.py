"""RAG Incident Triage & Answer Guardrail Engine."""

from pathlib import Path
from typing import Any
from pydantic import BaseModel, Field

from app.database import get_db, get_db_path
from app.incidents import get_incident_by_id
from app.triage.rag.retriever import get_runbook_index
from app.logging_config import logger

class RagCitation(BaseModel):
    source_file: str = Field(..., description="Markdown runbook filename")
    section_heading: str = Field(..., description="Section title within the runbook")
    relevance_score: float = Field(..., description="Cosine similarity score (0.0 to 1.0)")
    chunk_id: str

class RagTriageResult(BaseModel):
    incident_id: str
    query: str
    summary: str
    empirical_facts: list[str] = Field(default_factory=list, description="Verified facts from database telemetry")
    hypotheses_and_causes: list[str] = Field(default_factory=list, description="Diagnosed failure mechanisms")
    recommended_mitigations: list[str] = Field(default_factory=list, description="Operational actions grounded in runbooks")
    citations: list[RagCitation] = Field(default_factory=list, description="Direct citations to operational runbooks")
    confidence: float = Field(..., ge=0.0, le=1.0)
    refusal: bool = Field(default=False, description="True if evidence is insufficient to answer safely")
    refusal_reason: str | None = None
    requires_human_review: bool = True
    advisory_notice: str = "AI recommendations are advisory only. SRE human review is required before modifying production systems."
    disclaimer: str = "All telemetry and operational runbooks are synthetic for educational evaluation."

def generate_rag_triage(
    incident_id: str | None = None,
    query: str | None = None,
    min_score: float = 0.08,
    top_k: int = 3,
    db_path: Path | str | None = None
) -> RagTriageResult:
    """
    Executes grounded RAG investigation combining structured database facts
    with vector-retrieved operational runbook evidence.
    """
    effective_query = query or ""
    empirical_facts: list[str] = []
    inc_data: dict[str, Any] | None = None
    
    # 1. Query structured telemetry if incident_id is supplied
    if incident_id:
        target_db = Path(db_path) if db_path else get_db_path()
        try:
            with get_db(target_db) as conn:
                inc_data = get_incident_by_id(conn, incident_id)
        except Exception as e:
            logger.warning(f"Failed to query incident {incident_id}: {e}")

        if inc_data:
            empirical_facts.append(
                f"Incident '{incident_id}': Severity {inc_data['severity']}, Status {inc_data['status']}, Cohort '{inc_data['affected_cohort']}'."
            )
            cohort_stats = inc_data.get("cohort_telemetry", {})
            if cohort_stats:
                fails = cohort_stats.get("failure_events_sampled", 0)
                total = cohort_stats.get("total_events_sampled", 0)
                lat = cohort_stats.get("avg_latency_ms", 0.0)
                fail_pct = round((fails / max(1, total)) * 100, 1)
                empirical_facts.append(
                    f"Cohort telemetry: {fails}/{total} failures sampled ({fail_pct}% failure rate, avg latency {lat}ms)."
                )
            if inc_data.get("root_cause_summary"):
                empirical_facts.append(f"Recorded root cause telemetry: {inc_data['root_cause_summary']}")

            if not effective_query:
                effective_query = f"{inc_data['title']} {inc_data['failure_category']} {inc_data['affected_cohort']}"

    # 2. Vector Retrieval across Runbook Index
    index = get_runbook_index()
    retrieved_chunks = index.retrieve(effective_query, top_k=top_k, min_score=min_score)

    # 3. Guardrail Check: Insufficient Evidence Refusal
    if not retrieved_chunks:
        return RagTriageResult(
            incident_id=incident_id or "GENERAL_INQUIRY",
            query=effective_query,
            summary="Refusal: Insufficient verified operational runbook evidence.",
            empirical_facts=empirical_facts,
            hypotheses_and_causes=[],
            recommended_mitigations=[],
            citations=[],
            confidence=0.0,
            refusal=True,
            refusal_reason=(
                f"No runbook documentation met the minimum relevance threshold ({min_score}) "
                f"for query: '{effective_query}'. Refusing to hypothesize without verified operational procedures."
            )
        )

    # 4. Compile Citations & Grounded Mitigations
    citations = [
        RagCitation(
            source_file=c["source_file"],
            section_heading=c["section_heading"],
            relevance_score=c["score"],
            chunk_id=c["chunk_id"]
        )
        for c in retrieved_chunks
    ]

    top_chunk = retrieved_chunks[0]
    hypotheses = [
        f"Grounded in '{top_chunk['source_file']}': Failure characteristics align with {top_chunk['section_heading']}."
    ]
    
    # Extract mitigation actions from chunks
    mitigations = []
    for c in retrieved_chunks:
        if "Mitigation" in c["section_heading"] or "Action" in c["section_heading"] or "Step" in c["section_heading"]:
            # Extract bullet lines
            for line in c["content"].splitlines():
                stripped = line.strip()
                if stripped.startswith("-") or stripped.startswith("•") or (len(stripped) > 2 and stripped[0].isdigit() and stripped[1] in (".", ")")):
                    mitigations.append(f"[{c['source_file']}] {stripped}")

    if not mitigations:
        mitigations.append(f"Refer to {top_chunk['source_file']} section '{top_chunk['section_heading']}' for verified SOP.")

    summary = (
        f"RAG investigation grounded in {len(citations)} operational runbook chunks. "
        f"Primary procedure: {top_chunk['source_file']} ({top_chunk['section_heading']})."
    )
    confidence = min(0.96, max(0.50, top_chunk["score"] * 1.5))

    return RagTriageResult(
        incident_id=incident_id or "GENERAL_INQUIRY",
        query=effective_query,
        summary=summary,
        empirical_facts=empirical_facts,
        hypotheses_and_causes=hypotheses,
        recommended_mitigations=mitigations[:5],
        citations=citations,
        confidence=round(confidence, 2),
        refusal=False
    )
