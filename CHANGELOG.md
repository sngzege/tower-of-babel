# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

### Added

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
