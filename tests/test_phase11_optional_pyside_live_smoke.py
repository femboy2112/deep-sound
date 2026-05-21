from __future__ import annotations

import sys
from pathlib import Path

import pytest

from deep_sound.domain.confidence import Confidence
from deep_sound.domain.source import Source, SourceType
from deep_sound.domain.stem import Stem, StemType
from deep_sound.domain.track import Track
from deep_sound.services.library_analysis_service import AnalysisProfile
from deep_sound.services.source_service import SourceGraph, SourceGraphStem
from deep_sound.ui.main_window import create_main_window
from deep_sound.ui.source_graph import create_source_graph_view
from deep_sound.ui.track_detail import create_track_detail_widget


def test_phase11_optional_pyside_live_smoke_skips_without_ui_extra(
    tmp_path: Path,
) -> None:
    pytest.importorskip("PySide6")
    from PySide6.QtWidgets import QApplication, QPushButton  # type: ignore[import-not-found]

    app = QApplication.instance() or QApplication(sys.argv[:1])
    track = Track(
        id="track-1",
        filepath=tmp_path / "song.wav",
        title="Live Song",
        duration_sec=2.0,
    )
    controller = _FakeController()

    window = create_main_window(
        (track,),
        controller=controller,
        active_profile=AnalysisProfile.SEARCHABLE,
    )
    detail = create_track_detail_widget(track)
    graph_view = create_source_graph_view(_source_graph(tmp_path, track.id))

    playback_labels = {
        button.text().lower() for button in detail.findChildren(QPushButton) if button.text()
    }
    assert app is not None
    assert window is not None
    assert detail is not None
    assert graph_view is not None
    assert {"play", "pause"}.issubset(playback_labels)


class _FakeController:
    def import_paths(self, intent: object) -> object:
        return intent

    def analyze(self, intent: object) -> object:
        return intent

    def build_index(self, intent: object) -> object:
        return intent

    def search(self, intent: object) -> object:
        return ()

    def snapshot(self) -> object:
        return object()


def _source_graph(tmp_path: Path, track_id: str) -> SourceGraph:
    stem = Stem(
        id=f"{track_id}:other",
        track_id=track_id,
        stem_type=StemType.OTHER,
        confidence=Confidence(0.8),
        artifact_path=tmp_path / "other.wav",
    )
    source = Source(
        id=f"{stem.id}:source",
        track_id=track_id,
        parent_stem_id=stem.id,
        source_type=SourceType.PITCHED_HARMONIC,
        source_label="possible accompaniment stem",
        confidence=Confidence(0.7),
    )
    return SourceGraph(
        track_id=track_id,
        stems=(SourceGraphStem(stem=stem, sources=(source,), feature_views=()),),
    )
