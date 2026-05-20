from __future__ import annotations

from pathlib import Path

import pytest

from deep_sound.domain.confidence import Confidence
from deep_sound.domain.feature_view import FeatureType
from deep_sound.domain.source import Source, SourceType
from deep_sound.domain.stem import Stem, StemType
from deep_sound.domain.track import Track
from deep_sound.infra.analyzers.melody_contour import summarize_melody_contour
from deep_sound.infra.storage.sqlite_store import SqliteStore
from deep_sound.services.analysis_service import AnalysisService


def test_melody_contour_summary_is_bounded(click_track_wav: Path) -> None:
    summary = summarize_melody_contour(click_track_wav)

    assert all(0.0 <= value <= 1.0 for value in summary.contour.values())
    assert 0.0 <= summary.confidence.value <= 1.0


def test_analysis_service_routes_melody_to_compatible_sources(
    tmp_path: Path,
    click_track_wav: Path,
) -> None:
    store = SqliteStore(tmp_path / "library.sqlite")
    store.init_schema()
    store.add_track(Track(id="track-1", filepath=click_track_wav))
    stem = Stem(
        id="track-1:vocals",
        track_id="track-1",
        stem_type=StemType.VOCALS,
        confidence=Confidence(0.8),
        artifact_path=click_track_wav,
    )
    store.add_stem(stem)
    source = Source(
        id="source-1",
        track_id="track-1",
        parent_stem_id=stem.id,
        source_type=SourceType.MELODIC,
        source_label="possible vocal melody",
        confidence=Confidence(0.75),
    )

    view = AnalysisService(store).analyze_melody_contour(source)

    assert view.feature_type is FeatureType.MELODY_CONTOUR
    assert view.confidence is not None
    assert view.confidence.value <= 0.75


def test_analysis_service_rejects_melody_for_drums(tmp_path: Path) -> None:
    store = SqliteStore(tmp_path / "library.sqlite")
    store.init_schema()
    source = Source(
        id="source-1",
        track_id="track-1",
        parent_stem_id="missing",
        source_type=SourceType.DRUM,
        source_label="possible drum source",
        confidence=Confidence(0.75),
    )

    with pytest.raises(ValueError, match="Melody contour is not enabled"):
        AnalysisService(store).analyze_melody_contour(source)
