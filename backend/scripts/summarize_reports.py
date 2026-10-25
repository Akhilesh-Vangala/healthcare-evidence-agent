#!/usr/bin/env python3
"""Print the published ablation and, separately, the excluded pilot."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
REPORTS = ROOT / "reports"


def _print_file(path: Path) -> None:
    data = json.loads(path.read_text())
    for cfg, s in (data.get("summary") or {}).items():
        ci = s.get("task_pass_ci95") or [0, 0]
        prec = s.get("claim_precision_mean")
        cost = s.get("cost_usd_per_task_list_price") or 0.0
        print(
            f"{path.name:<62} {cfg:<24} "
            f"{(s.get('task_pass_rate') or 0):6.1%} "
            f"{ci[0]:5.1%}-{ci[1]:5.1%} "
            f"{(prec if prec is not None else 0):7.1%} "
            f"${cost:7.4f}"
        )


def main() -> int:
    spec = json.loads((REPORTS / "canonical.json").read_text())
    print("published study (exploratory/ is not included)\n")
    print(f"{'report':<62} {'config':<24} {'pass':>6} {'CI lo-hi':>14} {'claims':>7} {'$/task':>8}")
    for name in spec["files"]:
        _print_file(REPORTS / name)
    exploratory = sorted((REPORTS / "exploratory").glob("eval-*.json"))
    if exploratory:
        print("\nexploratory — excluded from the published table\n")
        for path in exploratory:
            _print_file(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
