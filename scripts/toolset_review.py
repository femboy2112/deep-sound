"""Suggest harness additions based on repo state and recent verification signals.

This script is deliberately suggest-only. It inspects the current repo control
plane and writes structured recommendations under `.build/`. It does not edit
tracked repo files.
"""

from __future__ import annotations

import json
import time
from dataclasses import asdict, dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
BUILD_DIR = REPO_ROOT / ".build"
JSON_PATH = BUILD_DIR / "toolset_review.json"
MARKDOWN_PATH = BUILD_DIR / "toolset_review.md"
VERIFY_REPORT_PATH = BUILD_DIR / "verify_report.json"
REPAIR_ATTEMPTS_PATH = BUILD_DIR / "repair_attempts.txt"
CODEx_ROOT = REPO_ROOT / ".codex"
CLAUDE_ROOT = REPO_ROOT / ".claude"


@dataclass(frozen=True, slots=True)
class Recommendation:
    kind: str
    priority: str
    title: str
    evidence: str
    proposal: str
    safety: str


def read_text(path: Path) -> str:
    return path.read_text() if path.exists() else ""


def read_repair_attempts() -> int:
    raw = read_text(REPAIR_ATTEMPTS_PATH).strip()
    if not raw:
        return 0
    try:
        return int(raw)
    except ValueError:
        return 0


def collect_recommendations() -> list[Recommendation]:
    recs: list[Recommendation] = []

    if not CODEx_ROOT.exists():
        recs.append(
            Recommendation(
                kind="missing-surface",
                priority="high",
                title="Add a Codex-native repo harness",
                evidence="No .codex directory exists.",
                proposal="Create .codex docs, bounded agent roles, domain skills, and safe hooks that reuse scripts/.",
                safety="docs-and-hooks",
            )
        )

    if not (CODEx_ROOT / "skills").exists():
        recs.append(
            Recommendation(
                kind="missing-skill",
                priority="medium",
                title="Add Codex skills for recurring repo domains",
                evidence="The Codex surface has no skills directory.",
                proposal="Add short skills for analyzer work, confidence policy, vector search, and harness maintenance.",
                safety="docs-only",
            )
        )

    if not (CODEx_ROOT / "agents").exists():
        recs.append(
            Recommendation(
                kind="missing-review-role",
                priority="medium",
                title="Add bounded Codex agent roles",
                evidence="The Codex surface has no agents directory.",
                proposal="Add planner, build, verifier, repair, MIR review, and harness review role docs.",
                safety="docs-only",
            )
        )

    if not (CODEx_ROOT / "hooks").exists():
        recs.append(
            Recommendation(
                kind="missing-hook",
                priority="medium",
                title="Add safe repo-local Codex hooks",
                evidence="The Codex surface has no hooks directory.",
                proposal="Add session-start and stop-review hooks that only read state and write .build artifacts.",
                safety="hooks-only",
            )
        )

    if CLAUDE_ROOT.exists() and not CODEx_ROOT.exists():
        recs.append(
            Recommendation(
                kind="surface-asymmetry",
                priority="high",
                title="Reduce orchestration asymmetry",
                evidence="A Claude surface exists without a Codex counterpart.",
                proposal="Mirror the shared control-plane concepts in .codex while keeping scripts/ as the common backend.",
                safety="docs-and-hooks",
            )
        )

    if VERIFY_REPORT_PATH.exists():
        report = json.loads(VERIFY_REPORT_PATH.read_text())
        if report.get("overall") == "fail":
            recs.append(
                Recommendation(
                    kind="verification-blind-spot",
                    priority="medium",
                    title="Review repeated failure patterns for missing harness guidance",
                    evidence="The most recent verify report failed.",
                    proposal="Inspect the failing check types and consider adding or refining a skill, hook, or review role for the dominant failure mode.",
                    safety="report-only",
                )
            )

    repair_attempts = read_repair_attempts()
    if repair_attempts >= 2:
        recs.append(
            Recommendation(
                kind="repeated-repair-pattern",
                priority="high",
                title="Escalate repeated repair loops into harness guidance",
                evidence=f"repair_attempts.txt records {repair_attempts} attempts.",
                proposal="Add or refine a repair-focused skill or hook message so future agents detect the pattern earlier.",
                safety="docs-only",
            )
        )

    audio_skill = CODEx_ROOT / "skills" / "audio-pipeline" / "SKILL.md"
    confidence_skill = CODEx_ROOT / "skills" / "mir-confidence-policy" / "SKILL.md"
    if not audio_skill.exists() or not confidence_skill.exists():
        recs.append(
            Recommendation(
                kind="coverage-gap",
                priority="medium",
                title="Keep analyzer and confidence guidance visible in the Codex surface",
                evidence="One or more core MIR skills are missing from .codex/skills.",
                proposal="Add audio-pipeline and mir-confidence-policy skills so analyzer work triggers repo-local guidance.",
                safety="docs-only",
            )
        )

    return recs


def render_markdown(recommendations: list[Recommendation]) -> str:
    timestamp = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    lines = [
        f"# Toolset Review — {timestamp}",
        "",
        "This review is suggest-only. It never auto-applies harness changes.",
        "",
    ]
    if not recommendations:
        lines.extend(["No toolset additions suggested from the current signals.", ""])
        return "\n".join(lines)

    lines.extend(["## Recommendations", ""])
    for index, rec in enumerate(recommendations, start=1):
        lines.extend(
            [
                f"{index}. **{rec.title}**",
                f"   Kind: `{rec.kind}`",
                f"   Priority: `{rec.priority}`",
                f"   Evidence: {rec.evidence}",
                f"   Proposal: {rec.proposal}",
                f"   Safety: `{rec.safety}`",
                "",
            ]
        )
    return "\n".join(lines)


def main() -> int:
    BUILD_DIR.mkdir(exist_ok=True)
    recommendations = collect_recommendations()
    payload = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "recommendations": [asdict(rec) for rec in recommendations],
    }
    JSON_PATH.write_text(json.dumps(payload, indent=2))
    MARKDOWN_PATH.write_text(render_markdown(recommendations))

    print(f"toolset review: {len(recommendations)} recommendation(s)")
    print(f"report: {MARKDOWN_PATH.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
