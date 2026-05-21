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
    PauseIntentDTO,
    PlayIntentDTO,
    SearchIntentDTO,
    SeekIntentDTO,
    StopIntentDTO,
)


class MainWindowController(Protocol):
    def import_paths(self, intent: ImportIntentDTO) -> object: ...

    def analyze(self, intent: AnalyzeIntentDTO) -> object: ...

    def build_index(self, intent: IndexIntentDTO) -> object: ...

    def search(self, intent: SearchIntentDTO) -> object: ...

    def play(self, intent: PlayIntentDTO) -> object: ...

    def pause(self, intent: PauseIntentDTO) -> object: ...

    def seek(self, intent: SeekIntentDTO) -> object: ...

    def stop(self, intent: StopIntentDTO) -> object: ...

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


@dataclass(frozen=True, slots=True)
class UsabilityActionState:
    action_id: str
    label: str
    enabled: bool
    reason: str = ""


@dataclass(frozen=True, slots=True)
class MainWindowUsabilityState:
    library_empty_state: str
    queue_empty_state: str
    result_empty_state: str
    waveform_empty_state: str
    source_graph_empty_state: str
    playback_status_text: str
    actions: tuple[UsabilityActionState, ...]
    error_states: tuple[str, ...] = ()


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


def main_window_usability_state(
    *,
    track_count: int,
    job_count: int = 0,
    result_count: int = 0,
    selected_track_id: str | None = None,
    selected_source_id: str | None = None,
    selected_result_id: str | None = None,
    failed_job_count: int = 0,
    stale_index_warning_count: int = 0,
    playback_error: str | None = None,
) -> MainWindowUsabilityState:
    has_tracks = track_count > 0
    has_selection = selected_track_id is not None
    error_states: list[str] = []
    if failed_job_count:
        error_states.append(f"{failed_job_count} failed job(s) need review.")
    if stale_index_warning_count:
        error_states.append("Search indexes may be stale; scan fallback remains available.")
    if playback_error:
        error_states.append(f"Playback unavailable: {playback_error}")
    actions = (
        UsabilityActionState(
            "analyze_library",
            "Analyze",
            has_tracks,
            "" if has_tracks else "Import tracks before analysis.",
        ),
        UsabilityActionState(
            "build_index",
            "Reindex",
            has_tracks,
            "" if has_tracks else "Import and analyze tracks before indexing.",
        ),
        UsabilityActionState(
            "search_selected",
            "Search Selected",
            has_selection,
            "" if has_selection else "Select a track before searching.",
        ),
        UsabilityActionState(
            "play_selected",
            "Play",
            has_selection,
            "" if has_selection else "Select a track before playback.",
        ),
        UsabilityActionState(
            "source_search",
            "Search Source",
            selected_source_id is not None,
            "" if selected_source_id is not None else "Select a compatible source first.",
        ),
        UsabilityActionState(
            "result_feedback",
            "Mark Relevant",
            selected_result_id is not None,
            "" if selected_result_id is not None else "Select a result before feedback.",
        ),
    )
    return MainWindowUsabilityState(
        library_empty_state="" if has_tracks else "No tracks imported.",
        queue_empty_state="" if job_count else "No queued jobs.",
        result_empty_state="" if result_count else "No search results.",
        waveform_empty_state="" if has_selection else "Select a track to inspect its waveform.",
        source_graph_empty_state="" if selected_source_id else "No source selected.",
        playback_status_text=(
            f"Playback failed: {playback_error}" if playback_error else "Playback ready."
        ),
        actions=actions,
        error_states=tuple(error_states),
    )


