from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest
import soundfile as sf

from deep_sound.domain.confidence import Confidence
from deep_sound.domain.feature_view import FeatureType, OwnerType
from deep_sound.domain.source import Source, SourceType
from deep_sound.domain.stem import Stem, StemType
from deep_sound.domain.track import Track
from deep_sound.infra.storage.sqlite_store import SqliteStore
from deep_sound.services.analysis_service import AnalysisService


def test_analysis_service_rejects_incompatible_source_chord_analysis(tmp_path: Path) -> None:
    store = SqliteStore(tmp_path / "library.sqlite")
    store.init_schema()
    store.add_track(Track(id="track-1", filepath=tmp_path / "song.wav"))
    stem = store.add_stem(
        Stem(
            id="track-1:drums",
            track_id="track-1",
            stem_type=StemType.DRUMS,
            confidence=Confidence(0.8),
            artifact_path=tmp_path / "drums.wav",
        )
    )
    source = store.add_source(
        Source(
            id="source-drums",
            track_id="track-1",
            parent_stem_id=stem.id,
            source_type=SourceType.DRUM,
            source_label="possible drums stem",
            confidence=Confidence(0.8),
        )
    )

    with pytest.raises(ValueError, match="not enabled"):
        AnalysisService(store).infer_source_chords(source)


def test_analysis_service_persists_source_chords_and_feature_views(tmp_path: Path) -> None:
    sample_rate = 22050
    duration = 2.0
    t = np.linspace(0.0, duration, int(sample_rate * duration), endpoint=False)
    audio = (
        0.2 * np.sin(2 * np.pi * 261.63 * t)
        + 0.2 * np.sin(2 * np.pi * 329.63 * t)
        + 0.2 * np.sin(2 * np.pi * 392.0 * t)
    ).astype(np.float32)
    audio_path = tmp_path / "other.wav"
    sf.write(audio_path, audio, sample_rate)

    store = SqliteStore(tmp_path / "library.sqlite")
    store.init_schema()
    store.add_track(Track(id="track-1", filepath=audio_path))
    stem = store.add_stem(
        Stem(
            id="track-1:other",
            track_id="track-1",
            stem_type=StemType.OTHER,
            confidence=Confidence(0.8),
            artifact_path=audio_path,
        )
    )
    source = store.add_source(
        Source(
            id="source-harmony",
            track_id="track-1",
            parent_stem_id=stem.id,
            source_type=SourceType.PITCHED_HARMONIC,
            source_label="possible pitched harmonic accompaniment",
            confidence=Confidence(0.7),
        )
    )

    views = AnalysisService(store, sample_rate=sample_rate).analyze_source(source)

    assert store.list_chord_events_for_owner(source.id)
    assert {view.owner_type for view in views} == {OwnerType.SOURCE}
    assert {view.feature_type for view in views} == {
        FeatureType.HARMONY_CHORD_SEQUENCE,
        FeatureType.HARMONY_CHORD_CHANGE,
    }
    assert all(view.confidence is not None for view in views)
