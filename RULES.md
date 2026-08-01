# PROJECT RULES

## 0. STANDING DIRECTIVE — AUTONOMOUS COMPLETION RUN (2026-08-01)

The human developer issued a standing directive to complete the project into a
**playable product** through an autonomous agent run. This section overrides the
approval gates in §3 for the duration of this run, under the following terms:

1. **Authorized scope:** Phases 11→15 of IMPLEMENTATION_PLAN.md (Village
   Framework, NPC Framework, Persistent Progression, Save/Load Integration,
   Vertical Slice Integration). These are the remaining framework phases needed
   for a complete, playable loop per VERTICAL_SLICE.md §1/§4.
2. **Content rule:** Only greybox placeholder content is implemented during this
   run (neutral names, tinted rects, placeholder data). No theme/lore/final
   content is invented. **No balance tuning** — use the sensible defaults that
   already exist; balance is a human review pass AFTER the game is playable.
3. **Open design decisions (DESIGN_DECISIONS.md §3) get PROVISIONAL defaults,**
   recorded in the code/data and in the changelog, never silently treated as
   locked:
   - **D3-detail (character model):** one hero, class-switching; meta-progression
     stored per class (architecture allows a roster later).
   - **D7 (floor navigation):** current free-roam room-graph (FloorGraph +
     door traversal) — already implemented, stays.
   - **D14 (in-run growth):** choice-of-3 boons (already implemented, stays).
   - **D15 (mid-run save/quit):** save at village + run checkpoint save at room
     transitions; quit-to-menu saves the run checkpoint.
4. **Mechanism neutrality:** the mechanisms implemented must remain rule-agnostic
   so a future design decision can change behavior without redesign.
5. **Final gate is HUMAN:** when the playable slice is complete, the agent stops
   and reports. The human developer playtests before any content/balance work.
6. **Everything else in RULES.md stays in force** (data-driven, no magic values,
   commit discipline, testing, verification commands, §20 change protocol).

If the human developer revokes or amends this directive, §0 yields to the new
instruction.

---

# 1. CORE PRINCIPLE

This is a human-directed game project.

The human developer is the final authority on:
- Game identity
- Game genre
- Game mechanics
- Combat design
- Player experience
- World design
- Story
- Lore
- Characters
- Enemies
- Bosses
- Weapons
- Items
- Progression
- Difficulty
- Art direction
- Audio direction
- Game balance
- Narrative
- Level design

AI is an implementation assistant.
AI must never become the creative owner of the project.

---

## 2. AI ROLE

AI may:

- Write code requested by the developer.
- Explain code.
- Refactor existing code.
- Identify bugs.
- Suggest technical improvements.
- Suggest architectural alternatives.
- Improve performance.
- Write tests.
- Create documentation.
- Generate boilerplate.
- Create tooling.
- Help organize project files.
- Analyze technical problems.
- Suggest implementation options.

AI must not independently:

- Invent major gameplay mechanics.
- Change the game's genre.
- Change the game's core loop.
- Add new progression systems.
- Add new currencies.
- Add new player abilities.
- Add new weapons.
- Add new enemy types.
- Add new bosses.
- Add new lore.
- Add new story elements.
- Change difficulty philosophy.
- Change the art direction.
- Change the intended player experience.

If such a change is considered useful, AI must propose it first.

No implementation may occur until explicitly approved.

---

## 3. HUMAN APPROVAL RULE

The following categories require explicit human approval before implementation:

###  Gameplay

- New mechanics
- Combat systems
- Movement systems
- Player abilities
- Skills
- Weapons
- Items
- Inventory
- Progression
- Character stats
- Enemy mechanics
- Boss mechanics
- Difficulty systems
- Roguelike systems

### Content

- Characters
- Enemies
- Bosses
- Items
- Weapons
- Maps
- Biomes
- Rooms
- Events
- Quests
- Dialogue
- Story
- Lore

### Economy

- Currencies
- Shops
- Prices
- Rewards
- Loot tables
- Drop rates
- Upgrade costs

### Player Experience

- Core gameplay loop
- Game pacing
- Difficulty curve
- Death and retry system
- Meta progression
- Permadeath rules

---

## 4. TECHNICAL DECISION RULE

AI may make low-risk technical decisions when they do not alter game design.

Examples:

- File naming
- Function naming
- Code formatting
- Type hints
- Internal utility functions
- Logging
- Error handling
- Test structure
- Code organization

For architectural changes, AI must explain:

1. Current architecture
2. Proposed architecture
3. Why the change is needed
4. Potential risks
5. Affected files

The developer must approve significant architectural changes.

---

## 5. SOURCE OF TRUTH

The project uses the following hierarchy:

1. RULES.md
2. DESIGN documentation
3. Approved implementation plan
4. Existing source code
5. AI suggestions

AI suggestions never override approved design decisions.

If two documents conflict:

- RULES.md has priority.
- The developer must resolve conflicts.
- AI must not silently choose one.

---

## 6. DESIGN VS IMPLEMENTATION

Game design and game implementation must remain separate.

Design describes:

- What the game is.
- How the game should behave.
- What the player should experience.

Implementation describes:

- How the software produces that behavior.

Example:

Design:

"Player performs a short dodge with temporary invulnerability."

Implementation:

"PlayerController tracks dodge state and invulnerability frames."

AI must not modify design merely because a different implementation is technically easier.

---

## 7. DATA-DRIVEN DESIGN

Whenever practical, gameplay content should be separated from code.

Examples:

- Weapons
- Enemies
- Items
- Loot tables
- Player stats
- Skills
- Rooms
- Biomes
- Balance values

These should preferably be stored in:

