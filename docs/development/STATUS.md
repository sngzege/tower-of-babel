# CURRENT STATUS (living handoff file)

> **Purpose:** single, always-up-to-date checkpoint so ANY agent (or the
> developer) can resume work without re-reading the whole project.
> **Rule:** whoever advances the project updates this file in the same
> commit (IMPLEMENTATION_PLAN.md snapshot + CHANGELOG.md too).
> Last updated: **2026-07-28** (Phase 9 — Build System Foundation COMPLETE).

## 1. Where we are

- **Phase 0-7:** COMPLETE.
- **Phase 8 — Vertical Slice:** COMPLETE.
- **Phase 9 — Build System Foundation:** COMPLETE.

## 2. What is playable right now

`uv run python scripts/run.py` launches the greybox build with full run lifecycle:

- WASD: 8-direction movement, analog speed.
- Arrow keys: independent 8-direction aim.
- Mouse: positional 360-degree aim.
- Space: dodge roll with charge-based cooldown (2 charges, 1.5s regen).
- Left Mouse / primary attack key: basic 360-degree attack.
- **Seeded stage traversal**: 3 procedural floors + 1 boss floor (4 floors total).
- **Room encounters**: combat rooms spawn enemies (greybox dummies).
- **Room clear + reward**: clear all enemies → 3-choice reward selection via aim direction.
- **Player death**: player dies → run ends → red overlay → attack to restart.
- **Boss encounter**: First Boss "Warden of the First Floor" on final floor.
  - Phase 1 (100%-50% HP): slow charge/sweep attack.
  - Phase 2 (50%-0% HP): faster movement, faster attacks, AoE shockwave.
  - Exit blocked while boss alive; boss death unlocks exit.
- **Boss victory**: exit arena → stage complete → green overlay → attack to restart.
- **All tuning in data files** (enemies, rooms, stage, attacks, rewards).

## 3. Verification (as of Phase 8)

```text
uv run pytest -q                                -> 285 passed, 1 skipped
uv run ruff check src tests tools scripts       -> clean
uv run python -m mypy src                       -> clean (122 files)
uv run python tools/data_validation/validate_data.py -> OK
uv run python scripts/run.py --headless --frames 300 --log-level WARNING -> exit 0
```

(The 1 skip is intentional: the pygame smoke test skips when pygame is unavailable.)

## 4. Architecture map after Phase 8

| Layer | State |
|-------|-------|
| `src/core` | events, state machine, DI, registry, data loader (Phase 1) |
| `src/engine` | game, loop, scenes, entity/component/system (Phase 2) |
| `src/input` | ActionFrame with independent move/aim channels (Phase 3.5) |
| `src/rendering` | renderer protocol + pygame adapter (Phase 2) — Camera (Phase 3) |
| `src/physics` | collision (swept AABB), movement, hitbox, hurtbox (Phase 3) |
| `src/gameplay/player` | Player + DodgeCharges + AimController + PlayerController (Phase 4) |
| `src/gameplay/combat` | DamagePipeline, AttackExecutor, InvulnService, StatusEffectManager, CombatSystem (Phase 4) |
| `src/gameplay/enemies` | Enemy, EnemyConfig, SimpleAI, EnemyFactory + build_boss (Phases 5/8) |
| `src/gameplay/bosses` | BossAI, BossPhase — phase-based AI with 2-phase combat (Phase 8) |
| `src/gameplay/roguelike` | RunManager, RunState, RunResult, RoomEncounter, Rewards (Phase 8) |
| `src/world` | Room, Door, RoomManager, FloorAssembler, StageManager, StageGenerator (Phases 6-7) |
| `src/gameplay` | PlaytestScene with boss integration, victory/death/restart (Phase 8) |

## 5. Phase 8 additions

- **Boss AI** (`src/gameplay/bosses/boss_ai.py`): BossAI class with phase-based AI, two AttackExecutors (primary + AoE), phase transition at 50% HP, strafing movement, aggro/circle/back-up positioning.
- **Boss data** (`data/enemies/bosses/first_boss.yaml`): 300 HP, 48x48 body, phase-specific speed/attack/AoE tuning.
- **Boss room** (`data/world/rooms/greybox_boss_arena.yaml`): 960x608 arena with entry/exit doors and two cover pillars.
- **Boss attacks** (`data/combat/attacks/boss_*.yaml`): three attack profiles (primary, primary_fast Phase 2, AoE shockwave).
- **Stage generator** (`src/world/stage_generator.py`): `_generate_boss_floor()` appends a single-room boss floor after normal floors.
- **PlaytestScene** (`src/gameplay/playtest_scene.py`): boss encounter detection, _is_boss_active() door blocking, BossAI integration, boss rendering (purple, phase indicator, wide health bar), victory/death game-over overlays.
- **EnemyFactory** (`src/gameplay/enemies/enemy_factory.py`): `build_boss()` function for BossAI + Enemy construction.
- **Integration tests**: 3 new tests (boss spawns in arena, boss blocks exit while alive, boss allows exit after death).

## 6. How to resume (for the next agent)

1. Read RULES.md, this file, IMPLEMENTATION_PLAN.md.
2. Next phase: Build System (Phase 8 BUILD SYSTEM — see IMPLEMENTATION_PLAN.md).
3. Follow the AI DEVELOPMENT LOOP (end of IMPLEMENTATION_PLAN.md).
4. Before finishing: run the five verification commands; update STATUS.md, plan, and CHANGELOG.md; commit per RULES.md section 19; push to remote.

## 7. Technical debt / known gaps

- No sprite pipeline: player/enemies/boss render as tinted rects.
- No input buffering / coyote-style dodge queue yet.
- Boss uses two separate AttackExecutors (primary + aoe) rather than a single data-driven attack switch — works for one boss but would need generalization for multiple boss types.
- Boss room's victory exit door target is hardcoded by the floor assembler (FLOOR_EXIT_TARGET) — works for all stages but doesn't support stage-specific exit behavior.
- No animation/VFX/sound for boss phase transition.
- Boss rewards: currently no special boss reward or trophy drop (just stage completion; rewards from combat rooms earned during traversal are preserved).
- No meta-progression (village, persistent upgrades, currency).
