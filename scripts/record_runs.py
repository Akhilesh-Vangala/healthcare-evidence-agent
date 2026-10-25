#!/usr/bin/env python3
"""Record real agent runs on the Anthropic API runtime for the console's replay panel.

    HEA_USD_CAP=1 python scripts/record_runs.py C01 V01 T01 R02

Each run is the exact event sequence /api/agent/stream emits (start, every model turn and tool call, then the graded
result), with the model, date and git commit, written to data/recorded_runs.jsonl. Spend goes through spend.SpendCap.
"""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from datetime import date
from pathlib import Path

from hea import evidence
from hea.api_runner import ApiConfig, run
from hea.claude_runner import ROOT
from hea.spend import SpendCap
from hea.verify import grade, verify_claims

OUT = ROOT / "data" / "recorded_runs.jsonl"
TITLES = {"C01": "Compare two boxed warnings", "V01": "Medicare coverage, escalated", "T01": "Phase 3 trial landscape",
          "R02": "Refuses a superiority slide", "A01": "Two products share a name"}


def main(ids: list[str]) -> None:
    tasks = {t["id"]: t for t in json.loads((ROOT / "evals/golden/agent_tasks.json").read_text())}
    commit = subprocess.run(["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True, cwd=ROOT).stdout.strip()
    cap, cfg, out = SpendCap.from_env(), ApiConfig(), []
    for tid in ids:
        task, events = tasks[tid], []
        with tempfile.TemporaryDirectory() as tmp:
            events.append({"type": "start", "model": cfg.model})
            result = run(task["query"], cfg, tmp, cap=cap, on_event=events.append)
            docs = evidence.load(Path(result.run_dir) / "evidence.jsonl")
            answer = result.answer or {}
            checks = verify_claims(answer, docs)
            claims = [{**c, **chk} for c, chk in zip(answer.get("claims", []), checks, strict=False)]
            graded = grade(task, result.answer, docs)
        events.append({"type": "result", "answer": result.answer, "claims": claims, "error": result.error,
                       "invented_nct_ids": graded["hallucinated_ncts"], "usage": result.usage,
                       "cost_usd": result.cost_usd_list_price, "latency_s": result.latency_s,
                       "skills_loaded": result.skills_loaded})
        out.append({"id": tid, "title": TITLES.get(tid, tid), "query": task["query"], "model": cfg.model,
                    "recorded_at": date.today().isoformat(), "commit": commit, "passed": graded["passed"], "events": events})
        print(tid, "PASS" if graded["passed"] else "FAIL", f"{graded['n_verified']}/{graded['n_claims']} verified",
              f"${result.cost_usd_list_price:.4f}", f"{result.latency_s}s")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text("".join(json.dumps(x, default=str) + "\n" for x in out))


if __name__ == "__main__":
    main(sys.argv[1:] or ["C01", "V01", "T01", "R02"])
