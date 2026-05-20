from __future__ import annotations

from pathlib import Path

from deep_sound.domain.confidence import Confidence
from deep_sound.domain.source import SourceType
from deep_sound.domain.stem import Stem, StemType
from deep_sound.domain.track import Track
from deep_sound.infra.storage.sqlite_store import SqliteStore
from deep_sound.services.source_service import SourceService


def test_discover_pitched_harmonic_sources_only_from_compatible_stems(tmp_path: Path) -> None:
    store = SqliteStore(tmp_path / "library.sqlite")
    store.init_schema()
    store.add_track(Track(id="track-1", filepath=tmp_path / "song.wav"))
    other = store.add_stem(
        Stem(
            id="track-1:other",
            track_id="track-1",
            stem_type=StemType.OTHER,
            confidence=Confidence(0.8),
            artifact_path=tmp_path / "other.wav",
        )
    )
    drums = store.add_stem(
        Stem(
            id="track-1:drums",
            track_id="track-1",
            stem_type=StemType.DRUMS,
            confidence=Confidence(0.8),
            artifact_path=tmp_path / "drums.wav",
        )
    )
    service = SourceService(store, app_data_dir=tmp_path / "app_data")

    discovered = service.discover_pitched_harmonic_sources(other)

    assert [source.source_type for source in discovered] == [SourceType.PITCHED_HARMONIC]
    assert "possible" in discovered[0].source_label
    assert 0.0 <= discovered[0].confidence.value <= 1.0
    assert service.discover_pitched_harmonic_sources(drums) == []
    assert service.discover_pitched_harmonic_sources(other) == discovered
