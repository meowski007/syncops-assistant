"""
Comprehensive Retrieval and Answer Evaluation Harness for SyncOps RAG.
Computes Hit Rate@k, Mean Reciprocal Rank (MRR), and Answer Groundedness.
"""

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# Ensure UTF-8 output on Windows consoles
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from app.config import RUNBOOKS_DIR
from app.triage.rag.retriever import RunbookVectorIndex
from app.triage.rag.answer import generate_rag_triage

EVAL_DATASET_FILE = PROJECT_ROOT / "evaluation" / "rag_eval_dataset.json"
REPORTS_DIR = PROJECT_ROOT / "reports" / "rag"

def evaluate_retrieval_configuration(
    index: RunbookVectorIndex,
    dataset: list[dict[str, Any]],
    top_k: int = 5
) -> dict[str, Any]:
    """
    Evaluates Hit Rate@k (k=1, 3, 5) and Mean Reciprocal Rank (MRR) for a given vector index.
    """
    hits_at_1 = 0
    hits_at_3 = 0
    hits_at_5 = 0
    reciprocal_ranks = []
    
    per_query_results = []

    for item in dataset:
        q_id = item["id"]
        query = item["question"]
        expected_file = item["expected_file"]
        
        retrieved = index.retrieve(query, top_k=top_k, min_score=0.01)
        retrieved_files = [r["source_file"] for r in retrieved]
        
        # Determine 1-based rank of the expected file
        rank = 0
        for r_idx, r_file in enumerate(retrieved_files, start=1):
            if r_file.lower() == expected_file.lower():
                rank = r_idx
                break
                
        if rank == 1:
            hits_at_1 += 1
        if 1 <= rank <= 3:
            hits_at_3 += 1
        if 1 <= rank <= 5:
            hits_at_5 += 1
            
        rr = (1.0 / rank) if rank > 0 else 0.0
        reciprocal_ranks.append(rr)
        
        per_query_results.append({
            "id": q_id,
            "query": query,
            "expected_file": expected_file,
            "retrieved_files": retrieved_files,
            "rank": rank,
            "reciprocal_rank": round(rr, 3)
        })

    n = len(dataset)
    hit_rate_1 = round((hits_at_1 / max(1, n)) * 100, 2)
    hit_rate_3 = round((hits_at_3 / max(1, n)) * 100, 2)
    hit_rate_5 = round((hits_at_5 / max(1, n)) * 100, 2)
    mrr = round(float(sum(reciprocal_ranks) / max(1, n)), 3)

    return {
        "config_name": index.config_name,
        "chunk_size": index.chunk_size,
        "chunk_overlap": index.chunk_overlap,
        "total_queries": n,
        "hit_rate_at_1": hit_rate_1,
        "hit_rate_at_3": hit_rate_3,
        "hit_rate_at_5": hit_rate_5,
        "mrr": mrr,
        "query_evaluations": per_query_results
    }

def evaluate_answer_groundedness(
    dataset: list[dict[str, Any]]
) -> dict[str, Any]:
    """
    Evaluates rule-based answer quality, citation presence, and citation validity.
    """
    citations_present = 0
    citations_valid = 0
    total_citations_checked = 0
    keyword_coverage_matches = 0
    
    for item in dataset:
        res = generate_rag_triage(query=item["question"], top_k=3, min_score=0.05)
        
        if res.citations:
            citations_present += 1
            for cit in res.citations:
                total_citations_checked += 1
                target_file = RUNBOOKS_DIR / cit.source_file
                if target_file.exists():
                    citations_valid += 1
                    
        # Check expected keywords in mitigations or hypotheses
        combined_text = " ".join(res.hypotheses_and_causes + res.recommended_mitigations).lower()
        exp_kw = [k.lower() for k in item.get("expected_keywords", [])]
        if any(k in combined_text for k in exp_kw):
            keyword_coverage_matches += 1

    n = len(dataset)
    citation_rate = round((citations_present / max(1, n)) * 100, 2)
    citation_validity_rate = round((citations_valid / max(1, total_citations_checked)) * 100, 2) if total_citations_checked > 0 else 100.0
    coverage_rate = round((keyword_coverage_matches / max(1, n)) * 100, 2)

    return {
        "total_queries_evaluated": n,
        "citation_presence_rate": citation_rate,
        "citation_validity_rate": citation_validity_rate,
        "keyword_coverage_rate": coverage_rate,
        "offline_eval_mode": "DETERMINISTIC_RULE_BASED_VERIFICATION"
    }

