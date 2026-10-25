"""Offline demo entrypoint imports and runs against the checked-in example."""

import sys

from hea.demo import DEFAULT_RUN, main


def test_default_run_exists():
    assert (DEFAULT_RUN / "result.json").exists()
    assert (DEFAULT_RUN / "evidence.jsonl").exists()


def test_demo_main_smoke(monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["hea-demo"])
    main()
    out = capsys.readouterr().out
    assert "KEYTRUDA" in out or "verified" in out.lower() or "Provenance" in out
