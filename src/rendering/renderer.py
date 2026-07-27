"""Renderer adapter: protocol + pygame-ce implementation (Phase 2 scope).

ADAPTER ISOLATION RULE (developer decision, 2026-07-27): pygame may only be
imported inside src/rendering, src/input, and src/audio. Everything else talks
to the Renderer protocol below. The full sprite/camera/effects pipeline
arrives in later phases; this module provides the window, frame timing, and
placeholder drawing primitives needed by Phase 2.
"""

from __future__ import annotations

from typing import Protocol

Color = tuple[int, int, int]
Rect = tuple[int, int, int, int]  # x, y, width, height (pixel units)


class Renderer(Protocol):
    """Framework-independent rendering surface (Phase 2 scope)."""

    @property
    def size(self) -> tuple[int, int]: ...

    def clear(self, color: Color) -> None: ...

    def draw_rect(self, rect: Rect, color: Color) -> None: ...

    def present(self) -> None: ...

    def tick(self, fps: int) -> float:
        """Limit the frame rate; return elapsed time since last call (seconds)."""
        ...

    def close(self) -> None: ...


class PygameRenderer:
    """pygame-ce backed renderer. The only module touching pygame display/time."""

    def __init__(self, width: int, height: int, title: str, vsync: bool = True) -> None:
        import pygame

        self._pygame = pygame
        pygame.init()
        self._screen = pygame.display.set_mode((width, height), vsync=1 if vsync else 0)
        pygame.display.set_caption(title)
        self._clock = pygame.time.Clock()

    @property
    def size(self) -> tuple[int, int]:
        return self._screen.get_size()

    def clear(self, color: Color) -> None:
        self._screen.fill(color)

    def draw_rect(self, rect: Rect, color: Color) -> None:
        self._pygame.draw.rect(self._screen, color, rect)

    def present(self) -> None:
        self._pygame.display.flip()

    def tick(self, fps: int) -> float:
        return self._clock.tick(fps) / 1000.0

    def close(self) -> None:
        self._pygame.quit()
