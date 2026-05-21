---
name: history-dive
description: Use when mining Deep-Sound git/build/test history for recurring failures, high-churn files, or harness/tooling recommendations.
---

# History Dive

Use this skill for harness-first analysis, phase closeouts, broad repair reviews, or any task that asks what the repository history says agents should watch.

## Commands

- `python3 scripts/repo_dive.py`
- `python3 scripts/repo_dive.py --strict`
- `python3 scripts/toolset_review.py` after repo-dive report generation

## Evidence

- `.build/repo_dive_report.json`
- `.build/repo_dive_report.md`
- `docs/build/REPO_DIVE.md`
- `git log --name-only`
- `.build/verify_report.json`
- `.build/live_qa_report.json`

## Rules

- Read-only by default.
- Treat detector output as evidence and recommendations, not automatic permission to edit tracked files.
- Preserve the normal FILE_PLAN picker unless a harness-first override is documented in build docs.
- When a detector points at a historical fix, look for the matching regression test before adding new behavior.
