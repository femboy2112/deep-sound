from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from types import ModuleType


def test_toolset_review_ingests_repo_dive_detectors(tmp_path: Path) -> None:
    toolset_review = _load_toolset_review_module()
    report_path = tmp_path / "repo_dive_report.json"
    report_path.write_text(
        json.dumps(
            {
                "failure_modes": [
                    {
                        "detector_id": "optional_dependency_drift",
                        "status": "watch",
                        "severity": "medium",
                        "evidence": "Demucs optional gate changed recently.",
                        "prevention": "Run dependency gate auditor before touching pyproject.toml.",
                    },
                    {
                        "detector_id": "ignored_control_plane",
                        "status": "pass",
                        "severity": "info",
                        "evidence": "ok",
                        "prevention": "ok",
                    },
                ],
                "recommendations": [
                    {
                        "kind": "skill",
                        "priority": "medium",
                        "title": "Use history-dive before broad harness or phase-closeout passes",
                        "evidence": "history-backed",
                        "suggested_artifact": ".codex/skills/history-dive/SKILL.md",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    recommendations = toolset_review.collect_repo_dive_recommendations(report_path)

    assert [rec.kind for rec in recommendations] == [
        "repo-dive-detector",
        "repo-dive-skill",
    ]
    assert recommendations[0].title == "Follow up repo-dive detector: optional_dependency_drift"
    assert "dependency gate auditor" in recommendations[0].proposal


def test_toolset_review_reports_malformed_repo_dive_json(tmp_path: Path) -> None:
    toolset_review = _load_toolset_review_module()
    report_path = tmp_path / "repo_dive_report.json"
    report_path.write_text("{not-json", encoding="utf-8")

    recommendations = toolset_review.collect_repo_dive_recommendations(report_path)

    assert len(recommendations) == 1
    assert recommendations[0].kind == "repo-dive-ingestion"
    assert recommendations[0].priority == "medium"


def _load_toolset_review_module() -> ModuleType:
    path = Path(__file__).resolve().parents[1] / "scripts" / "toolset_review.py"
    spec = importlib.util.spec_from_file_location("deep_sound_toolset_review", path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module
