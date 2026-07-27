# VERTICAL SLICE SPECIFICATION

> **Status:** SPECIFICATION DRAFT (autonomous pre-production). Scope definition only — content placeholders are neutral and temporary (task policy): **First Class**, **NPC A/B/C**, **First Stage**, **First Boss**. No theme, lore, or final content is invented here (D2/D12 stay open).
> Purpose per RULES.md §10: prove the core loop is fun **before** content volume.

## 1. What the Slice Must Demonstrate

```text
Village → Preparation → Dungeon Entry → Combat → Exploration → Build Choices
→ Stage Progression → Boss → Run End → Return → Village Upgrade
→ Character Progression → New Run
```

One complete, closed loop. If any arrow is missing, the slice is not done.

## 2. Slice Scope

| Element | Scope | Notes |
|---------|-------|-------|
| Playable class | **1** — the **Warrior** (L3) | signature attack + dodge + Q/E/R/T ability layout (L5); weapon-category behavior (L6); greybox visuals acceptable |
| Village | **1** compact hub | walkable, not a menu; 3 building plots with 2 visual tiers each |
| NPCs | **3** ("NPC A/B/C") | one service each (loadout / run prep / upgrades); 1 progression track each (service tier) |
| Dungeon stage | **1** ("First Stage") | **5 floors per L7**: floors 1-4 generated (combat/elite/event/shop/rest/caravan room kinds), floor 5 boss arena |
| Procgen | **1** layer | seeded floor graphs + room-template assembly |
| Boss | **1** ("First Boss") | 2-3 phases; gates stage completion; drops trophy |
| Run | **1** full run | death (L8) + post-boss Return-to-Town (L7) both functional; caravan banking (L10) demonstrated |
| Persistence | **1** loop | trophy unlocks village tier + ability options; save/load works |
| Build system | **1** basic form | class core + choice-of-3 boons + 2-3 passives; tag synergy demo (one tag) |

## 3. Explicitly Out of Scope for the Slice

Theme/world art, final class identity, specializations, gear (D6), multiple stages, meta currencies beyond one material, dialogue content, audio identity, difficulty tiers (D10), multiplayer (D11), minimap, achievements.

## 4. Acceptance Criteria

1. Player can start in the village, prepare, and enter the dungeon.
2. Floors are different per seed; boss is always reachable (generator tests back this).
3. Combat: attack/dodge/abilities work; enemies damage the player; player can die.
4. At least one meaningful build choice happens per run (choice-of-3 boon).
5. The boss gates progress; beating it grants a trophy.
6. Returning applies results: a village building visibly upgrades; an NPC service tier increases.
7. A new run starts with new options available; save/load survives an app restart.
8. All of it runs from `scripts/run.py`; all tests pass; `validate_data.py` passes.

## 5. Blocking Decisions (human) — RESOLVED 2026-07-27

- ~~D12~~ → **Warrior** is the slice class (L3). ~~D4/D5~~ → return-after-boss only (L7); temporary progress lost + 20/80 caravan rule (L8/L10). ~~Framework~~ → **pygame-ce**.
- Slice content rules now follow DESIGN_DECISIONS.md (L1-L16). Remaining open items that touch the slice: D3-detail (character model), D7 (floor navigation), D14 (in-run growth), D15 (mid-run save) — mechanisms stay rule-agnostic until these land.

## 6. Integration Order (per IMPLEMENTATION_PLAN.md)

Phases 2-16 build the systems; Phase 17 assembles this slice. Definition of done: this document's §4 plus the global DEFINITION OF DONE in IMPLEMENTATION_PLAN.md.
