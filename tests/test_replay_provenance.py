"""Replay + provenance against checked-in example runs."""

import json
from pathlib import Path

from hea.contracts import parse_answer
from hea.provenance import build_provenance
from hea.replay import replay_run

ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = ROOT / "examples/agent_runs/A01_keytruda_vs_keytruda_qlex"


def test_example_answer_matches_contract():
    result = json.loads((EXAMPLE / "result.json").read_text())
    ans = parse_answer(result["answer"])
    assert ans is not None
    assert ans.status in {"answered", "not_found", "refused"}
    assert ans.claims


def test_replay_builds_provenance():
    out = replay_run(EXAMPLE)
    assert out["contract_ok"]
    prov = out["provenance"]
    assert prov["n_sources"] >= 1
    assert prov["verified_claims"] >= 1
    assert any(n["type"] == "claim" and n["verified"] for n in prov["nodes"])


def test_provenance_marks_bad_source():
    answer = {
        "status": "answered",
        "summary": "x",
        "claims": [{"statement": "x", "source_id": "missing", "quote": "not in any document at all here"}],
        "needs_human_review": False,
        "review_reasons": [],
    }
    prov = build_provenance(answer, {})
    assert prov["verified_claims"] == 0
    assert prov["unverified_claims"] == 1
