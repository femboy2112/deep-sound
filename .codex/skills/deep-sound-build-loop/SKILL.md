---
name: deep-sound-build-loop
description: Use when the task is to build, continue, repair, verify, print status, replan, or otherwise operate the Deep-Sound repo through its standard build loop.
---

# Deep-Sound Build Loop

This skill is for repo execution flow, not product design.

## Use these shared scripts

- `python3 scripts/session_start.py`
- `python3 scripts/status.py`
- `python3 scripts/verify.py`
- `python3 scripts/repair.py`
- `python3 scripts/update_plan.py`
- `python3 scripts/toolset_review.py`

## Rules

- Repair first.
- Respect the normal picker unless a documented harness override is active.
- Use `docs/build/AGENT_CONTRACT.md` as the shared operational contract.

