# Evaluation

## Golden set

30 author-written tasks in `evals/golden/agent_tasks.json`, spanning labels, ambiguous products, comparisons, trials, Medicare NCDs, refusals / off-label, and not-found.

Grading is fully programmatic (`backend/src/cmg_agent/verify.py`). No LLM-as-judge.

## Configurations

| ID | Model | MCP tools | Skills |
| --- | --- | --- | --- |
| `BASELINE` | none (fixed pipeline) | n/a | n/a |
| `A_closed_book` | Claude Haiku | no | no |
| `B_tools_only` | Claude Haiku | yes | no |
| `C_tools_skills` | Claude Haiku | yes | yes |
| `D_tools_skills_sonnet` | Claude Sonnet | yes | yes |

Primary ablation (A/B/C × 30 tasks × 2 repeats) = **180 runs**. Adding baseline (30) and Sonnet (30) = **240 runs**. Membership is [`reports/canonical.json`](../reports/canonical.json). `scripts/build_eval_report.py` reads that list and nothing else.

## Headline results

| Config | Pass rate (95% CI) | Claim precision | Cost / task |
| --- | --- | --- | --- |
| Baseline | 20% (7–37%) | n/a† | $0 |
| A closed book | 23% (10–40%) | 0% | $0.0014 |
| B tools only | 80% (63–93%) | 89% | $0.0025 |
| **C tools + skills** | **95% (87–100%)** | **94%** | **$0.0033** |
| D Sonnet | 97% (90–100%) | 94% | $0.0532 |

† Baseline claims are excerpts of fetched text, so they verify by construction.

## What moved the needle

- **Tools (+57 pts vs A):** without retrieval, 0% of claims verified; 4 runs invented NCT IDs. With tools: zero invented NCTs across B/C/D.
- **Skills (+15 pts vs B, paired CI +2 to +30):** restored refusals (50%→100%), off-label escalation (0%→100%), ambiguous products (67%→100%), and cut MCP calls/task from 3.8 to 2.7.
- **Sonnet (+1.7 pts vs C, CI includes 0, ~16× cost):** not the default. The 97% vs 95% headline is the same comparison rounded.
- **Remaining C failures:** 3 of 60 runs, all over-escalation of the review flag — not wrong product, not an unverifiable claim, not a missed refusal.

## Reproducing

```bash
pip install -e ".[dev]"
# Claude Code signed in, or CLAUDE_BIN set
hea-eval --configs A_closed_book B_tools_only C_tools_skills --repeats 2 --workers 6
hea-eval --configs BASELINE D_tools_skills_sonnet --workers 4
python scripts/summarize_reports.py
```

Paired bootstrap CIs are computed over per-task pass means. Regenerate with `python scripts/build_eval_report.py` (canonical files only). Output: `reports/analysis/`.

## What is not a result

- `reports/exploratory/eval-C_tools_skills-pilot-20260930-114930.json` — single pass of C, 90%, 30 runs. Kept so the file is not deleted, excluded so it cannot be averaged with the 60-run C block (that average is 93.3% and matches neither run).
- `evals/adversarial/redteam_tasks.json` — six prompts. Not run. No pass rate.

Broader cross-project notes live in [agent-config-bench](https://github.com/Akhilesh-Vangala/agent-config-bench).

## Caveats

- Author-written golden set; CIs are wide. A held-out set would strengthen the claim.
- A pagination fix for long label sections landed after an early over-escalation failure mode on the same tasks.
- Grader checks structure and citations, not prose quality.
