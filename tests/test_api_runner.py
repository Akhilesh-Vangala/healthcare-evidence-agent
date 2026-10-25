"""The Anthropic-API runtime with a scripted client: tool loop, skills, evidence binding, caching and the cap."""

import json
from types import SimpleNamespace

import pytest
from hea import api_runner, evidence
from hea.spend import BudgetExceeded, SpendCap


class Block(SimpleNamespace):
    def model_dump(self, exclude_none=True):
        return {k: v for k, v in vars(self).items() if v is not None}


def turn(*blocks, stop="tool_use"):
    usage = SimpleNamespace(input_tokens=10, cache_read_input_tokens=900, cache_creation_input_tokens=100, output_tokens=50)
    return SimpleNamespace(content=list(blocks), stop_reason=stop, usage=usage)


def tool(name, args, i):
    return Block(type="tool_use", id=f"t{i}", name=name, input=args)


ANSWER = {"status": "answered", "summary": "s", "claims": [], "needs_human_review": False, "review_reasons": []}


class Client:
    def __init__(self, turns):
        self.turns, self.requests = list(turns), []
        self.messages = self

    def create(self, **kw):
        self.requests.append(json.loads(json.dumps(kw, default=str)))
        return self.turns.pop(0)


@pytest.fixture(autouse=True)
def offline_tools(monkeypatch):
    async def fake_tools():
        return [{"name": "cms_ncd_search", "description": "search", "input_schema": {"type": "object"}}]

    async def fake_call(name, args):
        evidence.record("cms:ncd:372", "cms_ncd", "Next Generation Sequencing coverage text.")
        return json.dumps({"results": [{"ncd_id": 372}]}), False

    monkeypatch.setattr(api_runner, "_mcp_tools", fake_tools)
    monkeypatch.setattr(api_runner, "_call_mcp", fake_call)


def test_loop_loads_skill_calls_tools_submits_and_logs_evidence_per_run(tmp_path):
    client = Client([
        turn(tool("load_skill", {"name": "cited-evidence"}, 1), tool("cms_ncd_search", {"keywords": "ngs"}, 2)),
        turn(Block(type="thinking", thinking="", signature="sig"), tool("submit_answer", ANSWER, 3)),
    ])
    r = api_runner.run("q", api_runner.ApiConfig(), tmp_path, client=client)
    assert r.answer == ANSWER and r.skills_loaded == ["cited-evidence"] and r.error is None
    assert [c["tool"] for c in r.tool_calls] == ["mcp__hea__cms_ncd_search"]  # the grader's Claude Code naming
    assert "cms:ncd:372" in evidence.load(tmp_path / r.run_id / "evidence.jsonl")
    first, second = client.requests
    assert first["cache_control"] == {"type": "ephemeral"} and first["output_config"] == {"effort": "medium"}
    assert "cited-evidence" in first["system"] and {t["name"] for t in first["tools"]} >= {"submit_answer", "load_skill"}
    assert second["messages"][1]["content"][0]["type"] == "tool_use"  # assistant turn replayed unchanged
    assert r.usage["cache_read_input_tokens"] == 1800 and r.cost_usd_list_price > 0


def test_closed_book_has_no_retrieval_tools_and_no_skills(tmp_path):
    client = Client([turn(tool("submit_answer", ANSWER, 1))])
    api_runner.run("q", api_runner.ApiConfig(name="A", use_tools=False, use_skills=False), tmp_path, client=client)
    assert [t["name"] for t in client.requests[0]["tools"]] == ["submit_answer"]


def test_refusal_and_missing_submission_are_recorded_not_raised(tmp_path):
    r1 = api_runner.run("q", api_runner.ApiConfig(), tmp_path, client=Client([turn(stop="refusal")]))
    assert r1.answer is None and r1.error.startswith("refusal")
    r2 = api_runner.run("q", api_runner.ApiConfig(), tmp_path,
                        client=Client([turn(Block(type="text", text="hi"), stop="end_turn")] * 2))
    assert r2.error == "no submit_answer"


def test_spend_cap_refuses_before_the_call(tmp_path):
    cap = SpendCap(0.0001, tmp_path / "spend.json")
    client = Client([turn(tool("submit_answer", ANSWER, 1))])
    with pytest.raises(BudgetExceeded):
        api_runner.run("q", api_runner.ApiConfig(), tmp_path, client=client, cap=cap)
    assert client.requests == []


def test_skills_index_comes_from_the_shipped_skill_files():
    skills = api_runner.load_skills()
    assert set(skills) == {"cited-evidence", "fda-label-lookup", "review-escalation", "trial-landscape"}
    assert all(s["description"] and s["body"] for s in skills.values())
