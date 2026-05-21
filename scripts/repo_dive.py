"""Read-only repository history and harness-risk audit for Deep-Sound.

The report is intentionally observational. It mines current repo state and, when
available, git history so future agents can see which failure modes already
cost the project time and which guards should remain in place.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import time
import tomllib
from collections import Counter, defaultdict
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_OUTPUT_DIR = REPO_ROOT / ".build"
JSON_REPORT_NAME = "repo_dive_report.json"
MARKDOWN_REPORT_NAME = "repo_dive_report.md"
SCHEMA_VERSION = 1

ACTIVE_PHASE_RE = re.compile(r"^\*\*ACTIVE_PHASE:\*\*\s*(\d+)\s*$", re.MULTILINE)
PLAN_ID_RE = re.compile(r"^Plan-Id:\s*(\S+)\s*$", re.MULTILINE)

SERVICE_HOTSPOTS = (
    "src/deep_sound/services/similarity_service.py",
    "src/deep_sound/services/source_service.py",
    "src/deep_sound/services/analysis_service.py",
    "src/deep_sound/services/library_analysis_service.py",
    "src/deep_sound/services/index_service.py",
    "src/deep_sound/infra/storage/sqlite_store.py",
    "src/deep_sound/ui/library_workflow.py",
    "src/deep_sound/ui/results_view.py",
    "src/deep_sound/ui/source_graph.py",
)


@dataclass(frozen=True, slots=True)
class Detector:
    detector_id: str
    description: str
    run: Callable[[DiveContext], dict[str, Any]]


@dataclass(frozen=True, slots=True)
class DiveContext:
    repo_root: Path
    repo_state: dict[str, Any]
    history: dict[str, Any]
    signals: dict[str, Any]


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.exists() else ""


def read_active_phase_from_text(text: str) -> int | None:
    match = ACTIVE_PHASE_RE.search(text)
    return int(match.group(1)) if match else None


def parse_plan_rows(text: str) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    headers: list[str] = []
    in_table = False
    for line in text.splitlines():
        if not line.startswith("|"):
            if in_table:
                headers = []
                in_table = False
            continue
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if not headers:
            headers = cells
            continue
        if all(set(cell) <= set("-: ") for cell in cells):
            in_table = True
            continue
        if in_table and len(cells) == len(headers):
            rows.append(dict(zip(headers, cells, strict=True)))
    return rows


def _git(repo_root: Path, args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=False,
        timeout=30,
    )


def _git_stdout(repo_root: Path, args: list[str]) -> str:
    proc = _git(repo_root, args)
    if proc.returncode != 0:
        return ""
    return proc.stdout.strip()


def _is_git_repo(repo_root: Path) -> bool:
    return (repo_root / ".git").exists() and _git(
        repo_root, ["rev-parse", "--is-inside-work-tree"]
    ).returncode == 0


def collect_repo_state(repo_root: Path, *, use_git: bool = True) -> dict[str, Any]:
    phase_text = read_text(repo_root / "docs" / "build" / "PHASES.md")
    rows = parse_plan_rows(read_text(repo_root / "docs" / "build" / "FILE_PLAN.md"))
    counts = Counter(row.get("status", "?") for row in rows)
    state: dict[str, Any] = {
        "branch": None,
        "head": None,
        "active_phase": read_active_phase_from_text(phase_text),
        "file_plan_counts": dict(sorted(counts.items())),
        "repair_state": {
            "brief_present": (repo_root / ".build" / "repair_brief.md").exists(),
            "attempts": _read_int(repo_root / ".build" / "repair_attempts.txt"),
        },
    }
    if use_git and _is_git_repo(repo_root):
        state["branch"] = _git_stdout(repo_root, ["branch", "--show-current"]) or None
        state["head"] = _git_stdout(repo_root, ["rev-parse", "--short", "HEAD"]) or None
    return state


def _read_int(path: Path) -> int:
    raw = read_text(path).strip()
    if not raw:
        return 0
    try:
        return int(raw)
    except ValueError:
        return 0


def collect_history(
    repo_root: Path, *, since: str | None = None, use_git: bool = True
) -> dict[str, Any]:
    if not use_git or not _is_git_repo(repo_root):
        return {
            "available": False,
            "commits": [],
            "plan_id_coverage": {"with_plan_id": 0, "without_plan_id": 0, "missing": []},
            "fix_stabilization_commits": [],
            "commit_file_stats": [],
        }

    log_args = ["log", "--date=iso-strict", "--format=%H%x1f%h%x1f%ad%x1f%s", "--name-only"]
    if since:
        log_args.insert(1, f"--since={since}")
    raw = _git_stdout(repo_root, log_args)
    commits: list[dict[str, Any]] = []
    current: dict[str, Any] | None = None
    for line in raw.splitlines():
        if "\x1f" in line:
            if current is not None:
                commits.append(current)
            full_sha, short_sha, date, subject = line.split("\x1f", maxsplit=3)
            body = _git_stdout(repo_root, ["show", "-s", "--format=%B", full_sha])
            plan_ids = PLAN_ID_RE.findall(body)
            current = {
                "sha": short_sha,
                "full_sha": full_sha,
                "date": date,
                "subject": subject,
                "plan_ids": plan_ids,
                "files": [],
            }
        elif current is not None and line.strip():
            current["files"].append(line.strip())
    if current is not None:
        commits.append(current)

    file_counts: Counter[str] = Counter()
    for commit in commits:
        file_counts.update(commit["files"])

    fix_commits = [
        {
            "sha": commit["sha"],
            "subject": commit["subject"],
            "files": commit["files"],
        }
        for commit in commits
        if _looks_like_fix_or_stabilization(commit["subject"])
    ]
    missing_plan = [
        {"sha": commit["sha"], "subject": commit["subject"]}
        for commit in commits
        if not commit["plan_ids"]
    ]
    return {
        "available": True,
        "commits": commits,
        "plan_id_coverage": {
            "with_plan_id": len(commits) - len(missing_plan),
            "without_plan_id": len(missing_plan),
            "missing": missing_plan,
        },
        "fix_stabilization_commits": fix_commits,
        "commit_file_stats": [
            {"path": path, "commit_count": count} for path, count in file_counts.most_common()
        ],
    }


def _looks_like_fix_or_stabilization(subject: str) -> bool:
    lowered = subject.lower()
    return any(
        token in lowered for token in ("fix", "stabilize", "stabilise", "harden", "smoke", "repair")
    )


def collect_hotspots(history: dict[str, Any]) -> dict[str, Any]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for stat in history.get("commit_file_stats", []):
        path = stat["path"]
        group = _subsystem_for_path(path)
        grouped[group].append(stat)
    return {
        group: sorted(stats, key=lambda item: (-item["commit_count"], item["path"]))[:10]
        for group, stats in sorted(grouped.items())
    }


def _subsystem_for_path(path: str) -> str:
    if path.startswith(("docs/build/", ".codex/", ".claude/", "scripts/")):
        return "harness_control_plane"
    if path.startswith("src/deep_sound/services/"):
        return "services"
    if path.startswith("src/deep_sound/infra/storage/"):
        return "storage"
    if path.startswith("src/deep_sound/ui/"):
        return "ui"
    if "similarity" in path or "index" in path or "search" in path:
        return "search"
    if path in {"pyproject.toml", "uv.lock"}:
        return "optional_dependencies"
    if path.startswith("tests/"):
        return "tests"
    return "other"


def collect_signals(repo_root: Path) -> dict[str, Any]:
    return {
        "verify": _read_json(repo_root / ".build" / "verify_report.json"),
        "live_qa": _read_json(repo_root / ".build" / "live_qa_report.json"),
        "toolset": _read_json(repo_root / ".build" / "toolset_review.json"),
        "repair": {
            "brief_present": (repo_root / ".build" / "repair_brief.md").exists(),
            "attempts": _read_int(repo_root / ".build" / "repair_attempts.txt"),
        },
        "manual_qa_docs": {
            "desktop_beta_manual_qa": (repo_root / "docs" / "desktop_beta_manual_qa.md").exists()
        },
    }


def _read_json(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        loaded = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {"malformed": True, "path": str(path)}
    return loaded if isinstance(loaded, dict) else {"unexpected_type": type(loaded).__name__}


def detector_ignored_control_plane(context: DiveContext) -> dict[str, Any]:
    text = read_text(context.repo_root / ".gitignore")
    problematic = []
    for line in text.splitlines():
        pattern = line.strip()
        if not pattern or pattern.startswith("#"):
            continue
        normalized = pattern.rstrip("/")
        if normalized in {"build", "dist"}:
            problematic.append(pattern)
    status = "fail" if problematic else "pass"
    return _failure_mode(
        "ignored_control_plane",
        status=status,
        severity="high" if problematic else "info",
        evidence=(
            f"Unanchored ignore patterns can hide docs/build: {problematic}"
            if problematic
            else "Build/dist ignore patterns are root-anchored; docs/build remains trackable."
        ),
        affected_paths=[".gitignore", "docs/build/"],
        prevention="Keep runtime build outputs anchored as /build/ and /dist/; regression-test unanchored patterns.",
    )


def detector_optional_dependency_drift(context: DiveContext) -> dict[str, Any]:
    pyproject_path = context.repo_root / "pyproject.toml"
    lock_text = read_text(context.repo_root / "uv.lock")
    problems: list[str] = []
    try:
        pyproject = tomllib.loads(read_text(pyproject_path))
    except tomllib.TOMLDecodeError as exc:
        problems.append(f"pyproject.toml is not valid TOML: {exc}")
        pyproject = {}
    demucs_deps = pyproject.get("project", {}).get("optional-dependencies", {}).get("demucs", [])
    uv_config = pyproject.get("tool", {}).get("uv", {})
    sources = uv_config.get("sources", {})
    if "demucs>=4.0" not in demucs_deps:
        problems.append("[demucs] no longer depends on demucs>=4.0")
    if "torchcodec>=0.12" not in demucs_deps:
        problems.append("[demucs] is missing torchcodec, which real Demucs smoke has needed")
    if sources.get("torch") != {"index": "pytorch-cpu", "extra": "demucs"}:
        problems.append(
            "torch is not pinned to the explicit pytorch-cpu index for the demucs extra"
        )
    if sources.get("torchaudio") != {"index": "pytorch-cpu", "extra": "demucs"}:
        problems.append(
            "torchaudio is not pinned to the explicit pytorch-cpu index for the demucs extra"
        )
    forbidden = _lockfile_forbidden_cuda_packages(lock_text)
    if forbidden:
        problems.append(f"uv.lock contains CUDA/GPU packages in the CPU Demucs path: {forbidden}")
    return _failure_mode(
        "optional_dependency_drift",
        status="fail" if problems else "pass",
        severity="high" if problems else "info",
        evidence="; ".join(problems)
        if problems
        else "Optional extras remain separated and Demucs CPU guards are present.",
        affected_paths=["pyproject.toml", "uv.lock"],
        prevention="Keep Demucs/PySide/playback extras opt-in and preserve the CPU Torch/Torchaudio source guards.",
    )


def _lockfile_forbidden_cuda_packages(lock_text: str) -> list[str]:
    forbidden = {
        "nvidia-cublas",
        "nvidia-cuda-cupti",
        "nvidia-cuda-nvrtc",
        "nvidia-cuda-runtime",
        "nvidia-cudnn-cu13",
        "nvidia-cufft",
        "nvidia-cufile",
        "nvidia-curand",
        "nvidia-cusolver",
        "nvidia-cusparse",
        "nvidia-cusparselt-cu13",
        "nvidia-nccl-cu13",
        "nvidia-nvjitlink",
        "nvidia-nvshmem-cu13",
        "nvidia-nvtx",
        "triton",
    }
    package_names = set(re.findall(r'^name = "([^"]+)"$', lock_text, flags=re.MULTILINE))
    return sorted(forbidden.intersection(package_names))


def detector_real_smoke_contract(context: DiveContext) -> dict[str, Any]:
    live_qa = read_text(context.repo_root / "scripts" / "live_qa.py")
    problems = []
    required_tokens = [
        "--real-smoke-policy",
        "--playback-smoke-policy",
        'choices=("auto", "required", "off")',
        "skipped_optional",
        "--run-demucs-smoke",
        "--run-pyside-smoke",
        "--run-playback-smoke",
    ]
    for token in required_tokens:
        if token not in live_qa:
            problems.append(f"missing live QA contract token: {token}")
    provider = read_text(
        context.repo_root / "src" / "deep_sound" / "infra" / "separation" / "providers.py"
    )
    if "--two-stems" in provider:
        problems.append(
            "Demucs provider still uses --two-stems; the historical real-smoke fix removed it"
        )
    return _failure_mode(
        "real_smoke_contract",
        status="fail" if problems else "pass",
        severity="high" if problems else "info",
        evidence=(
            "; ".join(problems)
            if problems
            else "Live QA keeps auto|required|off semantics and Demucs no longer uses invalid --two-stems."
        ),
        affected_paths=[
            "scripts/live_qa.py",
            "src/deep_sound/infra/separation/providers.py",
            "tests/test_phase12_live_qa_policy.py",
            "tests/test_phase13_live_qa_playback_policy.py",
        ],
        prevention="Keep optional smoke gates explicit: auto records skips, required fails missing/running gates, off records skips.",
    )


def detector_pyside_import_boundary(context: DiveContext) -> dict[str, Any]:
    violations: list[str] = []
    for path in (context.repo_root / "src").rglob("*.py"):
        rel = path.relative_to(context.repo_root).as_posix()
        text = read_text(path)
        for line_no, line in enumerate(text.splitlines(), start=1):
            stripped = line.lstrip()
            if "PySide6" not in stripped:
                continue
            if stripped.startswith(("from PySide6", "import PySide6")) and not line.startswith(
                " " * 4
            ):
                violations.append(f"{rel}:{line_no}")
    return _failure_mode(
        "pyside_import_boundary",
        status="fail" if violations else "pass",
        severity="medium" if violations else "info",
        evidence=(
            f"Top-level PySide imports found: {violations}"
            if violations
            else "PySide imports are guarded inside UI/widget factory paths."
        ),
        affected_paths=violations or ["src/deep_sound/ui/"],
        prevention="Keep PySide imports inside optional UI call paths so default verification stays dependency-light.",
    )


def detector_artifact_safety(context: DiveContext) -> dict[str, Any]:
    needed = {
        "tests/test_phase9_artifact_safety.py": ("artifact_path", "app_data"),
        "tests/test_phase10_source_artifact_safety.py": (
            "original_bytes",
            "app_data",
            "input_hash",
        ),
        "scripts/live_qa.py": ("original_hashes", "fixture_unchanged"),
    }
    missing = []
    for rel, tokens in needed.items():
        text = read_text(context.repo_root / rel)
        if not all(token in text for token in tokens):
            missing.append(rel)
    return _failure_mode(
        "artifact_safety",
        status="fail" if missing else "pass",
        severity="high" if missing else "info",
        evidence=(
            f"Artifact/original-hash safety coverage is incomplete: {missing}"
            if missing
            else "Tests and live QA cover app-data artifact placement and original fixture hash preservation."
        ),
        affected_paths=list(needed),
        prevention="Keep original audio immutable and keep all generated stems, waveforms, and clips under app_data.",
    )


def detector_confidence_language(context: DiveContext) -> dict[str, Any]:
    targets = [
        "src/deep_sound/ui/results_view.py",
        "src/deep_sound/ui/library_workflow.py",
        "src/deep_sound/ui/source_graph.py",
        "tests/test_phase8_result_cards.py",
        "tests/test_ui_models.py",
    ]
    missing = []
    for rel in targets:
        text = read_text(context.repo_root / rel)
        if "confidence" not in text.lower() and "caveat" not in text.lower():
            missing.append(rel)
    result_card_tests = read_text(context.repo_root / "tests" / "test_phase8_result_cards.py")
    if "do_not_label_scores_as_confidence" not in result_card_tests:
        missing.append("tests/test_phase8_result_cards.py::score-language-regression")
    return _failure_mode(
        "confidence_language",
        status="fail" if missing else "pass",
        severity="medium" if missing else "info",
        evidence=(
            f"Confidence/caveat language coverage is missing from {missing}"
            if missing
            else "Result/source UI paths retain caveats and score-vs-confidence regression coverage."
        ),
        affected_paths=targets,
        prevention="Keep inferred labels confidence-bounded and never describe similarity dimension scores as analyzer confidence.",
    )


def detector_stale_index_correction(context: DiveContext) -> dict[str, Any]:
    targets = [
        "src/deep_sound/services/index_service.py",
        "src/deep_sound/ui/library_workflow.py",
        "tests/test_phase9_stale_correction_regressions.py",
        "tests/test_phase7_ui_workflow.py",
    ]
    missing = []
    for rel in targets:
        text = read_text(context.repo_root / rel)
        if "stale" not in text.lower():
            missing.append(rel)
    return _failure_mode(
        "stale_index_correction",
        status="fail" if missing else "pass",
        severity="medium" if missing else "info",
        evidence=(
            f"Stale-index/correction coverage missing from {missing}"
            if missing
            else "Stale-index disclosure and correction-compatible retrieval coverage remain present."
        ),
        affected_paths=targets,
        prevention="Keep stale-index caveats visible and keep fallback scans/correction overlays regression-tested.",
    )


def detector_service_boundary_hotspot(context: DiveContext) -> dict[str, Any]:
    churn = {
        stat["path"]: stat["commit_count"]
        for stat in context.history.get("commit_file_stats", [])
        if stat["path"] in SERVICE_HOTSPOTS and stat["commit_count"] >= 3
    }
    return _failure_mode(
        "service_boundary_hotspot",
        status="watch" if churn else "pass",
        severity="medium" if churn else "info",
        evidence=(
            f"High-churn service/UI/storage files need focused review before future phases: {churn}"
            if churn
            else "No service-boundary hotspot exceeded the churn threshold in the inspected history."
        ),
        affected_paths=sorted(churn) or list(SERVICE_HOTSPOTS),
        prevention="Use focused service-boundary review before future phases touch high-churn service, storage, UI, or search files.",
    )


def detector_history_fix_followup(context: DiveContext) -> dict[str, Any]:
    fix_commits = context.history.get("fix_stabilization_commits", [])
    known = [
        commit
        for commit in fix_commits
        if any(
            token in commit["subject"].lower()
            for token in ("gitignore", "demucs", "smoke", "cpu", "playback", "harden")
        )
    ]
    return _failure_mode(
        "history_fix_followup",
        status="watch" if known else "pass",
        severity="medium" if known else "info",
        evidence=(
            "History contains fix/stabilization commits that should stay represented in tests and skills: "
            + ", ".join(f"{commit['sha']} {commit['subject']}" for commit in known)
            if known
            else "No fix/stabilization commits found in the inspected history."
        ),
        affected_paths=sorted({path for commit in known for path in commit.get("files", [])}),
        prevention="Convert each real fix into a regression detector, focused test, or role/skill reminder.",
    )


def _failure_mode(
    detector_id: str,
    *,
    status: str,
    severity: str,
    evidence: str,
    affected_paths: list[str],
    prevention: str,
) -> dict[str, Any]:
    return {
        "detector_id": detector_id,
        "status": status,
        "severity": severity,
        "evidence": evidence,
        "affected_paths": affected_paths,
        "prevention": prevention,
    }


DETECTORS: tuple[Detector, ...] = (
    Detector(
        "ignored_control_plane",
        "Detect ignore patterns that can hide docs/build.",
        detector_ignored_control_plane,
    ),
    Detector(
        "optional_dependency_drift",
        "Detect optional-extra and CPU lockfile drift.",
        detector_optional_dependency_drift,
    ),
    Detector(
        "real_smoke_contract",
        "Detect optional live-smoke policy drift.",
        detector_real_smoke_contract,
    ),
    Detector(
        "pyside_import_boundary",
        "Detect unguarded PySide imports.",
        detector_pyside_import_boundary,
    ),
    Detector(
        "artifact_safety",
        "Detect original-audio and app-data artifact safety coverage drift.",
        detector_artifact_safety,
    ),
    Detector(
        "confidence_language",
        "Detect confidence/caveat language coverage drift.",
        detector_confidence_language,
    ),
    Detector(
        "stale_index_correction",
        "Detect stale-index and correction-compatible retrieval coverage drift.",
        detector_stale_index_correction,
    ),
    Detector(
        "service_boundary_hotspot",
        "Report high-churn service-boundary hotspots.",
        detector_service_boundary_hotspot,
    ),
    Detector(
        "history_fix_followup",
        "Turn fix/stabilization commits into prevention follow-ups.",
        detector_history_fix_followup,
    ),
)


def run_detectors(
    context: DiveContext, detectors: tuple[Detector, ...] = DETECTORS
) -> list[dict[str, Any]]:
    return [detector.run(context) for detector in detectors]


def build_recommendations(
    failure_modes: list[dict[str, Any]],
    history: dict[str, Any],
    hotspots: dict[str, Any],
) -> list[dict[str, Any]]:
    recommendations: list[dict[str, Any]] = [
        {
            "kind": "skill",
            "priority": "medium",
            "title": "Use history-dive before broad harness or phase-closeout passes",
            "evidence": "repo_dive can now cluster git/build/test-history failure modes.",
            "suggested_artifact": ".codex/skills/history-dive/SKILL.md",
        },
        {
            "kind": "agent",
            "priority": "medium",
            "title": "Route optional dependency and live-smoke work through a dependency gate auditor",
            "evidence": "Demucs, PySide, playback, uv.lock, and live_qa policy drift have all been recurring risk areas.",
            "suggested_artifact": ".codex/agents/dependency-gate-auditor.md and .claude/agents/dependency-gate-auditor.md",
        },
    ]
    for mode in failure_modes:
        if mode["status"] == "fail":
            recommendations.append(
                {
                    "kind": "test",
                    "priority": mode["severity"],
                    "title": f"Repair failing detector {mode['detector_id']}",
                    "evidence": mode["evidence"],
                    "suggested_artifact": "focused regression test or harness doc update",
                }
            )
        elif mode["status"] == "watch":
            recommendations.append(
                {
                    "kind": "review",
                    "priority": mode["severity"],
                    "title": f"Review watch detector {mode['detector_id']} before related future phases",
                    "evidence": mode["evidence"],
                    "suggested_artifact": "future FILE_PLAN row or pre-implementation review checklist",
                }
            )
    if history.get("plan_id_coverage", {}).get("without_plan_id", 0):
        recommendations.append(
            {
                "kind": "docs",
                "priority": "low",
                "title": "Keep Plan-Id coverage visible for future commits",
                "evidence": f"{history['plan_id_coverage']['without_plan_id']} inspected commit(s) lack Plan-Id trailers.",
                "suggested_artifact": "commit discipline note in harness docs",
            }
        )
    if hotspots:
        recommendations.append(
            {
                "kind": "future-file-plan-row",
                "priority": "medium",
                "title": "Add focused review rows before high-churn subsystem expansions",
                "evidence": "Hotspots are grouped under repo_dive_report.json::hotspots.",
                "suggested_artifact": "future FILE_PLAN review rows for services, UI, storage, search, and optional gates",
            }
        )
    return recommendations


def collect_repo_dive(
    repo_root: Path, *, since: str | None = None, use_git: bool = True
) -> dict[str, Any]:
    repo_state = collect_repo_state(repo_root, use_git=use_git)
    history = collect_history(repo_root, since=since, use_git=use_git)
    hotspots = collect_hotspots(history)
    signals = collect_signals(repo_root)
    context = DiveContext(
        repo_root=repo_root, repo_state=repo_state, history=history, signals=signals
    )
    failure_modes = run_detectors(context)
    return {
        "schema_version": SCHEMA_VERSION,
        "timestamp": _utc_timestamp(),
        "repo_state": repo_state,
        "history": history,
        "hotspots": hotspots,
        "signals": signals,
        "failure_modes": failure_modes,
        "recommendations": build_recommendations(failure_modes, history, hotspots),
    }


def _utc_timestamp() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def render_markdown(payload: dict[str, Any]) -> str:
    state = payload["repo_state"]
    lines = [
        f"# Repo Dive Report - {payload['timestamp']}",
        "",
        "Read-only harness/history audit. Generated by `python3 scripts/repo_dive.py`.",
        "",
        "## Repo State",
        "",
        f"- Branch: `{state.get('branch') or 'unknown'}`",
        f"- Head: `{state.get('head') or 'unknown'}`",
        f"- Active phase: `{state.get('active_phase')}`",
        f"- FILE_PLAN counts: `{state.get('file_plan_counts')}`",
        f"- Repair brief present: `{state.get('repair_state', {}).get('brief_present')}`",
        "",
        "## History",
        "",
    ]
    history = payload["history"]
    if not history.get("available"):
        lines.extend(["Git history unavailable or disabled.", ""])
    else:
        lines.extend(
            [
                f"- Inspected commits: `{len(history.get('commits', []))}`",
                f"- Fix/stabilization commits: `{len(history.get('fix_stabilization_commits', []))}`",
                f"- Commits without Plan-Id trailers: `{history.get('plan_id_coverage', {}).get('without_plan_id', 0)}`",
                "",
            ]
        )

    lines.extend(["## Failure Modes", ""])
    for mode in payload["failure_modes"]:
        lines.extend(
            [
                f"- `{mode['detector_id']}` [{mode['status']}/{mode['severity']}]",
                f"  - Evidence: {mode['evidence']}",
                f"  - Prevention: {mode['prevention']}",
            ]
        )
    lines.extend(["", "## Recommendations", ""])
    for recommendation in payload["recommendations"]:
        lines.extend(
            [
                f"- **{recommendation['title']}**",
                f"  - Kind: `{recommendation['kind']}`",
                f"  - Priority: `{recommendation['priority']}`",
                f"  - Suggested artifact: `{recommendation['suggested_artifact']}`",
            ]
        )
    lines.append("")
    return "\n".join(lines)


def write_reports(
    payload: dict[str, Any], output_dir: Path, *, write_json: bool, write_markdown: bool
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    if write_json:
        (output_dir / JSON_REPORT_NAME).write_text(
            json.dumps(payload, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    if write_markdown:
        (output_dir / MARKDOWN_REPORT_NAME).write_text(render_markdown(payload), encoding="utf-8")


def strict_failures(payload: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        mode
        for mode in payload["failure_modes"]
        if mode["status"] == "fail" and mode["severity"] in {"high", "critical"}
    ]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--since", help="Git revision/date window passed to git log --since")
    parser.add_argument(
        "--strict", action="store_true", help="Fail on high-severity failing detectors"
    )
    parser.add_argument("--json-only", action="store_true", help="Write only the JSON report")
    parser.add_argument(
        "--markdown-only", action="store_true", help="Write only the Markdown report"
    )
    parser.add_argument("--no-git", action="store_true", help="Skip git history collection")
    args = parser.parse_args(argv)

    if args.json_only and args.markdown_only:
        parser.error("--json-only and --markdown-only are mutually exclusive")

    payload = collect_repo_dive(REPO_ROOT, since=args.since, use_git=not args.no_git)
    write_reports(
        payload,
        Path(args.output_dir),
        write_json=not args.markdown_only,
        write_markdown=not args.json_only,
    )
    failure_count = len(strict_failures(payload))
    print(
        f"repo dive: {len(payload['failure_modes'])} detector(s), {failure_count} strict failure(s)"
    )
    if not args.markdown_only:
        print(f"json: {Path(args.output_dir) / JSON_REPORT_NAME}")
    if not args.json_only:
        print(f"markdown: {Path(args.output_dir) / MARKDOWN_REPORT_NAME}")
    return 1 if args.strict and failure_count else 0


if __name__ == "__main__":
    sys.exit(main())
