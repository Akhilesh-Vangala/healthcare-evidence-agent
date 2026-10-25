"""The published ablation is one study, and the red-team file is not a result."""

import json
from pathlib import Path

from hea.analysis.study import load_canonical_rows, load_manifest, published_summaries

ROOT = Path(__file__).resolve().parents[1]


def test_canonical_rows_are_the_published_240():
    spec = load_manifest()
    rows = load_canonical_rows()
    assert spec["study"] == "published-240"
    assert len(rows) == 240
    assert sum(1 for r in rows if r["config"] == "C_tools_skills") == 60
    assert not any(str(r["task_id"]).startswith("RT") for r in rows)


def test_pilot_c_is_not_in_the_canonical_files():
    spec = load_manifest()
    joined = " ".join(spec["files"])
    assert "pilot" not in joined
    assert "114930" not in joined
    pilot = ROOT / "reports/exploratory/eval-C_tools_skills-pilot-20260930-114930.json"
    assert pilot.is_file()
    pilot_rows = json.loads(pilot.read_text())["rows"]
    assert len(pilot_rows) == 30
    assert all(r["config"] == "C_tools_skills" for r in pilot_rows)


def test_published_summaries_match_the_readme_headline():
    summaries = published_summaries()
    assert summaries["C_tools_skills"]["task_pass_rate"] == 0.95
    assert summaries["C_tools_skills"]["n_runs"] == 60
    assert summaries["BASELINE"]["task_pass_rate"] == 0.2
    assert summaries["A_closed_book"]["n_runs"] == 60
    assert summaries["D_tools_skills_sonnet"]["n_runs"] == 30


def test_checked_in_analysis_uses_only_the_canonical_study():
    stats = json.loads((ROOT / "reports/analysis/stats.json").read_text())
    assert stats["n_rows"] == 240
    assert stats["study"] == "published-240"
    assert all("pilot" not in name and "114930" not in name for name in stats["source_files"])


def test_console_bundle_matches_the_published_study():
    bundle = json.loads((ROOT / "frontend/src/generated/study.json").read_text())
    assert bundle["n_rows"] == 240
    assert bundle["study"] == "published-240"
    assert len(bundle["tasks"]) == 30
    assert len(bundle["traces"]) == 5
    assert bundle["configs"][3]["id"] == "C_tools_skills"
    assert bundle["configs"][3]["pass_rate"] == 0.95


def test_redteam_file_is_marked_unscored():
    spec = load_manifest()
    assert any("redteam" in item["file"] for item in spec["not_scored"])
    note = (ROOT / "evals/adversarial/README.md").read_text().lower()
    assert "not scored" in note
    assert "no pass rate" in note or "no red-team pass rate" in note
