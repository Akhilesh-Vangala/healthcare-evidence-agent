# Development

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
make test
make lint
```

## Layout

```text
src/cmg_agent/          library (historical package name; product = Healthcare Evidence Agent)
agent_workspace/        Claude Code skills workspace
evals/golden/           30 golden tasks
reports/                raw ablation JSON
examples/agent_runs/    checked-in traces
scripts/                report helpers / plots
docs/                   architecture, eval, responsible AI
```

## MCP from Claude Code

Repo-root `.mcp.json` registers the stdio server. Or:

```bash
hea-mcp
# equivalent: python -m cmg_agent.mcp_server
```

Set `CMG_EVIDENCE_PATH` per run so evidence logs do not collide.

## Offline CI

Pytest covers the verifier and fixture-backed source parsing. Live openFDA / CT.gov / CMS calls are not required for `make ci`.
