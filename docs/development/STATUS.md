# CURRENT STATUS (living handoff file)

> **Purpose:** single, always-up-to-date checkpoint so ANY agent (or the
> developer) can resume work without re-reading the whole project.
> **Rule:** whoever advances the project updates this file in the same
> commit (IMPLEMENTATION_PLAN.md snapshot + CHANGELOG.md too).
> Last updated: **2026-07-27** (Phase 3.5 amendments complete, Phase 4 ready).

## 1. Where we are

- **Phase 0 — Project foundation:** COMPLETE.
- **Phase 1 — Core engine/runtime:** COMPLETE (verified 2026-07-27).
- **Phase 2 — Input and game state:** COMPLETE (2026-07-27). pygame-ce, adapter isolation.
- **Phase 3 — Player controller:** COMPLETE (2026-07-27). Playable greybox slice.
- **Phase 3.5 — Approved amendments:** COMPLETE (2026-07-27). Dodge charge system (DodgeCharges service, data-driven max/cooldown, independent per-charge timers); movement/aim/facing split (AimController: mouse vs keyboard priority policy, keyboard aim unchanged); camera screen_to_world; player reset logic.
- **NEXT: Phase 4 — Combat foundation** (see IMPLEMENTATION_PLAN.md; depends on Phase 3.5).

## 2. What is playable right now

'uv run python scripts/run.py' launches the greybox arena:

- WASD: 8-direction movement, analog speed.
- Arrow keys: independent 8-direction aim (keyboard aim channel).
- Mouse: positional aim (mouse aim channel). Priority: most recent input wins
  (mouse movement when moved; arrow keys when pressed; retains last direction).
- Space (or gamepad A): dodge roll with i-frames + charge-based cooldown
  (default 2 charges, 1.5s regen each).
- Player facing and animation follow AIM, not movement.
- The player collides with walls/obstacles; the camera follows smoothly,
  clamped to the room; Escape/close button quits.
- All tuning lives in `data/player/stats.yaml`; the map in
  `data/world/rooms/greybox_arena.yaml`; camera defaults in
  `config/display.yaml` (`camera:` section).

## 3. Verification (all green as of Phase 3.5)

```text
uv run pytest -q                                -> 163 passed, 1 skipped
uv run ruff check src tests tools scripts       -> clean
uv run python -m mypy src                       -> clean (116 files)
uv run python tools/data_validation/validate_data.py -> OK
uv run python scripts/run.py --headless --frames 300 -> exit 0
```

(The 1 skip is intentional: the pygame smoke test skips when pygame is
unavailable; in this environment it runs and passes.)

## 4. Architecture map after Phase 3.5

| Layer | State |
|-------|-------|
| `src/core` | events, state machine, DI, registry, data loader (Phase 1) |
| `src/engine` | game, loop, scenes, hybrid entity/component/system (Phase 2) |
| `src/input` | **ActionFrame with independent move/aim channels**, keyboard+gamepad adapters (Phase 3.5) |
| `src/rendering` | renderer protocol + pygame adapter (Phase 2) · **Camera with screen_to_world (Phase 3.5)** |
| `src/physics` | **collision (swept AABB), movement (KinematicBody), hitbox, hurtbox (Phase 3)** |
| `src/gameplay/player` | **Player (composition root) + DodgeCharges + AimController (Phase 3.5)** |
| `src/gameplay` | **PlaytestScene (Phase 3 greybox slice with independent aim)** |
| `src/world` | **Room data model (Phase 3)** + dungeon prototype (Phase 1) |

Key contracts future phases must respect:

- Adapter isolation: pygame imports ONLY in `src/rendering`, `src/input`,
  `src/audio` (guarded by tests/unit/test_framework_isolation.py).
- Input contract: `DeviceSnapshot` and `ActionFrame` have separate `move_*`
  axes (WASD) and `aim_*` axes (arrows / gamepad right stick), plus
  `pointer`/`pointer_moved` for mouse aim. `PlayerController.build_intent`
  only sees `ActionFrame` and emits `PlayerIntent` (wish, dodge, attack).
- Aim policy: `AimController.resolve(frame, wx, wy)` returns
  `AimResult(direction, source)` where source is "keyboard", "mouse", or
  "held". Policy is documented in
  `src/gameplay/player/aim_controller.py` and can be swapped without
  touching Player or Combat.
- Player facing = aim direction (`facing` property derives from `aim_vector`).
  Movement direction is stored separately (`movement_direction`).
- Dodge charges: `Player.dodge_charges` is a reusable `DodgeCharges`
  (max_charges + cooldown from data). Exposes `current`, `charges`
  progress tuples, `ready`. UI subscribes; Player does not render UI.
- Dodge i-frames remain independent from charge regeneration.
- Camera hooks: `screen_to_world` (shake/zoom-aware inverse transform),
  `shake_offset`, `set_bounds` (boss arenas), `world_to_screen`.
- HIT and DEAD player states are wired placeholders; Phase 4 fills them.
- Collision layers (WORLD/PLAYER_*/ENEMY_*) + masks are ready for enemies.
- `Player.reset()` restores run-start state (health, mana, charges, state).
- ActionFrame Aim/Attack channels are reserved for Phase 4 combat.

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
- General invulnerability system (beyond dodge i-frames) arrives with combat.
- Mouse aim priority policy ("most recent input wins") is implemented but
  not fully exercised by integration tests; Phase 4 can change it via
  AimController without touching Player/Combat.
