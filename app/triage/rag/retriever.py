"""Vector retrieval and semantic similarity matching for SyncOps RAG system."""

import pickle
from pathlib import Path
from typing import Any
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from app.config import RUNBOOKS_DIR
from app.triage.rag.chunker import chunk_runbook_corpus, DocumentChunk
from app.logging_config import logger

INDEX_CACHE_DIR = Path(__file__).resolve().parent.parent.parent.parent / "data"

class RunbookVectorIndex:
    """
    Local Vector Index using TF-IDF sublinear word and n-gram embeddings with cosine similarity.
    
    DESIGN RATIONALE:
    1. 100% Offline & Reproducible: Requires zero external model downloads or API credentials.
    2. Precision on Technical SRE Terminology: Accurately matches error tokens (e.g., 'AUTH_EXPIRED', 'PAYLOAD_TIMEOUT', '429', 'BLE').
    3. Low Latency: Sub-millisecond vector similarity calculations across the chunk corpus.
    """
    def __init__(
        self,
        chunk_size: int = 350,
        chunk_overlap: int = 60,
        config_name: str = "default"
    ):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.config_name = config_name
        
        self.chunks: list[DocumentChunk] = []
        self.vectorizer: TfidfVectorizer | None = None
        self.matrix: Any = None
        self.is_indexed: bool = False

    def build_index(self, runbooks_dir: Path | None = None) -> "RunbookVectorIndex":
        """Chunks all markdown runbooks and fits the TF-IDF vector matrix."""
        target_dir = runbooks_dir or RUNBOOKS_DIR
        self.chunks = chunk_runbook_corpus(
            target_dir,
            chunk_size=self.chunk_size,
            chunk_overlap=self.chunk_overlap
        )
        if not self.chunks:
            logger.warning(f"No runbook chunks found in {target_dir}")
            return self

        corpus = [c.content for c in self.chunks]
        self.vectorizer = TfidfVectorizer(
            ngram_range=(1, 2),
            sublinear_tf=True,
            stop_words="english"
        )
        self.matrix = self.vectorizer.fit_transform(corpus)
        self.is_indexed = True
        logger.info(
            f"RAG Index built ({self.config_name}): {len(self.chunks)} chunks indexed from {target_dir}"
        )
        return self

    def save(self, cache_dir: Path | None = None) -> Path:
        """Serializes vectorizer, matrix, and chunk metadata to disk."""
        target_dir = cache_dir or INDEX_CACHE_DIR
        target_dir.mkdir(parents=True, exist_ok=True)
        file_path = target_dir / f"rag_index_{self.config_name}.pkl"
        with open(file_path, "wb") as f:
            pickle.dump({
                "chunks": [c.to_dict() for c in self.chunks],
                "vectorizer": self.vectorizer,
                "matrix": self.matrix,
                "chunk_size": self.chunk_size,
                "chunk_overlap": self.chunk_overlap,
                "config_name": self.config_name
            }, f)
        return file_path

    @classmethod
    def load(cls, file_path: Path) -> "RunbookVectorIndex":
        """Deserializes vector index from disk."""
        with open(file_path, "rb") as f:
            data = pickle.load(f)
        idx = cls(
            chunk_size=data["chunk_size"],
            chunk_overlap=data["chunk_overlap"],
            config_name=data["config_name"]
        )
        idx.chunks = [DocumentChunk(**c) for c in data["chunks"]]
        idx.vectorizer = data["vectorizer"]
        idx.matrix = data["matrix"]
        idx.is_indexed = True
        return idx

    def retrieve(
        self,
        query: str,
        top_k: int = 3,
        min_score: float = 0.08
    ) -> list[dict[str, Any]]:
        """
        Retrieves the top-k most relevant chunks using cosine similarity.
        Enforces a minimum relevance threshold; queries below threshold return empty results
        to trigger explicit refusal rather than hallucinated answers.
        """
        if not self.is_indexed or self.vectorizer is None or self.matrix is None:
            self.build_index()

        if not self.chunks:
            return []

        query_vec = self.vectorizer.transform([query])
        similarities = cosine_similarity(query_vec, self.matrix).flatten()
        
        # Rank by descending similarity
        top_indices = np.argsort(similarities)[::-1]
        
        results = []
        for rank, idx in enumerate(top_indices[:top_k], start=1):
            score = float(similarities[idx])
            chunk = self.chunks[idx]
            
            # Record item if it meets minimum score threshold
            if score >= min_score:
                results.append({
                    "rank": rank,
                    "score": round(score, 4),
                    "chunk_id": chunk.chunk_id,
                    "source_file": chunk.source_file,
                    "section_heading": chunk.section_heading,
                    "content": chunk.content,
                })

        return results

# Singleton index instances
_default_index: RunbookVectorIndex | None = None

def get_runbook_index(force_rebuild: bool = False) -> RunbookVectorIndex:
    """Returns the default initialized vector index."""
    global _default_index
    if _default_index is None or force_rebuild:
        _default_index = RunbookVectorIndex(chunk_size=350, chunk_overlap=60, config_name="default")
        _default_index.build_index()
    return _default_index
