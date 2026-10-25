#!/usr/bin/env python3
"""Regenerate docs/pass_rate.png from the published ablation numbers."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "pass_rate.png"

ROWS = [
    ("Baseline\n(no LLM)", 0.20, 0.07, 0.37),
    ("A Haiku\nclosed book", 0.23, 0.10, 0.40),
    ("B Haiku\n+ tools", 0.80, 0.63, 0.93),
    ("C Haiku\n+ tools + skills", 0.95, 0.87, 1.00),
    ("D Sonnet\n+ tools + skills", 0.97, 0.90, 1.00),
]


def main() -> None:
    import matplotlib.pyplot as plt

    means = [r[1] for r in ROWS]
    low = [r[1] - r[2] for r in ROWS]
    high = [r[3] - r[1] for r in ROWS]
    labels = [r[0] for r in ROWS]
    colors = ["#94a3b8", "#94a3b8", "#38bdf8", "#0f766e", "#0ea5e9"]

    fig, ax = plt.subplots(figsize=(8.2, 4.2), dpi=160)
    ax.bar(
        range(len(ROWS)),
        [m * 100 for m in means],
        yerr=[[lo * 100 for lo in low], [hi * 100 for hi in high]],
        color=colors,
        capsize=4,
        ecolor="#334155",
        width=0.72,
    )
    ax.set_xticks(range(len(ROWS)))
    ax.set_xticklabels(labels, fontsize=8)
    ax.set_ylabel("Task pass rate (%)")
    ax.set_ylim(0, 105)
    ax.set_title("Healthcare Evidence Agent — golden-set pass rate by configuration")
    ax.axhline(95, color="#0f766e", ls="--", lw=0.8, alpha=0.5)
    fig.tight_layout()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT)
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
