.PHONY: install test lint ci demo mcp serve eval-claude-code eval-api redteam crosscheck console

install:
	python3 -m venv .venv
	.venv/bin/pip install -U pip
	.venv/bin/pip install -e ".[dev]"

lint:
	.venv/bin/ruff check backend api

test:
	.venv/bin/pytest -q

ci: lint test

demo:            ## offline walkthrough of a checked-in run
	.venv/bin/hea-demo

mcp:             ## stdio MCP server (Claude Code, Claude Desktop)
	.venv/bin/hea-mcp

serve:           ## HTTP service behind the console (http://127.0.0.1:8000)
	.venv/bin/hea-serve

eval-claude-code:  ## the published study's runtime (needs Claude Code on PATH)
	.venv/bin/hea-eval --configs A_closed_book B_tools_only C_tools_skills --repeats 2 --workers 6

eval-api:        ## same configurations on the Anthropic API (needs ANTHROPIC_API_KEY and HEA_USD_CAP)
	.venv/bin/hea-eval --configs A_api_closed_book B_api_tools_only C_api_tools_skills --repeats 2 --workers 4

redteam:
	.venv/bin/hea-eval --tasks evals/adversarial/redteam_tasks.json --configs C_api_tools_skills --repeats 2 --workers 3

crosscheck:      ## reports/analysis/RUNTIME.md from committed reports (no model calls)
	.venv/bin/python backend/scripts/runtime_crosscheck.py

console:         ## regenerate the console's data and build it
	.venv/bin/python backend/scripts/build_console_data.py
	cd frontend && npm ci && npm run build
