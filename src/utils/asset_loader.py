"""Asset path catalog.

Maps logical asset references to files under assets/ without decoding them.
Decoding belongs to the future rendering/audio stack (framework decision
pending - see docs/architecture/ARCHITECTURE.md). Infrastructure only.
"""

from __future__ import annotations

from pathlib import Path

from utils.file_utils import find_project_root


class AssetCatalog:
    """Resolves and validates asset paths relative to the assets/ directory."""

    def __init__(self, assets_dir: Path | None = None) -> None:
        self.assets_dir = assets_dir or find_project_root() / "assets"

    def resolve(self, *parts: str) -> Path:
        """Absolute path for an asset: resolve('sprites', 'player', 'idle.png')."""
        return self.assets_dir.joinpath(*parts)

    def exists(self, *parts: str) -> bool:
        return self.resolve(*parts).is_file()

    def list_files(self, *parts: str, suffix: str | None = None) -> list[Path]:
        """All files below an asset subdirectory, optionally filtered by suffix."""
        directory = self.resolve(*parts)
        if not directory.is_dir():
            return []
        files = [p for p in directory.rglob("*") if p.is_file()]
        if suffix is not None:
            files = [p for p in files if p.suffix == suffix]
        return sorted(files)
