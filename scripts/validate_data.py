"""Data validation entry point from the repository root.

Usage: python scripts/validate_data.py
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools" / "data_validation"))
sys.path.insert(0, str(ROOT / "src"))

from validate_data import main  # noqa: E402

if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
