from __future__ import annotations

from pathlib import Path

from deep_sound.domain.confidence import Confidence
from deep_sound.domain.source import Source, SourceType
from deep_sound.domain.stem import Stem, StemType
from deep_sound.domain.track import Track
from deep_sound.infra.storage.sqlite_store import SqliteStore
from deep_sound.services.correction_service import CorrectionService
from deep_sound.services.source_service import SourceService


def test_source_service_effective_reads_apply_user_overrides_without_mutating_raw(
    tmp_path: Path,
) -> None:
    store = SqliteStore(tmp_path / "library.sqlite")
    store.init_schema()
    store.add_track(Track(id="track-1", filepath=tmp_path / "song.wav", audio_hash="hash"))
    stem = store.add_stem(
        Stem(id="stem-1", track_id="track-1", stem_type=StemType.OTHER, confidence=Confidence(0.8))
    )
    raw_source = store.add_source(
        Source(
            id="source-1",
            track_id="track-1",
            parent_stem_id=stem.id,
            source_type=SourceType.PITCHED_HARMONIC,
            source_label="possible accompaniment stem",
            confidence=Confidence(0.7),
        )
    )
    corrections = CorrectionService(store)
    corrections.add_source_label_correction(
        raw_source,
        label="likely piano",
        source_type=SourceType.MELODIC,
    )
    service = SourceService(
        store,
        app_data_dir=tmp_path / "app_data",
        correction_service=corrections,
    )

    effective = service.list_effective_sources("track-1")
    raw_after = store.get_source("source-1")
    graph_node = service.source_graph("track-1").stems[0].sources[0]

    assert effective[0].source_label == "likely piano"
    assert effective[0].source_type is SourceType.MELODIC
    assert effective[0].is_user_corrected
    assert graph_node.source_label == "likely piano"
    assert raw_after == raw_source
