# Eval analysis

Study `published-240`: **240** rows from 3 files. The same-morning single-pass of C is not included.

Source files:

- `eval-BASELINE-20260930-114747.json`
- `eval-A_closed_book-B_tools_only-C_tools_skills-20260930-115633.json`
- `eval-D_tools_skills_sonnet-20261003-115832.json`

## Paired deltas

| Contrast | Δ pass | 95% CI | sig≠0 | B∨¬A | A∨¬B |
|---|---:|---|:---:|---:|---:|
| BASELINE → C_tools_skills | +75.0% | [+60.0%, +90.0%] | yes | 23 | 0 |
| A_closed_book → B_tools_only | +56.7% | [+33.3%, +76.7%] | yes | 19 | 2 |
| B_tools_only → C_tools_skills | +15.0% | [+1.7%, +30.0%] | yes | 5 | 0 |
| C_tools_skills → D_tools_skills_sonnet | +1.7% | [+0.0%, +5.0%] | no | 0 | 0 |

## Efficiency

| Config | Task pass | Cost/task | Latency med | Tools/task | Claim prec |
|---|---:|---:|---:|---:|---:|
| A_closed_book | 23.3% | $0.0014 | 10.33 | 0.0 | 0.0% |
| BASELINE | 20.0% | $0.0000 | 0.055 | None | 98.2% |
| B_tools_only | 80.0% | $0.0025 | 11.07 | 3.8167 | 88.6% |
| C_tools_skills | 95.0% | $0.0033 | 14.155 | 2.65 | 94.1% |
| D_tools_skills_sonnet | 96.7% | $0.0532 | 16.225 | 2.0667 | 93.9% |

Task pass is the mean of per-task means (repeats averaged first). It is the same definition as the README table.


## Not scored

`evals/adversarial/redteam_tasks.json` is a prompt spec. No configuration was run on it, so it has no pass rate.


## Failure taxonomy (C_tools_skills)

Failed runs: 3 / 60. Over-escalation-only: 3. Invented NCT runs: 0.

```
{
  "review_flag": 3
}
```
