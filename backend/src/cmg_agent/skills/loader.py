"""Skill catalog for the baseline FastAPI path.

Claude Code loads the canonical skills from ``agent/workspace/.claude/skills/``.
These in-package SKILL.md files remain for the fixed-pipeline API catalog.
"""

from __future__ import annotations

from pathlib import Path

SKILLS_ROOT = Path(__file__).resolve().parent
WORKSPACE_SKILLS = Path(__file__).resolve().parents[4] / "agent" / "workspace" / ".claude" / "skills"


def load_skills() -> dict[str, str]:
    skills: dict[str, str] = {}
    for root in (SKILLS_ROOT, WORKSPACE_SKILLS):
        if not root.exists():
            continue
        for path in root.glob("*/SKILL.md"):
            skills[path.parent.name] = path.read_text(encoding="utf-8")
    return skills


def skill_catalog() -> list[str]:
    return sorted(load_skills().keys())
