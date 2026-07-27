# CONTINUATION PROMPT — Phase 4: Combat Foundation

> **When to use:** the next agent picks up from this exact state. Copy-paste
> this prompt at the start of the session so the agent knows exactly where we
> are, what is already implemented, and what the next deliverables are.

---

## Context

- Project: Tower of Babel (Action RPG + Roguelite)
- Repo: https://github.com/sngzege/tower-of-babel
- Branch: `main`
- Latest commit: `f9441c5` (Phase 0-3 baseline)
- Living status file: `docs/development/STATUS.md`
- Last agent is stopped at: Phase 3.5 amendments are complete, Phase 3.5
  changes have been verified and committed (tests, ruff, mypy, data,
  headless run all green). Phase 4 not started yet.

## What is already implemented (Phase 3.5)

- Player controller composition root with isolated components:
  - `PlayerController` (ActionFrame -> PlayerIntent)
  - `DodgeCharges` (reusable charge-based cooldown service, data-driven
    `dodge_max_charges` + `dodge_cooldown`)
  - `AimController` (mouse-vs-keyboard aim priority policy, documented,
    swappable without touching Player/Combat)
  - `Player` with separate `aim_vector`, `aim_direction`, `facing` (from
    aim), `movement_direction` (from WASD), and `dodge_charges`
- Input system extended with independent aim/movement channels:
  - WASD = movement
  - Arrow keys / gamepad right stick = directional aim
  - Mouse = positional aim with `pointer_moved` flag
- Camera has `screen_to_world` (inverse of `world_to_screen`, shake-aware).
- Data-driven config in `data/player/stats.yaml` (including
  `dodge_max_charges: 2`, `dodge_cooldown: 1.5`).
- Schema updated (`data/schemas/player.schema.yaml`).
- 163 tests + 1 skip (all green), ruff clean, mypy clean, validate_data OK,
  headless 300-frame run exit 0.

## What the next agent must do now

Continue with Phase 4 — Combat Foundation (`docs/development/STATUS.md` and
`IMPLEMENTATION_PLAN.md`).

### Immediate next steps

1. Read these files at session start:
   - `RULES.md`
   - `IMPLEMENTATION_PLAN.md`
   - `docs/development/STATUS.md`
   - `ARCHITECTURE.md` (sections 4 and 5)
   - `DESIGN_DECISIONS.md` (locked decisions L1-L16)
2. Implement Phase 4 combat foundation:
   - damage pipeline (hitbox/hurtbox hit resolution on top of static world)
   - attack executor (consume primary_attack intent from ActionFrame)
   - invulnerability service (general, not just dodge i-frames)
   - status effect hooks
3. Continue to use the reusable components created in Phase 3.5:
   - `DodgeCharges`
   - `AimController`
   - `screen_to_world`
   - independent move/aim channels from `ActionFrame`
4. Do NOT implement full combat content or enemies yet. Combat is framework
   only (damage pipeline, attack executor, invulnerability, status effects).
5. Add tests only for meaningful behavior (no artificial coverage).
6. Run the five verification commands before finishing:
   - `uv run pytest -q`
   - `uv run ruff check src tests tools scripts`
   - `uv run mypy src`
   - `uv run python tools/data_validation/validate_data.py`
   - `uv run python scripts/run.py --headless --frames 300 --log-level WARNING`
7. Update these files in the same commit:
   - `docs/development/STATUS.md`
   - `IMPLEMENTATION_PLAN.md`
   - `CHANGELOG.md`
8. Commit with a clear message and push to `main`.

## Important constraints

- Do NOT change gameplay decisions already locked in DESIGN_DECISIONS.md.
- Maintain adapter isolation (`pygame` only in approved adapters).
- Player must stay as composition root; no monolithic additions.
- Aim/movement must remain independent.
- All numbers stay in data files.
- If a change is not part of Phase 4 scope, document it as a proposal only.

## Deliverable at end of Phase 4

- Combat framework (damage, attack, invulnerability, status effects).
- Tests pass + lint/type/data clean.
- Manual playtest shows nothing broken from Phase 3.5.
- Final report (files created/modified, architecture changes, tests,
  playable features, manual instructions, technical debt, readiness for
  Phase 5).
- Documentation updated.
