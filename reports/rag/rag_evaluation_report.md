# SyncOps RAG Retrieval & Answer Evaluation Report

> **SYNTHETIC DISCLOSURE:** Evaluation queries and runbook documents are synthetic operational artifacts designed to validate enterprise RAG retrieval benchmarks (Hit Rate@k, MRR, Citation Groundedness).

---

### 1. Executive Summary & Comparative Benchmark
- **Evaluation Dataset:** 25 curated SRE queries across 13 operational runbooks.
- **Retrieval Engine:** Sublinear TF-IDF word/n-gram vectorizer with Cosine Similarity Matrix.
- **Optimal Champion Configuration:** **Configuration B (Large Chunks: 600)**

| Retrieval Configuration | Chunk Size / Overlap | Hit Rate@1 | Hit Rate@3 | Hit Rate@5 | Mean Reciprocal Rank (MRR) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Config A (Fine-Grained)** | 300 chars / 50 overlap | **80.0%** | **88.0%** | **96.0%** | **0.858** |
| **Config B (Coarse)** | 600 chars / 100 overlap | **84.0%** | **88.0%** | **96.0%** | **0.880** |

---

### 2. Answer Groundedness & Guardrail Metrics
- **Citation Presence Rate:** **100.0%** (Percentage of answers containing verifiable runbook citations).
- **Citation Validity Rate:** **100.0%** (Verifies cited markdown files actually exist on disk).
- **Keyword Grounding Coverage:** **68.0%** (Presence of target operational keywords in generated recommendations).
- **Evaluation Mode:** `DETERMINISTIC_RULE_BASED_VERIFICATION` (Zero-credential, deterministic verification).

---

### 3. Metric Definitions & Formulas
1. **Hit Rate@k:** Percentage of queries where the true expected runbook is present within the top-k retrieved chunks:
   `Hit Rate@k = (1 / |Q|) * sum(I(rank_i <= k)) * 100%`
2. **Mean Reciprocal Rank (MRR):** Evaluates the position of the first relevant document. Perfect score is 1.0 (expected file ranked #1 on every query):
   `MRR = (1 / |Q|) * sum(1 / rank_i)`

---

### 4. Qualitative Chunking Insights
- **Why Chunking Matters:** Smaller chunk sizes (Config A) isolate specific diagnostic commands (e.g., `PRAGMA busy_timeout = 10000;`), yielding higher top-1 rank precision without polluting context.
- **Refusal Behavior:** Queries with no matching documentation below the threshold (< 0.08) are explicitly refused rather than hallucinated.
