"""Run the Phase 15 beta testing and usability evidence campaign."""
# ruff: noqa: E402

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from collections.abc import Callable
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
SRC_ROOT = REPO_ROOT / "src"
SCRIPTS_ROOT = REPO_ROOT / "scripts"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))

from report_contracts import (
    SCHEMA_VERSION,
    command_metadata,
    dependency_policy,
    follow_up_items_from_gates,
    known_skips_from_gates,
    runtime_environment,
)

BUILD_DIR = REPO_ROOT / ".build"
JSON_REPORT_PATH = BUILD_DIR / "beta_campaign_report.json"
MD_REPORT_PATH = BUILD_DIR / "beta_campaign_report.md"


@dataclass(frozen=True, slots=True)
class CampaignGate:
    name: str
    status: str
    command: list[str]
    optional: bool = False
    exit_code: int = 0
    summary: str = ""
    artifacts: list[str] = field(default_factory=list)
    stdout_tail: str = ""
    stderr_tail: str = ""


@dataclass(frozen=True, slots=True)
class CampaignReport:
    schema_version: str
    command: list[str]
    environment: dict[str, Any]
    dependency_policy: dict[str, Any]
    inputs: dict[str, Any]
    artifacts: dict[str, str]
    timestamp: str
    overall: str
    required_gates: list[CampaignGate]
    optional_gates: list[dict[str, Any]]
    known_skips: list[dict[str, str]]
    follow_up_items: list[dict[str, str]]


Runner = Callable[[list[str], int], subprocess.CompletedProcess[str]]


def _utc_timestamp() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def run_command(argv: list[str], timeout_sec: int) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env.setdefault("UV_CACHE_DIR", "/tmp/uv-cache")
    env.setdefault("QT_QPA_PLATFORM", "offscreen")
    return subprocess.run(
        argv,
        cwd=REPO_ROOT,
        env=env,
        capture_output=True,
        text=True,
        timeout=timeout_sec,
    )


def build_report(
    *,
    fixture_mode: str,
    real_smoke_policy: str,
    playback_smoke_policy: str,
    timeout_sec: int,
    runner: Runner = run_command,
    command: list[str] | None = None,
) -> CampaignReport:
    BUILD_DIR.mkdir(parents=True, exist_ok=True)
    required_specs = [
        (
            "verify",
            ["python3", "scripts/verify.py"],
            [".build/verify_report.json"],
        ),
        (
            "live_qa_generated",
            [
                "python3",
                "scripts/live_qa.py",
                "--fixture-mode",
                fixture_mode,
                "--real-smoke-policy",
                real_smoke_policy,
                "--playback-smoke-policy",
                playback_smoke_policy,
            ],
            [".build/live_qa_report.json", ".build/live_qa_report.md"],
        ),
        (
            "mir_quality_generated",
            [
                "python3",
                "scripts/mir_quality_eval.py",
                "--fixture-mode",
                fixture_mode,
                "--strict",
            ],
            [".build/mir_quality_report.json", ".build/mir_quality_report.md"],
        ),
        (
            "repo_dive",
            ["python3", "scripts/repo_dive.py", "--strict"],
            [".build/repo_dive_report.json", ".build/repo_dive_report.md"],
        ),
        (
            "toolset_review",
            ["python3", "scripts/toolset_review.py"],
            [".build/toolset_review.json", ".build/toolset_review.md"],
        ),
    ]
    required_gates: list[CampaignGate] = []
    for name, argv, artifacts in required_specs:
        proc = runner(argv, timeout_sec)
        required_gates.append(
            CampaignGate(
                name=name,
                status="passed" if proc.returncode == 0 else "failed",
                command=argv,
                exit_code=proc.returncode,
                summary=f"{name} exited {proc.returncode}.",
                artifacts=artifacts,
                stdout_tail=_tail(proc.stdout),
                stderr_tail=_tail(proc.stderr),
            )
        )

    optional_gates = _load_live_optional_gates()
    all_gate_like: list[Any] = [*required_gates, *optional_gates]
    overall = "passed" if all(gate.status == "passed" for gate in required_gates) else "failed"
    report = CampaignReport(
        schema_version=SCHEMA_VERSION,
        command=command_metadata(
            command
            or [
                "python3",
                "scripts/beta_campaign.py",
                "--fixture-mode",
                fixture_mode,
                "--real-smoke-policy",
                real_smoke_policy,
                "--playback-smoke-policy",
                playback_smoke_policy,
            ]
        ),
        environment=runtime_environment(REPO_ROOT),
        dependency_policy=dependency_policy(
            real_smoke_policy=real_smoke_policy,
            playback_smoke_policy=playback_smoke_policy,
        ),
        inputs={
            "fixture_mode": fixture_mode,
            "real_smoke_policy": real_smoke_policy,
            "playback_smoke_policy": playback_smoke_policy,
            "timeout_sec": timeout_sec,
        },
        artifacts={
            "json_report": str(JSON_REPORT_PATH),
            "markdown_report": str(MD_REPORT_PATH),
            "verify_report": str(BUILD_DIR / "verify_report.json"),
            "live_qa_report": str(BUILD_DIR / "live_qa_report.json"),
            "mir_quality_report": str(BUILD_DIR / "mir_quality_report.json"),
            "repo_dive_report": str(BUILD_DIR / "repo_dive_report.json"),
            "toolset_review_report": str(BUILD_DIR / "toolset_review.json"),
        },
        timestamp=_utc_timestamp(),
        overall=overall,
        required_gates=required_gates,
        optional_gates=optional_gates,
        known_skips=known_skips_from_gates(all_gate_like),
        follow_up_items=follow_up_items_from_gates(all_gate_like),
    )
    return report


