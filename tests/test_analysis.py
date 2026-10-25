"""Paired bootstrap and failure summaries over synthetic rows."""

from hea.analysis.paired import paired_delta, summarize_efficiency, summarize_failures


def _row(task_id, config, passed, **kw):
    base = {
        "task_id": task_id,
        "config": config,
        "passed": passed,
        "category": "label",
        "checks": {"has_answer": True, "review_flag": passed},
        "failed_claim_reasons": [],
        "hallucinated_ncts": [],
        "latency_s": 10.0,
        "cost_usd_list_price": 0.003,
        "tool_calls": 3,
        "claim_precision": 1.0 if passed else 0.0,
        "input_tokens": 1000,
        "output_tokens": 200,
        "n_claims": 2,
        "n_verified": 2 if passed else 0,
    }
    base.update(kw)
    return base


def test_paired_delta_tools_lift():
    rows = []
    for tid in ["T1", "T2", "T3", "T4", "T5"]:
        rows.append(_row(tid, "A_closed_book", False))
        rows.append(_row(tid, "B_tools_only", True))
    d = paired_delta(rows, "A_closed_book", "B_tools_only", n_boot=500)
    assert d["delta_pass_rate"] == 1.0
    assert d["delta_significant_vs_zero"]
    assert d["contingency"]["b_pass_a_fail"] == 5


def test_failure_taxonomy_over_escalation():
    rows = [
        _row("L1", "C", False, checks={"has_answer": True, "review_flag": False}),
        _row("L2", "C", False, checks={"has_answer": True, "correct_product": False}),
        _row("L3", "C", True),
    ]
    s = summarize_failures(rows, "C")
    assert s["n_failed"] == 2
    assert s["over_escalation_only"] == 1


def test_efficiency_means():
    rows = [_row("L1", "C", True), _row("L2", "C", False, cost_usd_list_price=0.01)]
    e = summarize_efficiency(rows, "C")
    assert e["n_runs"] == 2
    assert e["pass_rate"] == 0.5
