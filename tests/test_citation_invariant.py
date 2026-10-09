"""Formal citation invariant: verified ⇒ source in evidence and quote ⊆ text."""

from cmg_agent.verify import verify_claims


def test_verified_implies_source_and_substring():
    ev = {
        "fda:1:indications_and_usage": {
            "source_id": "fda:1:indications_and_usage",
            "kind": "fda_label",
            "brand_name": "X",
            "section": "indications_and_usage",
            "text": "Drug X is indicated for the treatment of condition Y in adults.",
        }
    }
    quote = "Drug X is indicated for the treatment of condition Y in adults."
    out = verify_claims(
        {"claims": [{"statement": "X treats Y", "source_id": "fda:1:indications_and_usage", "quote": quote}]},
        ev,
    )
    assert out[0]["verified"]
    # Negatives
    assert verify_claims(
        {"claims": [{"statement": "X", "source_id": "fda:missing", "quote": quote}]},
        ev,
    )[0]["reason"] == "unknown_source_id"
    assert verify_claims(
        {"claims": [{"statement": "X", "source_id": "fda:1:indications_and_usage", "quote": "Drug X cures everything forever."}]},
        ev,
    )[0]["reason"] == "quote_not_in_source"
