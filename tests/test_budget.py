from cmg_agent.budget import RunBudget


def test_budget_flags_tool_and_cost_overrun():
    b = RunBudget(max_tool_calls=2, max_cost_usd=0.01, max_unverified_claims=0)
    out = b.check({"tool_calls": 5, "cost_usd_list_price": 0.05, "n_claims": 2, "n_verified": 2, "latency_s": 10})
    assert not out["ok"]
    assert any("tool_calls" in v for v in out["violations"])
    assert any("cost_usd" in v for v in out["violations"])


def test_budget_ok_when_inside_limits():
    b = RunBudget()
    out = b.check({"tool_calls": 3, "cost_usd_list_price": 0.003, "n_claims": 2, "n_verified": 2, "latency_s": 14})
    assert out["ok"]