def write_reports(report: CampaignReport) -> None:
    BUILD_DIR.mkdir(parents=True, exist_ok=True)
    JSON_REPORT_PATH.write_text(
        json.dumps(asdict(report), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    MD_REPORT_PATH.write_text(_markdown_report(report), encoding="utf-8")


def _load_live_optional_gates() -> list[dict[str, Any]]:
    path = BUILD_DIR / "live_qa_report.json"
    if not path.is_file():
        return []
    payload = json.loads(path.read_text(encoding="utf-8"))
    gates = payload.get("optional_gates", [])
    return gates if isinstance(gates, list) else []


def _markdown_report(report: CampaignReport) -> str:
    lines = [
        "# Beta Campaign Report",
        "",
        f"- Schema version: `{report.schema_version}`",
        f"- Timestamp: `{report.timestamp}`",
        f"- Overall: `{report.overall}`",
        f"- Command: `{' '.join(report.command)}`",
        "",
        "## Required Gates",
        "",
        "| Gate | Status | Exit | Artifacts |",
        "|---|---|---:|---|",
    ]
    for gate in report.required_gates:
        lines.append(
            f"| `{gate.name}` | `{gate.status}` | {gate.exit_code} | "
            f"{', '.join(f'`{artifact}`' for artifact in gate.artifacts)} |"
        )
    lines.extend(
        [
            "",
            "## Optional Gates",
            "",
            "| Gate | Status | Summary |",
            "|---|---|---|",
        ]
    )
    for gate in report.optional_gates:
        lines.append(
            f"| `{gate.get('name', '')}` | `{gate.get('status', '')}` | {gate.get('summary', '')} |"
        )
    lines.extend(
        [
            "",
            "## Follow-up Items",
            "",
        ]
    )
    if not report.follow_up_items:
        lines.append("No follow-up items were recorded.")
    for item in report.follow_up_items:
        lines.append(f"- `{item['source']}` ({item['status']}): {item['recommendation']}")
    lines.append("")
    return "\n".join(lines)


def _tail(text: str, *, limit: int = 4000) -> str:
    if text is None:
        return ""
    return text[-limit:] if len(text) > limit else text


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fixture-mode", choices=("generated",), default="generated")
    parser.add_argument("--real-smoke-policy", choices=("auto", "required", "off"), default="off")
    parser.add_argument(
        "--playback-smoke-policy",
        choices=("auto", "required", "off"),
        default="off",
    )
    parser.add_argument("--timeout-sec", type=int, default=900)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    raw_argv = sys.argv[1:] if argv is None else argv
    args = parse_args(raw_argv)
    report = build_report(
        fixture_mode=args.fixture_mode,
        real_smoke_policy=args.real_smoke_policy,
        playback_smoke_policy=args.playback_smoke_policy,
        timeout_sec=args.timeout_sec,
        command=["python3", "scripts/beta_campaign.py", *raw_argv],
    )
    write_reports(report)
    print(f"beta_campaign: {report.overall}")
    for gate in report.required_gates:
        print(f"  {gate.name}: {gate.status} (exit={gate.exit_code})")
    print(f"  report: {JSON_REPORT_PATH.relative_to(REPO_ROOT)}")
    print(f"  report: {MD_REPORT_PATH.relative_to(REPO_ROOT)}")
    return 0 if report.overall == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
