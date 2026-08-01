"""Main menu scene (Phase 15).

A minimal greybox menu: NEW GAME (Enter) always available; CONTINUE RUN
(C) only when a mid-run checkpoint exists. This keeps the loop
menu → village → dungeon → return → menu reproducible headlessly.

Greybox scope (RULES.md §0): no theme/art — plain tinted panel + text.
"""

from __future__ import annotations

from collections.abc import Callable

from core.content_registry import ContentRegistry
from core.enums import SceneID
from engine.scene import Scene
from input.input_manager import Action, ActionFrame
from rendering.renderer import Color, Renderer

_BG: Color = (16, 18, 26)
_PANEL: Color = (30, 34, 48)
_ACCENT: Color = (120, 160, 220)
_TEXT: Color = (230, 230, 235)
_DIM: Color = (130, 140, 160)
_HINT: Color = (170, 200, 170)


class MenuScene(Scene):
    """Main menu: new game or continue from a saved run checkpoint."""

    scene_id = SceneID.MAIN_MENU

    def __init__(
        self,
        registry: ContentRegistry | None = None,
        can_continue: bool = False,
        on_new_game: Callable[[], None] | None = None,
        on_continue: Callable[[], None] | None = None,
    ) -> None:
        self._registry = registry
        self._can_continue = can_continue
        self._on_new_game = on_new_game
        self._on_continue = on_continue
        self._message = ""

    def update(self, frame: ActionFrame, dt: float) -> None:
        if Action.INTERACT in frame.pressed or Action.PRIMARY_ATTACK in frame.pressed:
            if self._on_new_game is not None:
                self._on_new_game()
            return
        if Action.PAUSE in frame.pressed:  # Escape/C = continue (when available)
            if self._can_continue and self._on_continue is not None:
                self._on_continue()
            else:
                self._message = "No saved run checkpoint."

    def render(self, renderer: Renderer) -> None:
        w, h = renderer.size
        renderer.draw_rect((0, 0, w, h), _BG)
        panel_w, panel_h = 480, 240
        px, py = (w - panel_w) // 2, (h - panel_h) // 2
        renderer.draw_rect((px, py, panel_w, panel_h), _PANEL)
        renderer.draw_rect((px + 2, py + 2, panel_w - 4, panel_h - 4), _BG)

        title = "TOWER OF BABEL"
        renderer.draw_text(title, px + 90, py + 30, _ACCENT, 28)
        renderer.draw_text("(greybox slice)", px + 170, py + 62, _DIM, 14)

        renderer.draw_text("[F / Click]  New Game", px + 110, py + 110, _TEXT, 16)
        continue_label = "[Esc]  Continue Run"
        continue_color = _TEXT if self._can_continue else _DIM
        renderer.draw_text(continue_label, px + 110, py + 140, continue_color, 16)

        if self._message:
            renderer.draw_text(self._message, px + 110, py + 190, _HINT, 13)
