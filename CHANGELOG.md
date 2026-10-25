# Changelog

Measured numbers are tied to the report files that produced them (`reports/`), so history is kept as written.

## 1.0.0 — 2026-10-25

**Second runtime and cross-runtime check**
- `api_runner.py`: the agent on the Anthropic Messages API with the same model, prompt, schema, MCP registry (called
  in-process), skills text (`load_skill`) and grader as the Claude Code runtime; prompt caching on every request;
  thinking blocks replayed; refusal and max_tokens handled; hard USD cap (`spend.py`).
- Re-ran A/B/C (180 runs): on the 28 tasks unaffected by data drift, config C is 92.9% on the API vs 94.6% on Claude
  Code (paired −1.8 pts, CI −7.1 to +3.6); cost per task $0.0033 → $0.0019 with 63% of input from cache; claim
  precision 94.1% → 97.9%. Analysis: `reports/analysis/RUNTIME.md` (reproducible, no model calls).
- Red-team suite scored for the first time: 10 of 12 runs pass; every run refused, escalated or reported not found.

**Data drift found and handled**
- openFDA's current TECENTRIQ label has no harmonized `openfda` block; label search falls back to the product text and
  marks `name_source` (affects 1 of 15 golden products). Evrysdi (task N02) is now present in openFDA.

**Service and console**
- `server.py`: live MCP tools, live citation check (re-fetches the document behind a `source_id`), recorded runs and
  the agent streamed as server-sent events, behind rate and daily spend limits that fail closed; request ids, JSON
  access logs, security headers. Deployed as its own Vercel project; the console rewrites `/api` to it.
- Console: Ask the agent (live or replay of recorded real runs with a live trace), Evidence explorer, live Citation
  check with divergence view, Study with cross-runtime and red-team sections.

**Cleanup**
- Package renamed `cmg_agent` → `hea`; removed the unevaluated Ollama runner, the baseline-only FastAPI app and
  duplicate entry points. CI lints scripts, checks that the published analysis reproduces, and builds the console.

## 0.3.x

- 240-run study on headless Claude Code: config C 95% (87–100) vs 20% fixed-pipeline baseline; tools +57 pts, skills
  +15 pts, Sonnet +1.7 pts at ~16× cost; zero invented NCT IDs with tools.
- Operator console replaying the study, five saved runs and the citation rule.
