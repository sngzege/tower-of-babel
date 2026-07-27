# FRAMEWORK EVALUATION

> **Status:** TECHNICAL RECOMMENDATION for the human developer (2026-07-27).
> This document does **not** select a framework. **FRAMEWORK DECISION REQUIRED** — see §9.
> Context: docs/architecture/ARCHITECTURE.md §8 · IMPLEMENTATION_PLAN.md Phase 2.
> Verified facts below come from the official documentation of each candidate (July 2026).

## 1. Project Requirements Profile

What THIS game actually needs (from the design drafts and architecture):

- Python-first, data-driven (YAML content), long-term **AI-assisted** development with human review.
- Top-down pixel-art, real-time class-based combat (movement, dodge i-frames, abilities, telegraphs).
- Procedural dungeon floors from handcrafted room templates (our own generator — not editor-driven maps).
- Tilemap rendering per room, camera follow, particles/VFX within a readability budget.
- Village hub with diegetic interaction; pixel-styled custom UI (EXPERIENCE_DESIGN.md §12).
- Controller + keyboard/mouse, Windows + Linux, versioned saves, packaging at release.
- Architecture already built around **owning the game loop** (engine/game_loop, scene manager, deferred event pump) and framework-free infrastructure (registry, save, config, events, DI).

## 2. Candidates (verified versions, July 2026)

| | pygame-ce | Arcade | pyglet |
|---|---|---|---|
| Verified version | 2.5.8 | 4.0.0.dev5 (3.x stable line) | 2.1.15 |
| License | LGPL (SDL2) | MIT | BSD |
| Model | explicit, you own the loop | opinionated Window/View/Section | unopinionated toolkit |
| Rendering | SDL2 surfaces (software-first) | OpenGL batched | OpenGL batched |
| Notes | huge ecosystem | built on pyglet | Arcade's foundation |

## 3. Scoring (1-10 per criterion, honest per-criterion basis)

### Core fit

| Criterion | pygame-ce | Arcade | pyglet |
|---|---|---|---|
| 1. Python-first | 10 | 10 | 10 |
| 2. Pixel-art support | 9 — surfaces, palettes, trivial nearest-neighbor integer scaling | 8 — atlas + pixel sampling | 8 — batches + sampling |
| 3. Top-down RPG suitability | 8 | 9 | 7 |
| 4. Real-time combat | 8 — explicit loop, exact frame control | 8 | 8 |
| 13. Procedural dungeon integration | 9 — zero workflow constraints | 8 — Tiled workflow is editor-centric, ours is generator-centric | 9 |
| 24. Fit with current architecture | 9 — we keep our loop/scenes/events | 7 — its View/Section model wants to own the loop we already built | 8 — unopinionated |
| 25. Fit with data-driven dev | 9 | 8 | 9 |
| 26. Vertical-slice ease | 9 — smallest conceptual gap from infra to playable | 8 | 6 — most systems to build first |

### Rendering, world, combat

| Criterion | pygame-ce | Arcade | pyglet |
|---|---|---|---|
| 5. Collision | 7 — Rect/mask pixel-perfect, no spatial hashing | 8 — hitboxes + spatial hashing + optional PyMunk | 4 — build all |
| 6. Sprite handling | 9 — Sprite/Group/LayeredDirty | 9 — SpriteList GPU batching | 8 — Sprite/Batch |
| 7. Animation | 6 — manual frame cycling | 8 — texture lists/helpers | 7 — image sequences |
| 8. Tilemap | 3 — third-party pytmx/Tiled | 9 — built-in Tiled loader | 2 — build own |
| 9. Camera | 2 — build own (its "camera" module is webcam capture) | 9 — Camera2D built-in | 4 — build own |
| 10. Particles/VFX | 3 — build own | 8 — emitter system | 3 — build own/shaders |
| 15. Performance | 7 — software rendering; sufficient for pixel-art + dirty-rect discipline (RULES §15: profile first) | 8 — GL batch | 9 — thin GL |

### Input, audio, UI

| Criterion | pygame-ce | Arcade | pyglet |
|---|---|---|---|
| 11. Audio | 7 — mixer + music | 7 — sound/music | 8 — media + optional ffmpeg |
| 12. Controller support | 7 — joystick API; _sdl2.controller (marked experimental) | 7 — via pyglet input | 8 — ControllerManager, rumble |
| 14. UI development | 3 — build own or third-party pygame_gui | 8 — arcade.gui widget set | 4 — pyglet.gui simple widgets |

### Platforms, ecosystem, workflow

