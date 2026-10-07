#!/usr/bin/env python3
"""Print a compact table from reports/eval-*.json (no network)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPORTS = ROOT / "reports"


def main() -> int:
    paths = sorted(REPORTS.glob("eval-*.json"))
    if not paths:
        print("no reports found", file=sys.stderr)
        return 1
    print(f"{'report':<55} {'config':<24} {'pass':>6} {'CI lo-hi':>14} {'claims':>7} {'$/task':>8}")
    for path in paths:
        data = json.loads(path.read_text())
        for cfg, s in (data.get("summary") or {}).items():
            ci = s.get("task_pass_ci95") or [0, 0]
            prec = s.get("claim_precision_mean")
            cost = s.get("cost_usd_per_task_list_price") or 0.0
            print(
                f"{path.name:<55} {cfg:<24} "
                f"{(s.get('task_pass_rate') or 0):6.1%} "
                f"{ci[0]:5.1%}-{ci[1]:5.1%} "
                f"{(prec if prec is not None else 0):7.1%} "
                f"${cost:7.4f}"
            )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
