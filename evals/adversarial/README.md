# Adversarial task spec — not scored

`redteam_tasks.json` is a prompt list (injection, promotional copy, patient advice, off-label pressure, source spoofing, comparison pressure).

No configuration was run on it. There is no pass rate, cost, or failure count for these six tasks. Do not cite them as results.

Scoring them needs a live Claude Code session:

```bash
hea-eval --tasks evals/adversarial/redteam_tasks.json --configs C_tools_skills --workers 2
```

Until that file exists under `reports/` and is added to `reports/canonical.json`, the suite stays out of the published study.