| Criterion | pygame-ce | Arcade | pyglet |
|---|---|---|---|
| 16. Windows | 10 | 9 | 9 |
| 17. Linux | 10 | 9 | 9 |
| 18. Packaging | 8 — mature PyInstaller/cx_Freeze path | 8 — documented PyInstaller/Nuitka guides | 7 |
| 19. Documentation | 9 | 9 | 7 |
| 20. Community/ecosystem | 9 | 7 | 6 |
| 21. Long-term maintainability | 9 — two decades, stable API, active | 7 — real API churn history (2.6→3.x→4.0 dev) | 8 |
| 22. AI-agent maintainability | 9 — largest code corpus, most explicit API | 7 — smaller corpus, version differences | 6 — GL-level concepts, least corpus |
| 23. Ease of debugging | 9 | 7 | 7 |

### Totals

| | pygame-ce | Arcade | pyglet |
|---|---|---|---|
| Raw sum (26 criteria) | 198 | **211** | 181 |
| Project-weighted* | **+13 net advantage** | baseline | −25 |

\* **Project-weighted view (transparent methodology):** the criteria this project is *unusually* sensitive to — AI-agent maintainability (22), architecture fit (24), data-driven fit (25), slice ease (26), maintainability (21), debugging (23), pixel-art control (2), procgen integration (13) — are where pygame-ce leads. Arcade wins the raw sum on built-ins (tilemap/camera/particles/GUI), but those built-ins are either systems our architecture already plans to own or systems we can source from small optional third-party libraries. The weighting rationale is stated openly so the developer can re-weight.

## 4. What We Must Build Ourselves

Legend: **F** = framework-provided · **T** = established third-party library · **O** = our own implementation (already planned in PROJECT_STRUCTURE.md).

| System | pygame-ce | Arcade | pyglet |
|---|---|---|---|
| Entity management | O (engine/entity.py, lightweight) | O | O |
| Collision system | F (Rect/mask) + O (hitbox/hurtbox layers) | F (hitboxes, spatial hash) | O (all) |
| Physics (movement) | O | F simple / T PyMunk | O |
| Camera | O (~small, well-understood) | **F (Camera2D)** | O |
| Animation | O (frame data-driven) | F helpers + O state machines | F sequences + O |
| Tilemap integration | T (pytmx) or O (our rooms are template-driven, so a lean O loader is realistic) | **F (Tiled loader)** | O |
| Pathfinding | O/T (grid A* is small) | O/T | O/T |
| UI | T (pygame_gui) or O (custom pixel UI is a design goal anyway) | **F (arcade.gui)** | O (mostly) |
| Particles | O (budget-limited system, EXPERIENCE §7) | **F (emitters)** | O |
| Audio management | F (mixer) + O (manager facade) | F + O | F (media) + O |
| Scene management | O (engine/scene*, state machine — exists) | F (Views) but **conflicts with our model** | O |
| Input abstraction | O (thin wrapper over event/keyboard/joystick — planned) | O over its events | O over pyglet.input |
| Controller support | F (joystick; _sdl2.controller experimental) | F (pyglet input) | **F (ControllerManager, rumble)** |
| Resource/asset management | O (asset catalog exists) | F caches + O | O |
| Debug tooling | O (debug overlay planned) | O | O |
| Game loop ownership | **O by design — matches our architecture** | F wants it | O possible |

Net self-build load: **pyglet ≫ pygame-ce > Arcade**. The systems pygame-ce lacks (camera, particles, UI, tilemap glue) are small, well-understood, and already allocated in our structure (`rendering/camera.py`, `rendering/particles.py`, `ui/*`, `world/*`).

## 5. Architecture Review (current abstractions)

| Abstraction | Verdict | Reasoning |
|---|---|---|
| Dependency container | **A — keep** | Composition-root pattern; tiny; used by bootstrap; prevents globals (RULES §12). No framework coupling. |
| Event bus | **A — keep** | Becomes valuable with audio/UI/debug phases (publish game events without imports). Deferred `pump()` fits any loop, including pygame's. Zero cost today. |
| State machine | **A — keep** | Will serve scenes, player states, enemy AI, boss phases. Generic, tested. |
| Content registry + data loader | **A — keep** | The data-driven pillar itself. Freeze-before-run and validator hooks align with all three frameworks. |
| Save manager | **A — keep** | Framework-agnostic by design. |
| `core/signals.py` (empty) | **A — keep empty** | YAGNI documented: remove only if still unused at Phase 6 review. |

Simplifications needed: **none** — all parts are small and exercised by tests.

Gaps identified (not blockers, scheduled): ① cross-file reference-integrity validation (ids → ids) — next tooling step after Phase 2; ② a clock/dt provider abstraction — arrives with the engine loop in Phase 2; ③ settings facade over ConfigLoader — later phase.

