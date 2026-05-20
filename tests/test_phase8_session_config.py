from __future__ import annotations

from pathlib import Path

from deep_sound.services.library_analysis_service import AnalysisProfile
from deep_sound.services.similarity_service import SearchMode
from deep_sound.ui.session_config import (
    DesktopSessionConfig,
    load_session_config,
    save_session_config,
)


def test_desktop_session_config_round_trip(tmp_path: Path) -> None:
    config = DesktopSessionConfig(
        library_db_path=tmp_path / "library.sqlite",
        app_data_dir=tmp_path / "app_data",
        active_profile=AnalysisProfile.SOURCE_AWARE,
        last_query_owner_id="track-1",
        last_query_mode=SearchMode.ADVANCED,
    )
    path = tmp_path / "settings.json"

    save_session_config(config, path)
    loaded = load_session_config(path)

    assert loaded == config
