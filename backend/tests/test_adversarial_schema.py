import json
from pathlib import Path

TASKS = json.loads((Path(__file__).resolve().parents[2] / "evals/adversarial/redteam_tasks.json").read_text())


def test_redteam_suite_shape():
    assert len(TASKS) >= 6
    ids = [t["id"] for t in TASKS]
    assert len(ids) == len(set(ids))
    assert any(t["category"] == "injection" for t in TASKS)
    assert any(t["category"] == "promotional" for t in TASKS)
