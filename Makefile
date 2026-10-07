.PHONY: install test lint eval-smoke ci

install:
	python3 -m venv .venv
	.venv/bin/pip install -U pip
	.venv/bin/pip install -e ".[dev]"

test:
	.venv/bin/pytest -q

lint:
	.venv/bin/ruff check src tests

eval-smoke:
	.venv/bin/hea-eval --configs BASELINE --only L01 N01 R02

ci: lint test

mcp:
	.venv/bin/hea-mcp
