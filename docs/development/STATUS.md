# CURRENT STATUS (living handoff file)

> **Purpose:** single, always-up-to-date checkpoint so ANY agent (or the
> developer) can resume work without re-reading the whole project.
> **Rule:** whoever advances the project updates this file in the same
> commit (IMPLEMENTATION_PLAN.md snapshot + CHANGELOG.md too).
> Last updated: **2026-07-27** (Phase 3 complete).

## 1. Where we are

- **Phase 0 — Project foundation:** COMPLETE.
- **Phase 1 — Core engine/runtime:** COMPLETE (verified 2026-07-27).
- **Phase 2 — Input and game state:** COMPLETE (2026-07-27). pygame-ce, adapter isolation.
- **Phase 3 — Player controller:** COMPLETE (2026-07-27). Playable greybox slice.
- **NEXT: Phase 4 — Combat foundation** (see IMPLEMENTATION_PLAN.md; depends on Phase 3).

## 2. What is playable right now

`uv run python scripts/run.py` launches the greybox arena:

- WASD/arrows (or gamepad left stick): 8-direction movement, analog speed.
- Space (or gamepad A): dodge roll with i-frames (player flashes white).
- The player collides with walls/obstacles; the camera follows smoothly,
  clamped to the room; Escape/close button quits.
- All tuning lives in `data/player/stats.yaml`; the map in
  `data/world/rooms/greybox_arena.yaml`; camera defaults in
  `config/display.yaml` (`camera:` section).

## 3. Verification (all green as of Phase 3 completion)

```text
uv run pytest -q                                -> 145 passed, 1 skipped
uv run ruff check src tests tools scripts       -> clean
uv run python -m mypy src                       -> clean (114 files)
uv run python tools/data_validation/validate_data.py -> OK
uv run python scripts/run.py --headless --frames 300 -> exit 0
```

(The 1 skip is intentional: the pygame smoke test skips when pygame is
unavailable; in this environment it runs and passes.)

## 4. Architecture map after Phase 3

| Layer | State |
|-------|-------|
| `src/core` | events, state machine, DI, registry, data loader (Phase 1) |
| `src/engine` | game, loop, scenes, entity/component/system (Phase 2) |
| `src/input` | ActionFrame abstraction, keyboard+gamepad adapters (Phase 2) |
| `src/rendering` | renderer protocol + pygame adapter (Phase 2) · **Camera (Phase 3)** |
| `src/physics` | **collision (swept AABB), movement (KinematicBody), hitbox, hurtbox (Phase 3)** |
| `src/gameplay/player` | **Player (composition root), controller, state machine, stats (Phase 3)** |
| `src/gameplay` | **PlaytestScene (Phase 3 greybox slice)** |
| `src/world` | **Room data model (Phase 3)** + dungeon prototype (Phase 1) |

Key contracts future phases must respect:

- Adapter isolation: pygame imports ONLY in `src/rendering`, `src/input`,
  `src/audio` (guarded by tests/unit/test_framework_isolation.py).
- Player responsibilities are split: input -> PlayerController (only place
  that sees ActionFrame), movement -> KinematicBody, collision -> Hitbox/
  Hurtbox, state -> core StateMachine, values -> data/player/*.yaml.
- Player events on the bus: `player_state_changed`, `player_dodge`.
- Animation hook: `player.animation_pose` (state + facing -> clip name
  convention "idle_down", "dodge_up_right", ...). Greybox tints by state.
- Collision layers (WORLD/PLAYER_*/ENEMY_*) + masks are ready for enemies.
- HIT and DEAD player states are wired placeholders; Phase 4 fills them.
- Camera hooks: `shake_offset` (screen shake), `set_bounds` (boss arenas).

## 5. How to resume (for the next agent)

1. Read RULES.md, this file, IMPLEMENTATION_PLAN.md (status snapshot).
2. For Phase 4: also read ARCHITECTURE.md section 5 (Combat) and
   GAMEPLAY_DESIGN.md section 4. Combat is FRAMEWORK ONLY: damage pipeline,
   attack executor, invulnerability, status effects - zero content.
3. Follow the AI DEVELOPMENT LOOP (end of IMPLEMENTATION_PLAN.md).
4. Before finishing: run the five verification commands above; update this
   file, the plan snapshot, and CHANGELOG.md; commit per RULES.md section 19.

## 6. Technical debt / known gaps

- No input buffering / coyote-style dodge queue yet (feel tuning, optional).
- No sprite pipeline: player renders as a tinted rect via the animation hook.
- Internal pixel resolution is an open DESIGN decision (EXPERIENCE_DESIGN.md
  section 3); camera zoom is provisional until then.
- CollisionWorld is static-only; Phase 4 adds dynamic hitbox/hurtbox hit
  resolution on top (layers/masks already exist).
- Hurtbox.vulnerable is driven only by dodge i-frames; the general
  invulnerability system arrives with combat (Phase 4).
