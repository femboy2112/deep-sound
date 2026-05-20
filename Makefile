.PHONY: bootstrap verify repair status toolset-review build phase clean help

help:
	@echo "Deep-Sound build orchestration targets:"
	@echo "  make bootstrap   Install uv if missing, run uv sync --extra dev"
	@echo "  make verify      Run ruff + mypy + pytest, write .build/verify_report.json"
	@echo "  make repair      Print .build/repair_brief.md if present"
	@echo "  make status      Show FILE_PLAN summary and active phase"
	@echo "  make toolset-review  Write suggest-only harness recommendations"
	@echo "  make phase       Print current ACTIVE_PHASE"
	@echo "  make clean       Remove .build/, caches"
	@echo ""
	@echo "Use Claude Code slash commands (/build, /continue, /repair, /verify, /status)"
	@echo "to drive the build loop; targets above are for manual invocation."

bootstrap:
	bash scripts/bootstrap.sh

verify:
	uv run python scripts/verify.py

repair:
	@if [ -f .build/repair_brief.md ]; then cat .build/repair_brief.md; \
	else echo "No repair brief present. Run 'make verify' first."; fi

status:
	uv run python scripts/status.py

toolset-review:
	python3 scripts/toolset_review.py

phase:
	uv run python scripts/update_plan.py --print-phase

clean:
	rm -rf .build .pytest_cache .mypy_cache .ruff_cache
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
