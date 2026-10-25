"""Re-grade a saved run directory without calling a model.

Given ``result.json`` + ``evidence.jsonl`` (and optionally a golden task),
replay reconstructs the grade and provenance graph. Useful for CI, audits,
and regenerating reports after grader changes.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from hea.contracts import parse_answer
from hea.evidence import load
from hea.provenance import build_provenance
from hea.verify import grade


def replay_run(run_dir: Path, task: dict[str, Any] | None = None) -> dict[str, Any]:
    run_dir = Path(run_dir)
    result = json.loads((run_dir / "result.json").read_text())
    evidence = load(run_dir / "evidence.jsonl")
    answer = result.get("answer")
    contract_ok = True
    contract_error = None
    try:
        parse_answer(answer)
    except Exception as exc:  # noqa: BLE001
        contract_ok = False
        contract_error = str(exc)

    graded = None
    if task is not None:
        graded = grade(task, answer, evidence)

    return {
        "run_dir": str(run_dir),
        "run_id": result.get("run_id"),
        "query": result.get("query"),
        "config": result.get("config"),
        "contract_ok": contract_ok,
        "contract_error": contract_error,
        "grade": graded,
        "provenance": build_provenance(answer, evidence),
        "n_evidence": len(evidence),
        "latency_s": result.get("latency_s"),
        "cost_usd_list_price": result.get("cost_usd_list_price"),
    }


def _load_task(tasks_path: Path, task_id: str) -> dict[str, Any]:
    tasks = json.loads(tasks_path.read_text())
    for t in tasks:
        if t["id"] == task_id:
            return t
    raise KeyError(f"task {task_id} not in {tasks_path}")


def main() -> None:
    ap = argparse.ArgumentParser(description="Replay and re-grade a saved agent run")
    ap.add_argument("run_dir", type=Path)
    ap.add_argument("--task-id")
    ap.add_argument("--tasks", default="evals/golden/agent_tasks.json")
    ap.add_argument("--out", type=Path, help="optional JSON output path")
    args = ap.parse_args()
    task = _load_task(Path(args.tasks), args.task_id) if args.task_id else None
    payload = replay_run(args.run_dir, task)
    text = json.dumps(payload, indent=2)
    if args.out:
        args.out.write_text(text)
        print(f"wrote {args.out}")
    else:
        print(text)


if __name__ == "__main__":
    main()
