"""Per-run evidence store.

Every document a tool returns to the agent is appended here with a stable
``source_id``. The verifier later checks that each quote the agent cites is a
verbatim substring of the document it names, so citations are checked against
what the agent actually saw, not against what it claims to have seen.
"""

from __future__ import annotations

import contextlib
import contextvars
import json
import os
import re
import time
from collections.abc import Iterator
from pathlib import Path
from typing import Any

DEFAULT_PATH = Path(__file__).resolve().parents[3] / ".cache" / "evidence_default.jsonl"

# In-process runs (the API runtime, the web service) bind their own evidence file per run; the stdio MCP server used
# by Claude Code is one process per run and uses HEA_EVIDENCE_PATH instead.
_BOUND: contextvars.ContextVar[Path | None] = contextvars.ContextVar("evidence_path", default=None)


@contextlib.contextmanager
def bound_to(path: Path) -> Iterator[None]:
    token = _BOUND.set(path)
    try:
        yield
    finally:
        _BOUND.reset(token)


def _path() -> Path:
    p = _BOUND.get() or Path(os.environ.get("HEA_EVIDENCE_PATH") or DEFAULT_PATH)
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


def record(source_id: str, kind: str, text: str, **meta: Any) -> None:
    row = {
        "source_id": source_id,
        "kind": kind,
        "text": text,
        "retrieved_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        **meta,
    }
    with _path().open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(row) + "\n")


def load(path: str | Path) -> dict[str, dict[str, Any]]:
    """Load an evidence file into {source_id: row}; later rows win."""
    out: dict[str, dict[str, Any]] = {}
    p = Path(path)
    if not p.exists():
        return out
    for line in p.read_text(encoding="utf-8").splitlines():
        if line.strip():
            row = json.loads(line)
            out[row["source_id"]] = row
    return out


_WS = re.compile(r"\s+")
_QUOTES = str.maketrans({"‘": "'", "’": "'", "“": '"', "”": '"', "–": "-", "—": "-"})


def normalize(text: str) -> str:
    return _WS.sub(" ", text.translate(_QUOTES)).strip().lower()
