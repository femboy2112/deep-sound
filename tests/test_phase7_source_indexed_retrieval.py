from __future__ import annotations

from pathlib import Path

from deep_sound.domain.confidence import Confidence
from deep_sound.domain.feature_view import FeatureType, FeatureView, OwnerType
from deep_sound.domain.source import Source, SourceType
from deep_sound.domain.stem import Stem, StemType
from deep_sound.domain.track import Track
from deep_sound.infra.storage.sqlite_store import SqliteStore
from deep_sound.services.feature_service import FeatureService
from deep_sound.services.index_service import IndexService
from deep_sound.services.similarity_service import SimilarityService


def _source(
    source_id: str,
    *,
    stem_id: str,
    source_type: SourceType,
) -> Source:
    return Source(
        id=source_id,
        track_id="track-1",
        parent_stem_id=stem_id,
        source_type=source_type,
        source_label=f"possible {source_type.value}",
        confidence=Confidence(0.7),
    )


def _feature(source_id: str, value: float) -> FeatureView:
    return FeatureView(
        id=f"{source_id}:harmony.chord_sequence",
        owner_type=OwnerType.SOURCE,
        owner_id=source_id,
        feature_type=FeatureType.HARMONY_CHORD_SEQUENCE,
        algorithm="test",
        algorithm_version="1",
        params_hash="params",
        stats={"x": value, "y": 1.0 - value},
        confidence=Confidence(0.7),
    )


def test_indexed_source_chord_retrieval_excludes_incompatible_source_types(
    tmp_path: Path,
) -> None:
    store = SqliteStore(tmp_path / "library.sqlite")
    store.init_schema()
    store.add_track(Track(id="track-1", filepath=tmp_path / "song.wav", audio_hash="hash"))
    pitched_stem = store.add_stem(
        Stem(
            id="track-1:other",
            track_id="track-1",
            stem_type=StemType.OTHER,
            confidence=Confidence(0.8),
            artifact_path=tmp_path / "other.wav",
        )
    )
    drum_stem = store.add_stem(
        Stem(
            id="track-1:drums",
            track_id="track-1",
            stem_type=StemType.DRUMS,
            confidence=Confidence(0.8),
            artifact_path=tmp_path / "drums.wav",
        )
    )
    for source in [
        _source(
            "query-source",
            stem_id=pitched_stem.id,
            source_type=SourceType.PITCHED_HARMONIC,
        ),
        _source(
            "compatible-source",
            stem_id=pitched_stem.id,
            source_type=SourceType.PITCHED_HARMONIC,
        ),
        _source("drum-source", stem_id=drum_stem.id, source_type=SourceType.DRUM),
    ]:
        store.add_source(source)
    store.add_feature_view(_feature("query-source", 1.0))
    store.add_feature_view(_feature("compatible-source", 0.9))
    store.add_feature_view(_feature("drum-source", 0.99))

    features = FeatureService(store)
    index = IndexService(store, index_root=tmp_path / "indices", features=features)
    index.build_index(FeatureType.HARMONY_CHORD_SEQUENCE, owner_type=OwnerType.SOURCE)
    results = SimilarityService(features, index_service=index).search_source_chords(
        "query-source",
        include_chord_change=False,
    )

    assert [result.owner_id for result in results] == ["compatible-source"]
    assert results[0].search_backend == "index"
