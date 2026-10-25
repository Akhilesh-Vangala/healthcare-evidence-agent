"""Load the published ablation and refuse to mix in other run files.

The headline table is 240 rows:

- baseline, 30
- A/B/C × 30 tasks × 2 repeats, 180
- Sonnet, 30

A same-morning single pass of C (90%) lives under ``reports/exploratory/`` and
is not part of this load. Pairing it with the 2-repeat C block is what
produced the 93.3% figure that disagreed with the 95% table.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[4]
REPORTS = ROOT / "reports"
MANIFEST = REPORTS / "canonical.json"


def load_manifest() -> dict[str, Any]:
    return json.loads(MANIFEST.read_text())


def load_canonical_rows() -> list[dict[str, Any]]:
    spec = load_manifest()
    rows: list[dict[str, Any]] = []
    for name in spec["files"]:
        path = REPORTS / name
        if not path.is_file():
            raise FileNotFoundError(f"canonical report missing: {path}")
        data = json.loads(path.read_text())
        for row in data.get("rows") or []:
            item = dict(row)
            item["_report"] = name
            rows.append(item)
    expected = int(spec["expected_rows"])
    if len(rows) != expected:
        raise ValueError(f"canonical study has {len(rows)} rows, manifest expects {expected}")
    return rows


def published_summaries() -> dict[str, dict[str, Any]]:
    """Per-config summary objects as written by the eval harness, not re-pooled."""
    out: dict[str, dict[str, Any]] = {}
    for name in load_manifest()["files"]:
        data = json.loads((REPORTS / name).read_text())
        for cfg, summary in (data.get("summary") or {}).items():
            if cfg in out:
                raise ValueError(f"config {cfg} appears in more than one canonical file")
            out[cfg] = {**summary, "_report": name}
    return out
