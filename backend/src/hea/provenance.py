"""Claim → source provenance graph built from an answer + evidence log.

Used for audit trails and for the HTML eval report. A verified claim always
has a path: claim → source_id → evidence row → (kind, brand/section/url).
"""

from __future__ import annotations

from typing import Any

from hea.evidence import normalize
from hea.verify import verify_claims


def build_provenance(answer: dict[str, Any] | None, evidence: dict[str, dict[str, Any]]) -> dict[str, Any]:
    if not answer:
        return {"nodes": [], "edges": [], "verified_claims": 0, "unverified_claims": 0}

    checks = verify_claims(answer, evidence)
    nodes: dict[str, dict[str, Any]] = {}
    edges: list[dict[str, Any]] = []

    nodes["answer"] = {"id": "answer", "type": "answer", "status": answer.get("status")}
    for sid, row in evidence.items():
        nodes[sid] = {
            "id": sid,
            "type": "source",
            "kind": row.get("kind"),
            "brand_name": row.get("brand_name"),
            "section": row.get("section"),
            "url": row.get("url"),
            "chars": len(row.get("text") or ""),
        }
        edges.append({"from": "tool", "to": sid, "rel": "retrieved"})

    verified = 0
    for i, (claim, check) in enumerate(zip(answer.get("claims") or [], checks, strict=False)):
        cid = f"claim:{i}"
        nodes[cid] = {
            "id": cid,
            "type": "claim",
            "statement": claim.get("statement"),
            "source_id": claim.get("source_id"),
            "verified": check["verified"],
            "reason": check["reason"],
            "quote_chars": len(normalize(str(claim.get("quote") or ""))),
        }
        edges.append({"from": "answer", "to": cid, "rel": "asserts"})
        edges.append({
            "from": cid,
            "to": claim.get("source_id"),
            "rel": "cites",
            "verified": check["verified"],
        })
        if check["verified"]:
            verified += 1

    return {
        "nodes": list(nodes.values()),
        "edges": edges,
        "n_sources": sum(1 for n in nodes.values() if n["type"] == "source"),
        "n_claims": len(answer.get("claims") or []),
        "verified_claims": verified,
        "unverified_claims": len(answer.get("claims") or []) - verified,
    }
