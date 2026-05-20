---
name: harness-maintenance
description: Use when changing Deep-Sound agent docs, hooks, review scripts, repo audit docs, or other control-plane tooling under .codex, .claude, docs, scripts, or AGENTS.md.
---

# Harness Maintenance

This skill governs repo-control-plane work.

## Goals

- Keep `.claude/` and `.codex/` aligned on shared backend scripts and spec rules.
- Prefer extending shared scripts over forking new ones.
- Keep self-review suggest-only.
- Document any temporary priority override in build docs.

## Required checks

- `python3 scripts/status.py`
- `python3 scripts/toolset_review.py`
- targeted grep or doc review for drift between `.claude/` and `.codex/`

## Do not do

- Do not auto-apply toolset recommendations.
- Do not loosen spec, phase, or FILE_PLAN constraints silently.

