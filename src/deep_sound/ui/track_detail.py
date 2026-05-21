"""Track detail view helpers for waveform, sections, and feature summaries."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from enum import StrEnum
from typing import cast

from deep_sound.domain.feature_view import FeatureView
from deep_sound.domain.track import Track
from deep_sound.infra.storage.sqlite_store import SectionRecord, SourceActivityRecord
from deep_sound.services.playback_service import PlaybackState, PlaybackStatus
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


class PlaybackAction(StrEnum):
    PLAY = "play"
    PAUSE = "pause"
    SEEK = "seek"
    STOP = "stop"


@dataclass(frozen=True, slots=True)
class PlaybackActionDTO:
    action: PlaybackAction
    track_id: str
    position_sec: float | None = None
    source_path: str | None = None
    duration_sec: float | None = None


@dataclass(frozen=True, slots=True)
class PlaybackControlsData:
    track_id: str
    status: PlaybackStatus
    position_sec: float = 0.0
    duration_sec: float | None = None
    backend: str = "inspection"
    is_output_active: bool = False
    error_message: str | None = None
    play_action: PlaybackActionDTO | None = None
    pause_action: PlaybackActionDTO | None = None
    stop_action: PlaybackActionDTO | None = None
    seek_action: PlaybackActionDTO | None = None


@dataclass(frozen=True, slots=True)
class TrackDetailData:
    track_id: str
    title: str
    analysis_status: str
    duration: str
    waveform: WaveformPanelData | None = None
    selected_clip: ClipSelectionState | None = None
    playback: PlaybackControlsData | None = None
    feature_summaries: tuple[FeatureSummaryRow, ...] = ()


def track_detail_data(
    track: Track,
    *,
    waveform_cache: WaveformCacheDTO | None = None,
    selected_clip: ClipSelectionState | None = None,
    persisted_clips: tuple[ClipWindowDTO, ...] = (),
    features: Sequence[FeatureView] = (),
    playback_state: PlaybackState | None = None,
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
        playback=playback_controls_data(track, playback_state=playback_state),
        feature_summaries=tuple(feature_summary_rows(features)),
    )


def playback_controls_data(
    track: Track,
    *,
    playback_state: PlaybackState | None = None,
) -> PlaybackControlsData:
    state = playback_state or PlaybackState(
        track_id=track.id,
        source_path=track.filepath,
        status=PlaybackStatus.STOPPED,
        duration_sec=track.duration_sec,
    )
    position = state.position_sec if state.track_id == track.id else 0.0
    duration = state.duration_sec if state.track_id == track.id else track.duration_sec
    return PlaybackControlsData(
        track_id=track.id,
        status=state.status if state.track_id == track.id else PlaybackStatus.STOPPED,
        position_sec=position,
        duration_sec=duration,
        backend=state.backend,
        is_output_active=state.is_output_active,
        error_message=state.error_message if state.track_id == track.id else None,
        play_action=PlaybackActionDTO(
            PlaybackAction.PLAY,
            track.id,
            position,
            str(track.filepath),
            duration,
        ),
        pause_action=PlaybackActionDTO(PlaybackAction.PAUSE, track.id),
        stop_action=PlaybackActionDTO(PlaybackAction.STOP, track.id),
        seek_action=PlaybackActionDTO(
            PlaybackAction.SEEK,
            track.id,
            position,
            str(track.filepath),
            duration,
        ),
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
    playback_state: PlaybackState | None = None,
    on_play: Callable[[PlaybackActionDTO], object] | None = None,
    on_pause: Callable[[PlaybackActionDTO], object] | None = None,
    on_seek: Callable[[PlaybackActionDTO], object] | None = None,
    on_stop: Callable[[PlaybackActionDTO], object] | None = None,
) -> object:
    """Create a PySide track-detail widget from service-level DTOs."""
    try:
        from PySide6.QtWidgets import (
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
    playback = playback_controls_data(track, playback_state=playback_state)
    play_button = QPushButton("Play")
    pause_button = QPushButton("Pause")
    seek_button = QPushButton("Seek")
    stop_button = QPushButton("Stop")
    if on_play is not None and playback.play_action is not None:
        play_button.clicked.connect(lambda: on_play(playback.play_action))
    if on_pause is not None and playback.pause_action is not None:
        pause_button.clicked.connect(lambda: on_pause(playback.pause_action))
    if on_seek is not None and playback.seek_action is not None:
        seek_button.clicked.connect(lambda: on_seek(playback.seek_action))
    if on_stop is not None and playback.stop_action is not None:
        stop_button.clicked.connect(lambda: on_stop(playback.stop_action))
    controls.addWidget(play_button)
    controls.addWidget(pause_button)
    controls.addWidget(seek_button)
    controls.addWidget(stop_button)
    controls.addWidget(QPushButton("Analyze"))
    controls.addWidget(QPushButton("Reanalyze"))
    layout.addLayout(controls)
    layout.addWidget(
        QLabel(
            "Playback "
            f"{playback.status.value} | backend {playback.backend} | "
            f"{playback.position_sec:.1f}s/{_format_duration(playback.duration_sec)} | "
            f"output {'active' if playback.is_output_active else 'inactive'}"
        )
    )
    if playback.error_message:
        layout.addWidget(QLabel(f"Playback error: {playback.error_message}"))

    if waveform is None:
        layout.addWidget(QLabel("Waveform cache unavailable"))
    else:
        layout.addWidget(cast(QWidget, create_waveform_panel(waveform)))

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
