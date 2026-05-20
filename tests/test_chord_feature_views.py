from __future__ import annotations

from pathlib import Path

from deep_sound.domain.confidence import Confidence
from deep_sound.domain.feature_view import FeatureType
from deep_sound.domain.harmony import ChordEvent, HarmonicOwnerType
from deep_sound.domain.source import Source, SourceType
from deep_sound.infra.storage.sqlite_store import SqliteStore
from deep_sound.services.analysis_service import AnalysisService


def test_chord_feature_views_have_stable_numeric_proxy_stats(tmp_path: Path) -> None:
    store = SqliteStore(tmp_path / "library.sqlite")
    store.init_schema()
    source = Source(
        id="source-1",
        track_id="track-1",
        parent_stem_id="stem-1",
        source_type=SourceType.PITCHED_HARMONIC,
        source_label="possible pitched harmonic accompaniment",
        confidence=Confidence(0.7),
    )
    events = [
        ChordEvent(
            id="chord-1",
            owner_type=HarmonicOwnerType.SOURCE,
            owner_id=source.id,
            start_sec=0.0,
            end_sec=1.0,
            chord_label="C",
            root="C",
            quality="major",
            confidence=Confidence(0.7),
        ),
        ChordEvent(
            id="chord-2",
            owner_type=HarmonicOwnerType.SOURCE,
            owner_id=source.id,
            start_sec=1.0,
            end_sec=2.0,
            chord_label="G",
            root="G",
            quality="major",
            confidence=Confidence(0.6),
        ),
    ]

    views = AnalysisService(store).chord_feature_views(source, events)

    sequence = next(
        view for view in views if view.feature_type is FeatureType.HARMONY_CHORD_SEQUENCE
    )
    change = next(view for view in views if view.feature_type is FeatureType.HARMONY_CHORD_CHANGE)
    assert "token_I" in sequence.stats
    assert "token_V" in sequence.stats
    assert len(change.stats) == 12
    assert sequence.confidence == Confidence(0.6)
