"""FAISS-backed vector index. Spec §14.3, §17.1. Phase 1 target (P1-005)."""

from __future__ import annotations

from pathlib import Path


class FaissIndex:
    """Approximate vector search index with manifest mapping row → entity.

    Stub — requires `pip install deep-sound[index]` (faiss-cpu). Implemented
    in P1-005.
    """

    def __init__(self, index_path: Path, manifest_path: Path, dim: int) -> None:
        self.index_path = index_path
        self.manifest_path = manifest_path
        self.dim = dim

    def add(self, entity_id: str, vector: list[float]) -> None:
        raise NotImplementedError("FaissIndex.add pending P1-005")

    def query(self, vector: list[float], k: int = 10) -> list[tuple[str, float]]:
        raise NotImplementedError("FaissIndex.query pending P1-005")
