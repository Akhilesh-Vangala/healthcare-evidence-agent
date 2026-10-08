# Report index

Raw JSON under this directory backs the README table and the 240-run ablation.

| File | Configs | Runs |
| --- | --- | --- |
| `eval-BASELINE-20260930-114747.json` | BASELINE | 30 |
| `eval-A_closed_book-B_tools_only-C_tools_skills-20260930-115633.json` | A, B, C (×2) | 180 |
| `eval-C_tools_skills-20260930-114930.json` | C (single pass) | 30 |
| `eval-D_tools_skills_sonnet-20261003-115832.json` | D | 30 |

Headline (task pass rate): Baseline 20% · A 23% · B 80% · **C 95% (CI 87–100%)** · D 97%. Claim precision at C: **94%**. Invented NCT IDs with tools: **0**. List cost at C: **$0.0033 / task**.

```bash
python scripts/summarize_reports.py
```
