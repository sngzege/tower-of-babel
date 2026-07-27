# ARCHITECTURE

> **Status:** FIRST ARCHITECTURE DRAFT (autonomous pre-production). Technical structure only — it locks **no** game design decisions (D1-D15 remain open, see docs/design/GAME_DESIGN.md §12).
> Companion documents: DATA_FLOW.md (content pipeline), SAVE_SYSTEM.md (persistence), ../development/VERTICAL_SLICE.md (slice scope).

## 1. Purpose and Principles

This document defines how the future implementation is organized so that:

- **RULES.md is enforced structurally:** Python-first, data-driven content, layered dependencies, loose coupling, no global state, no circular imports (§12, §13, §23).
- **Content grows without code changes:** new classes/abilities/enemies/rooms/NPCs are data files, not engine edits.
- **Unresolved design decisions stay open:** every system that depends on D1-D15 is built behind an abstraction that supports multiple valid outcomes.

Core principles (from RULES.md, restated as architecture rules):

1. Layers depend **downward only** (§4). Upward/lateral communication happens through events.
2. Dependencies are **explicit** (constructor injection via a dependency container), never globals.
3. The **engine knows no game content**; the **content knows no engine** (RULES.md §13, §23).
4. Everything gameplay-relevant is **data-defined and validated** before a run starts.

## 2. Layer Map

| Layer | Package | Status after pre-production |
|-------|---------|-----------------------------|
| Configuration | `config/` | minimal technical defaults in place (+ camera section, Phase 3) |
| Core foundations | `src/core/` | **implemented** (events, state machine, DI container, constants, enums, data loader, content registry) |
| Utilities | `src/utils/` | **implemented** (logger, config loader, asset catalog, seeded RNG, file utils) |
| Persistence | `src/save/` | **implemented** (schema, manager, migrations) |
| World / procgen | `src/world/` | prototype floor-graph generator + **Room data model (Phase 3)** |
| Engine | `src/engine/` | **implemented** (game, loop, scenes, hybrid entity/component/system, Phase 2) |
| Input | `src/input/` | **implemented** (abstract actions, keyboard + gamepad adapters, Phase 2) |
| Rendering | `src/rendering/` | **implemented** (renderer protocol + pygame adapter, Phase 2; **Camera**, Phase 3) |
| Physics | `src/physics/` | **implemented** (swept-AABB collision world, kinematic movement, hitbox/hurtbox, Phase 3) |
| Audio | `src/audio/` | empty — audio phase |
| Gameplay | `src/gameplay/` | **player controller + greybox playtest scene (Phase 3)**; combat/enemies/etc. pending |
| UI / Debug | `src/ui`, `src/debug` | empty |
| Validation tooling | `tools/data_validation/`, `scripts/` | **implemented** (schema validator CLI, run/test wrappers) |

## 3. Dependency Rules

Allowed dependency flow (mirrors RULES.md §23; arrows mean "may import"):

```text
config
  ↓
core  (events, state machine, DI, registry, data loading)
  ↓
engine  (game loop, scenes, entities)          [blocked: framework decision]
  ↓
physics / rendering / audio                    [framework adapters]
  ↓
gameplay  (player, combat, enemies, builds, village, progression)
  ↓
world  (stages, rooms, procgen, dungeon)
  ↓
ui
```

Data flows sideways into systems, never the reverse:

```text
data/  →  core.data_loader  →  core.content_registry  →  gameplay/world systems  →  runtime state
```

### Hard rules

- **No upward imports.** E.g. `core` never imports `gameplay`; `gameplay` never imports `ui`.
- **No lateral imports between siblings** (e.g. `rendering` ↔ `audio`). Communicate via events or a shared parent.
- **Gameplay never imports rendering/audio internals.** It emits events and consumes abstractions.
- **Engine never imports gameplay.** Engine provides mechanisms (loop, scenes, entities); gameplay provides policies.
- **No circular imports, ever.** A cycle means a boundary is wrong; fix the boundary, not the import.
- **No module-level mutable globals.** Shared services live in the dependency container, created at bootstrap.

## 4. Communication Patterns

