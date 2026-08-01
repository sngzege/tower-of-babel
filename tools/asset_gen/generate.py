"""Generate all pixel-art assets into assets/sprites/*.png.

Run:  uv run python tools/asset_gen/generate.py

Deterministic: same input grids -> identical PNGs. Re-run after editing
sprites.py. Pure stdlib (see png_writer.py) — no new dependencies.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from tools.asset_gen.png_writer import write_png  # noqa: E402
from tools.asset_gen.sprites import (  # noqa: E402
    ALL_SPRITES,
    make_npc,
    rows_to_pixels,
)

OUT_DIR = ROOT / "assets" / "sprites"


def main() -> int:
    count = 0
    for sprite_id, sprite in ALL_SPRITES.items():
        pixels = rows_to_pixels(sprite["rows"], sprite["palette"])
        path = OUT_DIR / f"{sprite_id}.png"
        write_png(path, pixels)
        count += 1

    # NPC variants per service (hood color = service accent).
    for service, color in (
        ("loadout", "cyan"),
        ("run_prep", "green"),
        ("upgrades", "gold"),
    ):
        pixels = rows_to_pixels(*[make_npc(color)["rows"], make_npc(color)["palette"]])
        write_png(OUT_DIR / f"npc_{service}.png", pixels)
        count += 1

    print(f"generated {count} sprites -> {OUT_DIR}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
