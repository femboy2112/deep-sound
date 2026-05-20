from __future__ import annotations

from pathlib import Path

from deep_sound.services.library_analysis_service import AnalysisProfile
from deep_sound.ui.library_workflow import (
    AnalyzeIntentDTO,
    ImportIntentDTO,
    IndexIntentDTO,
    SearchIntentDTO,
)
from deep_sound.ui.main_window import MainWindowActionBinder, main_window_action_map


class FakeController:
    def __init__(self) -> None:
        self.imports: list[ImportIntentDTO] = []
        self.analyzes: list[AnalyzeIntentDTO] = []
        self.indexes: list[IndexIntentDTO] = []
        self.searches: list[SearchIntentDTO] = []
        self.snapshot_count = 0

    def import_paths(self, intent: ImportIntentDTO) -> str:
        self.imports.append(intent)
        return "imported"

    def analyze(self, intent: AnalyzeIntentDTO) -> str:
        self.analyzes.append(intent)
        return "analyzed"

    def build_index(self, intent: IndexIntentDTO) -> str:
        self.indexes.append(intent)
        return "indexed"

    def search(self, intent: SearchIntentDTO) -> str:
        self.searches.append(intent)
        return "searched"

    def snapshot(self) -> str:
        self.snapshot_count += 1
        return "snapshot"


def test_main_window_action_map_includes_import_intent(tmp_path: Path) -> None:
    wav_path = tmp_path / "song.wav"

    actions = main_window_action_map(
        active_profile=AnalysisProfile.SEARCHABLE,
        import_paths=(wav_path,),
        recursive_import=False,
        selected_track_id="track-1",
        search_mode="rhythm",
    )

    assert actions.import_intent == ImportIntentDTO(
        paths=(wav_path,),
        recursive=False,
    )
    assert actions.analyze_intent.profile is AnalysisProfile.SEARCHABLE
    assert actions.index_intent.profile is AnalysisProfile.SEARCHABLE
    assert actions.refresh_action == "refresh_library_state"
    assert actions.selected_track_search == SearchIntentDTO(
        query_id="track-1",
        mode="rhythm",
    )


def test_main_window_binder_routes_import_analyze_index_refresh_and_search(
    tmp_path: Path,
) -> None:
    controller = FakeController()
    binder = MainWindowActionBinder(
        controller=controller,
        active_profile=AnalysisProfile.SOURCE_AWARE,
    )

    file_path = tmp_path / "one.wav"
    folder_path = tmp_path / "library"

    assert binder.import_files((file_path,)) == "imported"
    assert binder.import_folder(folder_path) == "imported"
    assert binder.analyze_library() == "analyzed"
    assert binder.build_index() == "indexed"
    assert binder.refresh() == "snapshot"
    assert binder.search_selected() is None

    binder.set_selected_track("track-1")
    assert binder.search_selected() == "searched"

    assert controller.imports == [
        ImportIntentDTO(paths=(file_path,), recursive=False),
        ImportIntentDTO(paths=(folder_path,), recursive=True),
    ]
    assert controller.analyzes == [AnalyzeIntentDTO(profile=AnalysisProfile.SOURCE_AWARE)]
    assert controller.indexes == [IndexIntentDTO(profile=AnalysisProfile.SOURCE_AWARE)]
    assert controller.snapshot_count == 1
    assert controller.searches == [SearchIntentDTO(query_id="track-1", mode="weighted")]


def test_main_window_binder_ignores_empty_imports() -> None:
    controller = FakeController()
    binder = MainWindowActionBinder(
        controller=controller,
        active_profile=AnalysisProfile.SEARCHABLE,
    )

    assert binder.import_files(()) is None
    assert binder.import_folder(None) is None

    assert controller.imports == []
