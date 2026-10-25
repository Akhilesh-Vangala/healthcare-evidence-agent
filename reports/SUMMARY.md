# Report index

The published table is the **240-row** study in [`canonical.json`](canonical.json). Do not average it with the pilot.

| File | Role | Configs | Runs |
| --- | --- | --- | --- |
| `eval-BASELINE-20260930-114747.json` | published | BASELINE | 30 |
| `eval-A_closed_book-B_tools_only-C_tools_skills-20260930-115633.json` | published | A, B, C ×2 | 180 |
| `eval-D_tools_skills_sonnet-20261003-115832.json` | published | D | 30 |
| `exploratory/eval-C_tools_skills-pilot-20260930-114930.json` | excluded | C ×1 | 30 |

Headline (task pass, from the published files only): Baseline 20% · A 23% · B 80% · **C 95% (CI 87–100%, n=60)** · D 97%. Claim precision at C: **94%**. Invented NCT IDs with tools: **0**. List cost at C: **$0.0033 / task**.

The excluded file is a same-morning single pass of C at 90%. Pooling it with the 60-run C block is what produced a 93.3% figure that is not a result of either run.

The red-team suite and the cross-runtime re-run on the Anthropic API are reported separately in [`analysis/RUNTIME.md`](analysis/RUNTIME.md) and are not part of the 240.

```bash
python scripts/summarize_reports.py
python scripts/build_eval_report.py
```
