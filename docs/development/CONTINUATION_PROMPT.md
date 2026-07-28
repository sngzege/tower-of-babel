# CONTINUATION PROMPT — Phase 8 Complete: Vertical Slice

> **When to use:** the next agent picks up from this exact state. Copy-paste
> this prompt at the start of the session so the agent knows exactly where we
> are, what is already implemented, and what the next deliverables are.

---

## Context

- Project: Tower of Babel (Action RPG + Roguelite)
- Repo: https://github.com/sngzege/tower-of-babel
- Branch: `main`
- Latest commit: (Phase 8 vertical slice complete)
- Living status file: `docs/development/STATUS.md`
- Last agent completed: Phase 8 — Vertical Slice.

## What is already implemented

### Playable at the end of Phase 8

`uv run python scripts/run.py` launches a greybox build with full run lifecycle:

- **Player**: WASD movement, 360-degree aim (mouse or arrows), attack, dodge with charges + i-frames.
- **Combat**: attack hitbox, enemy damage, player damage, hitstun, death.
- **Procedural stage**: 3 seeded floors (start → combat rooms → exit), deterministic per seed.
- **Room encounters**: combat rooms spawn greybox dummies; clear all → 3-choice reward.
- **Reward system**: data-driven buffs (damage, HP, speed, etc.), selectable via aim direction.
- **Boss**: First Boss "Warden of the First Floor" — Phase 1 (slow sweep), Phase 2 (fast sweep + AoE shockwave), phase transition at 50% HP.
- **Boss arena**: single-room boss floor after normal floors; exit blocked while boss alive.
- **Run outcomes**: victory (→ green overlay → restart) or death (→ red overlay → restart).
- **All tuning in data files** (YAML: enemies, rooms, stage config, attacks, rewards).

### Full verification

```text
pytest: 285 passed + 1 skip
ruff: clean
mypy: clean (122 files)
data validation: OK
headless 300-frame run: exit 0
```

## What the next agent should do

The next phase is **Build System**:

1. Read RULES.md, STATUS.md, IMPLEMENTATION_PLAN.md, ARCHITECTURE.md.
2. The Build System phase adds:
   - In-run build choices (boon/ability selection during traversal)
   - Passive/ability data architecture
   - Integration with the existing reward system (reward → persistent build)
   - Tools/weapons pipeline if applicable
3. Follow the AI DEVELOPMENT LOOP (end of IMPLEMENTATION_PLAN.md).
4. Run the five verification commands before finishing.
5. Update STATUS.md, IMPLEMENTATION_PLAN.md, CHANGELOG.md.
6. Commit and push.

## Key architecture constraints

- Python + pygame-ce remain the framework.
- Hybrid component-based architecture stays.
- Data-driven YAML architecture stays.
- 360-degree free aim remains.
- Dodge charges + i-frames remain.
- Warrior is the first class (Ranger/Mage are future).
- Framework isolation rules remain.
- Do NOT add final art, full village progression, full inventory, or lock unresolved design decisions.

## Files created/modified in Phase 8

**Created:**
- `src/gameplay/bosses/boss_ai.py` — BossAI with 2-phase combat
- `data/enemies/bosses/first_boss.yaml` — Boss config
- `data/world/rooms/greybox_boss_arena.yaml` — Boss arena room
- `data/combat/attacks/boss_primary.yaml` — Phase 1 attack
- `data/combat/attacks/boss_primary_fast.yaml` — Phase 2 primary attack
- `data/combat/attacks/boss_aoe.yaml` — AoE shockwave attack

**Modified:**
- `src/gameplay/playtest_scene.py` — Boss integration, encounter blocking, victory/death overlays
- `src/gameplay/enemies/enemy_factory.py` — build_boss() function
- `src/world/stage_generator.py` — Boss floor appending
- `src/world/floor_assembler.py` — Boss kind → boss arena template
- `tests/unit/test_stage_generation.py` — Updated for boss floor
- `tests/integration/gameplay/test_stage_traversal.py` — 3 new boss tests

## Deliverable for the next agent

- A clean, working vertical slice with boss.
- All verification green.
- Updated documentation.
- Ready for Build System phase.
