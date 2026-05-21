from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from types import ModuleType


def test_live_qa_writes_manual_usability_task_results(tmp_path: Path) -> None:
    live_qa = _load_live_qa_module()
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
    tasks = payload["manual_usability_tasks"]
    assert exit_code == 0
    assert {task["task_id"] for task in tasks} >= {
        "U-IMPORT",
        "U-ANALYZE-INDEX",
        "U-SEARCH",
        "U-WAVEFORM-CLIP",
        "U-FEEDBACK",
    }
    assert all(
        task["status"] in {"passed", "failed", "blocked", "skipped_optional"} for task in tasks
    )
    assert {
        "task_id",
        "action",
        "expected_result",
        "observed_result",
        "status",
        "dependency_mode",
        "evidence_paths",
        "follow_up_recommendation",
    } <= set(tasks[0])
    markdown = Path(live_qa.MD_REPORT_PATH).read_text(encoding="utf-8")
    assert "## Manual Usability Tasks" in markdown


def _load_live_qa_module() -> ModuleType:
    path = Path(__file__).resolve().parents[1] / "scripts" / "live_qa.py"
    spec = importlib.util.spec_from_file_location("deep_sound_live_qa_manual", path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module
