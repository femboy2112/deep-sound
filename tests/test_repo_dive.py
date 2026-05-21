from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from types import ModuleType


def test_phase_and_file_plan_parsers() -> None:
    repo_dive = _load_repo_dive_module()

    assert repo_dive.read_active_phase_from_text("x\n**ACTIVE_PHASE:** 13\n") == 13
    rows = repo_dive.parse_plan_rows(
        "\n".join(
            [
                "| id | path | phase | status | depends_on |",
                "|---|---|---:|---|---|",
                "| P0-001 | src/a.py | 0 | DONE | - |",
                "| P0-002 | src/b.py | 0 | TODO | P0-001 |",
                "",
            ]
        )
    )

    assert rows == [
        {
            "id": "P0-001",
            "path": "src/a.py",
            "phase": "0",
            "status": "DONE",
            "depends_on": "-",
        },
        {
            "id": "P0-002",
            "path": "src/b.py",
            "phase": "0",
            "status": "TODO",
            "depends_on": "P0-001",
        },
    ]


def test_detector_registry_and_no_git_schema() -> None:
    repo_dive = _load_repo_dive_module()

    payload = repo_dive.collect_repo_dive(repo_dive.REPO_ROOT, use_git=False)

    assert payload["schema_version"] == 1
    assert set(payload) == {
        "schema_version",
        "timestamp",
        "repo_state",
        "history",
        "hotspots",
        "signals",
        "failure_modes",
        "recommendations",
    }
    assert payload["history"]["available"] is False
    assert {mode["detector_id"] for mode in payload["failure_modes"]} == {
        detector.detector_id for detector in repo_dive.DETECTORS
    }


def test_unanchored_build_ignore_regression_detector(tmp_path: Path) -> None:
    repo_dive = _load_repo_dive_module()
    (tmp_path / ".gitignore").write_text("build/\ndist/\n", encoding="utf-8")
    context = _context(repo_dive, tmp_path)

    mode = repo_dive.detector_ignored_control_plane(context)

    assert mode["status"] == "fail"
    assert mode["severity"] == "high"
    assert "docs/build" in mode["evidence"]


def test_demucs_optional_dependency_regression_detector(tmp_path: Path) -> None:
    repo_dive = _load_repo_dive_module()
    (tmp_path / "pyproject.toml").write_text(
        """
[project]
optional-dependencies = { demucs = ["demucs>=4.0", "torch>=2.0", "torchaudio>=2.0"] }

[tool.uv]
sources = {}
""",
        encoding="utf-8",
    )
    (tmp_path / "uv.lock").write_text('name = "nvidia-cublas"\n', encoding="utf-8")
    context = _context(repo_dive, tmp_path)

    mode = repo_dive.detector_optional_dependency_drift(context)

    assert mode["status"] == "fail"
    assert "torchcodec" in mode["evidence"]
    assert "nvidia-cublas" in mode["evidence"]


def test_demucs_two_stems_and_live_policy_regression_detector(tmp_path: Path) -> None:
    repo_dive = _load_repo_dive_module()
    provider = tmp_path / "src" / "deep_sound" / "infra" / "separation" / "providers.py"
    provider.parent.mkdir(parents=True)
    provider.write_text('command = ["demucs", "--two-stems", "none"]\n', encoding="utf-8")
    script = tmp_path / "scripts" / "live_qa.py"
    script.parent.mkdir()
    script.write_text("--real-smoke-policy\n", encoding="utf-8")
    context = _context(repo_dive, tmp_path)

    mode = repo_dive.detector_real_smoke_contract(context)

    assert mode["status"] == "fail"
    assert "--two-stems" in mode["evidence"]
    assert "--playback-smoke-policy" in mode["evidence"]


def test_markdown_rendering_and_json_report_write(tmp_path: Path) -> None:
    repo_dive = _load_repo_dive_module()
    payload = repo_dive.collect_repo_dive(repo_dive.REPO_ROOT, use_git=False)

    markdown = repo_dive.render_markdown(payload)
    repo_dive.write_reports(payload, tmp_path, write_json=True, write_markdown=True)

    assert "## Failure Modes" in markdown
    written = json.loads((tmp_path / repo_dive.JSON_REPORT_NAME).read_text(encoding="utf-8"))
    assert written["schema_version"] == 1
    assert (tmp_path / repo_dive.MARKDOWN_REPORT_NAME).is_file()


def _load_repo_dive_module() -> ModuleType:
    path = Path(__file__).resolve().parents[1] / "scripts" / "repo_dive.py"
    spec = importlib.util.spec_from_file_location("deep_sound_repo_dive", path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _context(repo_dive: ModuleType, root: Path) -> object:
    return repo_dive.DiveContext(
        repo_root=root,
        repo_state={},
        history={"commit_file_stats": [], "fix_stabilization_commits": []},
        signals={},
    )
