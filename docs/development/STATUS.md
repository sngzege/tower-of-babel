# CURRENT STATUS (living handoff file)

> **Purpose:** single, always-up-to-date checkpoint so ANY agent (or the
> developer) can resume work without re-reading the whole project.
> **Rule:** whoever advances the project updates this file in the same
> commit (IMPLEMENTATION_PLAN.md snapshot + CHANGELOG.md too).
> Last updated: **2026-07-28** (Phase 6 — Room/Dungeon Foundation complete).

## 1. Where we are

- **Phase 0 — Project foundation:** COMPLETE.
- **Phase 1 — Core engine/runtime:** COMPLETE.
- **Phase 2 — Input and game state:** COMPLETE. pygame-ce, adapter isolation.
- **Phase 3 — Player controller:** COMPLETE. Playable greybox slice.
- **Phase 3.5 — Approved amendments:** COMPLETE. Dodge charge system, movement/aim/facing split.
- **Phase 4 — Combat foundation:** COMPLETE. Damage pipeline, attack executor, invulnerability service, status effect framework. 360-degree free-aim hitbox rotation.
- **Phase 5 — Enemy foundation:** COMPLETE. Enemy entity, SimpleAI, EnemyFactory, two dummies, combat wiring.
- **Phase 6 — Room / dungeon foundation:** COMPLETE (2026-07-28). FloorAssembler, FloorGraph→room assembly, room templates, door transitions, floor traversal, per-room enemy spawning.
- **NEXT: Phase 7 — Procedural generation** (see IMPLEMENTATION_PLAN.md).

## 2. What is playable right now

`uv run python scripts/run.py` launches the greybox arena (now with floor assembly):

- WASD: 8-direction movement, analog speed.
- Arrow keys: independent 8-direction aim.
- Mouse: positional 360-degree aim.
- Space: dodge roll with charge-based cooldown (2 charges, 1.5s regen).
- Left Mouse / primary attack key: basic 360-degree attack.
- **Seeded floor traversal**: each run generates a FloorGraph, assembles rooms, and the player traverses start → combat rooms → exit.
- **Enemies in combat rooms**: greybox dummies chase and attack.
- Player takes damage from enemies, enters hitstun state.
- Dodge i-frames block damage.
- Room transitions via doors: player walks through → new room loads with correct camera.
- All tuning in data files.

## 3. Verification (as of Phase 6)

```text
uv run pytest -q                                -> 246 passed, 1 skipped
uv run ruff check src tests tools scripts       -> clean
uv run python -m mypy src                       -> clean (117 files)
uv run python tools/data_validation/validate_data.py -> OK
uv run python scripts/run.py --headless --frames 300 -> exit 0
```

(The 1 skip is intentional: the pygame smoke test skips when pygame is unavailable.)

## 4. Architecture map after Phase 6

| Layer | State |
|-------|-------|
| `src/core` | events, state machine, DI, registry, data loader (Phase 1) |
| `src/engine` | game, loop, scenes, entity/component/system (Phase 2) |
| `src/input` | ActionFrame with independent move/aim channels (Phase 3.5) |
| `src/rendering` | renderer protocol + pygame adapter (Phase 2) — Camera (Phase 3) |
| `src/physics` | collision (swept AABB), movement, hitbox, hurtbox (Phase 3) |
| `src/gameplay/player` | Player + DodgeCharges + AimController + AttackExecutor (Phase 4) |
| `src/gameplay/combat` | DamagePipeline, AttackExecutor, InvulnService, StatusEffectManager, CombatSystem (Phase 4) |
| `src/gameplay/enemies` | Enemy, EnemyConfig, SimpleAI, EnemyFactory (Phase 5) |
| `src/gameplay` | PlaytestScene with floor assembly + combat (Phase 6) |
| `src/world` | Room, Door, RoomManager (Phase 6); RoomManager (transitions); FloorAssembler (Phase 6); DungeonGenerator prototype (Phase 1) |

### Phase 6 additions highlighted

- **FloorAssembler**: converts FloorGraph → FloorData (all rooms wired with doors). Template selection by kind. `kind_to_template` mapping extensible for Phase 7.
- **FloorData**: `rooms` dict, `start_room_id`, `exit_room_id`, `connections` map.
- **Room templates**: `greybox_start` (right door only), `greybox_room` (left+right doors), `greybox_exit` (left door only).
- **RoomManager**: now supports floor mode (`load_floor()`) + registry mode.
- **PlaytestScene**: floor mode with per-kind enemy spawning (combat rooms get 2 dummies).
- **main.py**: generates seeded FloorGraph, assembles via FloorAssembler, passes to scene.

## 5. How to resume (for the next agent)

1. Read RULES.md, this file, IMPLEMENTATION_PLAN.md.
2. For Phase 7: extend FloorAssembler for seeded template subset selection, add encounter population, 20-seed smoke check.
3. Follow the AI DEVELOPMENT LOOP (end of IMPLEMENTATION_PLAN.md).
4. Before finishing: run the five verification commands; update STATUS.md, plan, and CHANGELOG.md; commit per RULES.md section 19; push to remote.

## 6. Technical debt / known gaps

- No input buffering / coyote-style dodge queue yet.
- No sprite pipeline: player and enemies render as tinted rects.
- Internal pixel resolution is an open DESIGN decision; camera zoom is provisional.
- **Attack data is currently hardcoded in Player.__init__** instead of loaded from data files.
- CombatSystem only checks AABB overlaps; no knockback/physics push applied yet.
- Still only greybox enemies (no production content).
- FloorAssembler doesn't randomize template selection per kind (always picks the same template for a given kind).
- Room transitions use camera `center_on` (instant snap); no smooth transition animation yet.
- Per-room enemy state is ephemeral: revisiting a room respawns enemies.
