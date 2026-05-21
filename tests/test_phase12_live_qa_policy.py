from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from types import ModuleType


def test_live_qa_auto_policy_skips_absent_real_smoke_dependencies(
    tmp_path: Path,
) -> None:
    live_qa = _load_live_qa_module()
    run_dir = tmp_path / "live-qa-run"

    exit_code = live_qa.main(
        ["--fixture-mode", "generated", "--run-dir", str(run_dir), "--real-smoke-policy", "auto"]
    )

    assert exit_code == 0
    payload = json.loads(Path(live_qa.JSON_REPORT_PATH).read_text(encoding="utf-8"))
    assert payload["overall"] == "pass"
    optional = {gate["name"]: gate for gate in payload["optional_gates"]}
    assert optional["pyside_smoke"]["status"] in {"passed", "skipped_optional"}
    assert optional["real_source_smoke"]["status"] in {"passed", "skipped_optional"}


def test_live_qa_required_policy_fails_missing_demucs(
    tmp_path: Path,
) -> None:
    live_qa = _load_live_qa_module()
    run_dir = tmp_path / "live-qa-run"

    exit_code = live_qa.main(
        [
            "--fixture-mode",
            "generated",
            "--run-dir",
            str(run_dir),
            "--real-smoke-policy",
            "required",
            "--demucs-executable",
            str(tmp_path / "missing-demucs"),
        ]
    )

    assert exit_code == 1
    payload = json.loads(Path(live_qa.JSON_REPORT_PATH).read_text(encoding="utf-8"))
    optional = {gate["name"]: gate for gate in payload["optional_gates"]}
    assert optional["real_source_smoke"]["status"] == "failed"
    assert "required" in optional["real_source_smoke"]["summary"]


def test_live_qa_off_policy_skips_requested_real_smoke(
    tmp_path: Path,
) -> None:
    live_qa = _load_live_qa_module()
    run_dir = tmp_path / "live-qa-run"

    exit_code = live_qa.main(
        [
            "--fixture-mode",
            "generated",
            "--run-dir",
            str(run_dir),
            "--real-smoke-policy",
            "off",
            "--run-pyside-smoke",
            "--run-demucs-smoke",
        ]
    )

    assert exit_code == 0
    payload = json.loads(Path(live_qa.JSON_REPORT_PATH).read_text(encoding="utf-8"))
    assert {gate["name"]: gate["status"] for gate in payload["optional_gates"]} == {
        "pyside_smoke": "skipped_optional",
        "real_source_smoke": "skipped_optional",
    }


def _load_live_qa_module() -> ModuleType:
    path = Path(__file__).resolve().parents[1] / "scripts" / "live_qa.py"
    spec = importlib.util.spec_from_file_location("deep_sound_live_qa_phase12", path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module
