"""Vector index with optional FAISS acceleration. Spec §14.3, §17.1."""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

import numpy as np
import numpy.typing as npt

try:  # pragma: no cover - exercised only when the optional index extra is installed.
    import faiss
except ImportError:  # pragma: no cover - default test environment path.
    faiss = None

INDEX_VERSION = "faiss-index-v1"


class FaissIndex:
    """Cosine-similarity vector index with row-to-entity manifest persistence.

    If `faiss-cpu` is importable, vectors are stored in an `IndexFlatIP`.
    Otherwise the same normalized vectors are persisted as a NumPy archive at
    `index_path`; query semantics stay the same for mainline installs.
    """

    def __init__(self, index_path: Path, manifest_path: Path, dim: int) -> None:
        self.index_path = index_path
        self.manifest_path = manifest_path
        self.dim = dim
        self._entity_ids: list[str] = []
        self._vectors = np.empty((0, dim), dtype=np.float32)
        self._faiss_index: Any | None = None
        if faiss is not None:
            self._faiss_index = faiss.IndexFlatIP(dim)
        self._load_if_present()

    def add(self, entity_id: str, vector: list[float]) -> None:
        if not entity_id:
            raise ValueError("entity_id must not be empty")
        if entity_id in self._entity_ids:
            raise ValueError(f"entity_id already indexed: {entity_id}")
        normalized = _normalize_vector(vector, self.dim)

        self._entity_ids.append(entity_id)
        self._vectors = np.vstack([self._vectors, normalized])
        if self._faiss_index is not None:
            self._faiss_index.add(normalized.reshape(1, self.dim))
        self.save()

    def query(self, vector: list[float], k: int = 10) -> list[tuple[str, float]]:
        if k <= 0 or not self._entity_ids:
            return []
        normalized = _normalize_vector(vector, self.dim)
        limit = min(k, len(self._entity_ids))

        if self._faiss_index is not None:
            scores, rows = self._faiss_index.search(normalized.reshape(1, self.dim), limit)
            return [
                (self._entity_ids[int(row)], _clamp_score(float(score)))
                for row, score in zip(rows[0], scores[0], strict=True)
                if int(row) >= 0
            ]

        scores = self._vectors @ normalized
        ordered_rows = np.argsort(-scores, kind="stable")[:limit]
        return [
            (self._entity_ids[int(row)], _clamp_score(float(scores[int(row)])))
            for row in ordered_rows
        ]

    def save(self) -> None:
        self.index_path.parent.mkdir(parents=True, exist_ok=True)
        self.manifest_path.parent.mkdir(parents=True, exist_ok=True)
        if self._faiss_index is not None:
            faiss.write_index(self._faiss_index, str(self.index_path))
        else:
            with self.index_path.open("wb") as index_file:
                np.savez_compressed(index_file, vectors=self._vectors)
        self.manifest_path.write_text(
            json.dumps(
                {
                    "version": INDEX_VERSION,
                    "dim": self.dim,
                    "backend": "faiss" if self._faiss_index is not None else "numpy",
                    "rows": [
                        {"row": row, "entity_id": entity_id}
                        for row, entity_id in enumerate(self._entity_ids)
                    ],
                },
                indent=2,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )

    def _load_if_present(self) -> None:
        if not self.index_path.exists() or not self.manifest_path.exists():
            return
        manifest = json.loads(self.manifest_path.read_text(encoding="utf-8"))
        if int(manifest["dim"]) != self.dim:
            raise ValueError(
                f"Index dimension mismatch: manifest has {manifest['dim']}, expected {self.dim}"
            )
        rows = manifest.get("rows", [])
        if not isinstance(rows, list):
            raise ValueError("Index manifest rows must be a list")
        self._entity_ids = [_entity_id_from_row(row) for row in rows]

        if self._faiss_index is not None and manifest.get("backend") == "faiss":
            self._faiss_index = faiss.read_index(str(self.index_path))
            self._vectors = _reconstruct_vectors(self._faiss_index, len(self._entity_ids), self.dim)
            return

        with self.index_path.open("rb") as index_file:
            loaded = np.load(index_file)
            vectors = np.asarray(loaded["vectors"], dtype=np.float32)
        if vectors.shape != (len(self._entity_ids), self.dim):
            raise ValueError("Persisted index vector shape does not match manifest")
        self._vectors = vectors
        if self._faiss_index is not None:
            self._faiss_index.add(self._vectors)


def _normalize_vector(vector: list[float], dim: int) -> npt.NDArray[np.float32]:
    if len(vector) != dim:
        raise ValueError(f"Expected vector dimension {dim}, got {len(vector)}")
    values = np.asarray(vector, dtype=np.float32)
    if not np.all(np.isfinite(values)):
        raise ValueError("Vector values must be finite")
    norm = float(np.linalg.norm(values))
    if norm == 0.0:
        return values
    return values / norm


def _clamp_score(score: float) -> float:
    if not math.isfinite(score):
        return 0.0
    return max(0.0, min(1.0, score))


def _entity_id_from_row(row: object) -> str:
    if not isinstance(row, dict):
        raise ValueError("Index manifest row must be an object")
    entity_id = row.get("entity_id")
    if not isinstance(entity_id, str):
        raise ValueError("Index manifest entity_id must be a string")
    return entity_id


def _reconstruct_vectors(
    index: Any,
    count: int,
    dim: int,
) -> npt.NDArray[np.float32]:
    vectors = np.empty((count, dim), dtype=np.float32)
    for row in range(count):
        vectors[row] = np.asarray(index.reconstruct(row), dtype=np.float32)
    return vectors
