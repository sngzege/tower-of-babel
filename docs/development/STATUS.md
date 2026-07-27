# CURRENT STATUS (living handoff file)

> **Purpose:** single, always-up-to-date checkpoint so ANY agent (or the
> developer) can resume work without re-reading the whole project.
> **Rule:** whoever advances the project updates this file in the same
> commit (IMPLEMENTATION_PLAN.md snapshot + CHANGELOG.md too).
> Last updated: **2026-07-27** (Phase 5 — Enemy Foundation complete).

## 1. Where we are

- **Phase 0 — Project foundation:** COMPLETE.
- **Phase 1 — Core engine/runtime:** COMPLETE.
- **Phase 2 — Input and game state:** COMPLETE. pygame-ce, adapter isolation.
- **Phase 3 — Player controller:** COMPLETE. Playable greybox slice.
- **Phase 3.5 — Approved amendments:** COMPLETE. Dodge charge system, movement/aim/facing split.
- **Phase 4 — Combat foundation:** COMPLETE. Damage pipeline, attack executor, invulnerability service, status effect framework. 360-degree free-aim hitbox rotation.
- **Phase 5 — Enemy foundation:** COMPLETE (2026-07-27). Enemy entity, SimpleAI (chase+attack), enemy factory from data, two greybox dummies in PlaytestScene. Hit resolution wired (player attacks enemies, enemies attack player). Player hitstun/death handling.
- **NEXT: Phase 6 — Room / dungeon foundation** (see IMPLEMENTATION_PLAN.md; depends on Phases 3, 5).

## 2. What is playable right now

`uv run python scripts/run.py` launches the greybox arena:

- WASD: 8-direction movement, analog speed.
- Arrow keys: independent 8-direction aim.
- Mouse: positional 360-degree aim (priority: most recent input wins).
- Space: dodge roll with charge-based cooldown (2 charges, 1.5s regen).
- Left Mouse / primary attack key: basic 360-degree attack (orange hitbox).
- **Two greybox enemies** that chase and attack the player.
- Enemies have health bars, take damage, and die.
- Player takes damage from enemies, enters hitstun state.
- Dodge i-frames block damage.
- Player collision with walls/obstacles; camera follow.
- All tuning in data files; map in data/world/rooms/greybox_arena.yaml.

## 3. Verification (as of Phase 5)

```text
uv run pytest -q                                -> 236 passed, 1 skipped
uv run ruff check src tests tools scripts       -> clean
uv run python -m mypy src                       -> clean (116 files)
uv run python tools/data_validation/validate_data.py -> OK
uv run python scripts/run.py --headless --frames 300 -> exit 0
```

(The 1 skip is intentional: the pygame smoke test skips when pygame is unavailable.)

## 4. Architecture map after Phase 5

| Layer | State |
|-------|-------|
| `src/core` | events, state machine, DI, registry, data loader (Phase 1) |
| `src/engine` | game, loop, scenes, hybrid entity/component/system (Phase 2) |
| `src/input` | ActionFrame with independent move/aim channels (Phase 3.5) |
| `src/rendering` | renderer protocol + pygame adapter (Phase 2) — Camera (Phase 3) |
| `src/physics` | collision (swept AABB), movement (KinematicBody), hitbox, hurtbox (Phase 3) |
| `src/gameplay/player` | Player (composition root) + DodgeCharges + AimController + AttackExecutor + InvulnerabilityService + StatusEffectManager (Phase 4) |
| `src/gameplay/combat` | DamagePipeline, AttackExecutor, InvulnerabilityService, StatusEffectManager, CombatSystem (Phase 4) |
| `src/gameplay/enemies` | Enemy (composition root), EnemyConfig, SimpleAI (chase+attack), EnemyFactory (Phase 5) |
| `src/gameplay` | PlaytestScene with Phase 4+5 combat hooks (hit resolution, enemy rendering, player hitstun) |
| `src/world` | Room data model (Phase 3) + dungeon prototype (Phase 1) |

### Phase 5 additions highlighted

- **Enemy**: composition root with body, hurtbox, health (property-synced with alive state), InvulnerabilityService, StatusEffectManager, AttackExecutor. Implements DamageTarget protocol for CombatSystem integration.
- **SimpleAI**: state machine (IDLE → CHASE → ATTACK → CHASE loop), facing tracking, aggro range, attack range checks.
- **EnemyFactory**: builds Enemy + SimpleAI from ContentRegistry data documents using EnemyConfig.from_document().
- **PlaytestScene**: now takes `enemies` parameter; each frame runs AI updates, enemy movement, CombatSystem hit resolution in both directions (player→enemy, enemy→player). Player hitstun with timer-based recovery.
- **Player**: added `on_hit()`, `die()`, `set_hitstun()` methods; `_update_hit()` state handler; DEAD→IDLE transition allowed for reset.

## 5. How to resume (for the next agent)

1. Read RULES.md, this file, IMPLEMENTATION_PLAN.md.
2. For Phase 6: implement room instances, doors/transitions, room manager, floor assembly from the floor graph.
3. Follow the AI DEVELOPMENT LOOP (end of IMPLEMENTATION_PLAN.md).
4. Before finishing: run the five verification commands; update STATUS.md, plan, and CHANGELOG.md; commit per RULES.md section 19.

## 6. Technical debt / known gaps

- No input buffering / coyote-style dodge queue yet.
- No sprite pipeline: player and enemies render as tinted rects.
- Internal pixel resolution is an open DESIGN decision; camera zoom is provisional.
- **Attack data is currently hardcoded in Player.__init__** instead of loaded from data files.
- CombatSystem only checks AABB overlaps; no knockback/physics push applied yet.
- Still only greybox enemies (no production content).
- Verify combat tool (`tools/verify_combat.py`) is a development utility, not production code.
