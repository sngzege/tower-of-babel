# CURRENT STATUS (living handoff file)

> **Purpose:** single, always-up-to-date checkpoint so ANY agent (or the
> developer) can resume work without re-reading the whole project.
> **Rule:** whoever advances the project updates this file in the same
> commit (IMPLEMENTATION_PLAN.md snapshot + CHANGELOG.md too).
> Last updated: **2026-07-29** (Phase 12 — Stabilization & Developer Experience COMPLETE).

## 1. Where we are

- **Phase 0-8:** COMPLETE.
- **Phase 9 — Build System Foundation:** COMPLETE.
- **Phase 10 — Build System Integration:** COMPLETE.
- **Phase 11 — Stabilization & Readability:** COMPLETE (2026-07-28).
- **Phase 12 — Developer Experience & Damage Formula:** COMPLETE (2026-07-29).

## 2. What is playable right now

`uv run python scripts/run.py` launches the greybox build with full run lifecycle, build system, and abilities.
`uv run python scripts/run.py --combat-test` launches a dedicated combat arena with 4 enemies for quick testing.

### Controls
- WASD: 8-direction movement
- Arrow keys: independent 8-direction aim
- Mouse: positional 360-degree aim
- Left Click: primary attack
- Space: dodge (2 charges, 1.5s regen)
- **Q**: Charge (dash forward dealing damage)
- **E**: Shield Bash (close-range knockback + temp armor)
- **R**: Whirlwind (AoE spin attack)
- **T**: War Cry (toggle damage buff, 30% while ON)

### HUD
- Top-left: HP bar with numeric text, weapon name, room/floor info, Fury status, enemy count
- Top-right: Ability cooldown bars with text labels (Q/E/R/T — READY/cooldown seconds/ON or OFF)
- Damage numbers float up from hit targets
- Enemies flash white briefly when hit
- Knockback is collision-aware (stops at walls), both directional and radial
- Rewards show weapon/boon names with direction hint (←1 ↓2 →3)
- Game-over screen shows title, stats summary, click-to-continue hint

### Run lifecycle
- Seeded stage: 3 procedural floors + 1 boss floor (4 floors total)
- Room encounters: combat rooms spawn greybox dummies
- Room clear → reward: first clear = 3-weapon choice, subsequent = boon pool
- Build carries through rooms/floors/boss
- Player death → red overlay → attack to restart
- Boss victory → green overlay → attack to restart

### Build system (Phase 9-10)
- **Weapons**: Sword (balanced), Spear (reach/piercing), Axe (wide/high damage)
- **Boons**: 17 YAML-defined boons with global and tag-specific modifiers
- **Abilities**: 4 Warrior abilities (Q/E/R/T) with cooldowns and real effects
- **Passives**: Hardy (+25 HP), Fury (+15% dmg below 50% HP placeholder)
- **Weapon upgrades**: Run-time damage/speed/reach/spread upgrades
- **Class loadout**: Warrior starts with sword + 4 abilities + 1 passive
- **Build reset**: All temporary state cleared on death/restart

## 3. Verification (as of Phase 11 — improved greybox)

```text
uv run pytest -q                                -> 332 passed, 1 skipped
uv run ruff check src tests tools scripts       -> clean (0 errors)
uv run python -m mypy src                       -> clean (129 files)
uv run python tools/data_validation/validate_data.py -> OK
uv run python scripts/run.py --headless --frames 300 --log-level WARNING -> exit 0
uv run python scripts/run.py --headless --combat-test --frames 300 --log-level WARNING -> exit 0
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
2. Next phase: Content Expansion (Phase 11 — see IMPLEMENTATION_PLAN.md).
3. Follow the AI DEVELOPMENT LOOP (end of IMPLEMENTATION_PLAN.md).
4. Before finishing: run the five verification commands; update STATUS.md, plan, and CHANGELOG.md; commit per RULES.md section 19; push to remote.

## 7. Technical debt / known gaps

- No sprite pipeline: player/enemies/boss render as tinted rects (elite now gold vs red).
- No input buffering / coyote-style dodge queue yet.
- Boss uses two separate AttackExecutors (primary + aoe) rather than a single data-driven attack switch.
- Boss room's victory exit door target is hardcoded — works but doesn't support stage-specific behavior.
- No animation/VFX/sound for boss phase transition.
- Boss rewards: currently no special boss reward or trophy drop.
- No meta-progression (village, persistent upgrades, currency).
- Shield Bash defense buff is a visual placeholder only (no actual damage reduction implemented).
- Ruff clean (0 errors — line-length set to 100 in pyproject.toml).
- Floor traversal in integration tests requires walking through doors.
- Ability data still has backward-compatible `damage` field alongside `coefficient`.
- DamageFormula supports enemy resistances/armor/difficulty scaling as future extensions (not implemented).
- Combat test respawn does not restore dead boss (intentional — boss testing requires full run restart).
- Weapon tags loaded from registry each frame for formula (minor perf cost; cache for release).
