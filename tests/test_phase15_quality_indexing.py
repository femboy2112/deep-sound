from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import numpy as np
import soundfile as sf

from deep_sound.domain.feature_view import FeatureType, OwnerType
from deep_sound.domain.track import Track
from deep_sound.infra.separation.providers import file_sha256
from deep_sound.infra.storage.sqlite_store import SqliteStore
from deep_sound.services.feature_service import FeatureService
from deep_sound.services.index_service import INDEX_PROFILE_FEATURES, IndexService
from deep_sound.services.library_analysis_service import AnalysisProfile, LibraryAnalysisService
from deep_sound.services.similarity_service import SearchMode, SimilarityService


def test_quality_profile_builds_track_stem_and_source_indexes(tmp_path: Path) -> None:
    store, query_id = _quality_store(tmp_path)
    index = IndexService(store, index_root=tmp_path / "indices")

    statuses = index.build_profile(AnalysisProfile.QUALITY)

    assert INDEX_PROFILE_FEATURES[AnalysisProfile.QUALITY]
    assert {status.owner_type for status in statuses} >= {
        OwnerType.TRACK,
        OwnerType.STEM,
        OwnerType.SOURCE,
    }
    assert all(status.available for status in statuses)
    results = SimilarityService(
        FeatureService(store),
        index_service=index,
    ).search_mode(query_id, SearchMode.QUALITY)
    assert results
    assert results[0].search_backend == "index"


def test_quality_index_stale_status_preserves_scan_caveat(tmp_path: Path) -> None:
    store, _query_id = _quality_store(tmp_path)
    index = IndexService(store, index_root=tmp_path / "indices")
    index.build_profile(AnalysisProfile.QUALITY)
    original = store.get_feature_view_for_owner("track-1", FeatureType.RHYTHM_GLOBAL)
    store.replace_feature_view_for_owner(
        replace(original, stats={**original.stats, "phase15_drift": 1.0})
    )

    status = index.status(FeatureType.RHYTHM_GLOBAL, owner_type=OwnerType.TRACK)

    assert status.stale is True
    assert status.available is False
    assert status.backend in {"numpy", "faiss"}
    assert "search will scan feature rows" in status.caveats[0]


def _quality_store(tmp_path: Path) -> tuple[SqliteStore, str]:
    store = SqliteStore(tmp_path / "library.sqlite")
    store.init_schema()
    for index, bpm in enumerate((120.0, 124.0), start=1):
        audio_path = tmp_path / f"quality_{index}.wav"
        _write_quality_mix(audio_path, bpm=bpm)
        store.add_track(
            Track(
                id=f"track-{index}",
                filepath=audio_path,
                duration_sec=4.0,
                sample_rate=22_050,
                audio_hash=file_sha256(audio_path),
            )
        )
    summary = LibraryAnalysisService(store, app_data_dir=tmp_path / "app_data").analyze_library(
        profile=AnalysisProfile.QUALITY
    )
    assert summary.failed_count == 0
    return store, "track-1"


def _write_quality_mix(path: Path, *, bpm: float) -> None:
    sample_rate = 22_050
    duration = 4.0
    t = np.linspace(0.0, duration, int(sample_rate * duration), endpoint=False)
    chord = 0.18 * (
        np.sin(2 * np.pi * 261.63 * t)
        + np.sin(2 * np.pi * 329.63 * t)
        + np.sin(2 * np.pi * 392.0 * t)
    )
    bass = 0.14 * np.sin(2 * np.pi * 82.41 * t)
    clicks = np.zeros_like(t)
    click_len = int(0.02 * sample_rate)
    envelope = np.exp(-np.linspace(0, 6, click_len))
    beat = 0.0
    while beat < duration:
        start = int(beat * sample_rate)
        end = min(start + click_len, clicks.shape[0])
        clicks[start:end] += 0.2 * envelope[: end - start]
        beat += 60.0 / bpm
    sf.write(path, np.clip(chord + bass + clicks, -0.9, 0.9).astype(np.float32), sample_rate)
