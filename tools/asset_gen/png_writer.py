"""Minimal pure-Python PNG writer (no dependencies).

Writes 8-bit RGBA PNGs. Used by the asset generator so the project gains no
new runtime or tooling dependencies (RULES.md §14). ~40 lines, standard
library only.
"""

from __future__ import annotations

import struct
import zlib
from pathlib import Path

_PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"


def _chunk(tag: bytes, data: bytes) -> bytes:
    length = struct.pack(">I", len(data))
    crc = zlib.crc32(tag + data) & 0xFFFFFFFF
    return length + tag + data + struct.pack(">I", crc)


def write_png(path: Path, pixels: list[list[tuple[int, int, int, int]]]) -> None:
    """Write an RGBA image. ``pixels[row][col]`` = (r, g, b, a)."""
    height = len(pixels)
    width = len(pixels[0]) if height else 0

    def validate() -> None:
        for row in pixels:
            if len(row) != width:
                raise ValueError("ragged pixel rows")

    validate()

    # Filter: 0 (None) per scanline, then raw RGBA bytes.
    raw = bytearray()
    for row in pixels:
        raw.append(0)  # filter type 0
        for r, g, b, a in row:
            raw += bytes((r & 0xFF, g & 0xFF, b & 0xFF, a & 0xFF))

    ihdr = struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0)  # 8-bit RGBA
    data = (
        _chunk(b"IHDR", ihdr)
        + _chunk(b"IDAT", zlib.compress(bytes(raw), 9))
        + _chunk(b"IEND", b"")
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(_PNG_SIGNATURE + data)
