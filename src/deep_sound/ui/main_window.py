"""Main window and library view for the Phase 1 desktop shell."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from deep_sound.domain.track import Track
from deep_sound.infra.job_queue import JobRecord, JobState
from deep_sound.services.library_analysis_service import AnalysisProfile
from deep_sound.ui.library_workflow import AnalyzeIntentDTO, IndexIntentDTO, SearchIntentDTO


@dataclass(frozen=True, slots=True)
class LibraryRow:
    track_id: str
    title: str
    artist: str
    duration: str
    analysis_status: str


@dataclass(frozen=True, slots=True)
class QueueRow:
    job_id: str
    job_type: str
    target_id: str
    state: str
    progress: str


@dataclass(frozen=True, slots=True)
class MainWindowActionMap:
    analyze_intent: AnalyzeIntentDTO
    index_intent: IndexIntentDTO
    refresh_action: str
    selected_track_search: SearchIntentDTO | None = None


def main_window_action_map(
    *,
    active_profile: AnalysisProfile,
    selected_track_id: str | None = None,
    search_mode: str = "weighted",
) -> MainWindowActionMap:
    return MainWindowActionMap(
        analyze_intent=AnalyzeIntentDTO(profile=active_profile),
        index_intent=IndexIntentDTO(profile=active_profile),
        refresh_action="refresh_library_state",
        selected_track_search=(
            None
            if selected_track_id is None
            else SearchIntentDTO(query_id=selected_track_id, mode=search_mode)
        ),
    )


def library_rows(tracks: Sequence[Track]) -> list[LibraryRow]:
    return [
        LibraryRow(
            track_id=track.id,
            title=track.title or track.filepath.stem,
            artist=track.artist or "Unknown artist",
            duration=_format_duration(track.duration_sec),
            analysis_status=track.analysis_status,
        )
        for track in tracks
    ]


def queue_rows(jobs: Sequence[JobRecord]) -> list[QueueRow]:
    return [
        QueueRow(
            job_id=job.id,
            job_type=job.job_type.value,
            target_id=job.target_id,
            state=job.state.value,
            progress=f"{job.progress:.0%}",
        )
        for job in jobs
    ]


def create_main_window(tracks: Sequence[Track], jobs: Sequence[JobRecord] = ()) -> object:
    """Create the PySide main window.

    Importing this module does not require PySide. Calling this factory does.
    """
    try:
        from PySide6.QtCore import Qt  # type: ignore[import-not-found]
        from PySide6.QtWidgets import (  # type: ignore[import-not-found]
            QAbstractItemView,
            QHBoxLayout,
            QHeaderView,
            QLabel,
            QLineEdit,
            QMainWindow,
            QProgressBar,
            QPushButton,
            QTableWidget,
            QTableWidgetItem,
            QVBoxLayout,
            QWidget,
        )
    except ImportError as exc:  # pragma: no cover - exercised only with optional extra absent.
        raise RuntimeError(
            "Install deep-sound with the [ui] extra to create PySide widgets."
        ) from exc

    window = QMainWindow()
    window.setWindowTitle("Deep-Sound")

    root = QWidget()
    layout = QVBoxLayout(root)

    toolbar = QHBoxLayout()
    toolbar.addWidget(QPushButton("Import File"))
    toolbar.addWidget(QPushButton("Import Folder"))
    toolbar.addWidget(QPushButton("Analyze"))
    toolbar.addWidget(QPushButton("Reindex"))
    filter_box = QLineEdit()
    filter_box.setPlaceholderText("Filter library")
    toolbar.addWidget(filter_box)
    layout.addLayout(toolbar)

    table = QTableWidget(0, 5)
    table.setHorizontalHeaderLabels(["Title", "Artist", "Duration", "Status", "Track ID"])
    table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
    table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
    table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
    for row in library_rows(tracks):
        index = table.rowCount()
        table.insertRow(index)
        for column, value in enumerate(
            [row.title, row.artist, row.duration, row.analysis_status, row.track_id]
        ):
            table.setItem(index, column, QTableWidgetItem(value))
    layout.addWidget(table)

    queue_label = QLabel("Analysis Queue")
    layout.addWidget(queue_label)
    for job in queue_rows(jobs):
        progress = QProgressBar()
        progress.setRange(0, 100)
        progress.setValue(_progress_to_int(job.progress))
        progress.setFormat(f"{job.job_type} {job.state} {job.progress}")
        progress.setAlignment(Qt.AlignmentFlag.AlignLeft)
        layout.addWidget(progress)

    if not jobs:
        idle = QLabel(JobState.QUEUED.value.title() + " jobs will appear here")
        layout.addWidget(idle)

    window.setCentralWidget(root)
    return window


def _format_duration(duration_sec: float | None) -> str:
    if duration_sec is None:
        return "-"
    total = max(0, round(duration_sec))
    minutes, seconds = divmod(total, 60)
    return f"{minutes}:{seconds:02d}"


def _progress_to_int(progress: str) -> int:
    return int(progress.rstrip("%"))
