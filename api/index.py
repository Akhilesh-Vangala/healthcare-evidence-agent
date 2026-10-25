"""Vercel entry point for the agent service (backend/src/hea/server.py)."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend" / "src"))

from hea.server import app  # noqa: E402,F401
