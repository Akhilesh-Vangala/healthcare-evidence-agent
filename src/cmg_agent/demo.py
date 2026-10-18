"""Offline demo: walk a checked-in run for recruiters (no API / no Claude)."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from cmg_agent.evidence import load
from cmg_agent.provenance import build_provenance
from cmg_agent.verify import grade, verify_claims

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_RUN = ROOT / "examples/agent_runs/A01_keytruda_vs_keytruda_qlex"
TASKS = ROOT / "evals/golden/agent_tasks.json"


def main() -> None:
    ap = argparse.ArgumentParser(description="Offline Healthcare Evidence Agent demo")
    ap.add_argument("--run", type=Path, default=DEFAULT_RUN)
    ap.add_argument("--task-id", default="A01")
    args = ap.parse_args()
    console = Console()

    result = json.loads((args.run / "result.json").read_text())
    evidence = load(args.run / "evidence.jsonl")
    answer = result.get("answer") or {}
    tasks = {t["id"]: t for t in json.loads(TASKS.read_text())}
    task = tasks.get(args.task_id)
    graded = grade(task, answer, evidence) if task else None
    claim_checks = verify_claims(answer, evidence)
    prov = build_provenance(answer, evidence)

    console.print(Panel.fit(
        "[bold cyan]Healthcare Evidence Agent[/] — offline demo\n"
        "No model call. Replays a checked-in run through the verifier.",
        border_style="cyan",
    ))
    console.print(f"[bold]Query[/]: {result.get('query')}")
    console.print(f"[bold]Config[/]: {(result.get('config') or {}).get('name')}")
    console.print()

    table = Table(title="Provenance")
    table.add_column("Metric")
    table.add_column("Value", justify="right")
    table.add_row("Sources retrieved", str(prov["n_sources"]))
    table.add_row("Claims", str(prov["n_claims"]))
    table.add_row("Verified claims", f"[green]{prov['verified_claims']}[/]")
    table.add_row("Unverified claims", str(prov["unverified_claims"]))
    if graded:
        table.add_row("Golden task", args.task_id)
        table.add_row("Task passed", "[green]yes[/]" if graded["passed"] else "[red]no[/]")
        failed = [k for k, v in graded["checks"].items() if not v]
        table.add_row("Failed checks", ", ".join(failed) or "—")
    console.print(table)

    console.print()
    console.print("[bold]Summary[/]")
    console.print(answer.get("summary") or "")
    console.print()
    console.print("[bold]Claims[/]")
    for claim, check in zip(answer.get("claims") or [], claim_checks, strict=False):
        mark = "[green]OK[/]" if check["verified"] else f"[red]{check['reason']}[/]"
        console.print(f"• {mark}  {claim.get('statement')}")
        console.print(f"  source: [cyan]{claim.get('source_id')}[/]")
        quote = str(claim.get("quote") or "")
        console.print(f"  quote:  {quote[:180]}{'…' if len(quote) > 180 else ''}")

    console.print()
    console.print("Open the HTML trace: [cyan]examples/trace_viewer/index.html[/]")
    console.print("Full analysis:      [cyan]reports/analysis/REPORT.md[/]")


if __name__ == "__main__":
    main()
