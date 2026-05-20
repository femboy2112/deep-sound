from __future__ import annotations

from pathlib import Path

import numpy as np
import soundfile as sf

from deep_sound.domain.confidence import Confidence
from deep_sound.domain.feature_view import FeatureType, FeatureView, OwnerType
from deep_sound.domain.track import Track
from deep_sound.infra.storage.sqlite_store import SectionRecord, SqliteStore
from deep_sound.services.feature_service import FeatureService
from deep_sound.services.index_service import IndexService
from deep_sound.services.library_analysis_service import LibraryAnalysisService
from deep_sound.services.library_service import LibraryService
from deep_sound.services.similarity_service import SimilarityService


class _FastAnalysisService:
    def __init__(self, store: SqliteStore) -> None:
        self._store = store

    def analyze(self, track: Track) -> list[FeatureView]:
        views = [
            _view(track.id, FeatureType.RHYTHM_GLOBAL, 1.0),
            _view(track.id, FeatureType.HARMONY_CHROMA, 0.7),
            _view(track.id, FeatureType.TIMBRE_MFCC_STATS, 0.5),
        ]
        for view in views:
            self._store.replace_feature_view_for_owner(view)
        return views

    def analyze_production_texture(self, track: Track) -> FeatureView:
        view = _view(track.id, FeatureType.PRODUCTION_TEXTURE, 0.4)
        self._store.replace_feature_view_for_owner(view)
        return view

    def structure_feature_view(self, track: Track) -> FeatureView:
        self._store.add_section(
            SectionRecord(
                id=f"{track.id}:section",
                track_id=track.id,
                start_sec=0.0,
                end_sec=max(track.duration_sec or 1.0, 1.0),
                label="full",
                confidence=Confidence(0.8),
            )
        )
        view = _view(track.id, FeatureType.STRUCTURE_SECTION_SEQUENCE, 0.3)
        self._store.replace_feature_view_for_owner(view)
        return view


def test_100_track_synthetic_library_smoke_with_partial_failure(tmp_path: Path) -> None:
    library_dir = tmp_path / "library"
    library_dir.mkdir()
    for index in range(100):
        _write_tone(library_dir / f"track_{index:03d}.wav", frequency=220.0 + index)
    (library_dir / "broken.wav").write_bytes(b"not an audio file")
    store = SqliteStore(tmp_path / "library.sqlite")
    store.init_schema()

    imported = LibraryService(store).import_folder(library_dir)
    summary = LibraryAnalysisService(
        store,
        analysis_service=_FastAnalysisService(store),  # type: ignore[arg-type]
    ).analyze_library(imported, profile="searchable")
    features = FeatureService(store)
    index = IndexService(store, index_root=tmp_path / "indices", features=features)
    index_statuses = index.build_profile("searchable")
    results = SimilarityService(features, index_service=index).search_mode(
        imported[0].id,
        mode="rhythm",
        top_k=5,
    )

    assert len(imported) == 100
    assert len(store.list_jobs(status="failed")) == 1
    assert summary.completed_count == 100
    assert summary.failed_count == 0
    assert all(status.feature_count == 100 for status in index_statuses)
    assert len(results) == 5
    assert all(result.search_backend == "index" for result in results)


def _view(owner_id: str, feature_type: FeatureType, value: float) -> FeatureView:
    return FeatureView(
        id=f"{owner_id}:{feature_type.value}",
        owner_type=OwnerType.TRACK,
        owner_id=owner_id,
        feature_type=feature_type,
        algorithm="fast-smoke",
        algorithm_version="1",
        params_hash="params",
        stats={"x": value, "y": 1.0 - value},
        confidence=Confidence(0.8),
    )


def _write_tone(path: Path, *, frequency: float) -> None:
    sample_rate = 8000
    duration_sec = 0.05
    t = np.linspace(0.0, duration_sec, int(sample_rate * duration_sec), endpoint=False)
    audio = (0.1 * np.sin(2 * np.pi * frequency * t)).astype(np.float32)
    sf.write(path, audio, sample_rate)
