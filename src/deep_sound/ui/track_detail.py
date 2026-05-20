"""Track detail view helpers for waveform, sections, and feature summaries."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from deep_sound.domain.feature_view import FeatureView
from deep_sound.domain.track import Track
from deep_sound.infra.storage.sqlite_store import SectionRecord, SourceActivityRecord
from deep_sound.services.waveform_service import ClipWindowDTO, WaveformCacheDTO
from deep_sound.ui.waveform_panel import (
    ClipSelectionState,
    WaveformPanelData,
    create_waveform_panel,
    waveform_panel_data,
)


@dataclass(frozen=True, slots=True)
class FeatureSummaryRow:
    feature_type: str
    algorithm: str
    confidence: str


@dataclass(frozen=True, slots=True)
class TrackDetailData:
    track_id: str
    title: str
    analysis_status: str
    duration: str
    waveform: WaveformPanelData | None = None
    selected_clip: ClipSelectionState | None = None
    feature_summaries: tuple[FeatureSummaryRow, ...] = ()


def track_detail_data(
    track: Track,
    *,
    waveform_cache: WaveformCacheDTO | None = None,
    selected_clip: ClipSelectionState | None = None,
    persisted_clips: tuple[ClipWindowDTO, ...] = (),
    features: Sequence[FeatureView] = (),
) -> TrackDetailData:
    waveform = (
        None
        if waveform_cache is None
        else waveform_panel_data(
            waveform_cache,
            selected_clip=selected_clip,
            persisted_clips=persisted_clips,
        )
    )
    return TrackDetailData(
        track_id=track.id,
        title=track.title or track.filepath.stem,
        analysis_status=track.analysis_status,
        duration=_format_duration(track.duration_sec),
        waveform=waveform,
        selected_clip=selected_clip,
        feature_summaries=tuple(feature_summary_rows(features)),
    )


def feature_summary_rows(features: Sequence[FeatureView]) -> list[FeatureSummaryRow]:
    return [
        FeatureSummaryRow(
            feature_type=feature.feature_type.value,
            algorithm=f"{feature.algorithm} v{feature.algorithm_version}",
            confidence="unknown"
            if feature.confidence is None
            else f"{feature.confidence.value:.2f}",
        )
        for feature in features
    ]


def create_track_detail_widget(
    track: Track,
    sections: Sequence[SectionRecord] = (),
    source_activity: Sequence[SourceActivityRecord] = (),
    features: Sequence[FeatureView] = (),
    waveform: WaveformPanelData | None = None,
) -> object:
    """Create a PySide track-detail widget from service-level DTOs."""
    try:
        from PySide6.QtWidgets import (  # type: ignore[import-not-found]
            QGroupBox,
            QHBoxLayout,
            QLabel,
            QListWidget,
            QPushButton,
            QTableWidget,
            QTableWidgetItem,
            QVBoxLayout,
            QWidget,
        )
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError(
            "Install deep-sound with the [ui] extra to create PySide widgets."
        ) from exc

    root = QWidget()
    layout = QVBoxLayout(root)
    title = track.title or track.filepath.stem
    layout.addWidget(QLabel(f"{title}  |  {track.analysis_status}"))

    controls = QHBoxLayout()
    controls.addWidget(QPushButton("Play"))
    controls.addWidget(QPushButton("Pause"))
    controls.addWidget(QPushButton("Analyze"))
    controls.addWidget(QPushButton("Reanalyze"))
    layout.addLayout(controls)

    if waveform is None:
        layout.addWidget(QLabel("Waveform cache unavailable"))
    else:
        layout.addWidget(create_waveform_panel(waveform))

    section_box = QGroupBox("Sections")
    section_list = QListWidget()
    for section in sections:
        section_list.addItem(
            f"{section.label} {section.start_sec:.1f}-{section.end_sec:.1f}s "
            f"confidence {section.confidence.value:.2f}"
        )
    section_layout = QVBoxLayout(section_box)
    section_layout.addWidget(section_list)
    layout.addWidget(section_box)

    activity_box = QGroupBox("Source Activity")
    activity_list = QListWidget()
    for activity in source_activity:
        activity_list.addItem(
            f"{activity.source_id} {activity.start_sec:.1f}-{activity.end_sec:.1f}s "
            f"confidence {activity.confidence.value:.2f}"
        )
    activity_layout = QVBoxLayout(activity_box)
    activity_layout.addWidget(activity_list)
    layout.addWidget(activity_box)

    table = QTableWidget(0, 3)
    table.setHorizontalHeaderLabels(["Feature", "Algorithm", "Confidence"])
    for row in feature_summary_rows(features):
        index = table.rowCount()
        table.insertRow(index)
        for column, value in enumerate([row.feature_type, row.algorithm, row.confidence]):
            table.setItem(index, column, QTableWidgetItem(value))
    layout.addWidget(table)
    return root


def _format_duration(duration_sec: float | None) -> str:
    if duration_sec is None:
        return "-"
    total = max(0, round(duration_sec))
    minutes, seconds = divmod(total, 60)
    return f"{minutes}:{seconds:02d}"
