"""Main window and library view for the Phase 1 desktop shell."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from deep_sound.domain.track import Track
from deep_sound.infra.job_queue import JobRecord, JobState
from deep_sound.services.library_analysis_service import AnalysisProfile
from deep_sound.ui.library_workflow import (
    AnalyzeIntentDTO,
    ImportIntentDTO,
    IndexIntentDTO,
    SearchIntentDTO,
)


class MainWindowController(Protocol):
    def import_paths(self, intent: ImportIntentDTO) -> object: ...

    def analyze(self, intent: AnalyzeIntentDTO) -> object: ...

    def build_index(self, intent: IndexIntentDTO) -> object: ...

    def search(self, intent: SearchIntentDTO) -> object: ...

    def snapshot(self) -> object: ...


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
    import_intent: ImportIntentDTO | None
    analyze_intent: AnalyzeIntentDTO
    index_intent: IndexIntentDTO
    refresh_action: str
    selected_track_search: SearchIntentDTO | None = None


def main_window_action_map(
    *,
    active_profile: AnalysisProfile,
    import_paths: Sequence[Path] = (),
    recursive_import: bool = True,
    selected_track_id: str | None = None,
    search_mode: str = "weighted",
) -> MainWindowActionMap:
    return MainWindowActionMap(
        import_intent=(
            None
            if not import_paths
            else ImportIntentDTO(paths=tuple(import_paths), recursive=recursive_import)
        ),
        analyze_intent=AnalyzeIntentDTO(profile=active_profile),
        index_intent=IndexIntentDTO(profile=active_profile),
        refresh_action="refresh_library_state",
        selected_track_search=(
            None
            if selected_track_id is None
            else SearchIntentDTO(query_id=selected_track_id, mode=search_mode)
        ),
    )


@dataclass(slots=True)
class MainWindowActionBinder:
    controller: MainWindowController
    active_profile: AnalysisProfile
    selected_track_id: str | None = None
    search_mode: str = "weighted"

    def set_selected_track(self, track_id: str | None) -> None:
        self.selected_track_id = track_id

    def import_files(self, paths: Sequence[Path]) -> object | None:
        if not paths:
            return None
        return self.controller.import_paths(ImportIntentDTO(paths=tuple(paths), recursive=False))

    def import_folder(self, path: Path | None, *, recursive: bool = True) -> object | None:
        if path is None:
            return None
        return self.controller.import_paths(ImportIntentDTO(paths=(path,), recursive=recursive))

    def analyze_library(self) -> object:
        return self.controller.analyze(AnalyzeIntentDTO(profile=self.active_profile))

    def build_index(self) -> object:
        return self.controller.build_index(IndexIntentDTO(profile=self.active_profile))

    def refresh(self) -> object:
        return self.controller.snapshot()

    def search_selected(self) -> object | None:
        if self.selected_track_id is None:
            return None
        return self.controller.search(
            SearchIntentDTO(query_id=self.selected_track_id, mode=self.search_mode)
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


def create_main_window(
    tracks: Sequence[Track],
    jobs: Sequence[JobRecord] = (),
    *,
    controller: MainWindowController | None = None,
    active_profile: AnalysisProfile = AnalysisProfile.SEARCHABLE,
) -> object:
    """Create the PySide main window.

    Importing this module does not require PySide. Calling this factory does.
    """
    try:
        from PySide6.QtCore import Qt
        from PySide6.QtWidgets import (
            QAbstractItemView,
            QFileDialog,
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
    binder = (
        None
        if controller is None
        else MainWindowActionBinder(
            controller=controller,
            active_profile=active_profile,
        )
    )

    toolbar = QHBoxLayout()
    import_file_button = QPushButton("Import File")
    import_folder_button = QPushButton("Import Folder")
    analyze_button = QPushButton("Analyze")
    reindex_button = QPushButton("Reindex")
    refresh_button = QPushButton("Refresh")
    search_button = QPushButton("Search Selected")
    toolbar.addWidget(import_file_button)
    toolbar.addWidget(import_folder_button)
    toolbar.addWidget(analyze_button)
    toolbar.addWidget(reindex_button)
    toolbar.addWidget(refresh_button)
    toolbar.addWidget(search_button)
    filter_box = QLineEdit()
    filter_box.setPlaceholderText("Filter library")
    toolbar.addWidget(filter_box)
    layout.addLayout(toolbar)

    table = QTableWidget(0, 5)
    table.setHorizontalHeaderLabels(["Title", "Artist", "Duration", "Status", "Track ID"])
    table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
    table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
    table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
    table.setColumnHidden(4, True)
    for row in library_rows(tracks):
        index = table.rowCount()
        table.insertRow(index)
        for column, value in enumerate(
            [row.title, row.artist, row.duration, row.analysis_status, row.track_id]
        ):
            table.setItem(index, column, QTableWidgetItem(value))
    layout.addWidget(table)

    if binder is not None:

        def selected_track_id() -> str | None:
            item = table.item(table.currentRow(), 4)
            return None if item is None else item.text()

        def sync_selection() -> None:
            binder.set_selected_track(selected_track_id())

        def import_folder() -> None:
            path = QFileDialog.getExistingDirectory(window)
            binder.import_folder(None if not path else Path(path))

        def search_selected() -> None:
            sync_selection()
            binder.search_selected()

        table.itemSelectionChanged.connect(sync_selection)
        import_file_button.clicked.connect(
            lambda: binder.import_files(
                [Path(path) for path, _filter in [QFileDialog.getOpenFileName(window)] if path]
            )
        )
        import_folder_button.clicked.connect(import_folder)
        analyze_button.clicked.connect(binder.analyze_library)
        reindex_button.clicked.connect(binder.build_index)
        refresh_button.clicked.connect(binder.refresh)
        search_button.clicked.connect(search_selected)

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
