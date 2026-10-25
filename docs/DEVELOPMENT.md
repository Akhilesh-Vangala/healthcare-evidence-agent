# Development

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
make test
make lint
```

## Layout

```text
frontend/               operator console
agent/workspace/        Claude Code skills
backend/src/hea/  runtime, tools, verifier, analysis
evals/golden/           30 golden tasks
reports/                raw ablation JSON
examples/agent_runs/    checked-in traces
```

## MCP from Claude Code

Repo-root `.mcp.json` registers the stdio server. Or:

```bash
hea-mcp
# equivalent: python -m hea.mcp_server
```

Set `HEA_EVIDENCE_PATH` per run so evidence logs do not collide.

## Offline CI

Pytest covers the verifier and fixture-backed source parsing. Live openFDA / CT.gov / CMS calls are not required for `make ci`.
