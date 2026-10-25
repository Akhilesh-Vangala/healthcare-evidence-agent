"""Runtime budgets for tool calls, tokens, and wall-clock latency.

Budgets are advisory (enforced post-hoc on the grade; the hard USD cap for API runs is spend.py). Post-hoc budget checks surface as
extra grader diagnostics so cost regressions show up in reports.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class RunBudget:
    max_tool_calls: int = 12
    max_latency_s: float = 120.0
    max_cost_usd: float = 0.05
    max_unverified_claims: int = 0

    def check(self, row: dict[str, Any]) -> dict[str, Any]:
        violations: list[str] = []
        tools = row.get("tool_calls")
        if tools is not None and tools > self.max_tool_calls:
            violations.append(f"tool_calls {tools} > {self.max_tool_calls}")
        lat = row.get("latency_s")
        if lat is not None and lat > self.max_latency_s:
            violations.append(f"latency_s {lat} > {self.max_latency_s}")
        cost = row.get("cost_usd_list_price")
        if cost is not None and cost > self.max_cost_usd:
            violations.append(f"cost_usd {cost} > {self.max_cost_usd}")
        n_claims = row.get("n_claims") or 0
        n_verified = row.get("n_verified") or 0
        unverified = n_claims - n_verified
        if unverified > self.max_unverified_claims:
            violations.append(f"unverified_claims {unverified} > {self.max_unverified_claims}")
        return {
            "budget": asdict(self),
            "ok": not violations,
            "violations": violations,
        }


DEFAULT_BUDGET = RunBudget()
