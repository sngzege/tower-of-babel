"""Test runner: executes the pytest suite from the repository root.

Usage: python scripts/test.py [extra pytest args]
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

if __name__ == "__main__":
    args = [sys.executable, "-m", "pytest", "-q", *sys.argv[1:]]
    raise SystemExit(subprocess.call(args, cwd=ROOT))
