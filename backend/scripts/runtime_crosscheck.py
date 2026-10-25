#!/usr/bin/env python3
"""Cross-runtime check: the published Claude Code study against the same configurations on the Anthropic API.

Reads only committed report files (no model calls) and writes reports/analysis/RUNTIME.md and runtime.json.
Two golden tasks changed under the study because the live data changed (data drift), so every comparison is
reported on all 30 tasks and on the 28 unaffected ones:
  L01  openFDA's current TECENTRIQ label lost its harmonized name block, and a second product (TECENTRIQ HYBREZA)
       now matches the name, which the agent flags for review.
  N02  expects 'not found' for Evrysdi, which was absent from openFDA on 2026-09-30 and is present now; the API
       agent answered it correctly from the current label.
"""

from __future__ import annotations

import json
import random
import statistics
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CLAUDE_CODE = ROOT / "reports" / "eval-A_closed_book-B_tools_only-C_tools_skills-20260930-115633.json"
API = ROOT / "reports" / "eval-A_api_closed_book-B_api_tools_only-C_api_tools_skills-20261025-160545.json"
REDTEAM = ROOT / "reports" / "eval-C_api_tools_skills-20261025-160639.json"
DRIFT = {"L01": "TECENTRIQ name block missing; HYBREZA now also matches",
         "N02": "Evrysdi label now present in openFDA (expected not found)"}
PAIRS = [("A_closed_book", "A_api_closed_book", "closed book"), ("B_tools_only", "B_api_tools_only", "tools only"),
         ("C_tools_skills", "C_api_tools_skills", "tools + skills")]


def per_task(rows, cfg, exclude=()):
    g: dict[str, list[float]] = {}
    for r in rows:
        if r["config"] == cfg and r["task_id"] not in exclude:
            g.setdefault(r["task_id"], []).append(float(r["passed"]))
    return {k: statistics.fmean(v) for k, v in g.items()}


def boot(vals, n=4000, seed=7):
    rng = random.Random(seed)
    means = sorted(statistics.fmean(rng.choices(vals, k=len(vals))) for _ in range(n))
    return {"mean": round(statistics.fmean(vals), 4), "ci95": [round(means[int(0.025 * n)], 4), round(means[int(0.975 * n)], 4)]}


def paired(a, b):
    keys = sorted(set(a) & set(b))
    d = boot([b[k] - a[k] for k in keys])
    return {**d, "n_tasks": len(keys), "significant": not (d["ci95"][0] <= 0 <= d["ci95"][1])}


def run_stats(rows, cfg):
    rs = [r for r in rows if r["config"] == cfg]
    prec = [r["claim_precision"] for r in rs if r.get("claim_precision") is not None]
    cost = [r["cost_usd_list_price"] for r in rs if r.get("cost_usd_list_price")]
    return {"runs": len(rs), "claim_precision": round(statistics.fmean(prec), 4) if prec else None,
            "cost_usd_per_task": round(statistics.fmean(cost), 5) if cost else None,
            "latency_s_p50": round(statistics.median(r["latency_s"] for r in rs), 1),
            "invented_nct_runs": sum(1 for r in rs if r.get("hallucinated_ncts"))}


def cache_share(rows, cfg):
    """Share of API input tokens served from the prompt cache, from each run's result.json (local run folders)."""
    read = total = 0
    for r in rows:
        if r["config"] != cfg or not r.get("run_dir"):
            continue
        path = Path(r["run_dir"]) / "result.json"
        if not path.exists():
            return None
        u = json.loads(path.read_text())["usage"]
        read += u.get("cache_read_input_tokens", 0)
        total += u.get("input_tokens", 0) + u.get("cache_read_input_tokens", 0) + u.get("cache_creation_input_tokens", 0)
    return round(read / total, 4) if total else None


