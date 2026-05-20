from __future__ import annotations

from dataclasses import replace
from pathlib import Path

from deep_sound.domain.confidence import Confidence
from deep_sound.domain.feature_view import FeatureType, FeatureView, OwnerType
from deep_sound.domain.source import Source, SourceType
from deep_sound.domain.stem import Stem, StemType
from deep_sound.domain.track import Track
from deep_sound.infra.storage.sqlite_store import SqliteStore
from deep_sound.services.correction_service import CorrectionService
from deep_sound.services.feature_service import FeatureService
from deep_sound.services.index_service import IndexService
from deep_sound.services.similarity_service import SimilarityService


def test_index_status_detects_same_metadata_feature_value_drift(tmp_path: Path) -> None:
    store = SqliteStore(tmp_path / "library.sqlite")
    store.init_schema()
    service = IndexService(store, index_root=tmp_path / "indices")
    original = _track_feature("query", (1.0, 0.0))
    store.add_feature_view(original)
    service.build_index(FeatureType.RHYTHM_GLOBAL)

    store.replace_feature_view_for_owner(replace(original, stats={"x": 0.0, "y": 1.0}))
    status = service.status(FeatureType.RHYTHM_GLOBAL)

    assert status.available is False
    assert status.stale is True
    assert any("feature_fingerprint" in caveat for caveat in status.caveats)


def test_source_correction_changes_compatible_retrieval_filter(tmp_path: Path) -> None:
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
    query = _source(
        "query-source", stem_id=pitched_stem.id, source_type=SourceType.PITCHED_HARMONIC
    )
    candidate = _source("candidate-source", stem_id=drum_stem.id, source_type=SourceType.DRUM)
    store.add_source(query)
    store.add_source(candidate)
    store.add_feature_view(_source_feature(query.id, 1.0))
    store.add_feature_view(_source_feature(candidate.id, 0.95))
    corrections = CorrectionService(store)
    corrections.add_source_label_correction(
        candidate,
        label="corrected pitched source",
        source_type=SourceType.PITCHED_HARMONIC,
    )
    features = FeatureService(store, correction_service=corrections)
    index = IndexService(store, index_root=tmp_path / "indices", features=features)
    index.build_index(FeatureType.HARMONY_CHORD_SEQUENCE, owner_type=OwnerType.SOURCE)

    results = SimilarityService(features, index_service=index).search_source_chords(
        query.id,
        include_chord_change=False,
    )

    assert [result.owner_id for result in results] == [candidate.id]


def _track_feature(owner_id: str, values: tuple[float, float]) -> FeatureView:
    return FeatureView(
        id=f"{owner_id}:rhythm",
        owner_type=OwnerType.TRACK,
        owner_id=owner_id,
        feature_type=FeatureType.RHYTHM_GLOBAL,
        algorithm="test",
        algorithm_version="1",
        params_hash="params",
        stats={"x": values[0], "y": values[1]},
    )


def _source(source_id: str, *, stem_id: str, source_type: SourceType) -> Source:
    return Source(
        id=source_id,
        track_id="track-1",
        parent_stem_id=stem_id,
        source_type=source_type,
        source_label=f"possible {source_type.value}",
        confidence=Confidence(0.7),
    )


def _source_feature(source_id: str, value: float) -> FeatureView:
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
