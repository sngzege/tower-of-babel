"""Process AI-generated pixel art into game sprites.

Downloads the generated PNGs, removes the solid black background (chroma key
with feathering), scales to game sizes, and writes assets/sprites/<id>.png.

Run:  uv run python tools/asset_gen/process_ai_sprites.py
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

import pygame  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = ROOT / "assets" / "sprites"

# (output id, source url, target size px, brightness cut threshold)
SPRITES: list[tuple[str, str, int, int]] = [
    ("boss", "https://v3b.fal.media/files/b/0aa49815/cl8BuN2rL1xig-OJGYRDu_hEv3PILG.png", 48, 42),
    ("player", "https://v3b.fal.media/files/b/0aa4981a/GsInR0pNVkK3InJw8kptK_xNtJ1E4q.png", 28, 42),
    ("dummy", "https://v3b.fal.media/files/b/0aa4980b/k3sV-ST_puMwjStd6XKfQ_hyyFzUvs.png", 28, 42),
    ("elite", "https://v3b.fal.media/files/b/0aa4980c/hpEskQgWpu_kI0Uw0ltBg_CGJEx4XU.png", 36, 42),
    # floor texture is bright mid-tone; low threshold keeps it opaque
    ("tile_floor",
     "https://v3b.fal.media/files/b/0aa4980c/jkvE7Abf6HF63TbtCfmjk_m3TSpNar.png",
     32, 20),
]


def cutout_black(surface: pygame.Surface, threshold: int) -> pygame.Surface:
    """Make near-black pixels transparent (chroma key + soft edge)."""
    out = surface.convert_alpha()
    w, h = out.get_size()
    for y in range(h):
        for x in range(w):
            r, g, b, a = out.get_at((x, y))  # noqa: E741
            brightness = (r + g + b) / 3
            if brightness < threshold:
                # Fully transparent for pure black; feather near the edge.
                alpha = max(0, int(255 * (brightness / threshold)))
                out.set_at((x, y), (r, g, b, alpha))
    return out


def download(url: str, dest: Path) -> bool:
    import urllib.request

    try:
        urllib.request.urlretrieve(url, dest)  # noqa: S310
        return True
    except Exception as exc:  # noqa: BLE001
        print(f"  download failed: {exc}")
        return False


def main() -> int:
    pygame.init()
    pygame.display.set_mode((32, 32))  # surface ops need a display
    raw_dir = ROOT / "tools" / "asset_gen" / "_raw"
    raw_dir.mkdir(exist_ok=True)

    for sprite_id, url, size, threshold in SPRITES:
        raw = raw_dir / f"{sprite_id}_raw.png"
        print(f"== {sprite_id} ==")
        if not raw.is_file():
            if not download(url, raw):
                continue
        image = pygame.image.load(str(raw))
        # Center-crop to the largest centered square, then scale.
        iw, ih = image.get_size()
        side = min(iw, ih)
        crop = pygame.Surface((side, side), pygame.SRCALPHA)
        crop.blit(image, (0, 0), ((iw - side) // 2, (ih - side) // 2, side, side))
        scaled = pygame.transform.scale(crop, (size, size))
        processed = cutout_black(scaled, threshold)
        path = OUT_DIR / f"{sprite_id}.png"
        pygame.image.save(processed, str(path))
        print(f"  saved {path} ({size}x{size})")

    pygame.quit()
    print("done")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
