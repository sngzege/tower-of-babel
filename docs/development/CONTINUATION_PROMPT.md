# CONTINUATION PROMPT — Phase 12 Complete: Autonomous Completion Run

> **When to use:** the next agent picks up from this exact state. Copy-paste
> this prompt at the start of the session so the agent knows exactly where we
> are, what is already implemented, and what the next deliverables are.
> Updated: **2026-08-01**.

---

## Context

- Project: Tower of Babel (Action RPG + Roguelite)
- Repo: https://github.com/sngzege/tower-of-babel
- Branch: `main`
- Living status file: `docs/development/STATUS.md`
- **RULES.md §0 is a STANDING DIRECTIVE (2026-08-01): the human developer has
  pre-authorized an autonomous completion run for Phases 11→15** — Village
  Framework, NPC Framework, Persistent Progression, Save/Load Integration,
  Vertical Slice Integration — with greybox placeholders only, provisional
  defaults for open design decisions, and **no balance tuning**. The playable
  slice is the human gate; STOP after Phase 15.

## What is already implemented (Phase 12 complete, 2026-07-29)

Playable greybox build via `uv run python scripts/run.py` (full run lifecycle,
build system, abilities) and `uv run python scripts/run.py --combat-test`
(dedicated combat arena):

- **Player**: WASD movement, 360° aim (mouse or arrows), attack, dodge with
  charges + i-frames; Q/E/R/T ability slots (Charge, Shield Bash, Whirlwind,
  War Cry).
- **Combat**: centralized damage formula (`damage_formula.py`), data-driven
  attacks/abilities, damage numbers, hit flash, collision-aware knockback.
- **Build system**: 3 weapons (sword/spear/axe), 17 YAML boons, tag-based
  modifiers, passives, weapon upgrades, Warrior class loadout, build persists
  across rooms/floors, reset on death.
- **Procedural stage**: 3 seeded floors + 1 boss floor (4 total), room
  encounters, reward choice-of-3, run lifecycle with death/victory overlays.
- **Boss**: "Warden of the First Floor" — 2-phase AI, arena, exit gating,
  victory flow.
- **HUD**: HP/weapon/room/Fury, ability cooldown bars, responsive at multiple
  resolutions; mouse + keyboard reward selection.
- **Elite enemies**: gold-tinted elite variant in combat test.

### Full verification (as of Phase 12)

```text
uv run pytest -q                                -> 332 passed, 1 skipped
uv run ruff check src tests tools scripts       -> clean (0 errors)
uv run python -m mypy src                       -> clean (129 files)
uv run python tools/data_validation/validate_data.py -> OK
uv run python scripts/run.py --headless --frames 300 --log-level WARNING -> exit 0
uv run python scripts/run.py --headless --combat-test --frames 300 --log-level WARNING -> exit 0
```

## What the next agent should do (Phases 11→15, in order)

Per IMPLEMENTATION_PLAN.md detailed sections (original numbering) and
VERTICAL_SLICE.md §1/§4. Work phase by phase; do not skip ahead.

1. **Phase 11 — Village Framework**: `src/gameplay/village/` package, walkable
   village scene, 3 building plots with 2 visual tiers each, Town Level +
   building upgrade levels (L11/L12), application of run results
   (trophy/material → tier increase), greybox village map.
2. **Phase 12 — NPC Framework**: `src/gameplay/village/npc.py`, `data/npcs/`,
   3 service NPCs (loadout / run prep / upgrades), one service-tier progression
   track each, milestone-driven arrival (first boss kill), dialogue as data.
3. **Phase 13 — Persistent Progression**: `src/gameplay/progression/`,
   `data/unlocks/`, `data/progression/` — class mastery (L13), unlock engine
   feeding reward pools, depth records, save/load persistence, all permanent
   bonuses applied at run start (L15).
4. **Phase 14 — Save/Load Integration**: wire persistent + run state into the
   save manager (`src/save`), slot handling, D15 provisional policy (save at
   village + run checkpoint at room transitions), corrupted-save handling,
   full roundtrip tests.
5. **Phase 15 — Vertical Slice Integration**: assemble the complete loop per
   VERTICAL_SLICE.md §4: menu → village → prepare → dungeon (5 floors per L7:
   4 generated + boss floor) → boss → death/return → village upgrade → NPC tier
   up → new options next run → new run. Headless scripted full-run integration
   test. **This is the playable product gate — STOP and report here.**

**Provisional defaults for open design decisions (RULES.md §0, DESIGN_DECISIONS.md §3):**
- D3-detail: one hero, class-switching; meta-progression per class.
- D7: keep current free-roam room-graph navigation.
- D14: keep choice-of-3 boons.
- D15: save at village + run checkpoint at room transitions.

**Constraints:**
- Greybox placeholders only (neutral names, tinted rects). No theme/lore/final
  content. No balance tuning — sensible existing defaults only.
- Data-driven (YAML), no magic values, adapter isolation (pygame only in
  src/rendering/, src/input/, src/audio/), EventBus for cross-layer events.
- Do NOT start Phases 16+ (content/polish/QA/release) — they are blocked on the
  human playtest gate.

## AI DEVELOPMENT LOOP (per IMPLEMENTATION_PLAN.md)

REQUEST → CHECK RULES.md → CHECK DESIGN DOCUMENTS → CHECK EXISTING CODE →
IDENTIFY AFFECTED FILES → EXPLAIN IMPLEMENTATION → IMPLEMENT → TEST → REPORT.

## Completion discipline

1. Run the five verification commands above before finishing each phase.
2. Update STATUS.md, IMPLEMENTATION_PLAN.md snapshot, and CHANGELOG.md in the
   same commit as the phase work.
3. Commit meaningful milestones with conventional prefixes (feat:/fix:/test:/docs:/chore:).
4. Push to remote.
5. Final report must state: what is playable, controls, verification results,
   deferred items — in Turkish, concise and practical.

## Key architecture constraints (unchanged)

- Python + pygame-ce remain the framework.
- Hybrid component-based architecture stays.
- Data-driven YAML architecture stays.
- 360-degree free aim remains. Dodge charges + i-frames remain.
- Warrior is the first class (Ranger/Mage are future).
- Framework isolation rules remain.
