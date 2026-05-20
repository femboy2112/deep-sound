# Codex Agent Map

Use these roles when the task benefits from bounded parallel work.

## Roles

- `planner`: replan proposals, backlog analysis, repo audit updates.
- `build-engineer`: implement one bounded feature or FILE_PLAN row.
- `verifier`: run gates and summarize failures without editing.
- `repair-engineer`: make the smallest possible fix for a failing gate.
- `mir-reviewer`: review analyzer, feature, or similarity work against the spec.
- `harness-reviewer`: review the agent/tooling surface and suggest additions.

## Delegation Rules

- Keep the immediate blocking task local.
- Delegate sidecar analysis and read-only review freely.
- For coding work, assign clear file ownership.
- Do not have multiple agents edit the same file set.
- Require each coding delegate to report changed files and validation.

## When To Trigger Review Roles

- Use `mir-reviewer` after analyzer or similarity changes.
- Use `verifier` before declaring a broad pass done when multiple files changed.
- Use `harness-reviewer` after changing `.codex/`, `.claude/`, `scripts/toolset_review.py`, or harness docs.

