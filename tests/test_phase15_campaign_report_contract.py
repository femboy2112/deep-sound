from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from types import ModuleType


def test_live_qa_report_uses_phase15_contract(tmp_path: Path) -> None:
    live_qa = _load_script("live_qa.py", "deep_sound_live_qa_contract")
    run_dir = tmp_path / "live"

    exit_code = live_qa.main(
        [
            "--fixture-mode",
            "generated",
            "--run-dir",
            str(run_dir),
            "--real-smoke-policy",
            "off",
            "--playback-smoke-policy",
            "off",
        ]
    )

    payload = json.loads(Path(live_qa.JSON_REPORT_PATH).read_text(encoding="utf-8"))
    assert exit_code == 0
    _assert_report_contract(payload)
    assert payload["dependency_policy"]["default_required_gate"] == "dependency-light"
    assert payload["inputs"]["fixture_mode"] == "generated"
    assert payload["artifacts"]["run_dir"] == str(run_dir)


def test_mir_quality_report_uses_phase15_contract(tmp_path: Path) -> None:
    mir_quality = _load_script("mir_quality_eval.py", "deep_sound_mir_quality_contract")
    report = mir_quality.build_report(fixture_mode="generated", output_dir=tmp_path / "mir")
    mir_quality.write_reports(report)

    payload = json.loads(Path(mir_quality.JSON_REPORT_PATH).read_text(encoding="utf-8"))
    _assert_report_contract(payload)
    assert payload["required_gates"]
    assert payload["optional_gates"] == []
    assert payload["artifacts"]["run_dir"] == str(tmp_path / "mir")


def _assert_report_contract(payload: dict[str, object]) -> None:
    assert {
        "schema_version",
        "command",
        "environment",
        "dependency_policy",
        "inputs",
        "artifacts",
        "required_gates",
        "optional_gates",
        "known_skips",
        "follow_up_items",
    } <= set(payload)
    assert payload["schema_version"] == "phase15-report-v1"
    assert isinstance(payload["command"], list)
    assert isinstance(payload["environment"], dict)


def _load_script(filename: str, module_name: str) -> ModuleType:
    path = Path(__file__).resolve().parents[1] / "scripts" / filename
    spec = importlib.util.spec_from_file_location(module_name, path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module
