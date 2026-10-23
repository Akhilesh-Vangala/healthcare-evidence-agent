# Architecture

Healthcare Evidence Agent answers commercial, medical, and government-affairs questions about drugs and coverage using **only** evidence retrieved in the current run.

```text
question
   │
   ▼
Claude Code (headless)  +  4 Agent Skills (on demand)
   │
   ├── MCP server "cmg" (stdio)
   │     fda_search_labels / fda_get_label_section
   │     trials_search / trials_get
   │     cms_ncd_search / cms_ncd_get
   │     └─ each document → evidence.jsonl (source_id + text)
   ▼
structured answer {status, summary, claims[], needs_human_review, …}
   │
   ▼
verifier  claim OK ⇔ source_id ∈ this run  AND  quote ⊆ document (verbatim)
          task OK  ⇔ all golden checks hold (product, sections, status, NCT IDs, …)
```

## Runtimes

| Path | Role |
| --- | --- |
| `claude_runner.py` | Primary agent: headless Claude Code (`claude -p`), MCP tools, skills workspace |
| `agent.py` | Fixed pipeline baseline (no LLM) for ablation comparisons |
| `ollama_runner.py` | Same tools/skills loop on a local open-weight model |
| `api/app.py` | FastAPI surface over the baseline agent + skill catalog |

## MCP tools (6)

All tools are thin wrappers over `sources.py`. Tool results that contain citeable text call `evidence.record(...)` so the verifier sees exactly what the model saw.

| Tool | Source |
| --- | --- |
| `fda_search_labels` | openFDA drug labels (candidates only) |
| `fda_get_label_section` | openFDA section text (paged) |
| `trials_search` | ClinicalTrials.gov v2 |
| `trials_get` | Single NCT record |
| `cms_ncd_search` | CMS Coverage API — NCD list |
| `cms_ncd_get` | Single NCD body |

HTTP responses are disk-cached (~7 days) under `.cache/` for reproducible eval reruns.

## Agent Skills (4)

Loaded from `agent/workspace/.claude/skills/` when the Claude Code workspace includes them:

| Skill | Job |
| --- | --- |
| `fda-label-lookup` | Disambiguate colliding brand names; boxed-warning rules; `not_found` |
| `cited-evidence` | Verbatim quote discipline matching the verifier |
| `trial-landscape` | Trial search procedure; existence ≠ efficacy |
| `review-escalation` | When to escalate vs refuse |

The older copies under `backend/src/cmg_agent/skills/*/SKILL.md` feed the baseline FastAPI skill catalog only. Claude Code uses the workspace skills.

## Verifier contract

For each claim `(statement, source_id, quote)`:

1. `source_id` must appear in the run's `evidence.jsonl`.
2. After whitespace/quote normalization, `quote` must be a contiguous substring of that document's text and at least 20 normalized characters.
3. Any `NCTxxxxxxxx` mentioned in the answer must appear among retrieved clinical-trial source IDs.

Task-level checks are declared per golden task (`allowed_brands`, `require_sections`, `expect_status`, `expect_review`, …). A task passes only if **every** declared check is true.
