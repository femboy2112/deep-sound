"""SimilarityService — spec §10.2, §14, §16.5. Phase 0 cosine, Phase 1 FAISS."""

from __future__ import annotations


class SimilarityService:
    """Candidate retrieval + reranking + weighted combined scoring.

    Stub — Phase 0 implementation (cosine over numpy) lands in P0-017.
    """

    def search(
        self, query_id: str, weights: dict[str, float], top_k: int = 10
    ) -> list[tuple[str, float]]:
        raise NotImplementedError("SimilarityService.search pending P0-017")