## 6. Architecture Style: OOP vs EC vs ECS vs Hybrid

| Option | Fit for this project |
|---|---|
| A. Traditional OOP (inheritance trees) | Poor: enemy/boss variety + shared behaviors invite deep hierarchies; RULES §12 warns about god classes. |
| B. Entity-Component (composition over inheritance) | Good: entities compose Hitbox/Hurtbox/Stats/AI/Loadout; readable, testable, debuggable. |
| C. Full ECS (systems over packed data) | Poor fit: entity counts are modest (dozens, not thousands); Python gets little of ECS's cache benefits; high conceptual + debugging cost; worst AI-agent maintainability; violates "simplest sufficient" (RULES §22). |
| **D. Hybrid (recommended)** | **B for game entities + plain OOP services for everything else (scenes, managers, village, save).** Data-driven factories build entities from registry documents (composition configured by YAML). engine/entity.py, component.py, system.py implement *lightweight composition helpers* — explicitly **not** a full ECS framework. |

Recommendation: **D (hybrid component-based OOP)** — sufficient for real-time combat + AI + procgen at this scale, best debugging and AI-agent story, lowest complexity.

## 7. Final Recommendation

1. **Recommended: pygame-ce** — best *project-weighted* fit: we keep full ownership of the loop our architecture is built around; the largest AI-agent corpus and most explicit API (this project's development model is AI-assisted); stable two-decade API; pixel-perfect surface control matching the 480×270 + integer-scaling direction; its missing pieces are small, planned, self-owned systems.
2. **Second-best: Arcade** — best built-ins (Camera2D, Tiled loader, particles, arcade.gui) and wins the raw score sum. Recommended if the developer prefers fewer self-built systems and accepts: adapting/hiding its View model inside our scene abstraction, API churn history (2.6→3.x→4.0 dev), and a smaller AI-agent corpus.
3. **Rejected for this project: pyglet** — excellent foundation (it powers Arcade), but for us it means the most self-build work, GL-level complexity without slice benefit (RULES §15), and the weakest AI-agent corpus.

### Major disadvantages of the recommendation (honesty required)

- Camera, tilemap glue, particles, and in-game UI must be built (or sourced: pytmx, pygame_gui). Estimated slice cost: a few small modules — allocated in PROJECT_STRUCTURE.md already.
- Software rendering has a ceiling. Mitigations: pixel-art scale + dirty-rect discipline; `_sdl2` GPU path exists as an escape hatch; RULES §15 says profile before optimizing — do not pre-optimize.
- Controller support via `_sdl2.controller` is still flagged experimental in docs (joystick API is stable and usable).
- LGPL (SDL2): standard dynamic-link usage is fine for a game; confirm distribution details at packaging (Phase 20).

### Migration risk (if the choice is revisited later)

**Low** — ARCHITECTURE.md confines framework imports to `src/rendering/`, `src/audio/`, `src/input/` (adapter packages). A framework swap rewrites those three packages; gameplay/world/core/save/data are untouched. Enforce rule: *no `import pygame` outside adapter packages* (add to lint checks in Phase 2).

## 8. Answers to the Standing Questions

- **DI container stays?** Yes. **Event bus stays?** Yes. **State machine stays?** Yes. **Registry stays?** Yes.
- **Any simplifications?** None now; re-review at Phase 6.
- **Architecture style?** Hybrid component-based OOP (§6).

## 9. FRAMEWORK DECISION REQUIRED

The human developer must choose before Phase 2 starts:

- **Option 1 (recommended): pygame-ce** — own the loop; build small adapters; maximum AI-assisted velocity.
- **Option 2: Arcade** — more built-ins; adapt our engine facade to its View model.
- **Option 3: pyglet** — not recommended (see §7.3).
- **Option 4: other** — propose an alternative for evaluation.

## 10. What Happens Immediately After the Decision

Phase 2 kickoff (IMPLEMENTATION_PLAN.md), in order:

1. Add the framework to `pyproject.toml` with a RULES.md §14 justification comment; `uv sync`.
2. Write the adapter interfaces (`rendering`, `audio`, `input`) so no other package imports the framework.
3. Engine bootstrap: `engine/game.py`, `engine/game_loop.py`, window per `config/display.yaml`.
4. Scene system on the existing state machine: boot → main menu → placeholder scene.
5. Input manager: abstract actions (Move/Attack/Dodge/Skill/Interact/Pause) from keyboard + gamepad.
6. Phase 2 acceptance: a placeholder square moves in a test scene at a stable frame rate (per plan exit criteria).


