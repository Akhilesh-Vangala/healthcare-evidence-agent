# For hiring managers & reviewers

**One sentence:** a governed healthcare evidence agent that cannot pass a claim unless the quote is a verbatim substring of a source retrieved in that same run — measured on a 30-task golden set with bootstrap CIs and a 240-run ablation.

## Why this is not “another RAG demo”

| Naive LLM / RAG | This system |
| --- | --- |
| Cites memory or a vector store vaguely | Cites `source_id` from **this run’s** `evidence.jsonl` |
| Paraphrase often accepted | Paraphrase **fails** the grader |
| Trial IDs can be invented | Any unseen `NCT*` fails the task |
| “Looks good” judged by eye | 30 golden tasks, programmatic checks, paired bootstrap |
| Skills = prompt paste | 4 versioned Agent Skills + 6 MCP tools |

## Numbers that match the resume

| Claim | Evidence in-repo |
| --- | --- |
| **95%** pass (CI **87–100%**) vs **20%** fixed pipeline | `reports/` + README table + `reports/analysis/REPORT.md` |
| Claude agent, **6-tool MCP**, **4 Agent Skills** | `mcp_server.py`, `agent_workspace/.claude/skills/` |
| FDA / trials / Medicare | `sources.py` |
| **94%** verified claims, **0** invented trial IDs | ablation summary; failure taxonomy |
| Tools **+57 pts**; skills restore refusals; Sonnet **+2 pts** at ~16× cost / **$0.0033**/task | paired deltas in `reports/analysis/` |

## 5-minute review path

1. **README** — banner metrics, results table, architecture diagram  
2. **[`reports/analysis/REPORT.md`](../reports/analysis/REPORT.md)** — paired Δ, cost–quality, failure taxonomy  
3. **[`examples/trace_viewer/index.html`](../examples/trace_viewer/index.html)** — open locally; see claims mapped to sources  
4. **`make test`** — offline verifier, provenance, analysis (no API key)  
5. **[`docs/METHODOLOGY.md`](METHODOLOGY.md)** — formal citation invariant  

## Design choices worth probing in an interview

- Why Haiku + skills beats Sonnet on $/quality for this workload  
- Why skills fixed refusals that tools alone broke  
- Why the remaining C failures are over-escalation, not wrong products  
- How replay (`hea-replay`) re-grades without calling a model  

## Scope honesty

Public data only. Not medical advice. Author-written golden set (n=30); CIs are wide. CMS path = NCDs only.

The 95% figure is the 2-repeat config C block (60 runs). A 30-run pilot of the same config scored 90% and is filed under `reports/exploratory/`. It is not in the 240, and it is not averaged with the 60. That average (93.3%) was a bookkeeping error, not a third experiment.

`evals/adversarial/` is a prompt list. It has not been executed. Do not treat it as a red-team score.
