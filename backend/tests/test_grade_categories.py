"""Task-level grading across the check types used by the golden set."""

from hea.verify import grade

EV = {
    "fda:k:indications_and_usage": {
        "source_id": "fda:k:indications_and_usage",
        "kind": "fda_label",
        "brand_name": "KEYTRUDA",
        "section": "indications_and_usage",
        "text": "KEYTRUDA is a programmed death receptor-1 blocking antibody indicated for the treatment of melanoma.",
    },
    "fda:q:indications_and_usage": {
        "source_id": "fda:q:indications_and_usage",
        "kind": "fda_label",
        "brand_name": "KEYTRUDA QLEX",
        "section": "indications_and_usage",
        "text": "KEYTRUDA QLEX is a combination product with a different set of labeled uses.",
    },
    "ctgov:NCT01234567": {
        "source_id": "ctgov:NCT01234567",
        "kind": "clinical_trial",
        "text": "Randomized phase 3 trial of pembrolizumab versus chemotherapy.",
    },
    "cms:ncd:90.2": {
        "source_id": "cms:ncd:90.2",
        "kind": "cms_ncd",
        "text": "National Coverage Determination for Next Generation Sequencing.",
    },
}


def _ans(status="answered", claims=None, review=False, summary="ok"):
    return {
        "status": status,
        "summary": summary,
        "claims": claims or [],
        "needs_human_review": review,
        "review_reasons": ["x"] if review else [],
    }


def _claim(sid, quote):
    return {"statement": "fact", "source_id": sid, "quote": quote}


def test_required_sections_and_product():
    task = {
        "id": "L",
        "allowed_brands": ["KEYTRUDA"],
        "require_sections": ["indications_and_usage"],
        "min_verified_claims": 1,
    }
    quote = "KEYTRUDA is a programmed death receptor-1 blocking antibody indicated for the treatment of melanoma."
    g = grade(task, _ans(claims=[_claim("fda:k:indications_and_usage", quote)]), EV)
    assert g["passed"]


def test_ambiguous_product_rejects_wrong_brand():
    task = {"id": "A", "allowed_brands": ["KEYTRUDA"], "min_verified_claims": 1}
    quote = "KEYTRUDA QLEX is a combination product with a different set of labeled uses."
    g = grade(task, _ans(claims=[_claim("fda:q:indications_and_usage", quote)]), EV)
    assert not g["passed"] and not g["checks"]["correct_product"]


def test_coverage_requires_review_and_source():
    task = {
        "id": "V",
        "expect_review": True,
        "require_source_ids": ["cms:ncd:90.2"],
        "min_verified_claims": 1,
    }
    quote = "National Coverage Determination for Next Generation Sequencing."
    g = grade(task, _ans(claims=[_claim("cms:ncd:90.2", quote)], review=True), EV)
    assert g["passed"]


def test_min_trials():
    task = {"id": "T", "min_trials": 1}
    quote = "Randomized phase 3 trial of pembrolizumab versus chemotherapy."
    g = grade(task, _ans(claims=[_claim("ctgov:NCT01234567", quote)], summary="See NCT01234567"), EV)
    assert g["passed"] and g["checks"]["min_trials"]


def test_not_found_allows_zero_claims():
    task = {"id": "N", "expect_status": "not_found", "max_claims": 0}
    g = grade(task, _ans(status="not_found", claims=[]), EV)
    assert g["passed"]
