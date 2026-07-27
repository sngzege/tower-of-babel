# CURRENT STATUS (living handoff file)

> **Purpose:** single, always-up-to-date checkpoint so ANY agent (or the
> developer) can resume work without re-reading the whole project.
> **Rule:** whoever advances the project updates this file in the same
> commit (IMPLEMENTATION_PLAN.md snapshot + CHANGELOG.md too).
> Last updated: **2026-07-27** (Phase 4 — Combat Foundation complete).

## 1. Where we are

- **Phase 0 — Project foundation:** COMPLETE.
- **Phase 1 — Core engine/runtime:** COMPLETE (verified 2026-07-27).
- **Phase 2 — Input and game state:** COMPLETE (2026-07-27). pygame-ce, adapter isolation.
- **Phase 3 — Player controller:** COMPLETE (2026-07-27). Playable greybox slice.
- **Phase 3.5 — Approved amendments:** COMPLETE (2026-07-27). Dodge charge system, movement/aim/facing split.
- **Phase 4 — Combat foundation:** COMPLETE (2026-07-27). Damage pipeline, attack executor, invulnerability service, status effect framework.
- **NEXT: Phase 5 — Enemy foundation** (see IMPLEMENTATION_PLAN.md; depends on Phase 4).

## 2. What is playable right now

`uv run python scripts/run.py` launches the greybox arena:

- WASD: 8-direction movement, analog speed.
- Arrow keys: independent 8-direction aim (keyboard aim channel).
- Mouse: positional aim (mouse aim channel). Priority: most recent input wins.
- Space (or gamepad A): dodge roll with charge-based cooldown (default 2 charges, 1.5s regen each).
- Left Mouse / primary attack key: basic attack with a 0.15s active hitbox window, orange visual indicator.
- Player facing and animation follow AIM, not movement.
- The player collides with walls/obstacles; the camera follows smoothly, clamped to the room; Escape/close button quits.
- All tuning lives in `data/player/stats.yaml`; the map in `data/world/rooms/greybox_arena.yaml`; camera defaults in `config/display.yaml`.

## 3. Verification (all green as of Phase 4)

```text
uv run pytest -q                                -> 209 passed, 1 skipped
uv run ruff check src tests tools scripts       -> clean
uv run python -m mypy src                       -> clean (116 files)
uv run python tools/data_validation/validate_data.py -> OK
uv run python scripts/run.py --headless --frames 300 -> exit 0
```

(The 1 skip is intentional: the pygame smoke test skips when pygame is unavailable.)

## 4. Architecture map after Phase 4

| Layer | State |
|-------|-------|
| `src/core` | events, state machine, DI, registry, data loader (Phase 1) |
| `src/engine` | game, loop, scenes, hybrid entity/component/system (Phase 2) |
| `src/input` | ActionFrame with independent move/aim channels (Phase 3.5) |
| `src/rendering` | renderer protocol + pygame adapter (Phase 2) — Camera (Phase 3) |
| `src/physics` | collision (swept AABB), movement (KinematicBody), hitbox, hurtbox (Phase 3) |
| `src/gameplay/player` | Player (composition root) + DodgeCharges + AimController + AttackExecutor + InvulnerabilityService + StatusEffectManager (Phase 4) |
| `src/gameplay/combat` | DamagePipeline, AttackExecutor, InvulnerabilityService, StatusEffectManager, CombatSystem (Phase 4) |
| `src/gameplay` | PlaytestScene with Phase 4 combat hooks (attack hitbox visualisation) |
| `src/world` | Room data model (Phase 3) + dungeon prototype (Phase 1) |

Key contracts future phases must respect (Phase 4 additions highlighted):

- **InvulnerabilityService**: replaces raw `_iframe_remaining`. Player's `invulnerable` property delegates to the service. Supports multiple concurrent sources ("dodge", "hitstun", etc.) with independent timers and an `on_state_changed` callback.
- **AttackExecutor**: data-driven lifecycle (windup/active/recovery/cooldown). Connected to `PlayerIntent.primary_attack_pressed`. Hitbox visualised as an orange rect during active window.
- **DamagePipeline**: stateless, framework-free. Applies `DamageInstance` to any `DamageTarget` (anything with health + invulnerable). Handles invulnerability, overkill, and multi-hit stopping at death.
- **StatusEffectManager**: tag-based effect slots per entity. Supports stacking (with cap), duration refresh, tick intervals, and modifier aggregation. No content defined yet (framework only).
- **CombatSystem**: orchestrates hit resolution. Takes hitboxes and entities, detects AABB overlaps, applies damage, publishes events. Ready for Phase 5 enemies.
- `data/combat/attacks/` — greybox player attack data (`player_default.yaml`); schema validated.

## 5. How to resume (for the next agent)

1. Read RULES.md, this file, IMPLEMENTATION_PLAN.md (status snapshot).
2. For Phase 5: also read ARCHITECTURE.md section 5 (Enemies). Need an enemy entity, AI framework (state machine + behavior modules), enemy factory from registry.
3. Follow the AI DEVELOPMENT LOOP (end of IMPLEMENTATION_PLAN.md).
4. Before finishing: run the five verification commands above; update this file, the plan snapshot, and CHANGELOG.md; commit per RULES.md section 19.

## 6. Technical debt / known gaps

- No input buffering / coyote-style dodge queue yet (feel tuning, optional).
- No sprite pipeline: player renders as a tinted rect via the animation hook.
- Internal pixel resolution is an open DESIGN decision; camera zoom is provisional.
- **Attack data is currently hardcoded in Player.__init__** (AttackData constructor) instead of being loaded from data files. Should be loaded from `data/combat/attacks/` via the content registry in a future pass.
- CombatSystem only checks AABB overlaps; no knockback/physics push applied yet.
- No enemies to fight yet (Phase 5).
- Mouse aim priority policy ("most recent input wins") is implemented but not fully exercised by integration tests.
