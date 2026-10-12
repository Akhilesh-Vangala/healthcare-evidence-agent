"""Paired bootstrap comparisons and failure / efficiency summaries.

All functions are pure over eval ``rows`` so reports can be regenerated after
the fact without re-running models.
"""

from __future__ import annotations

import random
import statistics
from collections import Counter, defaultdict
from typing import Any


def _task_pass_map(rows: list[dict[str, Any]], config: str) -> dict[str, float]:
    """Mean pass rate per task_id for a config (handles repeats)."""
    buckets: dict[str, list[float]] = defaultdict(list)
    for r in rows:
        if r.get("config") != config:
            continue
        buckets[r["task_id"]].append(1.0 if r.get("passed") else 0.0)
    return {tid: statistics.fmean(vs) for tid, vs in buckets.items()}


def paired_delta(
    rows: list[dict[str, Any]],
    config_a: str,
    config_b: str,
    *,
    n_boot: int = 4000,
    seed: int = 7,
) -> dict[str, Any]:
    """Paired task-level pass-rate delta (B − A) with percentile bootstrap CI."""
    a = _task_pass_map(rows, config_a)
    b = _task_pass_map(rows, config_b)
    shared = sorted(set(a) & set(b))
    if not shared:
        return {"config_a": config_a, "config_b": config_b, "n_tasks": 0}

    deltas = [b[t] - a[t] for t in shared]
    mean = statistics.fmean(deltas)
    rng = random.Random(seed)
    boots = sorted(statistics.fmean(rng.choices(deltas, k=len(deltas))) for _ in range(n_boot))
    lo, hi = boots[int(0.025 * n_boot)], boots[int(0.975 * n_boot) - 1]

    # Sign test / McNemar-style on hard binary (pass on majority of repeats)
    a_bin = {t: a[t] >= 0.5 for t in shared}
    b_bin = {t: b[t] >= 0.5 for t in shared}
    b_only = sum(1 for t in shared if b_bin[t] and not a_bin[t])
    a_only = sum(1 for t in shared if a_bin[t] and not b_bin[t])
    both = sum(1 for t in shared if a_bin[t] and b_bin[t])
    neither = sum(1 for t in shared if not a_bin[t] and not b_bin[t])

    return {
        "config_a": config_a,
        "config_b": config_b,
        "n_tasks": len(shared),
        "delta_pass_rate": round(mean, 4),
        "delta_ci95": [round(lo, 4), round(hi, 4)],
        "delta_significant_vs_zero": not (lo <= 0.0 <= hi),
        "contingency": {
            "b_pass_a_fail": b_only,
            "a_pass_b_fail": a_only,
            "both_pass": both,
            "both_fail": neither,
        },
        "improved_tasks": [t for t in shared if b[t] > a[t]],
        "regressed_tasks": [t for t in shared if b[t] < a[t]],
    }


def summarize_failures(rows: list[dict[str, Any]], config: str) -> dict[str, Any]:
    subset = [r for r in rows if r.get("config") == config]
    failed = [r for r in subset if not r.get("passed")]
    check_counts: Counter[str] = Counter()
    by_cat: Counter[str] = Counter()
    claim_reasons: Counter[str] = Counter()
    for r in failed:
        by_cat[r.get("category") or "?"] += 1
        for k, ok in (r.get("checks") or {}).items():
            if not ok:
                check_counts[k] += 1
        for reason in r.get("failed_claim_reasons") or []:
            claim_reasons[reason] += 1
    return {
        "config": config,
        "n_runs": len(subset),
        "n_failed": len(failed),
        "fail_rate": round(len(failed) / len(subset), 4) if subset else None,
        "failed_checks": dict(check_counts.most_common()),
        "failed_by_category": dict(by_cat.most_common()),
        "failed_claim_reasons": dict(claim_reasons.most_common()),
        "invented_nct_runs": sum(1 for r in subset if r.get("hallucinated_ncts")),
        "over_escalation_only": sum(
            1
            for r in failed
            if set(k for k, ok in (r.get("checks") or {}).items() if not ok) <= {"review_flag"}
        ),
    }


def summarize_efficiency(rows: list[dict[str, Any]], config: str) -> dict[str, Any]:
    subset = [r for r in rows if r.get("config") == config]
    if not subset:
        return {"config": config, "n_runs": 0}

    def _med(key: str) -> float | None:
        vals = [r[key] for r in subset if r.get(key) is not None]
        return round(statistics.median(vals), 4) if vals else None

    def _mean(key: str) -> float | None:
        vals = [r[key] for r in subset if r.get(key) is not None]
        return round(statistics.fmean(vals), 4) if vals else None

    passed = [r for r in subset if r.get("passed")]
    return {
        "config": config,
        "n_runs": len(subset),
        "pass_rate": round(len(passed) / len(subset), 4),
        "latency_s_median": _med("latency_s"),
        "cost_usd_mean": _mean("cost_usd_list_price"),
        "tool_calls_mean": _mean("tool_calls"),
        "claim_precision_mean": _mean("claim_precision"),
        "tokens_in_mean": _mean("input_tokens"),
        "tokens_out_mean": _mean("output_tokens"),
        "n_passed": len(passed),
    }
