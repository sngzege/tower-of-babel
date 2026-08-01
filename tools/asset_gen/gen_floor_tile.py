"""Generate a seamless dark Babylon stone floor tile (32x32, fully opaque).

The AI-generated tile had chroma-key artifacts (grey squares inside each
tile). This procedural tile is deterministic, seamless (edges wrap), and
matches PAL-01: night base with subtle stone noise + faint cyan rune crack.

Run:  uv run python tools/asset_gen/gen_floor_tile.py
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

import pygame  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "assets" / "sprites" / "tile_floor.png"

TILE = 32

# PAL-01 (ART_DIRECTION.md)
NIGHT = (20, 26, 46)
STONE = (42, 51, 82)
SHADOW = (29, 36, 64)
RITE_CYAN = (125, 227, 232)


def _hash(px: int, py: int, seed: int) -> int:
    """Deterministic pseudo-random from pixel coords (seamless-safe)."""
    n = (px * 374761393 + py * 668265263 + seed * 1442695040888963407) & 0xFFFFFFFF
    n = ((n ^ (n >> 13)) * 1274126177) & 0xFFFFFFFF
    return n ^ (n >> 16)


def make_tile() -> pygame.Surface:
    surf = pygame.Surface((TILE, TILE))
    # Base fill: night.
    surf.fill(NIGHT)
    # Stone blocks: 4x4 grid of flagstones, each slightly varied.
    block = TILE // 4
    for by in range(4):
        for bx in range(4):
            variant = (_hash(bx, by, 7) % 5) - 2  # -2..2 brightness shift
            base = (
                max(0, min(255, STONE[0] + variant * 3)),
                max(0, min(255, STONE[1] + variant * 3)),
                max(0, min(255, STONE[2] + variant * 4)),
            )
            rect = pygame.Rect(bx * block, by * block, block, block)
            surf.fill(base, rect)
            # Block border (mortar): dark line between stones.
            pygame.draw.rect(surf, SHADOW, rect, 1)
    # Subtle noise speckles (deterministic, low contrast).
    for i in range(160):
        x = _hash(i, 0, 11) % TILE
        y = _hash(i, 1, 13) % TILE
        v = _hash(i, 2, 17) % 3
        if v == 0:
            surf.set_at((x, y), NIGHT)
        elif v == 1:
            surf.set_at((x, y), (30, 37, 62))
    # One faint cyan rune crack across the tile (wraps edges = seamless).
    pygame.draw.line(surf, RITE_CYAN, (6, TILE - 6), (TILE - 8, 10), 1)
    pygame.draw.line(surf, (60, 110, 120), (6, TILE - 6), (TILE - 8, 10), 2)
    # Tiny corner glyphs.
    pygame.draw.rect(surf, (60, 110, 120), (2, 2, 2, 1))
    pygame.draw.rect(surf, (60, 110, 120), (TILE - 4, TILE - 3, 2, 1))
    return surf


def main() -> int:
    pygame.init()
    pygame.display.set_mode((TILE, TILE))
    surf = make_tile()
    pygame.image.save(surf, str(OUT))
    pygame.quit()
    print(f"generated seamless floor tile -> {OUT} ({TILE}x{TILE})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
