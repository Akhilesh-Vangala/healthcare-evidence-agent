.PHONY: install test lint eval-smoke analysis trace demo ci mcp

install:
	python3 -m venv .venv
	.venv/bin/pip install -U pip
	.venv/bin/pip install -e ".[dev]"

test:
	.venv/bin/pytest -q

lint:
	.venv/bin/ruff check backend/src tests

eval-smoke:
	.venv/bin/hea-eval --configs BASELINE --only L01 N01 R02

analysis:
	.venv/bin/python scripts/build_eval_report.py

trace:
	.venv/bin/python scripts/build_trace_viewer.py

demo:
	.venv/bin/hea-demo

ci: lint test

mcp:
	.venv/bin/hea-mcp
