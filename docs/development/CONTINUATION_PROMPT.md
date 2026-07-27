# CONTINUATION PROMPT — Phase 5: Enemy Foundation

> **When to use:** the next agent picks up from this exact state. Copy-paste
> this prompt at the start of the session so the agent knows exactly where we
> are, what is already implemented, and what the next deliverables are.

---

## Context

- Project: Tower of Babel (Action RPG + Roguelite)
- Repo: https://github.com/sngzege/tower-of-babel
- Branch: `main`
- Latest commit: (Phase 4 baseline)
- Living status file: `docs/development/STATUS.md`
- Last agent completed: Phase 4 — Combat Foundation. Suite at 209 tests + 1 skip. All verification green (ruff, mypy, data validation, headless 300-frame run).

## What is already implemented (Phase 4)

- **DamagePipeline** (`src/gameplay/combat/damage.py`): invulnerability-aware damage application with overkill tracking, multi-hit stopping at death. Framework-free, testable in isolation.
- **AttackExecutor** (`src/gameplay/combat/attack.py`): windup → active → recovery → cooldown lifecycle. Data-driven `AttackData` (timing, damage, hitbox geometry, damage types). Connected to `PlayerIntent.primary_attack_pressed`.
- **InvulnerabilityService** (`src/gameplay/combat/invulnerability.py`): multiple concurrent invulnerability sources (dodge, hitstun, etc.) with independent timers, `has_source`/`remaining` queries, `on_state_changed` callback. Replaces raw `_iframe_remaining` on Player.
- **StatusEffectManager** (`src/gameplay/combat/status_effects.py`): tag-based effect slots with stacking (cap), duration refresh, tick intervals, modifier aggregation. No content defined (framework only — content requires human approval).
- **CombatSystem** (`src/gameplay/combat/combat_system.py`): orchestrates hit resolution — AABB overlap detection between hitboxes and vulnerable hurtboxes, publishes events (`entity_damaged`, `entity_killed`, `attack_hit`, `status_applied`, `status_expired`).
- **Player integration**: `Player` now has `invuln_service`, `status_manager`, `attack_executor`. Dodge uses the service. Attack triggers from intent. `reset()` clears all combat state.
- **PlaytestScene**: attack hitbox visualisation (orange rect) during active window. CombatSystem wired.
- **Data pipeline**: `data/schemas/attack.schema.yaml`, `data/combat/attacks/player_default.yaml` (greybox test attack). `combat` category registered in validate_data.py.
- **46 new tests** (4 modules): damage pipeline (10), invulnerability (14), attack executor (11), status effects (11).

## What the next agent must do now

Continue with Phase 5 — Enemy Foundation (`docs/development/STATUS.md` and `IMPLEMENTATION_PLAN.md`).

### Immediate next steps

1. Read these files at session start:
   - `RULES.md`
   - `IMPLEMENTATION_PLAN.md`
   - `docs/development/STATUS.md`
   - `ARCHITECTURE.md` (section 5 — Enemies & Bosses)
   - `DESIGN_DECISIONS.md` (locked decisions L1-L16)
2. Implement Phase 5 enemy foundation:
   - Enemy entity (composition root similar to Player)
   - AI framework (state machine + behavior modules)
   - Enemy factory building from registry documents
   - One greybox placeholder enemy that chases, attacks, and dies
   - Wire enemy into PlaytestScene for manual testing
3. Use the reusable combat components created in Phase 4:
   - `CombatSystem` for hit resolution
   - `DamagePipeline` for damage application
   - `InvulnerabilityService` for enemy invulnerability if needed
   - `StatusEffectManager` for enemy status effects
   - `AttackExecutor` for enemy attacks
4. Do NOT implement multiple enemy types or full stage families yet.
5. Add tests only for meaningful behavior (AI state transitions, factory builds, enemy-encounter spawn).
6. Run the five verification commands before finishing:
   - `uv run pytest -q`
   - `uv run ruff check src tests tools scripts`
   - `uv run mypy src`
   - `uv run python tools/data_validation/validate_data.py`
   - `uv run python scripts/run.py --headless --frames 300 --log-level WARNING`
7. Update these files in the same commit:
   - `docs/development/STATUS.md`
   - `IMPLEMENTATION_PLAN.md` (Phase 5 status)
   - `CHANGELOG.md`
8. Commit with a clear message and push to `main`.

## Important constraints

- Do NOT change gameplay decisions already locked in DESIGN_DECISIONS.md.
- Maintain adapter isolation (pygame only in approved adapters).
- Player must stay as composition root; no monolithic additions.
- All numbers stay in data files.
- Enemy behavior framework must scale to future families (RULES.md §22).
- Only ONE enemy type for now (greybox placeholder, approved by developer).
- If a change is not part of Phase 5 scope, document it as a proposal only.

## Deliverable at end of Phase 5

- Enemy entity with AI (chase, attack, die).
- Enemy factory that builds from data documents.
- One beatable placeholder enemy in the greybox arena.
- Tests pass + lint/type/data clean.
- Manual playtest shows the enemy chasing and taking damage.
- Final report (files created/modified, architecture changes, tests, playable features, manual instructions, technical debt, readiness for Phase 6).
- Documentation updated.