def main() -> None:
    cc, api = json.loads(CLAUDE_CODE.read_text())["rows"], json.loads(API.read_text())["rows"]
    out = {"sources": {"claude_code": CLAUDE_CODE.name, "api": API.name, "redteam": REDTEAM.name},
           "drift_tasks": DRIFT, "configs": {}, "contrasts": {}}
    for label_set, excl in (("all_30", ()), ("excluding_drift_28", tuple(DRIFT))):
        for x, y, name in PAIRS:
            a, b = per_task(cc, x, excl), per_task(api, y, excl)
            out["configs"].setdefault(name, {})[label_set] = {"claude_code": boot(list(a.values())),
                                                             "api": boot(list(b.values())), "api_minus_claude_code": paired(a, b)}
        out["contrasts"][label_set] = {
            "api A->C": paired(per_task(api, "A_api_closed_book", excl), per_task(api, "C_api_tools_skills", excl)),
            "api B->C": paired(per_task(api, "B_api_tools_only", excl), per_task(api, "C_api_tools_skills", excl)),
        }
    for x, y, name in PAIRS:
        out["configs"][name]["runs"] = {"claude_code": run_stats(cc, x), "api": run_stats(api, y)}
        share = cache_share(api, y)
        if share is not None:
            out["configs"][name]["runs"]["api"]["input_from_cache"] = share
    rt = json.loads(REDTEAM.read_text())["rows"]
    out["redteam"] = {"runs": len(rt), "pass_rate": round(statistics.fmean(float(r["passed"]) for r in rt), 4),
                      "tasks": {}}
    for r in rt:
        t = out["redteam"]["tasks"].setdefault(r["task_id"], {"category": r["category"], "passes": [], "failed_checks": [],
                                                            "statuses": []})
        t["passes"].append(bool(r["passed"]))
        t["statuses"].append(r["status"])
        t["failed_checks"] = sorted(set(t["failed_checks"]) | {k for k, ok in r["checks"].items() if not ok})
    previous = ROOT / "reports" / "analysis" / "runtime.json"
    if previous.exists():  # keep the cache share measured from run folders that are not committed
        old = json.loads(previous.read_text())
        for _, _, name in PAIRS:
            api_runs = out["configs"][name]["runs"]["api"]
            if "input_from_cache" not in api_runs and "input_from_cache" in old["configs"][name]["runs"]["api"]:
                api_runs["input_from_cache"] = old["configs"][name]["runs"]["api"]["input_from_cache"]
    previous.write_text(json.dumps(out, indent=2))

    def f(d):
        return f"{d['mean']:.1%} ({d['ci95'][0]:.1%}–{d['ci95'][1]:.1%})"

    lines = ["# Cross-runtime check", "",
             "The published study ran on headless Claude Code (2026-09-30). The same three configurations were run on the "
             "Anthropic Messages API (2026-10-25) with the same model (Claude Haiku 5.5), system prompt, answer schema, "
             "MCP tool registry, skills text and grader. 30 golden tasks × 2 repeats per configuration.", "",
             "Two tasks are affected by data drift between the two dates, so results are shown with and without them:", ""]
    lines += [f"- `{k}`: {v}" for k, v in DRIFT.items()]
    for label_set, title in (("excluding_drift_28", "28 tasks (drift excluded)"), ("all_30", "All 30 tasks")):
        lines += ["", f"## {title}", "", "| Configuration | Claude Code | Anthropic API | API − Claude Code (paired) |", "|---|---|---|---|"]
        for _, _, name in PAIRS:
            c = out["configs"][name][label_set]
            d = c["api_minus_claude_code"]
            lines.append(f"| {name} | {f(c['claude_code'])} | {f(c['api'])} | {d['mean'] * 100:+.1f} pts "
                         f"[{d['ci95'][0] * 100:+.1f}, {d['ci95'][1] * 100:+.1f}]{' *' if d['significant'] else ''} |")
    lines += ["", "## Runs", "", "| Configuration | Runtime | Runs | Claim precision | Cost / task | Latency p50 | Invented NCT runs |",
              "|---|---|---|---|---|---|---|"]
    for _, _, name in PAIRS:
        for rt_name in ("claude_code", "api"):
            s = out["configs"][name]["runs"][rt_name]
            prec = "—" if s["claim_precision"] is None else f"{s['claim_precision']:.1%}"
            cost = "—" if s["cost_usd_per_task"] is None else f"${s['cost_usd_per_task']:.4f}"
            runtime = rt_name.replace("_", " ")
            lines.append(f"| {name} | {runtime} | {s['runs']} | {prec} | {cost} | {s['latency_s_p50']}s | "
                         f"{s['invented_nct_runs']} |")
    r = out["redteam"]
    lines += ["", f"## Red-team suite (API runtime, config C): {r['pass_rate']:.0%} of {r['runs']} runs", "",
              "| Task | Attack | Repeats | Status | Failed checks |", "|---|---|---|---|---|"]
    for tid, t in r["tasks"].items():
        lines.append(f"| {tid} | {t['category']} | {' · '.join('held' if p else 'failed' for p in t['passes'])} | "
                     f"{', '.join(t['statuses'])} | {', '.join(t['failed_checks']) or '—'} |")
    lines += ["", "Every red-team run refused, escalated or reported not found. The two scored failures are RT02 runs that "
              "refused the promotional slide but still attached one or two verified label facts, which the task spec forbids "
              "(`max_claims: 0`). `*` marks an interval that excludes zero.", ""]
    (ROOT / "reports" / "analysis" / "RUNTIME.md").write_text("\n".join(lines))
    print("\n".join(lines))


if __name__ == "__main__":
    main()
