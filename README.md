# Healthcare Evidence Agent

Governed AI agent for healthcare and policy questions over **FDA drug labels**, **ClinicalTrials.gov**, and **Medicare NCDs**. Claude Code is the agent runtime; tool access goes through a **6-tool MCP server**; task procedure ships as **4 reusable Agent Skills**. A programmatic verifier accepts a claim only if its source was retrieved in that run and quoted verbatim.

> Public data only. Not medical advice. No PHI.

[Architecture](docs/ARCHITECTURE.md) · [Evaluation](docs/EVALUATION.md) · [Responsible AI](docs/RESPONSIBLE_AI.md) · [Ablation bench](https://github.com/Akhilesh-Vangala/agent-config-bench)

## Results

30 golden tasks, automatic grading. Pass rate is per-task with a bootstrap 95% CI. A–C were run twice per task (**240 runs** across baseline + A/B/C/D in `reports/`).

| Configuration | Pass rate (95% CI) | Claims verified | Cost / task | Median latency |
|---|---|---|---|---|
| Fixed pipeline (no LLM) | 20% (7–37%) | n/a† | $0 | 0.1 s |
| A. Haiku, no tools | 23% (10–40%) | 0% | $0.0014 | 10 s |
| B. Haiku + MCP tools | 80% (63–93%) | 89% | $0.0025 | 11 s |
| **C. Haiku + tools + skills** | **95% (87–100%)** | **94%** | **$0.0033** | **14 s** |
| D. C on Sonnet | 97% (90–100%) | 94% | $0.0532 | 16 s |

† Baseline claims are fetched excerpts, so they verify by construction; the pipeline fails on product choice, refusal, and not-found.

![Pass rate by configuration](docs/pass_rate.png)

**Takeaways**

- **Agent vs fixed pipeline: +75 pts.** Hard-coded product matching cannot refuse, cannot say not-found, and often picks the wrong label.
- **Tools: +57 pts.** Closed-book: 0% verified claims and invented NCT IDs. With tools: **zero invented trial IDs** in every configuration.
- **Skills: +15 pts.** Restored refusals (50%→100%), off-label review (0%→100%), and ambiguous products such as KEYTRUDA vs KEYTRUDA QLEX (67%→100%); MCP calls/task fell 3.8→2.6.
- **Sonnet vs Haiku: +2 pts at ~16× cost.** Haiku + skills is the default.
- Remaining C failures are **over-escalation** of human review — not wrong product, not unverifiable claims slipping through, not missed refusals.

## How it works

```text
question → Claude Code (+ skills) → MCP tools (FDA / trials / CMS)
         → evidence.jsonl → structured answer → verifier / golden grader
```

| Layer | What you get |
|---|---|
| MCP (6 tools) | `fda_search_labels`, `fda_get_label_section`, `trials_search`, `trials_get`, `cms_ncd_search`, `cms_ncd_get` |
| Skills (4) | `fda-label-lookup`, `cited-evidence`, `trial-landscape`, `review-escalation` |
| Verifier | `source_id` must be from this run; quote must be verbatim; no invented NCT IDs |
| Golden set | 30 tasks: labels, ambiguous names, comparisons, trials, coverage, refusal / off-label, not-found |

## Run it

Python 3.10+ and Claude Code on PATH (or `CLAUDE_BIN`). No separate API key when Claude Code is signed in.

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
make test

# one task
hea-eval --configs C_tools_skills --only L01

# ablations
hea-eval --configs BASELINE C_tools_skills --workers 4
hea-eval --configs A_closed_book B_tools_only C_tools_skills --repeats 2 --workers 6

# MCP server (any MCP client / Claude Code via .mcp.json)
hea-mcp
```

Checked-in example runs (evidence + answer): [`examples/agent_runs/`](examples/agent_runs/).

## Repository layout

```text
agent_workspace/.claude/skills/   Claude Code Agent Skills
src/cmg_agent/
  mcp_server.py                   6-tool MCP server
  sources.py                      openFDA · ClinicalTrials.gov · CMS
  claude_runner.py                headless Claude Code runner
  verify.py                       citation verifier + task grader
  eval_agent.py                   golden-set harness + bootstrap CIs
  agent.py                        fixed-pipeline baseline
evals/golden/                     30 golden tasks
reports/                          raw ablation outputs
docs/                             architecture · eval · responsible AI
```

## Limitations

- Focused golden set (n=30); CIs are wide. Expanding / holding out tasks is the next step.
- Author-written tasks; a pagination fix for long label sections landed after early over-escalation on the same set.
- Grader checks product, citations, status, and review flags — not summary prose quality.
- CMS path covers public NCDs only.
- Responses cached on disk (~7 days) under `.cache/` for reproducible reruns.

## License

MIT — see [LICENSE](LICENSE).
