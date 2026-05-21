from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from types import ModuleType


def test_live_qa_generated_fixture_report(tmp_path: Path) -> None:
    live_qa = _load_live_qa_module()
    run_dir = tmp_path / "live-qa-run"

    exit_code = live_qa.main(["--fixture-mode", "generated", "--run-dir", str(run_dir)])

    assert exit_code == 0
    json_report = Path(live_qa.JSON_REPORT_PATH)
    markdown_report = Path(live_qa.MD_REPORT_PATH)
    assert json_report.is_file()
    assert markdown_report.is_file()

    payload = json.loads(json_report.read_text(encoding="utf-8"))
    assert payload["overall"] == "pass"
    assert payload["fixture_mode"] == "generated"
    assert payload["run_dir"] == str(run_dir)
    assert {gate["name"] for gate in payload["required_gates"]} == {
        "import",
        "analysis",
        "index",
        "search",
        "waveform",
        "clip",
        "feedback",
        "artifact_safety",
    }
    assert all(gate["status"] == "passed" for gate in payload["required_gates"])
    assert {gate["name"]: gate["status"] for gate in payload["optional_gates"]} == {
        "pyside_smoke": "skipped_optional",
        "real_source_smoke": "skipped_optional",
    }
    assert "## Optional Gates" in markdown_report.read_text(encoding="utf-8")


def test_live_qa_requested_demucs_without_fixture_is_optional_skip(tmp_path: Path) -> None:
    live_qa = _load_live_qa_module()
    run_dir = tmp_path / "live-qa-run"

    exit_code = live_qa.main(
        ["--fixture-mode", "generated", "--run-dir", str(run_dir), "--run-demucs-smoke"]
    )

    assert exit_code == 0
    payload = json.loads(Path(live_qa.JSON_REPORT_PATH).read_text(encoding="utf-8"))
    optional = {gate["name"]: gate for gate in payload["optional_gates"]}
    assert optional["real_source_smoke"]["status"] == "skipped_optional"
    assert "--demucs-audio" in optional["real_source_smoke"]["summary"]


def _load_live_qa_module() -> ModuleType:
    path = Path(__file__).resolve().parents[1] / "scripts" / "live_qa.py"
    spec = importlib.util.spec_from_file_location("deep_sound_live_qa_script", path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module
