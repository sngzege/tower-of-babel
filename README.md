# Roguelike (working title — D1 undecided)

A pixel-art, top-down **action roguelite RPG / dungeon crawler** in early pre-production:
class-based combat, procedural dungeon stages, persistent hero and class progression,
build creation, and a living village that grows with every run.

> This is a **human-directed** project. RULES.md is the highest authority for all
> contributors (human or AI). Game design decisions belong to the human developer;
> the four documents in `docs/design/` are reviewable drafts, not final truth.

## Status

**Pre-production.** Infrastructure and documentation are prepared; no gameplay is implemented.

- Design drafts: `docs/design/` (GAME / GAMEPLAY / WORLD / EXPERIENCE)
- Architecture: `docs/architecture/` (ARCHITECTURE, DATA_FLOW, SAVE_SYSTEM)
- Roadmap: `IMPLEMENTATION_PLAN.md` · Slice spec: `docs/development/VERTICAL_SLICE.md`
- Setup: `docs/development/SETUP.md`

## Quickstart

```powershell
uv sync                                  # install dependencies
uv run python scripts/test.py            # run the test suite
uv run python scripts/validate_data.py   # validate data files
uv run python scripts/run.py             # run the app (bootstrap skeleton)
```

## Repository Layout

`src/` code · `data/` content (YAML, schema-validated) · `assets/` art+audio · `config/` technical config · `docs/` design+architecture+development · `tests/` · `tools/` · `scripts/` · `saves/` · `logs/`

See `PROJECT_STRUCTURE.md` for the full tree.
