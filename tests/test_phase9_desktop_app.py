from __future__ import annotations

import builtins
import importlib
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

from deep_sound.services.library_analysis_service import AnalysisProfile


def test_desktop_app_module_import_does_not_import_pyside() -> None:
    sys.modules.pop("deep_sound.ui.desktop_app", None)
    real_import = builtins.__import__

    def guarded_import(name: str, *args: object, **kwargs: object) -> object:
        if name.startswith("PySide6"):
            raise AssertionError(f"PySide import attempted during module import: {name}")
        return real_import(name, *args, **kwargs)

    with patch("builtins.__import__", side_effect=guarded_import):
        importlib.import_module("deep_sound.ui.desktop_app")


def test_desktop_app_config_defaults_to_adjacent_app_data(tmp_path: Path) -> None:
    from deep_sound.ui.desktop_app import desktop_app_config

    config = desktop_app_config(
        tmp_path / "library" / "library.sqlite",
        active_profile="source_aware",
    )

    assert config.library_db_path == tmp_path / "library" / "library.sqlite"
    assert config.app_data_dir == tmp_path / "library" / "app_data"
    assert config.active_profile is AnalysisProfile.SOURCE_AWARE


def test_bootstrap_desktop_app_creates_store_app_data_and_controller(tmp_path: Path) -> None:
    from deep_sound.ui.desktop_app import bootstrap_desktop_app, desktop_app_config

    config = desktop_app_config(
        tmp_path / "database" / "library.sqlite",
        app_data_dir=tmp_path / "app_data",
        active_profile=AnalysisProfile.SEARCHABLE,
    )

    bootstrap = bootstrap_desktop_app(config)
    snapshot = bootstrap.controller.snapshot()

    assert config.library_db_path.exists()
    assert config.app_data_dir.is_dir()
    assert bootstrap.store.db_path == config.library_db_path
    assert bootstrap.controller.active_profile is AnalysisProfile.SEARCHABLE
    assert snapshot.track_count == 0
    assert snapshot.clip_count == 0


def test_create_desktop_app_window_imports_pyside_only_when_called(tmp_path: Path) -> None:
    from deep_sound.ui.desktop_app import create_desktop_app_window, desktop_app_config

    config = desktop_app_config(
        tmp_path / "library.sqlite",
        app_data_dir=tmp_path / "app_data",
    )
    real_import = builtins.__import__

    def missing_pyside_import(name: str, *args: object, **kwargs: object) -> object:
        if name.startswith("PySide6"):
            raise ImportError(name)
        return real_import(name, *args, **kwargs)

    with patch("builtins.__import__", side_effect=missing_pyside_import):
        with pytest.raises(RuntimeError, match=r"\[ui\] extra"):
            create_desktop_app_window(config)

    assert not config.library_db_path.exists()
    assert not config.app_data_dir.exists()
