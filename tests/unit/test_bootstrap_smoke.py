"""Phase 2 smoke test: headless bootstrap runs N frames and exits 0.

Requires pygame-ce; skipped automatically when it is unavailable.
"""

from __future__ import annotations

import pytest

pygame = pytest.importorskip("pygame", reason="pygame-ce is not installed")


def test_headless_bootstrap_runs_frames() -> None:
    from main import main

    exit_code = main(["--headless", "--frames", "10", "--log-level", "WARNING"])
    assert exit_code == 0
