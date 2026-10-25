#!/usr/bin/env python3
"""Bundle the published study and five saved runs for the operator console.

No model calls. The console reads this file; it does not recompute the study.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend" / "src"))

from hea.analysis.study import load_manifest, published_summaries  # noqa: E402
from hea.evidence import load  # noqa: E402
from hea.verify import verify_claims  # noqa: E402

OUT = ROOT / "frontend" / "src" / "generated" / "study.json"

TRACES = [
    ("A01_keytruda_vs_keytruda_qlex", "A01", "Two products share a name"),
    ("L01_tecentriq_lung_indications", "L01", "Label indications"),
    ("N01_not_found_fake_drug", "N01", "Name not in openFDA"),
    ("R02_refuses_superiority_slide", "R02", "Refuses a superiority slide"),
    ("V01_medicare_ngs_coverage", "V01", "Medicare coverage, escalated"),
]


def _tasks() -> list[dict]:
    tasks = json.loads((ROOT / "evals/golden/agent_tasks.json").read_text())
    by_id = {t["id"]: t for t in tasks}
    report = json.loads(
        (ROOT / "reports/eval-A_closed_book-B_tools_only-C_tools_skills-20260930-115633.json").read_text()
    )
    grouped: dict[str, list[dict]] = {}
    for row in report["rows"]:
        if row["config"] != "C_tools_skills":
            continue
        grouped.setdefault(row["task_id"], []).append(row)
    out = []
    for tid, task in by_id.items():
        rows = grouped.get(tid, [])
        fails: list[str] = []
        for row in rows:
            if row.get("passed"):
                continue
            fails.extend(k for k, ok in (row.get("checks") or {}).items() if not ok)
        out.append(
            {
                "id": tid,
                "category": task.get("category"),
                "query": task.get("query"),
                "passes": [bool(r.get("passed")) for r in rows],
                "failed_checks": sorted(set(fails)),
            }
        )
    return out


def _trace(folder: str, task_id: str, title: str) -> dict:
    run_dir = ROOT / "examples/agent_runs" / folder
    result = json.loads((run_dir / "result.json").read_text())
    evidence = load(run_dir / "evidence.jsonl")
    answer = result.get("answer") or {}
    checks = verify_claims(answer, evidence)
    claims = []
    for claim, check in zip(answer.get("claims") or [], checks, strict=False):
        sid = str(claim.get("source_id") or "")
        src = evidence.get(sid) or {}
        claims.append(
            {
                "statement": claim.get("statement"),
                "source_id": sid,
                "quote": claim.get("quote"),
                "verified": bool(check["verified"]),
                "reason": check["reason"],
                "kind": src.get("kind"),
                "brand_name": src.get("brand_name"),
                "section": src.get("section"),
            }
        )
    cfg = result.get("config") or {}
    return {
        "id": task_id,
        "title": title,
        "query": result.get("query"),
        "model": cfg.get("model"),
        "config": cfg.get("name"),
        "status": answer.get("status"),
        "summary": answer.get("summary"),
        "needs_human_review": bool(answer.get("needs_human_review")),
        "review_reasons": answer.get("review_reasons") or [],
        "latency_s": result.get("latency_s"),
        "cost_usd": result.get("cost_usd_list_price"),
        "skills": [s for s in (result.get("skills_loaded") or []) if s],
        "n_sources": len(evidence),
        "claims": claims,
    }


def _runtime() -> dict:
    """Cross-runtime check and red-team results, from reports/analysis/runtime.json (backend/scripts/runtime_crosscheck.py)."""
    path = ROOT / "reports/analysis/runtime.json"
    if not path.exists():
        return {}
    rt = json.loads(path.read_text())
    labels = {"closed book": "Haiku, no tools", "tools only": "Haiku + tools", "tools + skills": "Haiku + tools + skills"}
    ids = {"closed book": "A_api_closed_book", "tools only": "B_api_tools_only", "tools + skills": "C_api_tools_skills"}
    configs = []
    for name, c in rt["configs"].items():
        run = c["runs"]["api"]
        configs.append({"id": ids[name], "label": labels[name], "pass_rate": c["all_30"]["api"]["mean"],
                        "ci": c["all_30"]["api"]["ci95"], "n_runs": run["runs"], "claim_precision": run["claim_precision"],
                        "cost_usd": run["cost_usd_per_task"], "latency_s": run["latency_s_p50"],
                        "cache_share": run.get("input_from_cache")})
    c = rt["configs"]["tools + skills"]
    deltas = [
        {"contrast": "tools + skills: API − Claude Code, 28 tasks", **_d(c["excluding_drift_28"]["api_minus_claude_code"])},
        {"contrast": "tools + skills: API − Claude Code, all 30", **_d(c["all_30"]["api_minus_claude_code"])},
        {"contrast": "API: closed book → tools + skills", **_d(rt["contrasts"]["all_30"]["api A->C"])},
    ]
    note = ("Same model, prompts, MCP tools, skills and grader; only the runtime and the date differ. Two tasks changed "
            "under the study because the live data changed (" + "; ".join(f"{k}: {v}" for k, v in rt["drift_tasks"].items())
            + "), so the like-for-like comparison is on the other 28.")
    red = rt["redteam"]
    redteam = {"runs": red["runs"], "pass_rate": red["pass_rate"],
               "tasks": [{"id": k, "category": v["category"], "passes": v["passes"], "failed_checks": v["failed_checks"]}
                         for k, v in red["tasks"].items()],
               "note": ("Six adversarial prompts × 2 repeats on the API runtime. Every run refused, escalated or reported "
                        "not found; the two scored failures are RT02 refusals that still attached verified label facts, "
                        "which the spec forbids.")}
    headline = {"api_c_28": c["excluding_drift_28"]["api"]["mean"], "claude_code_c_28": c["excluding_drift_28"]["claude_code"]["mean"]}
    return {"runtime": {"configs": configs, "deltas": deltas, "note": note, "headline": headline}, "redteam": redteam}


def _d(x: dict) -> dict:
    return {"delta": x["mean"], "ci95": x["ci95"], "significant": x["significant"]}


def main() -> int:
    spec = load_manifest()
    summaries = published_summaries()
    order = ["BASELINE", "A_closed_book", "B_tools_only", "C_tools_skills", "D_tools_skills_sonnet"]
    labels = {
        "BASELINE": "Fixed pipeline",
        "A_closed_book": "Haiku, no tools",
        "B_tools_only": "Haiku + tools",
        "C_tools_skills": "Haiku + tools + skills",
        "D_tools_skills_sonnet": "Sonnet + tools + skills",
    }
    configs = []
    for key in order:
        row = summaries[key]
        configs.append(
            {
                "id": key,
                "label": labels[key],
                "pass_rate": row["task_pass_rate"],
                "ci": row["task_pass_ci95"],
                "n_runs": row["n_runs"],
                "claim_precision": row.get("claim_precision_mean"),
                "cost_usd": row.get("cost_usd_per_task_list_price"),
                "latency_s": row.get("latency_s_median"),
                "invented_nct_runs": row.get("invented_nct_runs"),
            }
        )
    stats = json.loads((ROOT / "reports/analysis/stats.json").read_text())
    payload = {
        "study": spec["study"],
        "n_rows": stats["n_rows"],
        "configs": configs,
        "deltas": stats["paired_deltas"],
        "tasks": _tasks(),
        "traces": [_trace(*item) for item in TRACES],
        "excluded_note": (
            "A 30-run single pass of config C (90%) is stored under reports/exploratory "
            "and is not in these figures."
        ),
        "redteam_note": "The red-team suite was scored on the API runtime; see reports/analysis/RUNTIME.md.",
        **_runtime(),
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, indent=2))
    print(f"wrote {OUT} ({OUT.stat().st_size} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
