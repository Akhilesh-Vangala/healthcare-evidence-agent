# Exploratory run — not in the published 240

`eval-C_tools_skills-pilot-20260930-114930.json` is a single pass of config C: 30 tasks, 1 repeat, **90%** task pass (CI 80–100%).

The published C result is the 2-repeat block in `eval-A_closed_book-B_tools_only-C_tools_skills-20260930-115633.json`: 60 runs, **95%** (CI 87–100%).

These are not interchangeable. Averaging them produces 90 C rows and **93.3%**, which matches neither run. `scripts/build_eval_report.py` reads `reports/canonical.json` and does not open this directory.
