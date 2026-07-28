# IMPLEMENTATION PLAN

# ACTION RPG + ROGUELITE — START-TO-FINISH MASTER DEVELOPMENT PLAN

> **Status note (2026-07-26, autonomous pre-production):** this roadmap was rewritten to match the prepared architecture (docs/architecture/) and the design drafts (docs/design/). It supersedes the previous phase list. The original working agreements (development loop, AI loop, definition of done, final principle) are **preserved verbatim** at the end.
>
> **Legend:** `D1-D15` = open human design decisions (docs/design/GAME_DESIGN.md §12) · `TECH DECISION` = pending technical choice owned by the developer (framework, see docs/architecture/ARCHITECTURE.md §8) · `PROVISIONAL` = safe default that must remain easy to change.
>
> **How to use this plan (for the next AI agent):** work phase by phase, top to bottom. Do not skip ahead. Do not implement content that requires an unchecked design decision. After finishing work in a phase, run its tests and report per the AI DEVELOPMENT LOOP (end of file).

## CURRENT STATUS SNAPSHOT

- **Phase 0 — COMPLETE.**
- **Phase 1 — COMPLETE (verified 2026-07-27):** 57 tests + 1 intentional skip · data validation OK · bootstrap exit 0 · ruff/mypy clean.
- **Framework DECIDED (2026-07-27): pygame-ce** (docs/development/FRAMEWORK_EVALUATION.md). Design core **LOCKED**: docs/design/DESIGN_DECISIONS.md (L1-L16).
- **Phase 2 — COMPLETE (2026-07-27):** suite at 81 tests + 1 skip · headless 300-frame run exit 0 · loop order/input mapping/scene switching tested · adapter isolation enforced by test.
- **Phase 3 — COMPLETE (2026-07-27):** suite at 145 tests + 1 skip · playable greybox slice (move/dodge/collide/camera) · ruff/mypy/data-validation clean · headless 300-frame run exit 0. Details: docs/development/STATUS.md (living handoff file).
- **Phase 3.5 — COMPLETE (same commit):** charge-based dodge (reusable DodgeCharges component, data-driven dodge_max_charges + dodge_cooldown), movement/aim/facing split (AimController with mouse-vs-keyboard priority policy), screen_to_world camera inverse, keyboard-only movement (WASD) + arrow aim. Test suite at 163 passed + 1 skip. Details: CHANGELOG.md, ARCHITECTURE.md.
- **Phase 4 — COMPLETE (2026-07-27):** combat foundation — DamagePipeline (data-driven damage types/tags, invulnerability-aware, overkill tracking), AttackExecutor (windup/active/recovery/cooldown lifecycle, data-driven attack data), InvulnerabilityService (multiple concurrent sources with independent timers, event callback), StatusEffectManager (tag-based effect slots, stacking, tick/expire, modifier aggregation), CombatSystem (hit resolution orchestrator, AABB overlap detection, event publication). Suite at 209 passed + 1 skip. Details: CHANGELOG.md, STATUS.md.
- **Phase 4 post-baseline (2026-07-27):** 360-degree free-aim hitbox rotation (continuous aim vector, not 8-direction quantized). Attack hitbox follows raw mouse/keyboard aim. Attack cooldown tuned. PlaytestScene passes raw aim_vector to hitbox_for(). Suite at 236 passed + 1 skip.
- **Phase 5 — COMPLETE (2026-07-27):** enemy foundation — Enemy entity (composition root with body, hurtbox, health property synced to alive state, InvulnerabilityService, StatusEffectManager, AttackExecutor). SimpleAI (IDLE/CHASE/ATTACK/DEAD state machine, facing tracking, aggro range, attack range). EnemyFactory (builds from ContentRegistry data documents via EnemyConfig.from_document). Two greybox dummies in PlaytestScene. CombatSystem wired for both player→enemy and enemy→player hit resolution. Player hitstun/death handling. 27 new tests. Details: CHANGELOG.md, STATUS.md.
- **Phase 6 — COMPLETE (2026-07-28):** room/dungeon foundation — Door dataclass added to Room. RoomManager (floor mode + registry mode, transition detection/callbacks). FloorAssembler (FloorGraph→connected rooms, template selection by kind, door wiring). Room templates (greybox_start, greybox_room, greybox_exit) with standard door positions. PlaytestScene floor mode with per-kind enemy spawning. `main.py` uses FloorAssembler with seeded FloorGraph. 10 assembly integrity tests. Suite: 246 passed + 1 skip. Details: CHANGELOG.md, STATUS.md.
- **Phase 7 — IN PROGRESS (2026-07-28):** procedural generation — FloorAssembler extended with multi-template pools and seeded RNG selection. _KIND_TO_TEMPLATES supports multiple candidates per kind. 20-seed smoke test (all seeds produce valid floors). Suite: 248 passed + 1 skip. Remaining: encounter population wiring, stage data integration.
- **Phase 8 — IN PROGRESS (2026-07-28):** vertical slice / playable core loop — AttackData.from_document() for data-driven attack loading. Run lifecycle (RunManager, RunPhase, RunResult). Room encounter system (EncounterState, RoomEncounter, clear detection). Reward system (RewardDefinition, 3-choice selection, data-driven buffs). Player accepts AttackData from registry. Suite: 282 passed + 1 skip. Remaining: boss entity, full integration test, stage exit wiring.
- **Next phase: Phase 8 — BUILD SYSTEM** (after Phase 7 complete; depends on Phases 4, 1).