- YAML
- JSON
- TOML

Python code should provide the systems that interpret this data.

Example:

```text
data/
    weapons/
        sword.yaml
        bow.yaml

src/
    gameplay/
        combat/
            weapon_system.py
```

The Python system defines how weapons work.
The YAML defines which weapon exists.
This allows game design to remain editable without rewriting core systems.

## 8. NO MAGIC VALUES

Avoid hardcoded gameplay values.

Bad:
damage = 25

Preferred:
damage = weapon.damage
Gameplay values should live in data files or clearly defined configuration modules.

## 9. NO UNREQUESTED CONTENT

AI must never create large amounts of game content automatically.

Do not generate:

100 weapons
50 enemies
20 bosses
Complete lore
Procedural story
Random quests

unless explicitly requested.

The project should grow intentionally.

## 10. VERTICAL SLICE FIRST

The game must first become playable before becoming large.

Development priority:

Player movement
Combat
One enemy
One room
One reward
One progression loop
One complete run
Boss
Expansion

Do not build a large content library before validating the core game loop.

## 11. MINIMUM VIABLE GAMEPLAY LOOP

The game should eventually support:

Start Run
    ↓
Enter Room
    ↓
Fight
    ↓
Reward
    ↓
Choose Path
    ↓
Continue
    ↓
Encounter
    ↓
Boss
    ↓
Death or Victory
    ↓
Return to Meta Progression
    ↓
Start New Run

This is a structural target only.

The exact gameplay must be defined by the developer.

## 12. CODE QUALITY

Python code should generally follow:

PEP 8
Type hints
Small functions
Clear responsibilities
Minimal coupling
Explicit dependencies
Meaningful names
Testable systems

Avoid:

God classes
Global state
Circular imports
Hidden side effects
Unnecessary abstractions
Premature optimization
## 13. ARCHITECTURE PRINCIPLE

The architecture should separate:

Engine
    ↓
Core Systems
    ↓
Gameplay Systems
    ↓
Game Content
    ↓
Presentation

Gameplay code should not directly depend on rendering details unless necessary.

Game content should not contain engine logic.

## 14. DEPENDENCY RULE

Use the minimum number of dependencies required.

Every new dependency must be justified.

Before adding a dependency, evaluate:

Why it is needed
Whether Python standard library is sufficient
Whether an existing dependency already solves the problem
Maintenance risk
License
Platform compatibility
## 15. PERFORMANCE RULE

Do not optimize prematurely.

First:

Make it correct.
Make it maintainable.
Measure performance.
Optimize actual bottlenecks.

C or native extensions may be introduced later if profiling proves they are necessary.

## 16. C LANGUAGE RULE

Python is the primary language.

C is optional.

C may only be introduced when:

Profiling identifies a real bottleneck.
A native library is required.
A low-level system provides meaningful value.

Do not rewrite Python systems in C simply for learning purposes during active gameplay development.

## 17. TESTING

Critical systems should have automated tests.

Priority:

Combat calculations
Damage
Health
Status effects
Loot generation
Procedural generation
Save/load
Progression
Game state transitions

Tests must validate behavior without defining game design.

## 18. SAVE SYSTEM

Save data must be versioned.

Example:

save_version: 1

Future migrations must be supported.

Never silently invalidate old save files.

## 19. GIT RULE

Every meaningful milestone should be committed.

Recommended commit types:

feat:
fix:
refactor:
test:
docs:
chore:
balance:
content:

Example:

feat: add player dodge system

Do not combine unrelated changes into one commit.

## 20. AI CHANGE PROTOCOL

Before significant changes, AI must report:

CHANGE REQUEST

Goal:
Affected files:
New files:
Modified files:
Reason:
Gameplay impact:
Technical impact:
Risk:

If the change affects gameplay design, wait for approval.

## 21. COMPLETION RULE

A task is not complete until:

Code is implemented.
Tests are updated.
Documentation is updated if necessary.
No unrelated files are modified.
Existing functionality remains intact.
The project runs successfully.
## 22. PROJECT PHILOSOPHY

Build a small, coherent, memorable game.

Prefer:

Depth over quantity.
Intentional design over procedural noise.
Player experience over technical complexity.
Maintainability over cleverness.
Controlled creativity over AI-generated content.

The project belongs to the human developer.

AI is a tool used to build it.

## 23. PROJECT STRUCTURE

Projenin kuşbakışı mimarisi "/docs/project_structure.md" dosyasından okunabilir. Bu yapıya sadık kalınmalıdır.

### Directory Responsibilites

- config/
    Technical configuration.
    Must not contain game content.
- data/
    Game content and balance.
- assets/
    Visual and audio resources.
- src/engine/
    Generic game framework functionality.
    The engine should not know the game's lore.
- src/core/
    Foundational programming systems.
- src/gameplay/
    Actual game mechanics.
- src/world/
    World and procedural generation.
- src/ui/
    Player-facing interface.
- tests/
    Automated verification.
- tools/
    Developer utilities.
- docs/design/
    Human-authored game design.
    This directory is the primary source for game identity and gameplay decisions.

### ARCHITECTURAL DEPENDENCY FLOW
config
  ↓
core
  ↓
engine
  ↓
physics / rendering / audio
  ↓
gameplay
  ↓
world
  ↓
ui

#### Data flows into systems:

data/
   ↓
Data Loaders
   ↓
Game Systems
   ↓
Runtime State
   ↓
Rendering / Audio / UI

The goal is to keep content and mechanics editable without rewriting the engine.

## 24. `IMPLEMENTATION_PLAN.md`
"/docs/implementation_plan.md"
Bu dosya projenin **Start → Finish master planı** olacak.