@dataclass(slots=True)
class MainWindowActionBinder:
    controller: MainWindowController
    active_profile: AnalysisProfile
    selected_track_id: str | None = None
    search_mode: str = "weighted"

    @property
    def can_use_selected_track_actions(self) -> bool:
        return self.selected_track_id is not None

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

    def play_selected(self, *, start_sec: float = 0.0) -> object | None:
        if self.selected_track_id is None:
            return None
        return self.controller.play(
            PlayIntentDTO(track_id=self.selected_track_id, start_sec=start_sec)
        )

    def pause_selected(self, *, position_sec: float = 0.0) -> object | None:
        if self.selected_track_id is None:
            return None
        return self.controller.pause(
            PauseIntentDTO(track_id=self.selected_track_id, position_sec=position_sec)
        )

    def seek_selected(self, position_sec: float) -> object | None:
        if self.selected_track_id is None:
            return None
        return self.controller.seek(
            SeekIntentDTO(track_id=self.selected_track_id, position_sec=position_sec)
        )

    def stop_selected(self) -> object | None:
        if self.selected_track_id is None:
            return None
        return self.controller.stop(StopIntentDTO(track_id=self.selected_track_id))


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
            QApplication,
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

    QApplication.instance() or QApplication(["deep-sound-main-window"])
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
    play_button = QPushButton("Play")
    pause_button = QPushButton("Pause")
    stop_button = QPushButton("Stop")
    for name, widget in (
        ("importFileButton", import_file_button),
        ("importFolderButton", import_folder_button),
        ("analyzeButton", analyze_button),
        ("reindexButton", reindex_button),
        ("refreshButton", refresh_button),
        ("searchSelectedButton", search_button),
        ("playButton", play_button),
        ("pauseButton", pause_button),
        ("stopButton", stop_button),
    ):
        widget.setObjectName(name)
    toolbar.addWidget(import_file_button)
    toolbar.addWidget(import_folder_button)
    toolbar.addWidget(analyze_button)
    toolbar.addWidget(reindex_button)
    toolbar.addWidget(refresh_button)
    toolbar.addWidget(search_button)
    toolbar.addWidget(play_button)
    toolbar.addWidget(pause_button)
    toolbar.addWidget(stop_button)
    filter_box = QLineEdit()
    filter_box.setObjectName("libraryFilter")
    filter_box.setPlaceholderText("Filter library")
    toolbar.addWidget(filter_box)
    layout.addLayout(toolbar)

    table = QTableWidget(0, 5)
    table.setObjectName("libraryTable")
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
    library_empty_label = QLabel("No tracks imported.")
    library_empty_label.setObjectName("libraryEmptyState")
    library_empty_label.setVisible(not tracks)
    layout.addWidget(library_empty_label)

    def set_selected_actions_enabled(enabled: bool) -> None:
        search_button.setEnabled(enabled)
        play_button.setEnabled(enabled)
        pause_button.setEnabled(enabled)
        stop_button.setEnabled(enabled)

    analyze_button.setEnabled(bool(tracks))
    reindex_button.setEnabled(bool(tracks))
    set_selected_actions_enabled(False)

    if binder is not None:

        def selected_track_id() -> str | None:
            item = table.item(table.currentRow(), 4)
            return None if item is None else item.text()

        def sync_selection() -> None:
            binder.set_selected_track(selected_track_id())
            set_selected_actions_enabled(binder.can_use_selected_track_actions)

        def import_folder() -> None:
            path = QFileDialog.getExistingDirectory(window)
            if binder.import_folder(None if not path else Path(path)) is not None:
                binder.refresh()

        def search_selected() -> None:
            sync_selection()
            if binder.search_selected() is not None:
                binder.refresh()

        def play_selected() -> None:
            sync_selection()
            if binder.play_selected() is not None:
                binder.refresh()

        def pause_selected() -> None:
            sync_selection()
            binder.pause_selected()

        def stop_selected() -> None:
            sync_selection()
            binder.stop_selected()

        table.itemSelectionChanged.connect(sync_selection)
        import_file_button.clicked.connect(
            lambda: (
                binder.import_files(
                    [Path(path) for path, _filter in [QFileDialog.getOpenFileName(window)] if path]
                ),
                binder.refresh(),
            )
        )
        import_folder_button.clicked.connect(import_folder)
        analyze_button.clicked.connect(binder.analyze_library)
        reindex_button.clicked.connect(binder.build_index)
        refresh_button.clicked.connect(binder.refresh)
        search_button.clicked.connect(search_selected)
        play_button.clicked.connect(play_selected)
        pause_button.clicked.connect(pause_selected)
        stop_button.clicked.connect(stop_selected)

    queue_label = QLabel("Analysis Queue")
    queue_label.setObjectName("queueLabel")
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
        idle.setObjectName("queueEmptyState")
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
