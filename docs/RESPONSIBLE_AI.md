# Responsible AI

This agent is a **research prototype on public data**. It is not medical advice, not promotional content, and must not process PHI.

## Grounding

Every claim is accepted only if:

1. Its `source_id` was retrieved in **that** run (logged in `evidence.jsonl`).
2. Its `quote` is a **verbatim** substring of that source (after light whitespace/quote normalization).

Paraphrases fail. Invented trial IDs fail. Closed-book runs therefore score 0% claim precision by design.

## Escalation and refusal

The `review-escalation` skill encodes when to set `needs_human_review` (comparative claims, off-label use, coverage questions, ambiguous products, missing evidence) and when to `refuse` (promotional copy, superiority slides, individual patient advice).

Published golden-set behavior for configuration C:

- **94%** of claims verified against retrieved sources
- **Zero** invented NCT IDs across tool-using configs
- Off-label and promotional/superiority cases escalate or refuse as specified by the task

## Data sources

| Source | Scope |
| --- | --- |
| openFDA | Public US drug labels |
| ClinicalTrials.gov | Public trial registry |
| CMS Coverage API | National Coverage Determinations only |

Local coverage determinations and commercial payer policies are out of scope.

## Operator expectations

Treat answers as drafts for human medical/regulatory review. Prefer configuration **C** (Haiku + tools + skills) for cost/quality on this workload; do not silently upgrade to a larger model without measuring.
