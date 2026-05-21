from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from types import ModuleType, SimpleNamespace


def test_live_qa_playback_off_policy_records_skip(tmp_path: Path) -> None:
    live_qa = _load_live_qa_module()
    run_dir = tmp_path / "live"

    exit_code = live_qa.main(
        [
            "--fixture-mode",
            "generated",
            "--run-dir",
            str(run_dir),
            "--run-playback-smoke",
            "--playback-smoke-policy",
            "off",
            "--real-smoke-policy",
            "off",
        ]
    )

    payload = json.loads(Path(live_qa.JSON_REPORT_PATH).read_text(encoding="utf-8"))
    playback = _gate(payload, "playback_smoke")
    assert exit_code == 0
    assert playback["status"] == "skipped_optional"


def test_live_qa_playback_required_fails_without_sounddevice(
    monkeypatch: object,
    tmp_path: Path,
) -> None:
    live_qa = _load_live_qa_module()
    monkeypatch.setattr(live_qa, "find_spec", lambda name: None if name == "sounddevice" else True)

    exit_code = live_qa.main(
        [
            "--fixture-mode",
            "generated",
            "--run-dir",
            str(tmp_path / "live"),
            "--playback-smoke-policy",
            "required",
            "--real-smoke-policy",
            "off",
        ]
    )

    payload = json.loads(Path(live_qa.JSON_REPORT_PATH).read_text(encoding="utf-8"))
    playback = _gate(payload, "playback_smoke")
    assert exit_code == 1
    assert playback["status"] == "failed"
    assert "sounddevice is not installed" in playback["summary"]


def test_live_qa_playback_auto_runs_when_output_available(
    monkeypatch: object,
    tmp_path: Path,
) -> None:
    live_qa = _load_live_qa_module()
    from deep_sound.services import playback_service

    monkeypatch.setattr(live_qa, "find_spec", lambda name: True)

    def fake_import_module(name: str) -> object:
        if name == "sounddevice":
            return SimpleNamespace(
                query_devices=lambda: [{"max_output_channels": 2}],
                play=lambda data, sample_rate, blocking=False: None,
                stop=lambda: None,
            )
        return __import__(name)

    monkeypatch.setattr(live_qa, "import_module", fake_import_module)
    monkeypatch.setattr(playback_service, "import_module", fake_import_module)

    exit_code = live_qa.main(
        [
            "--fixture-mode",
            "generated",
            "--run-dir",
            str(tmp_path / "live"),
            "--playback-smoke-policy",
            "auto",
            "--real-smoke-policy",
            "off",
        ]
    )

    payload = json.loads(Path(live_qa.JSON_REPORT_PATH).read_text(encoding="utf-8"))
    playback = _gate(payload, "playback_smoke")
    assert exit_code == 0
    assert playback["status"] == "passed"
    assert playback["details"]["fixture_unchanged"] is True


def _load_live_qa_module() -> ModuleType:
    path = Path(__file__).resolve().parents[1] / "scripts" / "live_qa.py"
    spec = importlib.util.spec_from_file_location("deep_sound_live_qa_phase13", path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _gate(payload: dict[str, object], name: str) -> dict[str, object]:
    gates = payload["optional_gates"]
    assert isinstance(gates, list)
    matches = [gate for gate in gates if gate["name"] == name]
    assert len(matches) == 1
    return matches[0]
