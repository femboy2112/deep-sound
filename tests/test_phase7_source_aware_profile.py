from __future__ import annotations

from pathlib import Path

import numpy as np
import soundfile as sf

from deep_sound.domain.feature_view import FeatureType, OwnerType
from deep_sound.domain.source import SourceType
from deep_sound.domain.stem import StemType
from deep_sound.domain.track import Track
from deep_sound.infra.storage.sqlite_store import SqliteStore
from deep_sound.services.library_analysis_service import LibraryAnalysisService


def test_source_aware_profile_uses_fake_provider_and_is_idempotent(tmp_path: Path) -> None:
    sample_rate = 22050
    duration = 2.0
    t = np.linspace(0.0, duration, int(sample_rate * duration), endpoint=False)
    audio = (
        0.2 * np.sin(2 * np.pi * 261.63 * t)
        + 0.2 * np.sin(2 * np.pi * 329.63 * t)
        + 0.2 * np.sin(2 * np.pi * 392.0 * t)
    ).astype(np.float32)
    audio_path = tmp_path / "song.wav"
    sf.write(audio_path, audio, sample_rate)

    store = SqliteStore(tmp_path / "library.sqlite")
    store.init_schema()
    track = store.add_track(
        Track(
            id="track-1",
            filepath=audio_path,
            duration_sec=duration,
            sample_rate=sample_rate,
            audio_hash="hash",
        )
    )
    service = LibraryAnalysisService(store, app_data_dir=tmp_path / "app_data")

    first = service.analyze_track(track, profile="source_aware")
    second = service.analyze_track(track, profile="source_aware")

    assert first.succeeded
    assert second.succeeded
    assert store.get_track(track.id).analysis_status == "source_aware"
    assert {stem.stem_type for stem in store.list_stems_for_track(track.id)} == {
        StemType.VOCALS,
        StemType.DRUMS,
        StemType.BASS,
        StemType.OTHER,
    }
    sources = store.list_sources_for_track(track.id)
    assert any(source.source_type is SourceType.PITCHED_HARMONIC for source in sources)
    assert len(store.list_stems_for_track(track.id)) == 4
    assert len({source.id for source in sources}) == len(sources)
    all_features = [
        view
        for owner_id in [track.id, *(stem.id for stem in store.list_stems_for_track(track.id))]
        for view in store.list_feature_views_for_owner(owner_id)
    ]
    all_features.extend(
        view for source in sources for view in store.list_feature_views_for_owner(source.id)
    )
    assert OwnerType.STEM in {view.owner_type for view in all_features}
    assert OwnerType.SOURCE in {view.owner_type for view in all_features}
    assert {
        FeatureType.RHYTHM_DRUM,
        FeatureType.BASS_ROOT_MOTION,
        FeatureType.HARMONY_CHORD_SEQUENCE,
        FeatureType.TIMBRE_EMBEDDING,
    } <= {view.feature_type for view in all_features}
