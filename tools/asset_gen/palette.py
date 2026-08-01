"""PAL-01 palette (see .local-docs/docs/design/ART_DIRECTION.md).

Dark Babylon base tones + bright pastel magic accents. Every sprite in the
game uses these exact values so the palette stays consistent and tuning one
color updates the whole art style.
"""

from __future__ import annotations

# Base (dark, desaturated) — ~70% of any frame.
ABYSS = (13, 16, 32)
NIGHT = (20, 26, 46)
SHADOW = (29, 36, 64)
STONE = (42, 51, 82)
BRICK = (58, 44, 42)
SAND_DARK = (61, 53, 64)
ASH = (74, 68, 86)

# Magic accents (bright pastel — ~15% of any frame).
RITE_CYAN = (125, 227, 232)
SORCERY_PINK = (255, 158, 196)
GOLD = (255, 210, 125)
SPIRIT_GREEN = (159, 240, 176)
VIOLET_LIGHT = (183, 166, 255)
BONE = (232, 224, 208)

# Flesh / blood (enemies).
BLOOD_DARK = (90, 22, 38)
BLOOD = (160, 43, 62)
ICHOR = (224, 85, 110)

# Shading helpers (darker/lighter variants of a base).
SHADOW_ALPHA = (0, 0, 0, 90)

PALETTE = {
    "abyss": ABYSS,
    "night": NIGHT,
    "shadow": SHADOW,
    "stone": STONE,
    "brick": BRICK,
    "sand": SAND_DARK,
    "ash": ASH,
    "cyan": RITE_CYAN,
    "pink": SORCERY_PINK,
    "gold": GOLD,
    "green": SPIRIT_GREEN,
    "violet": VIOLET_LIGHT,
    "bone": BONE,
    "blood_dark": BLOOD_DARK,
    "blood": BLOOD,
    "ichor": ICHOR,
}
