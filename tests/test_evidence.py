"""Evidence store and normalize helpers."""

from pathlib import Path

from cmg_agent.evidence import load, normalize, record


def test_normalize_collapses_whitespace_and_smart_quotes():
    assert normalize("  Hello “world” —  there  ") == 'hello "world" - there'


def test_record_and_load_roundtrip(tmp_path: Path, monkeypatch):
    path = tmp_path / "ev.jsonl"
    monkeypatch.setenv("CMG_EVIDENCE_PATH", str(path))
    record("fda:x:indications_and_usage", "fda_label", "Alpha beta gamma delta epsilon.", brand_name="X")
    record("ctgov:NCT01234567", "clinical_trial", "A phase 3 study of something useful.")
    rows = load(path)
    assert set(rows) == {"fda:x:indications_and_usage", "ctgov:NCT01234567"}
    assert rows["fda:x:indications_and_usage"]["brand_name"] == "X"
