"""Shared report metadata helpers for generated beta evidence."""

from __future__ import annotations

import os
import platform
from pathlib import Path
from typing import Any

SCHEMA_VERSION = "phase15-report-v1"


def command_metadata(argv: list[str] | tuple[str, ...]) -> list[str]:
    return [str(part) for part in argv]


def runtime_environment(repo_root: Path) -> dict[str, str | bool]:
    return {
        "python_version": platform.python_version(),
        "platform": platform.platform(),
        "cwd": str(repo_root),
        "pyside6_available": _module_available("PySide6"),
        "sounddevice_available": _module_available("sounddevice"),
        "demucs_on_path": _executable_available("demucs"),
    }


def dependency_policy(
    *,
    real_smoke_policy: str = "off",
    playback_smoke_policy: str = "off",
) -> dict[str, str | bool]:
    return {
        "default_required_gate": "dependency-light",
        "requires_pyside": False,
        "requires_demucs": False,
        "requires_playback_device": False,
        "requires_faiss": False,
        "requires_gpu": False,
        "requires_mir_extra": False,
        "real_smoke_policy": real_smoke_policy,
        "playback_smoke_policy": playback_smoke_policy,
    }


def known_skips_from_gates(gates: list[Any]) -> list[dict[str, str]]:
    skips: list[dict[str, str]] = []
    for gate in gates:
        status = _field(gate, "status")
        if status == "skipped_optional":
            skips.append(
                {
                    "name": str(_field(gate, "name")),
                    "reason": str(_field(gate, "summary")),
                }
            )
    return skips


def follow_up_items_from_gates(gates: list[Any]) -> list[dict[str, str]]:
    items: list[dict[str, str]] = []
    for gate in gates:
        status = _field(gate, "status")
        if status in {"failed", "blocked", "skipped_optional"}:
            items.append(
                {
                    "source": str(_field(gate, "name")),
                    "status": str(status),
                    "recommendation": str(_field(gate, "summary")),
                }
            )
    return items


def _field(item: Any, name: str) -> object:
    if isinstance(item, dict):
        return item.get(name, "")
    return getattr(item, name, "")


def _module_available(name: str) -> bool:
    try:
        __import__(name)
    except Exception:
        return False
    return True


def _executable_available(name: str) -> bool:
    for raw_dir in os.environ.get("PATH", "").split(os.pathsep):
        if not raw_dir:
            continue
        candidate = Path(raw_dir) / name
        if candidate.is_file() and os.access(candidate, os.X_OK):
            return True
    return False
