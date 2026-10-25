#!/usr/bin/env python3
"""Build paired-delta stats, failure taxonomy, and figures from reports/*.json."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend" / "src"))

from hea.analysis.paired import paired_delta, summarize_efficiency, summarize_failures  # noqa: E402
from hea.analysis.study import load_canonical_rows, load_manifest  # noqa: E402

REPORTS = ROOT / "reports"
OUT = REPORTS / "analysis"
PAIRS = [
    ("BASELINE", "C_tools_skills"),
    ("A_closed_book", "B_tools_only"),
    ("B_tools_only", "C_tools_skills"),
    ("C_tools_skills", "D_tools_skills_sonnet"),
]


def _load_rows() -> list[dict]:
    return load_canonical_rows()


def _plot_pareto(eff: list[dict], dest: Path) -> None:
    try:
        import matplotlib.pyplot as plt
    except ImportError:
        return
    xs, ys, labels = [], [], []
    for e in eff:
        if e.get("cost_usd_mean") is None:
            continue
        xs.append(e["cost_usd_mean"])
        ys.append((e.get("pass_rate") or 0) * 100)
        labels.append(e["config"])
    if not xs:
        return
    fig, ax = plt.subplots(figsize=(7.2, 4.4), dpi=160)
    ax.scatter(xs, ys, s=70, c="#0f766e")
    for x, y, lab in zip(xs, ys, labels, strict=False):
        ax.annotate(lab, (x, y), textcoords="offset points", xytext=(6, 4), fontsize=8)
    ax.set_xlabel("Mean list-price cost / task (USD)")
    ax.set_ylabel("Pass rate (%)")
    ax.set_title("Cost–quality frontier")
    ax.set_ylim(0, 105)
    fig.tight_layout()
    fig.savefig(dest)
    plt.close(fig)


def _plot_failures(fails: dict, dest: Path) -> None:
    try:
        import matplotlib.pyplot as plt
    except ImportError:
        return
    checks = fails.get("failed_checks") or {}
    if not checks:
        # still write empty-ish note chart
        fig, ax = plt.subplots(figsize=(6, 3), dpi=140)
        ax.axis("off")
        ax.text(0.5, 0.5, f"{fails['config']}: no failures" if fails.get("n_failed") == 0 else "no check data",
                ha="center", va="center")
        fig.savefig(dest)
        plt.close(fig)
        return
    labels = list(checks.keys())
    vals = list(checks.values())
    fig, ax = plt.subplots(figsize=(7.2, 3.8), dpi=160)
    ax.barh(labels[::-1], vals[::-1], color="#b45309")
    ax.set_xlabel("Failed check count")
    ax.set_title(f"Failure taxonomy — {fails['config']}")
    fig.tight_layout()
    fig.savefig(dest)
    plt.close(fig)


def main() -> int:
    rows = _load_rows()
    if not rows:
        print("no rows", file=sys.stderr)
        return 1
    OUT.mkdir(parents=True, exist_ok=True)

    configs = sorted({r["config"] for r in rows})
    deltas = [paired_delta(rows, a, b) for a, b in PAIRS if a in configs and b in configs]
    failures = {c: summarize_failures(rows, c) for c in configs}
    efficiency = [summarize_efficiency(rows, c) for c in configs]

    spec = load_manifest()
    payload = {
        "study": spec["study"],
        "n_rows": len(rows),
        "source_files": spec["files"],
        "excluded": spec.get("excluded", []),
        "reported_separately": spec.get("reported_separately", []),
        "configs": configs,
        "paired_deltas": deltas,
        "failures": failures,
        "efficiency": efficiency,
    }
    (OUT / "stats.json").write_text(json.dumps(payload, indent=2))

    md = [
        "# Eval analysis\n",
        f"Study `{spec['study']}`: **{len(rows)}** rows from {len(spec['files'])} files. "
        "The same-morning single-pass of C is not included.\n",
        "Source files:\n",
    ]
    for name in spec["files"]:
        md.append(f"- `{name}`")
    md.append("\n## Paired deltas\n")
    md.append("| Contrast | Δ pass | 95% CI | sig≠0 | B∨¬A | A∨¬B |")
    md.append("|---|---:|---|:---:|---:|---:|")
    for d in deltas:
        ci = d.get("delta_ci95") or [None, None]
        c = d.get("contingency") or {}
        md.append(
            f"| {d['config_a']} → {d['config_b']} | {d.get('delta_pass_rate', 0):+.1%} | "
            f"[{ci[0]:+.1%}, {ci[1]:+.1%}] | {'yes' if d.get('delta_significant_vs_zero') else 'no'} | "
            f"{c.get('b_pass_a_fail', 0)} | {c.get('a_pass_b_fail', 0)} |"
        )
    md.append("\n## Efficiency\n")
    md.append("| Config | Task pass | Cost/task | Latency med | Tools/task | Claim prec |")
    md.append("|---|---:|---:|---:|---:|---:|")
    for e in efficiency:
        md.append(
            f"| {e['config']} | {(e.get('pass_rate') or 0):.1%} | "
            f"${(e.get('cost_usd_mean') or 0):.4f} | {e.get('latency_s_median')} | "
            f"{e.get('tool_calls_mean')} | {(e.get('claim_precision_mean') or 0):.1%} |"
        )
    md.append(
        "\nTask pass is the mean of per-task means (repeats averaged first). "
        "It is the same definition as the README table.\n"
    )
    md.append("\n## Not scored\n")
    md.append(
        "`evals/adversarial/redteam_tasks.json` is a prompt spec. "
        "No configuration was run on it, so it has no pass rate.\n"
    )
    md.append("\n## Failure taxonomy (C_tools_skills)\n")
    fc = failures.get("C_tools_skills") or {}
    md.append(
        f"Failed runs: {fc.get('n_failed')} / {fc.get('n_runs')}. "
        f"Over-escalation-only: {fc.get('over_escalation_only')}. "
        f"Invented NCT runs: {fc.get('invented_nct_runs')}.\n"
    )
    md.append("```")
    md.append(json.dumps(fc.get("failed_checks") or {}, indent=2))
    md.append("```\n")
    (OUT / "REPORT.md").write_text("\n".join(md))

    _plot_pareto(efficiency, OUT / "cost_quality.png")
    if "C_tools_skills" in failures:
        _plot_failures(failures["C_tools_skills"], OUT / "failures_C.png")
    if "B_tools_only" in failures:
        _plot_failures(failures["B_tools_only"], OUT / "failures_B.png")

    print(f"wrote {OUT / 'stats.json'}")
    print(f"wrote {OUT / 'REPORT.md'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
