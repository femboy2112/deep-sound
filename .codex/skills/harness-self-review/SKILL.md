---
name: harness-self-review
description: Use when reviewing the Deep-Sound control plane, repeated failure patterns, or whether new skills, hooks, or review roles should be suggested.
---

# Harness Self Review

This skill is for repo-control-plane feedback.

## Evidence sources

- `.build/verify_report.json`
- `.build/repair_brief.md`
- `.build/repair_attempts.txt`
- `docs/build/BUILD_LOG.md`
- `docs/build/AGENT_CONTRACT.md`
- `.claude/` and `.codex/`

## Output rule

- Suggestions only.
- Write recommendation artifacts under `.build/`.
- Do not auto-edit the harness.

