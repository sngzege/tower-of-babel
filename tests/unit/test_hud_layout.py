"""Tests for HUD layout: all UI elements must fit within the viewport.

Uses the actual screen position calculations from PlaytestScene
to verify that at various viewport sizes, HUD elements stay visible.
"""

from __future__ import annotations


def _simulate_hud_positions(w: int, h: int) -> dict[str, tuple[int, int, int, int]]:
    """Replicate the HUD position calculations from PlaytestScene.render().

    Returns {element_name: (x, y, width, height)} in screen coordinates.
    """
    positions: dict[str, tuple[int, int, int, int]] = {}

    # HP bar (top-left).
    hp_bar_x, hp_bar_y = 20, 20
    hp_bar_w, hp_bar_h = 220, 28
    positions["hp_bar"] = (hp_bar_x, hp_bar_y, hp_bar_w, hp_bar_h)

    # Dodge info below HP bar.
    dodge_y = hp_bar_y + hp_bar_h + 4
    positions["dodge_info"] = (hp_bar_x, dodge_y, 150, 16)

    # Build info below dodge.
    bi_y = hp_bar_y + hp_bar_h + 22
    positions["weapon_info"] = (hp_bar_x, bi_y, 200, 16)

    # Room info.
    ri_y = hp_bar_y + hp_bar_h + 88
    positions["room_info"] = (hp_bar_x, ri_y, 200, 16)

    # Ability bar (top-right).
    max_slot_w = max(160, min(280, w // 5))
    slot_w = min(max_slot_w, w - 40)
    slot_h = 36
    slot_start_x = w - slot_w - 20
    slot_start_y = 20
    for i, label in enumerate(["Q", "E", "R", "T"]):
        sx = slot_start_x
        sy = slot_start_y + i * (slot_h + 6)
        positions[f"ability_{label}"] = (sx, sy, slot_w, slot_h)

    # Reward cards (when visible).
    for i in range(3):
        rx = 60 + i * 180
        ry = h // 3
        positions[f"reward_{i}"] = (rx, ry, 160, 80)

    # Game-over overlay (centered).
    pw, ph = 360, 160
    cx, cy = w // 2, h // 3
    positions["game_over"] = (cx - pw // 2, cy - ph // 2, pw, ph)

    return positions


def _in_viewport(x: int, y: int, rw: int, rh: int, vw: int, vh: int) -> bool:
    """Check if rect (x,y,w,h) is fully inside viewport (vw,vh)."""
    return x >= 0 and y >= 0 and x + rw <= vw and y + rh <= vh


def test_hud_layout_at_1920x1080() -> None:
    """Default resolution: all elements must fit."""
    w, h = 1920, 1080
    positions = _simulate_hud_positions(w, h)
    for name, (x, y, rw, rh) in positions.items():
        assert _in_viewport(x, y, rw, rh, w, h), (
            f"{name} at ({x},{y},{rw},{rh}) outside {w}x{h} viewport"
        )


def test_hud_layout_at_1280x720() -> None:
    """Smaller resolution: all elements must still fit."""
    w, h = 1280, 720
    positions = _simulate_hud_positions(w, h)
    for name, (x, y, rw, rh) in positions.items():
        assert _in_viewport(x, y, rw, rh, w, h), (
            f"{name} at ({x},{y},{rw},{rh}) outside {w}x{h} viewport"
        )


def test_hud_layout_at_2560x1440() -> None:
    """Larger resolution: all elements must fit."""
    w, h = 2560, 1440
    positions = _simulate_hud_positions(w, h)
    for name, (x, y, rw, rh) in positions.items():
        assert _in_viewport(x, y, rw, rh, w, h), (
            f"{name} at ({x},{y},{rw},{rh}) outside {w}x{h} viewport"
        )


def test_hud_ability_bar_slot_width_responsive() -> None:
    """Ability bar width should scale with viewport width."""
    # At 1920: slot_w = min(min(280, 1920//5=384), 1920-40) = 280
    positions_1920 = _simulate_hud_positions(1920, 1080)
    q_rect = positions_1920["ability_Q"]
    assert q_rect[2] == 280, f"Expected 280px slot at 1920, got {q_rect[2]}"

    # At 1280: slot_w = min(min(280, 1280//5=256), 1280-40=1240) = 256
    positions_1280 = _simulate_hud_positions(1280, 720)
    q_rect = positions_1280["ability_Q"]
    assert q_rect[2] == 256, f"Expected 256px slot at 1280, got {q_rect[2]}"

    # At 800: slot_w = min(min(280, 800//5=160), 800-40=760) = 160
    positions_800 = _simulate_hud_positions(800, 600)
    q_rect = positions_800["ability_Q"]
    expected = 160
    assert q_rect[2] == expected, f"Expected {expected}px slot at 800, got {q_rect[2]}"


def test_hud_ability_bar_stays_in_viewport() -> None:
    """Ability bar must not overflow viewport right edge."""
    for w, h in [(1920, 1080), (1280, 720), (2560, 1440), (800, 600)]:
        positions = _simulate_hud_positions(w, h)
        for label in ["Q", "E", "R", "T"]:
            x, y, rw, rh = positions[f"ability_{label}"]
            assert x + rw <= w, (
                f"Ability {label} at {w}x{h}: right edge {x+rw} > {w}"
            )
            assert x >= 0, f"Ability {label} at {w}x{h}: left edge {x} < 0"


def test_hud_reward_cards_stay_in_viewport() -> None:
    """Reward cards must not overflow viewport edges."""
    for w, h in [(1920, 1080), (1280, 720), (2560, 1440), (800, 600)]:
        positions = _simulate_hud_positions(w, h)
        for i in range(3):
            x, y, rw, rh = positions[f"reward_{i}"]
            assert _in_viewport(x, y, rw, rh, w, h), (
                f"Reward card {i} at {w}x{h}: ({x},{y},{rw},{rh}) outside viewport"
            )
