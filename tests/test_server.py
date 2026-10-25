"""HTTP service: live-tool proxy, live citation check and the streamed agent, with the network mocked out."""

import json

import pytest
from fastapi.testclient import TestClient
from hea import evidence, limits, server, sources
from hea.claude_runner import RunResult

client = TestClient(server.app)
DOC = "KEYTRUDA is a programmed death receptor-1 (PD-1)-blocking antibody indicated for melanoma."


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    def label(set_id, section, offset=0):
        evidence.record(f"fda:{set_id}:{section}", "fda_label", DOC, brand_name="KEYTRUDA", section=section)
        return {"source_id": f"fda:{set_id}:{section}", "text": DOC}

    monkeypatch.setattr(sources, "fda_get_label_section", label)
    monkeypatch.setattr(sources, "fda_search_labels", lambda drug, limit=5: {"query": drug, "candidates": [
        {"set_id": "abc", "brand_name": "KEYTRUDA", "sections_available": ["indications_and_usage"]}]})
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)


def test_tools_are_listed_from_the_mcp_registry_and_callable():
    names = {t["name"] for t in client.get("/api/tools").json()["tools"]}
    assert names == server.TOOL_NAMES
    r = client.post("/api/tools/fda_get_label_section", json={"set_id": "abc", "section": "indications_and_usage"}).json()
    assert r["evidence"][0]["source_id"] == "fda:abc:indications_and_usage" and r["evidence"][0]["brand_name"] == "KEYTRUDA"
    assert client.post("/api/tools/rm_rf", json={}).status_code == 404


def test_live_check_verifies_against_the_fetched_document_and_reports_divergence():
    ok = client.post("/api/check", json={"source_id": "fda:abc:indications_and_usage", "quote": DOC[:60]}).json()
    bad = client.post("/api/check", json={"source_id": "fda:abc:indications_and_usage",
                                          "quote": DOC[:60].replace("blocking", "activating")}).json()
    assert ok["verified"] and ok["reason"] == "ok"
    assert not bad["verified"] and bad["normalized_quote"][: bad["matched_prefix"]].endswith("(pd-1)-")
    assert client.post("/api/check", json={"source_id": "nope", "quote": "x"}).status_code == 400


def test_agent_is_disabled_without_a_key_and_fails_closed_without_durable_limits(monkeypatch):
    assert client.post("/api/agent/stream", json={"query": "What does the Keytruda label say?"}).status_code == 503
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test")
    monkeypatch.setenv("VERCEL", "1")
    monkeypatch.delenv("KV_REST_API_URL", raising=False)
    r = client.post("/api/agent/stream", json={"query": "What does the Keytruda label say?"})
    assert r.status_code == 503 and "rate limiter" in r.json()["detail"]


def test_agent_stream_emits_events_then_a_graded_result(monkeypatch, tmp_path):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test")
    monkeypatch.setattr(server, "_limiter", lambda: limits.Limiter(limits.MemoryStore(), 10, 1.0))

    def fake_run(query, cfg, runs_dir, on_event=None, **kw):
        run_dir = tmp_path / "r"
        run_dir.mkdir(exist_ok=True)
        with evidence.bound_to(run_dir / "evidence.jsonl"):
            evidence.record("fda:abc:indications_and_usage", "fda_label", DOC, brand_name="KEYTRUDA")
        on_event({"type": "turn", "turn": 1, "ms": 5, "stop_reason": "tool_use", "tool_calls": ["fda_get_label_section"], "usage": {}})
        on_event({"type": "tool", "tool": "fda_get_label_section", "input": {}, "ok": True, "ms": 3})
        answer = {"status": "answered", "summary": "s", "needs_human_review": False, "review_reasons": [],
                  "claims": [{"statement": "x", "source_id": "fda:abc:indications_and_usage", "quote": DOC[:60]}]}
        return RunResult(run_id="r", config={}, query=query, answer=answer, run_dir=str(run_dir),
                         usage={"input_tokens": 1, "cache_read_input_tokens": 0, "cache_creation_input_tokens": 0,
                                "output_tokens": 1}, cost_usd_list_price=0.0001)

    import hea.api_runner as api_runner
    monkeypatch.setattr(api_runner, "run", fake_run)
    with client.stream("POST", "/api/agent/stream", json={"query": "What does the Keytruda label say?"}) as r:
        events = [json.loads(line[6:]) for line in r.iter_lines() if line.startswith("data: ")]
    assert [e["type"] for e in events] == ["start", "turn", "tool", "result"]
    assert events[-1]["claims"][0]["verified"] and events[-1]["invented_nct_ids"] == []


def test_security_headers_and_request_id():
    r = client.get("/api/health")
    assert r.headers["x-frame-options"] == "DENY" and len(r.headers["x-request-id"]) >= 8
