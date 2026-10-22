# Methodology

## Citation invariant

A claim `(statement, source_id, quote)` is **verified** iff:

1. `source_id ∈ Evidence(run)` — the document was retrieved in that run and logged to `evidence.jsonl`.
2. `normalize(quote)` is a contiguous substring of `normalize(Evidence[source_id].text)` and has length ≥ 20.

`normalize` lowercases, maps smart quotes/dashes to ASCII, and collapses whitespace. Paraphrase fails. Closed-book runs therefore have 0% claim precision by construction.

Any `NCTxxxxxxxx` string in the answer summary or claims must appear among retrieved clinical-trial source IDs.

## Task pass

A golden task declares a subset of checks (`expect_status`, `expect_review`, `allowed_brands`, `require_sections`, `min_verified_claims`, …). The task **passes** iff every declared check is true **and** the NCT invariant holds.

## Ablation design

| Config | Tools | Skills | Model |
| --- | --- | --- | --- |
| BASELINE | fixed pipeline | — | none |
| A | no | no | Haiku |
| B | yes | no | Haiku |
| C | yes | yes | Haiku |
| D | yes | yes | Sonnet |

Primary study: A/B/C × 30 tasks × 2 repeats = 180 runs. Plus baseline (30) and D (30) → **240 runs**, listed in `reports/canonical.json`.

One factor changes at a time. The grader and task set are fixed. A second C file from the same morning is not a second study and is not pooled.

## Inference

- **Task pass rate**: mean over tasks of (mean pass across repeats); percentile bootstrap CI over tasks.
- **Paired Δ**: for shared tasks, δ_t = pass_B(t) − pass_A(t); bootstrap the mean of δ. Significant vs 0 if the 95% CI excludes 0.
- **Contingency**: majority-vote pass per task → counts of B∨¬A / A∨¬B (McNemar-style).

Regenerate from checked-in reports:

```bash
python scripts/build_eval_report.py
```

Outputs land in `reports/analysis/` (`stats.json`, `REPORT.md`, figures).

## Replay

Model calls are not required to re-audit a run:

```bash
hea-replay examples/agent_runs/A01_keytruda_vs_keytruda_qlex --task-id A01
```

Replay validates the answer against the Pydantic contract, rebuilds the provenance graph, and re-applies the grader.

## Adversarial prompts

`evals/adversarial/redteam_tasks.json` lists injection, promotional copy, patient advice, off-label pressure, source spoofing, and comparison pressure. **None of these prompts have been run.** There is no red-team pass rate. The file is a spec for a future live session, not a result.

## Budgets

Default post-hoc budget (`budget.RunBudget`): ≤12 tool calls, ≤120s, ≤$0.05 list price, 0 unverified claims. Violations are diagnostics, not hard kills on the Claude Code path.
