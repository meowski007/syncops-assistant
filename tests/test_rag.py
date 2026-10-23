"""Tests for RAG System: Section-aware chunking, vector retrieval, refusal guardrails, evaluation."""

import pytest
from pathlib import Path

from app.config import RUNBOOKS_DIR
from app.triage.rag.chunker import parse_markdown_sections, chunk_runbook_corpus
from app.triage.rag.retriever import RunbookVectorIndex
from app.triage.rag.answer import generate_rag_triage, RagTriageResult
from evaluation.rag_evaluator import evaluate_retrieval_configuration

def test_parse_markdown_sections():
    sample_md = """# Title
Some overview text.

## 1. Symptoms & Detection
Alert triggered on timeout.

## 2. Mitigation Steps
Scale workers by 100%.
"""
    sections = parse_markdown_sections(sample_md, "test.md")
    assert len(sections) == 3
    assert sections[0]["heading"] == "Title"
    assert sections[1]["heading"] == "1. Symptoms & Detection"
    assert "Scale workers" in sections[2]["content"]

def test_chunk_runbook_corpus():
    chunks = chunk_runbook_corpus(RUNBOOKS_DIR, chunk_size=300, chunk_overlap=50)
    assert len(chunks) > 10
    first = chunks[0]
    assert first.source_file.endswith(".md")
    assert first.section_heading != ""
    assert len(first.content) > 0

def test_vector_index_retrieval_and_ordering():
    index = RunbookVectorIndex(chunk_size=300, chunk_overlap=50, config_name="test")
    index.build_index(RUNBOOKS_DIR)
    
    # Query for authentication failure
    results = index.retrieve("OAuth token expired leaf certificate rotation", top_k=3)
    assert len(results) > 0
    top = results[0]
    assert "authentication_errors.md" in top["source_file"]
    assert top["score"] > 0.10
    # Results must be ordered by descending similarity score
    scores = [r["score"] for r in results]
    assert scores == sorted(scores, reverse=True)

def test_rag_low_relevance_refusal_guardrail():
    # Nonsense query should score below threshold and trigger refusal
    res = generate_rag_triage(query="completely unrelated query about baking chocolate croissants in space", min_score=0.25)
    assert isinstance(res, RagTriageResult)
    assert res.refusal is True
    assert "Refusal" in res.summary
    assert res.confidence == 0.0
    assert len(res.citations) == 0

def test_rag_triage_grounded_answer_with_citations():
    res = generate_rag_triage(
        query="Client retry storms causing HTTP 429 surges",
        min_score=0.05,
        top_k=3
    )
    assert isinstance(res, RagTriageResult)
    assert res.refusal is False
    assert len(res.citations) > 0
    assert "retry_storms.md" in [c.source_file for c in res.citations]
    assert res.confidence >= 0.50
    assert res.requires_human_review is True

def test_rag_evaluator_metrics_calculation():
    # Mock evaluation check
    dataset = [
        {"id": "T1", "question": "OAuth token certificate error", "expected_file": "authentication_errors.md"},
        {"id": "T2", "question": "BLE MTU chunk failure", "expected_file": "firmware_update_failures.md"}
    ]
    index = RunbookVectorIndex(chunk_size=300, chunk_overlap=50, config_name="test_eval")
    index.build_index(RUNBOOKS_DIR)
    
    eval_res = evaluate_retrieval_configuration(index, dataset, top_k=3)
    assert eval_res["hit_rate_at_1"] >= 50.0
    assert eval_res["hit_rate_at_3"] == 100.0
    assert eval_res["mrr"] >= 0.50
    assert eval_res["total_queries"] == 2
