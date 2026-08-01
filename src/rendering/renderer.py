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

# In-memory font cache keyed by size.
_FONT_CACHE: dict[int, object] = {}


class Renderer(Protocol):
    """Framework-independent rendering surface (Phase 2 scope)."""

    @property
    def size(self) -> tuple[int, int]: ...

    def clear(self, color: Color) -> None: ...

    def draw_rect(self, rect: Rect, color: Color) -> None: ...

    def draw_text(self, text: str, x: int, y: int, color: Color, font_size: int = 12) -> None:
        """Render a single line of text at pixel (x, y)."""
        ...

    def draw_image(self, image_id: str, x: int, y: int, scale: int = 2) -> None:
        """Draw a sprite by id (assets/sprites/<id>.png) at pixel (x, y).

        ``x``/``y`` are the TOP-LEFT corner in screen pixels. ``scale`` is an
        integer multiplier of the 16x16 source grid. Missing sprites are a
        silent no-op (greybox fallback keeps rendering).
        """
        ...

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
        self._image_cache: dict[str, object] = {}
        self._images_dir = None

    @property
    def size(self) -> tuple[int, int]:
        return self._screen.get_size()

    def clear(self, color: Color) -> None:
        self._screen.fill(color)

    def draw_rect(self, rect: Rect, color: Color) -> None:
        self._pygame.draw.rect(self._screen, color, rect)

    def draw_text(self, text: str, x: int, y: int, color: Color, font_size: int = 12) -> None:
        """Render a single line of text at pixel (x, y)."""
        import pygame

        if font_size not in _FONT_CACHE:
            _FONT_CACHE[font_size] = pygame.font.Font(None, font_size)
        font: pygame.font.Font = _FONT_CACHE[font_size]  # type: ignore[assignment]
        surface = font.render(str(text), True, color)
        self._screen.blit(surface, (x, y))

    def draw_image(self, image_id: str, x: int, y: int, scale: int = 2) -> None:
        """Draw a sprite by id; missing sprites are a silent no-op."""
        import pygame

        surface = self._load_image(image_id)
        if surface is None:
            return
        pygame_surface = surface  # type: ignore[var-annotated]
        if scale != 1:
            scaled = pygame.transform.scale(
                pygame_surface,  # type: ignore[arg-type]
                (pygame_surface.get_width() * scale,  # type: ignore[attr-defined]
                 pygame_surface.get_height() * scale),  # type: ignore[attr-defined]
            )
            pygame_surface = scaled  # type: ignore[var-annotated]
        self._screen.blit(pygame_surface, (int(x), int(y)))  # type: ignore[arg-type]

    def _load_image(self, image_id: str) -> object | None:
        """Load assets/sprites/<id>.png once, cache by id."""
        import pygame

        cached = self._image_cache.get(image_id)
        if cached is not None:
            return cached
        if self._images_dir is None:
            from core.constants import ASSETS_DIR

            self._images_dir = ASSETS_DIR / "sprites"  # type: ignore[assignment]
        images_dir = self._images_dir
        if images_dir is None:  # pragma: no cover — defensive
            return None
        path = images_dir / f"{image_id}.png"
        if not path.is_file():
            self._image_cache[image_id] = None
            return None
        surface: object = pygame.image.load(str(path)).convert_alpha()
        self._image_cache[image_id] = surface
        return surface

    def present(self) -> None:
        self._pygame.display.flip()

    def tick(self, fps: int) -> float:
        return self._clock.tick(fps) / 1000.0

    def close(self) -> None:
        self._pygame.quit()