---

# PHASE 0 — PROJECT FOUNDATION

- **Objective:** governance documents, repository skeleton, tooling files.
- **Why:** rules and structure must exist before any code (RULES.md §1).
- **Depends on:** —
- **Systems:** none.
- **Files:** RULES.md, AI_CONTEXT.md, PROJECT_STRUCTURE.md, README.md, CHANGELOG.md, pyproject.toml, .gitignore, .editorconfig, .pre-commit-config.yaml, full directory skeleton.
- **Tests:** none.
- **Acceptance criteria:** structure matches PROJECT_STRUCTURE.md. ✔
- **Exit criteria:** — **COMPLETE (2026-07-26).**

---

# PHASE 1 — CORE ENGINE / RUNTIME

- **Objective:** framework-free runtime infrastructure: logging, config, events, state machine, dependency injection, seeded RNG, data loading, content registry, save infrastructure, data schemas, validation tooling, test foundation.
- **Why:** every later system builds on these primitives; they are design-decision-independent.
- **Depends on:** Phase 0.
- **Systems:** `src/core`, `src/utils`, `src/save`, `tools/data_validation`, `data/schemas`, `tests`.
- **Files (created):** core/{constants,enums,events,state_machine,dependency_container,data_loader,content_registry}.py · utils/{logger,config_loader,asset_loader,random_utils,file_utils}.py · save/{save_schema,save_manager,migrations}.py · world/dungeon_generator.py (prototype) · tools/data_validation/{schema_validator,validate_data}.py · scripts/{run,test,validate_data}.py · data/schemas/*.schema.yaml · tests/unit/*.py (9 modules).
- **Tests:** ~55 unit tests (infrastructure only; no gameplay tests).
- **Acceptance criteria:** `uv run python scripts/test.py` green · `uv run python scripts/validate_data.py` OK · `uv run python scripts/run.py` bootstraps cleanly.
- **Exit criteria:** all three commands pass on the developer machine (see docs/development/SETUP.md §4).

---

# PHASE 2 — INPUT AND GAME STATE

- **Objective:** choose the game framework (TECH DECISION), then build the engine bootstrap: window, game loop, scene system, and abstract input (keyboard + gamepad).
- **Why:** nothing can run without a window and a loop; gameplay must never depend on physical keys.
- **Depends on:** Phase 1 · **TECH DECISION: framework** (docs/architecture/ARCHITECTURE.md §8 — developer-owned).
- **Systems:** `src/engine` (game, game_loop, scene, scene_manager), `src/input`.
- **Status: COMPLETE (2026-07-27).**
- **Files:** engine/{game,game_loop,scene,scene_manager,entity,component,system}.py · input/{input_manager,keyboard,controller}.py · rendering/renderer.py (minimal window/timing adapter) · config/input.yaml (bindings) · pyproject.toml (+pygame-ce with RULES.md §14 justification).
- **Tests:** scene transitions; action-mapping unit tests; frame-order smoke test (headless if the framework allows).
- **Acceptance criteria:** window opens; scenes switch (boot → menu placeholder); abstract actions fire from keyboard and gamepad; loop order input → update → render is verified.
- **Exit criteria:** a placeholder square moves in a test scene at a stable frame rate.

---

# PHASE 3 — PLAYER CONTROLLER

- **Objective:** class-agnostic player entity: 8-direction movement, dodge with i-frames, player state machine, hitbox/hurtbox, greybox sprite.
- **Why:** movement feel is the first fun gate (RULES.md §10 priority order).
- **Depends on:** Phase 2.
- **Systems:** `src/gameplay/player`, `src/physics`.
- **Status: COMPLETE (2026-07-27).**
- **Files:** player/{player,player_controller,player_state,player_stats}.py · physics/{collision,hitbox,hurtbox,movement}.py · data/player/stats.yaml (PROVISIONAL greybox tuning) · rendering/camera.py · world/room.py · gameplay/playtest_scene.py · data/world/rooms/greybox_arena.yaml · config/display.yaml (camera section).
- **Tests:** movement math; dodge i-frame windows; state transitions; collision basics (incl. swept anti-tunneling); camera; scene-level scripted playtest (tests/integration/gameplay).
- **Acceptance criteria:** player moves and dodges in a test room; stats load from data files; no engine internals leaked into gameplay code. ✔
- **Exit criteria:** developer playtest approves movement feel. ⬅ HUMAN GATE (run: `uv run python scripts/run.py`).

---

# PHASE 4 — COMBAT FOUNDATION

- **Objective:** damage pipeline (data-driven types/tags), attack executor, invulnerability, status-effect framework.
- **Why:** combat is the moment-to-moment core; framework first, content later (RULES.md §10).
- **Depends on:** Phase 3.
- **Systems:** `src/gameplay/combat`.
- **Files:** combat/{combat_system,damage,attack,status_effects,invulnerability}.py.
- **Tests:** damage pipeline (RULES.md §17 priority); i-frame interaction; status stacking rules.
- **Acceptance criteria:** a scripted dummy can be damaged and killed; the player can be damaged and can die; combat events are published on the bus.
- **Exit criteria:** combat math is fully covered by tests; zero content implemented.

---

# PHASE 5 — ENEMY FOUNDATION

- **Objective:** enemy entity, AI framework (state machine + behavior modules), enemy factory building from registry documents.
- **Why:** one enemy proves the loop; the framework must scale to stage families later.
- **Depends on:** Phase 4.
- **Systems:** `src/gameplay/enemies`.
- **Files:** enemies/{enemy,enemy_ai,enemy_factory}.py · enemies/behaviors/ (framework) · data/enemies/common/ (ONE approved placeholder enemy).
- **Tests:** factory builds from a data document; AI state transitions; encounter spawn.
- **Acceptance criteria:** one approved placeholder enemy chases, attacks, and dies.
- **Exit criteria:** the enemy is beatable in a test room.

---

# PHASE 6 — ROOM / DUNGEON FOUNDATION

- **Objective:** room instances, doors/transitions, room manager, floor assembly from the floor graph.
- **Why:** turns the abstract graph (Phase 1 prototype) into playable space.
- **Depends on:** Phases 3, 5.
- **Systems:** `src/world` (world, room, room_manager), `src/physics` (collision).
- **Files:** world/{world,room,room_manager}.py · greybox room templates (data/world/rooms/) · placeholder tileset usage.
- **Tests:** graph→floor assembly integrity (doors match graph links); room transitions.
- **Acceptance criteria:** the player walks through a generated floor of connected greybox rooms.
- **Exit criteria:** floor traversal is stable across seeds.

---

# PHASE 7 — PROCEDURAL GENERATION

- **Objective:** stage assembly: stage data → floors → room templates + encounter sets; seeded reproducibility end to end.
- **Why:** replayability is a design pillar; seeds enable sharing and debugging.
- **Depends on:** Phase 6.
- **Systems:** `src/world` (dungeon_generator, map_generator, encounter_manager), registry.
- **Files:** world/{dungeon_generator,map_generator,encounter_manager}.py (extend prototype) · data/world/rooms/* · data/world/stages/* ("First Stage", greybox, approved placeholder).
- **Tests:** determinism per seed; room-kind placement rules; boss reachability (exists from Phase 1); encounter composition bounds.
- **Acceptance criteria:** First Stage generates valid floors for any seed; `validate_data.py` passes.
- **Exit criteria:** 20 seeds produce 20 valid floors (smoke check).

---

# PHASE 8 — BUILD SYSTEM

- **Objective:** tag/keyword vocabulary, modifier pipeline (stacking rules + priority), choice-of-3 boons, passives, ability loadout.
- **Why:** builds are the run's decisions (pillar 2, GAMEPLAY_DESIGN.md §19); framework before content.
- **Depends on:** Phases 4, 1 (registry).
- **Systems:** build framework across `src/gameplay` (abilities, modifiers, reward selection).
- **Files:** player/abilities.py · combat modifier hooks · roguelike/reward_selection.py · data/abilities/, data/passives/ (approved greybox placeholders).
- **Tests:** tag synergy resolution; stacking rules; seeded choice-of-3; loadout swap.
- **Acceptance criteria:** picking boons measurably changes a scripted fight; schemas validate.
- **Exit criteria:** one tag synergy is demonstrable in a test.

---

# PHASE 9 — RUN SYSTEM

- **Objective:** run state, stage progression, the Return-or-Descend mechanism, run end + outcomes, reward flow.
- **Why:** turns systems into a run — the middle of the core loop.
- **Depends on:** Phases 7, 8.
- **Systems:** `src/gameplay/roguelike` (run, run_manager, seed), `core.enums.RunOutcome`.
- **Files:** roguelike/{run,run_manager,seed}.py.
- **Tests:** run lifecycle; every RunOutcome path (death/extract/victory/abandon — mechanism is D4-agnostic); reward conversion to result payloads.
- **Acceptance criteria:** a simulated run completes headlessly: enter → stage clear → choice → end → results data.
- **Exit criteria:** run results are handed off as plain data (ready for the village).

---

# PHASE 10 — BOSS FRAMEWORK

- **Objective:** boss entity, data-driven phases, arena gate, trophy award, unlock hooks.
- **Why:** bosses gate progression and feed the village (GAMEPLAY_DESIGN.md §9).
- **Depends on:** Phase 9.
- **Systems:** `src/gameplay/bosses`.
- **Files:** bosses/{boss,boss_ai}.py · bosses/phases/ · data/enemies/bosses/ ("First Boss", approved greybox).
- **Tests:** phase transitions at hp thresholds; trophy award; gate locking/unlocking.
- **Acceptance criteria:** First Boss fight works end to end; the trophy lands in run results.
- **Exit criteria:** the slice boss is beatable and lethal.

---

# PHASE 11 — VILLAGE FRAMEWORK

- **Objective:** village scene, building plots, building tiers (functional + visual states), application of run results (trophies/materials) to the village.
- **Why:** the village is the body of the meta-game (pillar 4; GAMEPLAY_DESIGN.md §18).
- **Depends on:** Phase 9 (run results), Phase 1 (save infra).
- **Systems:** **new package `src/gameplay/village/`** (structural addition — PROJECT_STRUCTURE.md updated accordingly).
- **Files:** gameplay/village/{__init__,village,building,npc,village_scene}.py (skeleton prepared in pre-production) · data/village/buildings/ (3 placeholder buildings) · greybox village map.
- **Tests:** tier upgrade applies cost → unlock; visual state mapping; persistence roundtrip.
- **Acceptance criteria:** returning from a run spends a trophy + material → building tier increases → change is visible in the village scene.
- **Exit criteria:** the return-to-village beat works end to end.

---

# PHASE 12 — NPC FRAMEWORK

- **Objective:** service NPCs, progression tracks (service tier first), milestone-driven arrival, dialogue data plumbing.
- **Why:** NPC progression must have gameplay consequences (GAMEPLAY_DESIGN.md §18).
- **Depends on:** Phase 11.
- **Systems:** `src/gameplay/village/npc.py`, `data/npcs/`.
- **Files:** npc system module(s) · data/npcs/ ("NPC A/B/C" placeholders, approved) · dialogue as data (localization deferred).
- **Tests:** arrival trigger fires on milestone; track progression changes service options.
- **Acceptance criteria:** NPC A arrives after the first boss kill; a service tier unlocks a new option.
- **Exit criteria:** 3 slice NPCs functional per VERTICAL_SLICE.md.

---

# PHASE 13 — PERSISTENT PROGRESSION

- **Objective:** hero progression behind a D13-agnostic interface, class mastery, unlock engine feeding reward pools, depth records.
- **Why:** long-term goals — the player must always have a reason to push deeper.
- **Depends on:** Phases 8, 12.
- **Systems:** `src/gameplay/progression`, `data/unlocks/`, `data/progression/`.
- **Files:** progression/{xp,leveling,meta_progression}.py · unlock/progression data (approved placeholders).
- **Tests:** mastery gain; unlock grant → reward-pool integration; record updates; save/load persistence.
- **Acceptance criteria:** after a run, mastery and unlocks visibly expand the next run's options.
- **Exit criteria:** progression survives an app restart.

---

# PHASE 14 — SAVE / LOAD INTEGRATION

- **Objective:** wire persistent + run state into the save manager; slot handling; D15 policy behind a config switch.
- **Why:** persistence closes the meta loop (RULES.md §18).
- **Depends on:** Phase 13 (owners), Phase 1 (infra).
- **Systems:** `src/save` + all state owners.
- **Files:** payload builders per owning system; save wiring in bootstrap.
- **Tests:** full roundtrip including run_state; migration path; corrupted-save handling.
- **Acceptance criteria:** quit mid-slice → restart → exact state restored; SAVE_SYSTEM.md failure policy holds.
- **Exit criteria:** all save tests green.

---

# PHASE 15 — VERTICAL SLICE INTEGRATION

- **Objective:** assemble the complete loop per docs/development/VERTICAL_SLICE.md.
- **Why:** prove the loop is fun before content volume (RULES.md §10).
- **Depends on:** Phases 2-14.
- **Systems:** everything.
- **Files:** greybox assets, slice content data, scene flow (menu → village → dungeon → death/victory → village).
- **Tests:** headless scripted full run (integration); slice acceptance checklist.
- **Acceptance criteria:** VERTICAL_SLICE.md §4 items 1-8 all pass.
- **Exit criteria:** developer playtest sign-off: the loop is fun enough to expand.

---

# PHASE 16 — CONTENT EXPANSION

- **Objective:** real content per approved design: classes, specializations, stages, bosses, NPCs, items, abilities, passives.
- **Why:** content only after the loop is validated (RULES.md §9-§10).
- **Depends on:** Phase 15 · **human design approvals (D2, D12 and related).**
- **Systems:** all content pipelines (DATA_FLOW.md).
- **Files:** data/ content per category; assets per approved art direction.
- **Tests:** schema validation for every content file; balance harness; regression.
- **Acceptance criteria:** each content item is approved, schema-valid, and reviewed in play.
- **Exit criteria:** v1 content set complete.

---

# PHASE 17 — POLISH

- **Objective:** game feel (hit-stop, flashes, shake within budget), transitions, audio implementation, UI polish.
- **Why:** feel sells the loop (EXPERIENCE_DESIGN.md §17).
- **Depends on:** Phase 16.
- **Systems:** `src/rendering` (effects, particles), `src/audio`, `src/ui`.
- **Files:** rendering/{particles,effects,animation}.py · audio/*.py · ui polish.
- **Tests:** performance smoke; regression.
- **Acceptance criteria:** feedback checklist from EXPERIENCE_DESIGN.md §17 is satisfied.
- **Exit criteria:** developer feel-pass approved.

---

# PHASE 18 — OPTIMIZATION

- **Objective:** profile, then optimize measured bottlenecks only (RULES.md §15).
- **Why:** correctness first; performance work must be evidence-driven.
- **Depends on:** Phase 17.
- **Systems:** `src/debug` (profiler), hot paths identified by profiling.
- **Files:** debug/profiler.py · targeted optimizations.
- **Tests:** performance benchmarks before/after.
- **Acceptance criteria:** target frame rate on target hardware with headroom.
- **Exit criteria:** no critical performance issues open.

---

# PHASE 19 — QA

- **Objective:** full verification: unit/integration/regression, save compatibility, input devices, resolutions, performance, playtest rounds.
- **Depends on:** Phase 18.
- **Systems:** tests/, `src/debug`.
- **Files:** additional integration + regression tests as needed.
- **Tests:** the whole suite, plus manual QA checklist (new game, save, load, death, restart, victory, controller, keyboard, resolution, audio, performance).
- **Acceptance criteria:** no critical bugs open.
- **Exit criteria:** release candidate declared.

---

# PHASE 20 — RELEASE PREPARATION

- **Objective:** build script, asset packaging, versioning, release configuration.
- **Depends on:** Phase 19.
- **Systems:** `scripts/build.py`, packaging tooling.
- **Files:** scripts/build.py · release config.
- **Tests:** clean-machine install test of the packaged build.
- **Acceptance criteria:** packaged build runs the full loop on a clean machine.
- **Exit criteria:** release.

---

# DEVELOPMENT LOOP

Every feature follows:

1. Define
2. Approve
3. Design
4. Implement
5. Test
6. Play
7. Review
8. Balance
9. Document
10. Commit

---

# AI DEVELOPMENT LOOP

When AI is asked to implement a feature:

```text
REQUEST
    ↓
CHECK RULES.md
    ↓
CHECK DESIGN DOCUMENTS
    ↓
CHECK EXISTING CODE
    ↓
IDENTIFY AFFECTED FILES
    ↓
EXPLAIN IMPLEMENTATION
    ↓
IMPLEMENT
    ↓
TEST
    ↓
REPORT CHANGES
```

---

# DEFINITION OF DONE

A feature is complete only when:

- Design is approved.
- Implementation is complete.
- Tests pass.
- Existing systems still work.
- Documentation is updated.
- No unrelated gameplay decisions were introduced.
- The developer understands what changed.

---

# FINAL PROJECT PRINCIPLE

The project should never become:

```text
AI generates game
   ↓
Human accepts result
```

The intended workflow is:

```text
Human defines vision
        ↓
Human defines design
        ↓
AI helps structure
        ↓
Human approves
        ↓
AI implements
        ↓
Human plays
        ↓
Human gives feedback
        ↓
AI improves implementation
```

The game remains controlled by the human developer from concept to release.

---

## Önerdiğim nihai çalışma modeli

Bu üç dosyayı oluşturduktan sonra **hemen kod yazmaya başlamamak** daha doğru olur.

Sıralama:

```text
RULES.md
   │
   ▼
PROJECT_STRUCTURE.md
   │
   ▼
IMPLEMENTATION_PLAN.md
   │
   ▼
GAME_DESIGN.md
   │
   ├── CORE_LOOP.md
   ├── PLAYER_DESIGN.md
   ├── COMBAT_DESIGN.md
   ├── ENEMY_DESIGN.md
   ├── WORLD_DESIGN.md
   └── PROGRESSION_DESIGN.md
   │
   ▼
VERTICAL SLICE
   │
   ▼
PLAYTEST
   │
   ▼
DESIGN REVISION
   │
   ▼
CONTENT EXPANSION
   │
   ▼
POLISH
   │
   ▼
RELEASE
```




