"""Import-safe desktop session settings for Phase 8 workflows."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path

from deep_sound.services.library_analysis_service import AnalysisProfile
from deep_sound.services.similarity_service import SearchMode

SESSION_CONFIG_VERSION = "desktop-session-v1"


@dataclass(frozen=True, slots=True)
class DesktopSessionConfig:
    library_db_path: Path
    app_data_dir: Path
    active_profile: AnalysisProfile = AnalysisProfile.SEARCHABLE
    last_query_owner_id: str | None = None
    last_query_mode: SearchMode = SearchMode.WEIGHTED
    version: str = SESSION_CONFIG_VERSION


def load_session_config(path: Path) -> DesktopSessionConfig:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("Desktop session config must be a JSON object")
    return DesktopSessionConfig(
        library_db_path=Path(_required_str(payload, "library_db_path")),
        app_data_dir=Path(_required_str(payload, "app_data_dir")),
        active_profile=AnalysisProfile(str(payload.get("active_profile", "searchable"))),
        last_query_owner_id=_optional_str(payload.get("last_query_owner_id")),
        last_query_mode=SearchMode(str(payload.get("last_query_mode", "weighted"))),
        version=str(payload.get("version", SESSION_CONFIG_VERSION)),
    )


def save_session_config(config: DesktopSessionConfig, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = asdict(config)
    payload["library_db_path"] = str(config.library_db_path)
    payload["app_data_dir"] = str(config.app_data_dir)
    payload["active_profile"] = config.active_profile.value
    payload["last_query_mode"] = config.last_query_mode.value
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _required_str(payload: dict[str, object], key: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value:
        raise ValueError(f"Desktop session config requires {key}")
    return value


def _optional_str(value: object) -> str | None:
    if value is None:
        return None
    return str(value)
