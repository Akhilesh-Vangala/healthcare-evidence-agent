"""Hard spend cap for API runs: every call is admitted against its worst case (estimated input plus the full output
allowance) before it is sent, and settled at measured usage after. The ledger persists across runs, so a cap holds
for a whole study, not per process. Unlike budget.py (post-hoc diagnostics on a graded row), this one refuses."""

from __future__ import annotations

import json
import os
import threading
from pathlib import Path

from hea.claude_runner import ROOT


class BudgetExceeded(RuntimeError):
    pass


class SpendCap:
    def __init__(self, usd_cap: float, path: Path = ROOT / ".cache" / "spend.json"):
        from hea.api_runner import PRICES

        self.cap, self.path, self.prices, self.lock = usd_cap, path, PRICES, threading.Lock()
        self.state = json.loads(path.read_text()) if path.exists() else {"usd": 0.0, "calls": 0}

    @classmethod
    def from_env(cls) -> SpendCap:
        cap = os.getenv("HEA_USD_CAP")
        if not cap:
            raise RuntimeError("Set HEA_USD_CAP (USD) before any API run")
        return cls(float(cap))

    def admit(self, model: str, est_input_tokens: int, max_output_tokens: int) -> None:
        if model not in self.prices:
            raise BudgetExceeded(f"no list price for {model}; refusing to run unpriced")
        p_in, p_out = self.prices[model]
        worst = (est_input_tokens * p_in + max_output_tokens * p_out) / 1e6
        with self.lock:
            if self.state["usd"] + worst > self.cap:
                raise BudgetExceeded(f"cap ${self.cap:.2f} would be exceeded (spent ${self.state['usd']:.4f})")

    def record(self, model: str, usage: dict, usd: float | None) -> None:
        with self.lock:
            self.state["usd"] = round(self.state["usd"] + (usd or 0.0), 6)
            self.state["calls"] += 1
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self.path.write_text(json.dumps(self.state, indent=2))
