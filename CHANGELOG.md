# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

### Added

- Phase 10 — Build System Integration (2026-07-28):
  - Ability executors wired into Player: 4 ability slots (Q/E/R/T) in Player.ability_executors dict, activation from PlayerIntent.ability_pressed via input actions (SKILL_1→Q, SKILL_2→E, ULTIMATE→R, AURA→T). AbilityExecutor.cooldown lifecycle integrated into Player.update().
  - Ability data files: warrior_charge (dash), warrior_shield_bash (knockback+armor), warrior_whirlwind (AoE), warrior_war_cry (aura/buff). All with cooldowns and effects.
  - Passive modifiers applied to BuildState: apply_passive_modifier() for damage, max_health, move_speed, attack_speed, dodge_charges, crit_chance, tag-specific. Passives loaded from data/passives/ and applied through PlaytestScene._apply_passives_to_player().
  - Class loadout system: data/classes/warrior.yaml defines starting weapon/abilities/passives. PlaytestScene._apply_class_loadout() loads and applies on scene init.
  - Weapon upgrade system: BuildState.weapon_upgrades dict (run-time modifications), add_weapon_upgrade()/get_weapon_upgrade(), applied via _reapply_weapon() which recomputes attack data with upgrade modifiers.
  - Expanded reward pipeline: apply_boon_to_build() now handles weapon_upgrade, ability, passive boon tags to add new build components.
  - Build state re-application on room transitions: _reapply_weapon() + _apply_build_to_player() called in _on_room_transition.
  - 5 new tests: ability cooldown, passive + boon stacking, weapon upgrade + boon interaction, ability/passive acquisition via boons, full build reset.
  - Suite: **306 passed + 1 skip** (up from 301).

- Phase 9 — Build System Foundation (2026-07-28):
  - BuildState (`src/gameplay/builds/build_state.py`): authoritative run build representation with weapon/ability/passive/boon IDs, cached modifier values (damage_mult, move_speed_mult, attack_speed_mult, max_health_bonus, dodge_charge_bonus, crit_chance), tag-specific damage modifiers, total_damage_for() computation with tag synergy.
  - WeaponData (`src/gameplay/builds/weapon.py`): data-driven weapon definition from YAML, apply_to_attack() modifies AttackData (damage_mult, speed_mult, reach_mult, spread_mult).
  - 3 prototype weapons: Warrior Sword (balanced, sweep), Warrior Spear (reach, piercing/thrust), Warrior Axe (wide sweep, high damage, slow). Data files under data/weapons/ with corresponding attack data under data/combat/attacks/.
  - AbilityData + AbilityExecutor (`src/gameplay/builds/ability.py`): data-driven ability cooldowns, activation, effects. Three prototype abilities: Charge (dash), Shield Bash (knockback+armor), Whirlwind (AoE spin).
  - PassiveData (`src/gameplay/builds/passive.py`): data-driven passive modifiers (StatModifier) with stack/max_stacks support.
  - BoonData (`src/gameplay/builds/boon.py`): data-driven run boons, apply_boon_to_build() applies effects (stat modifiers + tag-specific bonuses). 11 prototype boons with tag synergy (melee, sweep, piercing, thrust, global).
  - Tag/synergy system: BuildState._tag_mods dictionary enables tag-based effect matching (e.g. "piercing attacks +35%" only applies to attacks with the piercing tag).
  - PlaytestScene updated: first room clear offers 3-weapon choice (→ aim direction selects), subsequent room clears offer boon choices from registry, BuildState modifications feed into player stats (move speed, max HP, attack data).
  - Reward → Build pipeline: Boon selection → apply_boon_to_build() → BuildState cached modifiers → Player stat updates.
  - Death/reset: BuildState.reset() clears all temporary boon IDs and cached modifier values.
  - Data validation and loader: weapons, abilities, passives, boons categories added to main.py/data_loader/validate_data.py.
  - 16 new tests: BuildState lifecycle, weapon data loading, weapon tag differences, weapon attack modification, boon loading, global damage/tag damage/health boons, stacking, tag synergy, build reset, sword+melee build path, spear+piercing build path.
  - Suite: **301 passed + 1 skip** (up from 285).

