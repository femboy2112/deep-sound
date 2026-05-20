from __future__ import annotations

import json
from pathlib import Path

import pytest

from deep_sound.infra.index.faiss_index import FaissIndex


def test_faiss_index_normalizes_queries_and_persists_manifest(tmp_path: Path) -> None:
    index_path = tmp_path / "rhythm.index"
    manifest_path = tmp_path / "rhythm.json"
    index = FaissIndex(index_path=index_path, manifest_path=manifest_path, dim=2)

    index.add("track-a", [10.0, 0.0])
    index.add("track-b", [0.0, 2.0])

    assert index.query([3.0, 0.0], k=2) == [("track-a", pytest.approx(1.0)), ("track-b", 0.0)]
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest["dim"] == 2
    assert manifest["rows"] == [
        {"row": 0, "entity_id": "track-a"},
        {"row": 1, "entity_id": "track-b"},
    ]

    reloaded = FaissIndex(index_path=index_path, manifest_path=manifest_path, dim=2)
    assert reloaded.query([0.0, 5.0], k=1) == [("track-b", pytest.approx(1.0))]


def test_faiss_index_rejects_bad_vectors_and_duplicate_entities(tmp_path: Path) -> None:
    index = FaissIndex(
        index_path=tmp_path / "timbre.index",
        manifest_path=tmp_path / "timbre.json",
        dim=2,
    )
    index.add("track-a", [1.0, 0.0])

    with pytest.raises(ValueError, match="already indexed"):
        index.add("track-a", [0.0, 1.0])
    with pytest.raises(ValueError, match="Expected vector dimension"):
        index.add("track-b", [1.0])
