"""
Cross-encoder reranker service.

Dense retrieval (FAISS) optimizes for recall — it casts a wide net.
A cross-encoder reranker then reads (query, chunk) as a pair and scores
true semantic relevance. This is the single biggest precision win you
can add to a RAG pipeline.

Model: BAAI/bge-reranker-base (~280MB, CPU-friendly, ~100ms for 20 pairs).

Design notes:
- Lazy-loaded singleton so startup stays fast.
- If the model fails to load (offline env, missing deps), we degrade
  gracefully: we keep the original FAISS order and log a warning.
  RAG keeps working; it's just less precise.
"""

import logging
from typing import Iterable

import torch

logger = logging.getLogger(__name__)

_DEVICE = "cuda" if torch.cuda.is_available() else "cpu"


class Reranker:
    """Cross-encoder reranker with lazy init and safe fallback."""

    _instance: "Reranker | None" = None
    _model = None
    _load_failed = False

    DEFAULT_MODEL = "BAAI/bge-reranker-base"

    @classmethod
    def get(cls) -> "Reranker":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def _load(self):
        """Load the cross-encoder on first use. Cache failure so we don't retry every call."""
        if self._model is not None or self._load_failed:
            return
        try:
            from sentence_transformers import CrossEncoder
            logger.info(f"Loading reranker model: {self.DEFAULT_MODEL}")
            self._model = CrossEncoder(self.DEFAULT_MODEL, device=_DEVICE, max_length=512)
            logger.info(f"Reranker running on: {_DEVICE}")
            logger.info("Reranker loaded.")
        except Exception as e:
            self._load_failed = True
            logger.warning(
                f"Reranker unavailable ({e}). Falling back to FAISS-only ordering."
            )

    def rerank(
        self,
        query: str,
        candidates: list[dict],
        top_k: int = 5,
    ) -> list[dict]:
        """
        Rerank FAISS candidates by cross-encoder relevance.

        Args:
            query: the user's question (already rewritten if applicable)
            candidates: list of {"content", "metadata", "score"} from FAISS
            top_k: how many to keep after reranking

        Returns:
            Same dict shape, but sorted by rerank_score (descending) and
            with a new "rerank_score" key added. If the reranker is
            unavailable, returns the first top_k of the input unchanged.
        """
        if not candidates:
            return []

        self._load()
        if self._model is None:
            # Graceful fallback: keep FAISS order
            return candidates[:top_k]

        try:
            pairs = [(query, c["content"]) for c in candidates]
            scores = self._model.predict(pairs, show_progress_bar=False)
            for c, s in zip(candidates, scores):
                c["rerank_score"] = float(s)
            ranked = sorted(candidates, key=lambda x: x["rerank_score"], reverse=True)
            return ranked[:top_k]
        except Exception as e:
            logger.warning(f"Rerank failed, using FAISS order: {e}")
            return candidates[:top_k]

    @staticmethod
    def passes_threshold(
        ranked: Iterable[dict],
        min_rerank_score: float = 0.0,
    ) -> bool:
        """
        Decide if the best reranked result is strong enough to answer from.

        BGE reranker scores are roughly:
          > 2   strong match
          0–2   reasonable match
          < 0   irrelevant / unrelated

        Default threshold 0.0 is permissive; tighten to ~0.5 for stricter
        grounding on clean corpora.
        """
        ranked = list(ranked)
        if not ranked:
            return False
        top = ranked[0]
        # If reranker ran, use its score.
        if "rerank_score" in top:
            return top["rerank_score"] >= min_rerank_score
        # If reranker was skipped, fall back to FAISS L2 distance threshold.
        # With normalized embeddings, L2 of ~1.5 already means "unrelated".
        return top.get("score", 99.0) < 1.5