- Phase 8 — Vertical Slice COMPLETE (2026-07-28):
  - Boss AI (`src/gameplay/bosses/boss_ai.py`): `BossAI` class with phase-based AI, `BossPhase` enum (PHASE_1, PHASE_2, DEAD), two AttackExecutors (primary sweep + AoE shockwave), phase transition at 50% HP, strafing/circle/back-up movement behaviors.
  - Boss data (`data/enemies/bosses/first_boss.yaml`): 300 HP, 48x48 body, phase-specific speed and attack tuning.
  - Boss arena room (`data/world/rooms/greybox_boss_arena.yaml`): 960x608 open arena with entry/exit doors and two cover pillars.
  - Boss attack data (`data/combat/attacks/boss_primary.yaml`, `boss_primary_fast.yaml`, `boss_aoe.yaml`): three attack profiles for Phase 1, Phase 2, and AoE shockwave.
  - Stage generator (`src/world/stage_generator.py`): `_generate_boss_floor()` appends a single-room boss floor after all normal floors. `generate_stage()` now returns `config.floor_count + 1` floors.
  - PlaytestScene boss integration (`src/gameplay/playtest_scene.py`): boss encounter detection, `_is_boss_active()` door blocking (can't leave while boss alive), BossAI hitbox collection, boss rendering (purple/red phase colors, wide health bar with phase dot indicator, attack hitbox visualization), victory/death game-over overlays, boss defeat → stage complete flow.
  - EnemyFactory (`src/gameplay/enemies/enemy_factory.py`): `build_boss()` function with lazy import, boss attack data wiring, phase 2 speed boost from document.
  - Integration tests (`tests/integration/gameplay/test_stage_traversal.py`): 3 new tests — boss spawns in arena, boss blocks exit while alive, boss allows exit after death.
  - Stage generation tests updated for boss floor: `test_generate_stage_creates_configured_floor_count` now expects `floor_count + 1`, `test_room_bounds_are_parameterized_by_config` exempts boss floor, `test_template_pools_actually_used` checks `greybox_boss_arena`.
  - Suite: **285 passed + 1 skip** (up from 282).

- Phase 4 — Combat Foundation (2026-07-27):
  - Damage pipeline (`src/gameplay/combat/damage.py`): `DamagePipeline` with invulnerability-aware damage application, overkill tracking, multi-hit stopping at death. Pure logic, framework-free.
  - Attack executor (`src/gameplay/combat/attack.py`): `AttackExecutor` managing the windup → active → recovery → cooldown lifecycle. Data-driven `AttackData` with configurable timing, damage, hitbox geometry. `AttackPhase` enum for state machine integration.
  - Invulnerability service (`src/gameplay/combat/invulnerability.py`): `InvulnerabilityService` managing multiple concurrent invulnerability sources (dodge, hitstun, etc.) with independent timers, `has_source`/`remaining` queries, `on_state_changed` callback, and `clear`.
  - Status effect framework (`src/gameplay/combat/status_effects.py`): `StatusEffectManager` with tag-based slot system, stacking (with cap), duration refresh, tick intervals, modifier aggregation.
  - Combat system (`src/gameplay/combat/combat_system.py`): `CombatSystem` orchestrating hit resolution via AABB overlap detection between hitboxes and vulnerable hurtboxes, publishing `entity_damaged`/`entity_killed`/`attack_hit`/`status_applied`/`status_expired` events.
  - Player integration: `Player` gains `invuln_service`, `status_manager`, and `attack_executor`. Dodge i-frames use the service instead of raw `_iframe_remaining`. Attack intent triggers the executor. `Player.reset()` clears combat state.
  - PlaytestScene: attack hitbox visualisation (orange rect) during the active window. `CombatSystem` wired and ready for Phase 5 enemies.
  - Data pipeline: `data/schemas/attack.schema.yaml`, `data/combat/attacks/player_default.yaml` (greybox test attack). `combat` category added to `validate_data.py` schema mapping.
  - 46 new tests (suite: 209 passed + 1 skip):
    - `tests/unit/combat/test_damage.py` — 10 damage pipeline tests
    - `tests/unit/combat/test_invulnerability.py` — 14 invulnerability service tests
    - `tests/unit/combat/test_attack.py` — 11 attack executor tests
    - `tests/unit/combat/test_status_effects.py` — 11 status effect tests

- Initial empty project skeleton (directory structure per PROJECT_STRUCTURE.md).
- Design drafts for the four design documents (proposal status, decisions D1-D15 open).
- Pre-production infrastructure (autonomous session, 2026-07-26):
  - Core runtime: events, state machine, dependency container, constants, enums.
  - Utilities: logging, YAML config loading, asset catalog, seeded RNG, atomic file IO.
  - Data pipeline: data loader, content registry, 17 provisional schemas, schema validator CLI.
  - Save infrastructure: versioned save schema, atomic save manager, migration registry.
  - Procedural floor-graph generator prototype (navigation-model agnostic, D7-safe).
  - Bootstrap entry point (`src/main.py`), dev scripts (run/test/validate_data).
  - 9 infrastructure test modules (~55 tests) — pending first execution (no interpreter in prep environment).
  - Docs: ARCHITECTURE.md, DATA_FLOW.md, SAVE_SYSTEM.md, VERTICAL_SLICE.md, SETUP.md, README.
  - IMPLEMENTATION_PLAN.md rewritten as Phases 0-20 (original working agreements preserved).

### Fixed

- Environment established (2026-07-27): Python 3.12.10 + uv 0.11.32 via winget; `.venv` created with `uv sync` (CPython 3.14.6 in venv); `uv.lock` generated.
- Phase 1 verification PASSED (2026-07-27): 57 tests + 1 intentional skip, data validation OK, bootstrap exit 0, ruff clean, mypy clean.
- `data_loader.load_category` now skips comment-only placeholder files consistently with the validator CLI (was a bootstrap warning source); 3 regression tests added.
- Lint/type hygiene: ruff auto-fixes + formatting across the codebase; `types-pyyaml` added to dev dependencies.

### Added

- docs/development/FRAMEWORK_EVALUATION.md — scored comparison of pygame-ce / Arcade / pyglet, architecture review, OOP-vs-ECS evaluation, and a framework recommendation (decision pending on the human developer).
- docs/design/DESIGN_DECISIONS.md — registry of the human developer's LOCKED decisions L1-L16 (2026-07-27): Dark Fantasy Babylon theme (Tower of Babel, humanity vs. gods), story foundation, Warrior/Ranger/Mage classes (Warrior first), combat philosophy, control layout (LMB/RMB/Q/E/R/T/Space), weapon categories per class, 5-floor stages with floor-5 boss + Return-or-Continue, death rules, Gold + Babylon Relics currencies, caravan banking (20/80 rule), permanent progression structure, town progression (mutual gating), class mastery, lightweight equipment philosophy, run start rule, core design philosophy.
- Phase 2 (Input and Game State) complete (2026-07-27): engine bootstrap (game, game_loop, scenes, hybrid entity/component/system model), abstract input system (config-driven bindings, keyboard+mouse and gamepad adapters), pygame-ce renderer adapter (window/timing), placeholder scene, bootstrap `--headless/--frames` flags.
- pygame-ce 2.5.7 as the official game framework (developer decision); adapter isolation rule guarded by tests/unit/test_framework_isolation.py.
- 24 new tests (suite: 81 passed + 1 intentional skip): entity/component/system, scene manager, game-loop frame order, input mapping, framework isolation, headless bootstrap smoke.

### Changed

- All four design documents updated to DRAFT v2 with the locked decisions (see DESIGN_DECISIONS.md); open questions reduced to D1, D3-detail, D7-D11, D14, D15.
- IMPLEMENTATION_PLAN.md: Phases 0-2 marked complete; next phase is Phase 3 (Player Controller).
- VERTICAL_SLICE.md and SETUP.md aligned with locked decisions and verified environment.

### Added

- Phase 3 (Player Controller) complete (2026-07-27) — the first PLAYABLE slice:
  - Player entity as a composition root (no god class): `PlayerController` (only ActionFrame consumer), `KinematicBody` (data-driven movement), Hitbox/Hurtbox components (layers + masks, enemy-ready), player state machine on `core.state_machine` (IDLE/MOVE/DODGE live; HIT/DEAD wired placeholders), `PlayerStats` from data files.
  - 8-direction movement with acceleration/friction, analog variable speed, diagonal normalization; sprint-ready architecture (max speed is a per-call parameter).
  - Dodge/roll (Space): fixed-velocity roll covering a configured distance, configurable i-frame window driving `Hurtbox.vulnerable`, events `player_dodge` / `player_state_changed` on the bus.
  - Physics layer: swept AABB `CollisionWorld.move_and_slide` (anti-tunneling), `Direction8`, `approach`/`clamp_magnitude` movement math.
  - Reusable camera: exponential smooth follow, pixel-perfect integer transforms, configurable zoom, bounds clamping (boss-arena ready), screen-shake hook (`shake_offset`).
  - Greybox test arena (`data/world/rooms/greybox_arena.yaml`, hand-authored, non-procedural) + `PlaytestScene` wired as the bootstrap scene; state-tinted placeholder rendering via the animation hook (`animation_pose`, clip-name convention settled).
  - Data-driven configuration: `data/player/stats.yaml` (movement/dodge/resources/boxes), `config/display.yaml` camera section; player + room schemas extended and validated.
  - docs/development/STATUS.md — living handoff file for future agents (referenced from AI_CONTEXT.md).
- 64 new tests (suite: 145 passed + 1 intentional skip): collision/movement/camera units, player stats/state/dodge units, scene-level scripted playtest integration.

### Fixed

- Collision resolution upgraded from discrete overlap to swept per-axis clamping after tests caught tunneling at large frame steps.
- Dodge applies roll velocity on its starting frame (instant response); the starting frame counts toward roll duration (no distance overshoot).

### Added (Phase 3.5 amendments, 2026-07-27)

- Charged dodge system (`src/gameplay/player/dodge_charges.py`): reusable,
  data-driven (`dodge_max_charges`, `dodge_cooldown`), independent per-charge
  timers, UI-ready state (`current`, `charges`, `ready`), reset on death.
- Aim/movement/facing split: `Player.aim_vector` / `Player.movement_direction` /
  `Player.facing` are separate properties; `AimController` owns priority policy.
- Input channels separation: `DeviceSnapshot`/`ActionFrame` gain independent
  `move_*` (WASD), `aim_*` (arrows / right stick), and `pointer`/`pointer_moved`
  (mouse); `PlayerController.build_intent` maps only movement+dodge attack;
  scene-level `AimController` feeds `Player.set_aim` each frame.
- Mouse-to-world via `Camera.screen_to_world` (shake/zoom-aware).
- Data/schema: `data/player/stats.yaml` gains `dodge_max_charges`; schema
  `data/schemas/player.schema.yaml` updated accordingly.
- Tests added: 18 new tests in `test_dodge_charges.py` (10 charge scenarios),
 `test_aim.py` (10 aim/movement/facing tests), plus `test_player_dodge.py`
 updated for facing independence. Suite: 163 passed + 1 skip.

 ### Added (Phase 5 — Enemy Foundation, 2026-07-27)

 - Enemy entity (`src/gameplay/enemies/enemy.py`): composition root with
 `KinematicBody`, `Hurtbox` (ENEMY_HURTBOX layer), health property synced to
 alive state, `InvulnerabilityService`, `StatusEffectManager`, `AttackExecutor`.
 Config parsed from data documents via `EnemyConfig.from_document()`.
 - SimpleAI (`src/gameplay/enemies/enemy_ai.py`): state machine
 (IDLE/CHASE/ATTACK/DEAD), facing tracking, aggro range, attack range checks,
 velocity control per AI state. Framework-extensible architecture.
 - EnemyFactory (`src/gameplay/enemies/enemy_factory.py`): builds Enemy + SimpleAI
 from `ContentRegistry` data documents. `register_enemy_hook` for per-type
 customization.
 - Data: `data/enemies/common/greybox_dummy.yaml` — greybox training dummy
 (health 50, damage 10, speed 60, chase+attack AI).
 - PlaytestScene wired for combat: `CombatSystem.resolve_hits()` called every
 frame for both player→enemy and enemy→player. Enemy rendering (tinted rect,
 health bar, attack hitbox). Two dummies spawned at fixed positions.
 - Player combat reactions: `on_hit()`, `die()`, `set_hitstun()` methods.
 `_update_hit()` state handler with timer-based recovery.
 DEAD→IDLE transition allowed in player state machine (for reset after death).
 - 360-degree attack fix: `PlaytestScene` now passes raw `player.aim_vector`
 (continuous) instead of `pose.facing.vector` (Direction8 quantized) to
 `AttackExecutor.hitbox_for()`.
 - 27 new tests (suite: 236 passed + 1 skip):
 - `tests/unit/enemies/test_enemy.py` — enemy entity (15), AI (5), factory (2),
   combat resolution (5).
 - Tools: `tools/verify_combat.py` — headless end-to-end combat verification
script.

### Added (Phase 6 — Room/Dungeon Foundation, 2026-07-28)

- FloorAssembler (`src/world/floor_assembler.py`): converts FloorGraph →
  FloorData with all rooms wired by graph links. Template selection by
  node kind (start→greybox_start, combat→greybox_room, boss→greybox_exit).
  Unknown kinds fall back to combat template.
- FloorData dataclass: `rooms`, `start_room_id`, `exit_room_id`,
  `connections` map for traversal.
- RoomManager extended: supports floor mode (`load_floor(floor_data)`)
  with pre-loaded rooms in addition to registry mode.
- Room templates: `greybox_start` (start kind, right door only),
  `greybox_room` (combat kind, left+right doors, interior obstacles),
  `greybox_exit` (boss kind, left door only, solid right wall).
- PlaytestScene floor mode: accepts FloorData, transitions between rooms,
  spawns enemies per room kind (combat → 2 dummies, start/boss → none).
- `main.py` rewritten: generates seeded FloorGraph → assembles floor →
  starts scene with floor data. `--seed` argument for reproducibility.
- 10 new tests (suite: 246 passed + 1 skip):
  - `tests/unit/test_floor_assembly.py` — floor assembly integrity,
    door validity, reachability, determinism (10 tests).