- **Downward (parent → child):** direct method calls through injected dependencies.
- **Upward (child → parent) and lateral:** `core.events.EventBus` — publish/subscribe by event name; payloads are plain dicts. Deferred delivery (`publish_deferred` + `pump`) is used at frame boundaries to avoid mutation during iteration.
- **Example (planned):** combat publishes `entity_damaged`; audio and UI subscribe. Combat never imports audio or UI.
- **Event vocabulary is owned by the system that publishes it** and documented when that system is built. No gameplay events exist yet.

## 5. System Boundaries

Each system lists: **responsibility** / **may know** / **must not know**.

### Bootstrap (`src/main.py`)
- Wires logging, configuration, content registry, dependency container; starts the engine.
- May know: every top-level system (it is the composition root).
- Must not know: gameplay rules, content semantics.

### Game Loop (`src/engine/game_loop.py` — planned)
- Fixed/variable timestep, frame order: input → update → render; pumps deferred events.
- May know: engine, core.
- Must not know: any game content or scene internals.

### Scenes / Game State (`src/engine/scene*.py` — planned)
- Scene lifecycle (enter/exit/update) built on `core.state_machine`; owns one active scene.
- May know: engine, core; scene implementations by interface.
- Must not know: what scenes *do* (village/dungeon logic lives in those scenes' own layers).

### Input (`src/input/` — planned)
- Translates devices (keyboard/gamepad) into **abstract actions**; action bindings from `config/input.yaml`.
- May know: core, config.
- Must not know: who consumes actions. Gameplay must never see physical keys (IMPLEMENTATION_PLAN input phase).

### Entities (`src/engine/entity|component|system.py` — planned)
- Lightweight entity/component container for game objects (PROVISIONAL: plain composition, no heavy ECS framework).
- May know: engine, core.
- Must not know: concrete entity types (player/enemy are gameplay-layer specializations).

### Player (`src/gameplay/player/` — implemented, Phase 3)
- Composition root (no god class): PlayerController (only ActionFrame consumer), KinematicBody movement, Hitbox/Hurtbox components, state machine (IDLE/MOVE/DODGE live; HIT/DEAD placeholders), stats from data (`data/player/`, schema validated).
- May know: gameplay services, physics interface, events.
- Must not know: rendering internals, enemy content, village state (reads progression via progression system).

### Combat (`src/gameplay/combat/` — planned)
- Damage pipeline (data-driven types/tags), hit resolution via physics hitbox/hurtbox, invulnerability, status-effect framework.
- May know: physics, core, registry (reads ability/effect documents).
- Must not know: rendering, audio, UI (publishes events instead).

### Enemies & Bosses (`src/gameplay/enemies|bosses/` — planned)
- Factories build instances from registry documents; AI = state machine + behavior modules; boss phases data-driven (`data/schemas/boss.schema.yaml`).
- May know: combat, core, registry.
- Must not know: player internals (sees a combat interface), rendering.

### Abilities / Passives / Builds (`src/gameplay/` — planned; framework design in DATA_FLOW.md)
- Build = class core + ability loadout + passive picks + run boons + optional gear (D6 open).
- Synergy via shared **tags**; modifiers resolve through an ordered pipeline (stacking rules, priority).
- May know: registry, events.
- Must not know: where boons came from (run system owns that).

### Run State (`src/gameplay/roguelike/` — planned)
- One run's mutable state: seed, depth, collected boons/resources, outcome (`core.enums.RunOutcome` — supports D4 either way).
- May know: world (progression through stages), gameplay.
- Must not know: save file format (save system serializes it), village internals (results are handed over as data).

### Dungeon / Rooms / Procgen (`src/world/` — prototype exists)
- Stage = ordered floors; floor = `FloorGraph` (navigation-agnostic adjacency graph, D7 open) instantiated with room templates from data.
- May know: registry, core (Rng), gameplay interfaces.
- Must not know: concrete enemy/boss content (references by id only).

### Village (`planned` — see VERTICAL_SLICE.md)
- Village scene, plots, building tiers (functional + visual states), service access points.
- Data-driven via `data/schemas/building.schema.yaml` / `village_upgrade.schema.yaml`.
- May know: progression, registry, save (persistent state owner candidate).
- Must not know: dungeon internals (receives run results as plain data).

### NPCs (`planned`)
- Service slots + progression tracks (service tier / questline / relationship) + milestone arrival.
- Data-driven via `data/schemas/npc.schema.yaml`; dialogue as data.
- May know: village, progression, registry.
- Must not know: combat, rendering.

### Progression (`src/gameplay/progression/` — planned)
- Hero growth (D13 open: XP-levels vs unlock-only — hidden behind a progression interface), class mastery, unlock engine feeding reward pools.
- May know: registry, events, save.
- Must not know: how rewards are chosen in-run (run system), rendering.

### Save / Load (`src/save/` — implemented)
- Versioned, atomic persistence with migrations; run/persistent split (SAVE_SYSTEM.md).
- May know: core only.
- Must not know: gameplay semantics (stores plain dicts owned by other systems).

### Data Loading / Registry (`src/core/` — implemented)
- Loads YAML documents, registers by id, answers id/tag queries; optional validator hooks.
- May know: utils only.
- Must not know: every consumer (systems query it; it never calls them).

### Audio (`src/audio/` — planned)
- Music/SFX managers reacting to events and scene state.
- May know: core (events), config.
- Must not know: gameplay internals (event-driven only).

### Rendering (`src/rendering/` — planned)
- Framework adapter: sprites, camera, effects behind a renderer interface.
- May know: engine, core.
- Must not know: game rules; draws snapshots provided by gameplay/world.

### UI (`src/ui/` — planned)
- HUD/menus reading state snapshots; issues *requests* (e.g. "pause", "choose reward") to owning systems.
- May know: core, interfaces of owning systems.
- Must not know: how requests are fulfilled; never mutates game rules directly.

## 6. State Ownership

| State | Owner | Lifetime | Serialized |
|-------|-------|----------|------------|
| Frame/transient state | engine/gameplay locals | one frame or less | never |
| Run state | run system (`gameplay/roguelike`) | one run | `run_state` (nullable; D15 open) |
| Persistent state | progression + village systems | forever | `persistent` |
| Settings | config files | forever | `config/*.yaml` |

Rule: a system serializes **only what it owns**, as plain dicts. The save manager never interprets payloads (SAVE_SYSTEM.md).

## 7. Extensibility Strategy

- **New content** = new YAML file in the right category + `scripts/validate_data.py` passing. No code changes.
- **New content category** = new schema in `data/schemas/` + mapping entry in `tools/data_validation/validate_data.py` + (optionally) a new data directory.
- **New system** = new package in the right layer + registration at bootstrap. Existing systems stay untouched (open/closed).
- **Synergies** = shared tags, resolved by the modifier pipeline — new synergies emerge from data, not code.
- **Difficulty tiers** = mutator data applied at stage assembly (D10 open).
- **Reproducibility** = every random decision flows from seeded `utils.random_utils.Rng` streams forked per scope (run → floor → room).

## 8. Framework Decision (DECIDED 2026-07-27: pygame-ce)

The human developer selected **pygame-ce** — reasons: full game-loop ownership, long-term API stability, fit with this architecture, AI-assisted development velocity (docs/development/FRAMEWORK_EVALUATION.md).

- **Adapter isolation is enforced:** pygame may only be imported inside `src/rendering/`, `src/input/`, `src/audio/` — guarded by `tests/unit/test_framework_isolation.py`. Everything else is framework-independent.
- A framework swap rewrites only those three adapter packages (FRAMEWORK_EVALUATION.md §7: migration risk low).

## 9. Implemented Now vs Planned

**Implemented and unit-tested:**

- *Phase 1 (2026-07-26/27):* logging; config loading; seeded RNG; atomic file IO; event bus; state machine; dependency container; data loader; content registry; save schema/manager/migrations; floor-graph generator prototype; schema validator + CLI; dev scripts.
- *Phase 2 (2026-07-27):* engine bootstrap (game, game loop, scenes, hybrid entity/component/system); abstract input (keyboard + gamepad adapters, config-driven bindings); pygame-ce renderer adapter with enforced adapter isolation.
- *Phase 3 (2026-07-27):* player controller (8-direction movement, dodge with i-frames, player state machine, composition-root Player); physics (swept-AABB collision world, kinematic body, hitbox/hurtbox with layers/masks); follow camera (pixel-perfect, zoom, bounds, shake hook); Room data model; greybox playtest scene — the first playable slice.

**Planned (blocked):** audio; combat (Phase 4); enemies/bosses; items/loot; progression; roguelike run system; village; UI; procedural stage assembly (Phases 6-7); content beyond approved greybox placeholders.


