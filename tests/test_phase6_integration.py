from __future__ import annotations

from pathlib import Path

import numpy as np
import soundfile as sf

from deep_sound.domain.feature_view import FeatureType
from deep_sound.infra.storage.sqlite_store import SqliteStore
from deep_sound.services.analysis_service import AnalysisService
from deep_sound.services.feature_service import FeatureService
from deep_sound.services.index_service import IndexService
from deep_sound.services.library_service import LibraryService
from deep_sound.services.similarity_service import SearchMode, SimilarityService


def test_import_analyze_index_search_over_sqlite_library(tmp_path: Path) -> None:
    first = _write_tone(tmp_path / "first.wav", 220.0)
    second = _write_tone(tmp_path / "second.wav", 224.0)
    store = SqliteStore(tmp_path / "library.sqlite")
    store.init_schema()
    library = LibraryService(store)
    tracks = [library.import_file(first), library.import_file(second)]
    analysis = AnalysisService(store)
    for track in tracks:
        analysis.analyze(track)
    features = FeatureService(store)
    index = IndexService(store, index_root=tmp_path / "indices", features=features)
    index.build_index(FeatureType.RHYTHM_GLOBAL)
    service = SimilarityService(features, index_service=index)

    results = service.search_mode(tracks[0].id, SearchMode.RHYTHM)

    assert results
    assert results[0].owner_id == tracks[1].id
    assert results[0].search_backend == "index"
    assert 0.0 <= results[0].score <= 1.0


def test_missing_index_falls_back_with_metadata(tmp_path: Path) -> None:
    first = _write_tone(tmp_path / "first.wav", 220.0)
    second = _write_tone(tmp_path / "second.wav", 224.0)
    store = SqliteStore(tmp_path / "library.sqlite")
    store.init_schema()
    library = LibraryService(store)
    tracks = [library.import_file(first), library.import_file(second)]
    analysis = AnalysisService(store)
    for track in tracks:
        analysis.analyze(track)
    features = FeatureService(store)
    service = SimilarityService(
        features,
        index_service=IndexService(store, index_root=tmp_path / "missing", features=features),
    )

    results = service.search_mode(tracks[0].id, SearchMode.RHYTHM)

    assert results[0].search_backend == "scan"
    assert results[0].retrieval_caveats


def _write_tone(path: Path, frequency: float, sample_rate: int = 22050) -> Path:
    duration_sec = 1.0
    t = np.linspace(0.0, duration_sec, int(sample_rate * duration_sec), endpoint=False)
    audio = (0.1 * np.sin(2.0 * np.pi * frequency * t)).astype(np.float32)
    sf.write(path, audio, sample_rate)
    return path
