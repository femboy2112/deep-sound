"""Import-safe desktop application bootstrap helpers for Phase 9."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from deep_sound.infra.storage.sqlite_store import SqliteStore
from deep_sound.services.library_analysis_service import AnalysisProfile
from deep_sound.ui.library_workflow import DesktopWorkflowController


@dataclass(frozen=True, slots=True)
class DesktopAppConfig:
    library_db_path: Path
    app_data_dir: Path
    active_profile: AnalysisProfile = AnalysisProfile.SEARCHABLE


@dataclass(frozen=True, slots=True)
class DesktopAppBootstrap:
    config: DesktopAppConfig
    store: SqliteStore
    controller: DesktopWorkflowController


@dataclass(frozen=True, slots=True)
class DesktopAppWindow:
    app: object
    window: object
    bootstrap: DesktopAppBootstrap


def desktop_app_config(
    library_db_path: Path,
    *,
    app_data_dir: Path | None = None,
    active_profile: AnalysisProfile | str = AnalysisProfile.SEARCHABLE,
) -> DesktopAppConfig:
    db_path = library_db_path.expanduser()
    resolved_app_data_dir = (
        app_data_dir.expanduser() if app_data_dir is not None else db_path.parent / "app_data"
    )
    return DesktopAppConfig(
        library_db_path=db_path,
        app_data_dir=resolved_app_data_dir,
        active_profile=AnalysisProfile(active_profile),
    )


def bootstrap_desktop_app(config: DesktopAppConfig) -> DesktopAppBootstrap:
    config.library_db_path.parent.mkdir(parents=True, exist_ok=True)
    config.app_data_dir.mkdir(parents=True, exist_ok=True)
    store = SqliteStore(config.library_db_path)
    store.init_schema()
    controller = DesktopWorkflowController(
        store,
        app_data_dir=config.app_data_dir,
        active_profile=config.active_profile,
    )
    return DesktopAppBootstrap(config=config, store=store, controller=controller)


def create_desktop_app_window(
    config: DesktopAppConfig,
    *,
    argv: Sequence[str] = (),
) -> DesktopAppWindow:
    """Create a PySide application and main window around a desktop controller.

    Importing this module does not require PySide. Calling this factory does.
    """

    try:
        from PySide6.QtWidgets import QApplication
    except ImportError as exc:  # pragma: no cover - exercised only with optional extra absent.
        raise RuntimeError(
            "Install deep-sound with the [ui] extra to create the desktop app window."
        ) from exc

    from deep_sound.ui.main_window import create_main_window

    app = QApplication.instance() or QApplication(list(argv))
    bootstrap = bootstrap_desktop_app(config)
    window = create_main_window(
        bootstrap.store.list_tracks(),
        controller=bootstrap.controller,
        active_profile=config.active_profile,
    )
    return DesktopAppWindow(app=app, window=window, bootstrap=bootstrap)
