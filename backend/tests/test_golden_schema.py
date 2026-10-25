"""Golden task file is complete and internally consistent."""

import json
from pathlib import Path

TASKS = json.loads((Path(__file__).resolve().parents[2] / "evals/golden/agent_tasks.json").read_text())


def test_thirty_tasks_unique_ids():
    ids = [t["id"] for t in TASKS]
    assert len(TASKS) == 30
    assert len(set(ids)) == 30


def test_every_task_has_query_and_category():
    for t in TASKS:
        assert t.get("query") and t.get("category") and t.get("id")
