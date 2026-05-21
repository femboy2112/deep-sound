from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path
from types import ModuleType


def test_beta_campaign_aggregates_required_and_optional_gates(
    monkeypatch: object,
    tmp_path: Path,
) -> None:
    beta = _load_beta_campaign_module()
    monkeypatch.setattr(beta, "BUILD_DIR", tmp_path)
    monkeypatch.setattr(beta, "JSON_REPORT_PATH", tmp_path / "beta_campaign_report.json")
    monkeypatch.setattr(beta, "MD_REPORT_PATH", tmp_path / "beta_campaign_report.md")
    (tmp_path / "live_qa_report.json").write_text(
        json.dumps(
            {
                "optional_gates": [
                    {
                        "name": "pyside_smoke",
                        "status": "skipped_optional",
                        "summary": "PySide6 is not installed.",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    calls: list[list[str]] = []

    def fake_runner(argv: list[str], timeout_sec: int) -> subprocess.CompletedProcess[str]:
        calls.append(argv)
        return subprocess.CompletedProcess(argv, 0, stdout=f"ran {argv[1]}", stderr="")

    report = beta.build_report(
        fixture_mode="generated",
        real_smoke_policy="off",
        playback_smoke_policy="off",
        timeout_sec=30,
        runner=fake_runner,
    )
    beta.write_reports(report)

    assert report.overall == "passed"
    assert [gate.name for gate in report.required_gates] == [
        "verify",
        "live_qa_generated",
        "mir_quality_generated",
        "repo_dive",
        "toolset_review",
    ]
    assert any(call[:2] == ["python3", "scripts/live_qa.py"] for call in calls)
    assert report.optional_gates[0]["status"] == "skipped_optional"
    assert report.known_skips[0]["name"] == "pyside_smoke"
    payload = json.loads((tmp_path / "beta_campaign_report.json").read_text(encoding="utf-8"))
    assert payload["schema_version"] == "phase15-report-v1"
    assert (tmp_path / "beta_campaign_report.md").is_file()


def test_beta_campaign_fails_when_required_command_fails() -> None:
    beta = _load_beta_campaign_module()

    def fake_runner(argv: list[str], timeout_sec: int) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(argv, 2 if argv[1] == "scripts/verify.py" else 0)

    report = beta.build_report(
        fixture_mode="generated",
        real_smoke_policy="off",
        playback_smoke_policy="off",
        timeout_sec=30,
        runner=fake_runner,
    )

    assert report.overall == "failed"
    assert report.required_gates[0].status == "failed"
    assert report.follow_up_items[0]["source"] == "verify"


def _load_beta_campaign_module() -> ModuleType:
    path = Path(__file__).resolve().parents[1] / "scripts" / "beta_campaign.py"
    spec = importlib.util.spec_from_file_location("deep_sound_beta_campaign", path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module