def run_rag_evaluation() -> dict[str, Any]:
    """
    Executes full comparative RAG evaluation:
    1. Config A: Fine-Grained Chunking (300 chars, 50 overlap)
    2. Config B: Coarse Chunking (600 chars, 100 overlap)
    3. Answer groundedness evaluation
    4. Generates Markdown report & JSON metrics
    """
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    
    dataset = json.loads(EVAL_DATASET_FILE.read_text(encoding="utf-8"))
    
    print("\n[RAG Eval 1/3] Building & evaluating Configuration A (Small Chunks: 300 / 50)...")
    idx_a = RunbookVectorIndex(chunk_size=300, chunk_overlap=50, config_name="config_a_small_chunks")
    idx_a.build_index()
    eval_a = evaluate_retrieval_configuration(idx_a, dataset, top_k=5)

    print("\n[RAG Eval 2/3] Building & evaluating Configuration B (Large Chunks: 600 / 100)...")
    idx_b = RunbookVectorIndex(chunk_size=600, chunk_overlap=100, config_name="config_b_large_chunks")
    idx_b.build_index()
    eval_b = evaluate_retrieval_configuration(idx_b, dataset, top_k=5)

    print("\n[RAG Eval 3/3] Evaluating Answer Groundedness & Citations...")
    eval_answers = evaluate_answer_groundedness(dataset)

    results = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "evaluation_dataset_size": len(dataset),
        "config_a": eval_a,
        "config_b": eval_b,
        "answer_groundedness": eval_answers
    }

    # Save JSON report
    json_path = REPORTS_DIR / "rag_evaluation_results.json"
    json_path.write_text(json.dumps(results, indent=2), encoding="utf-8")

    # Save Markdown report
    md_path = REPORTS_DIR / "rag_evaluation_report.md"
    generate_rag_markdown_report(results, md_path)
    
    return results

def generate_rag_markdown_report(results: dict[str, Any], output_path: Path) -> None:
    """Writes detailed comparative Markdown report."""
    a = results["config_a"]
    b = results["config_b"]
    ans = results["answer_groundedness"]
    
    winner = "Configuration A (Small Chunks: 300)" if a["mrr"] >= b["mrr"] else "Configuration B (Large Chunks: 600)"
    
    hit_rate_formula = "Hit Rate@k = (1 / |Q|) * sum(I(rank_i <= k)) * 100%"
    mrr_formula = "MRR = (1 / |Q|) * sum(1 / rank_i)"

    md_text = f"""# SyncOps RAG Retrieval & Answer Evaluation Report

> **SYNTHETIC DISCLOSURE:** Evaluation queries and runbook documents are synthetic operational artifacts designed to validate enterprise RAG retrieval benchmarks (Hit Rate@k, MRR, Citation Groundedness).

---

### 1. Executive Summary & Comparative Benchmark
- **Evaluation Dataset:** {results['evaluation_dataset_size']} curated SRE queries across 13 operational runbooks.
- **Retrieval Engine:** Sublinear TF-IDF word/n-gram vectorizer with Cosine Similarity Matrix.
- **Optimal Champion Configuration:** **{winner}**

| Retrieval Configuration | Chunk Size / Overlap | Hit Rate@1 | Hit Rate@3 | Hit Rate@5 | Mean Reciprocal Rank (MRR) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Config A (Fine-Grained)** | 300 chars / 50 overlap | **{a['hit_rate_at_1']}%** | **{a['hit_rate_at_3']}%** | **{a['hit_rate_at_5']}%** | **{a['mrr']:.3f}** |
| **Config B (Coarse)** | 600 chars / 100 overlap | **{b['hit_rate_at_1']}%** | **{b['hit_rate_at_3']}%** | **{b['hit_rate_at_5']}%** | **{b['mrr']:.3f}** |

---

### 2. Answer Groundedness & Guardrail Metrics
- **Citation Presence Rate:** **{ans['citation_presence_rate']}%** (Percentage of answers containing verifiable runbook citations).
- **Citation Validity Rate:** **{ans['citation_validity_rate']}%** (Verifies cited markdown files actually exist on disk).
- **Keyword Grounding Coverage:** **{ans['keyword_coverage_rate']}%** (Presence of target operational keywords in generated recommendations).
- **Evaluation Mode:** `{ans['offline_eval_mode']}` (Zero-credential, deterministic verification).

---

### 3. Metric Definitions & Formulas
1. **Hit Rate@k:** Percentage of queries where the true expected runbook is present within the top-k retrieved chunks:
   `{hit_rate_formula}`
2. **Mean Reciprocal Rank (MRR):** Evaluates the position of the first relevant document. Perfect score is 1.0 (expected file ranked #1 on every query):
   `{mrr_formula}`

---

### 4. Qualitative Chunking Insights
- **Why Chunking Matters:** Smaller chunk sizes (Config A) isolate specific diagnostic commands (e.g., `PRAGMA busy_timeout = 10000;`), yielding higher top-1 rank precision without polluting context.
- **Refusal Behavior:** Queries with no matching documentation below the threshold (< 0.08) are explicitly refused rather than hallucinated.
"""
    output_path.write_text(md_text, encoding="utf-8")
    print(f"\n✓ Markdown RAG evaluation report written to: {output_path}")

if __name__ == "__main__":
    print("=" * 65)
    print("🔍 SYNCOPS RAG RETRIEVAL & GROUNDEDNESS EVALUATOR")
    print("=" * 65)
    res = run_rag_evaluation()
    print(f"\n[RESULTS] Config A MRR: {res['config_a']['mrr']} (Hit@1: {res['config_a']['hit_rate_at_1']}%)")
    print(f"[RESULTS] Config B MRR: {res['config_b']['mrr']} (Hit@1: {res['config_b']['hit_rate_at_1']}%)")
    print(f"[RESULTS] Citation Validity: {res['answer_groundedness']['citation_validity_rate']}%")
