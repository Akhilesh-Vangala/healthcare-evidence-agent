# Eval analysis

Rows analyzed: **270** across `A_closed_book, BASELINE, B_tools_only, C_tools_skills, D_tools_skills_sonnet`.

## Paired deltas

| Contrast | Δ pass | 95% CI | sig≠0 | B∨¬A | A∨¬B |
|---|---:|---|:---:|---:|---:|
| BASELINE → C_tools_skills | +73.3% | [+57.8%, +87.8%] | yes | 22 | 0 |
| A_closed_book → B_tools_only | +56.7% | [+33.3%, +76.7%] | yes | 19 | 2 |
| B_tools_only → C_tools_skills | +13.3% | [-0.0%, +27.8%] | no | 5 | 1 |
| C_tools_skills → D_tools_skills_sonnet | +3.3% | [+0.0%, +8.9%] | no | 1 | 0 |

## Efficiency

| Config | Pass | Cost/task | Latency med | Tools/task | Claim prec |
|---|---:|---:|---:|---:|---:|
| A_closed_book | 23.3% | $0.0014 | 10.33 | 0.0 | 0.0% |
| BASELINE | 20.0% | $0.0000 | 0.055 | None | 98.2% |
| B_tools_only | 80.0% | $0.0025 | 11.07 | 3.8167 | 88.6% |
| C_tools_skills | 93.3% | $0.0033 | 14.265 | 2.5333 | 95.0% |
| D_tools_skills_sonnet | 96.7% | $0.0532 | 16.225 | 2.0667 | 93.9% |

## Failure taxonomy (C_tools_skills)

Failed runs: 6 / 90. Over-escalation-only: 6. Invented NCT runs: 0.

```
{
  "review_flag": 6
}
```
