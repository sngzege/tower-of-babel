# GAMEPLAY DESIGN

> **Status:** DRAFT v2 — reviewed by the human developer. Core direction is now **LOCKED** in DESIGN_DECISIONS.md (2026-07-27); remaining [PROPOSAL] items still need approval.
> **Legend:** **[FOUNDATION]** = developer-given direction · **[REFERENCE]** = observed in Heroes of Hammerwatch II (inspiration only) · **[PROPOSAL]** = AI recommendation, needs approval · **[DECISION D#]** = open question (master list: GAME_DESIGN.md §12).
> Sections 18-19 extend the original template to cover the village system and build philosophy required by the vision.

## 1. Core Gameplay Loop

[FOUNDATION] — developer's progression model:

```text
DUNGEON RUN → PROGRESS THROUGH STAGES → FIGHT ENEMIES → MAKE BUILD DECISIONS
→ COLLECT REWARDS → REACH THE FARTHEST POSSIBLE POINT → BOSS FIGHTS
→ DEATH OR SUCCESS → RETURN TO VILLAGE → UPGRADE CHARACTER / CLASS / BUILD
→ UPGRADE VILLAGE → UPGRADE NPCs → UNLOCK NEW POSSIBILITIES → START A NEW RUN
```

[PROPOSAL] — the loop at four time scales:

- **Moment-to-moment (seconds):** move → read telegraphs → attack / dodge / ability → reposition → collect.
- **Room loop (1-3 min):** enter room → encounter → clear → reward or choice → pick next route.
- **Run loop (20-45 min):** village preparation → stage sequence → stage bosses → *Return-or-Descend* decisions (D4) → death / extraction / final victory → run resolution.
- **Meta loop (days-weeks):** spend resources → village grows visibly → NPCs progress → new build options and unlocks → new goals → next run.

[PROPOSAL] — the loop, answered as ten questions:

- **What does the player do?** Fights through procedural stages, makes build choices, defeats bosses, decides how deep to push.
- **Why enter the dungeon?** It's the only source of gold, rare materials, boss trophies, unlocks, rescueable NPCs, and depth records.
- **Decisions during a run?** Route, rewards (choice-of-3), loadout use of resources, shops/events, and the recurring *Return-or-Descend* call.
- **What ends a run?** Death, voluntary extraction (D4), or final victory (D9).
- **What is kept / lost?** DESIGN DECISION REQUIRED (D5) — options in §14. Recommendation: keep currencies and unlocks; lose run boons and consumables.
- **How does the village change?** Resources convert into building tiers, NPC progression, and new services — all visible in the world (§18).
- **How does the character change?** Hero growth (D13), class mastery, new abilities/passives entering the build space.
- **How is the next run different?** New build options, new unlocks in reward pools, new NPC services, player skill, and deeper starting confidence.
- **How is progress felt?** Depth records, visible village growth, new faces in town, bosses that used to wall you now falling.

## 2. Run Structure

**A run has five phases** (macro-structure **LOCKED → L7/L10/L15**):

1. **Preparation (town):** choose class, set ability loadout, equip permanent gear (L14), buy consumables. Every run starts with all permanent bonuses applied (L15).
2. **Enter the Tower:** stages in a fixed macro order, each procedurally assembled (floor navigation model *within* a floor: D7, open).
3. **Stage anatomy [LOCKED → L7]:** a stage = **5 floors**. Floors 1-4: normal progression (combat rooms and optional side rooms: elite / event / shop / shrine / secret / rest — and **caravan checkpoints**, L10). **Floor 5: the boss.**
4. **Return-or-Continue [LOCKED → L7]:** after the boss — **Return to Town** (no penalty, L10) or **Continue to the next Stage**. The player **cannot voluntarily leave a run before defeating a boss**; caravan checkpoints are the only mid-run way to secure currencies (L10).
5. **Resolution (town):** results screen → resources applied → village/NPC changes shown → new goals surface.

Related open question — stage shortcuts (D8): none / unlockable later-stage entry / waypoint system. Decide after the vertical slice.

## 3. Player

- **Movement:** 8-directional top-down movement; dodge/dash with invulnerability frames as the core defensive verb [PROPOSAL — consistent with the RULES.md §6 design example].
- **Health:** single health pool; in-run healing is scarce and deliberate (rest rooms, consumables, specific boons) [PROPOSAL].
- **Resources:** one class-flavored resource per class (e.g., mana / rage / focus — final set per class design, D12) [PROPOSAL].
- **Death:** ends the run immediately **[LOCKED → L8]**: all temporary progress is lost (buffs, blessings, curses, temporary build choices, run-only upgrades); unbanked currencies follow the 20/80 caravan rule (L10, §14).

## 4. Combat

**Philosophy [LOCKED → L4]:** combat starts **deliberate and readable** — positioning, blocking, dodging, and timing matter, and the player feels their class identity. Toward endgame it gradually evolves into a **faster, build-focused, almost bullet-hell** style; the transition must feel earned, not immediate.

- **Attacks:** class-defining basic attack + active abilities (cooldown- and resource-based) [PROPOSAL].
- **Dodge:** i-frames; spacing and timing matter more than mitigation stats (pillar 5) [PROPOSAL].
- **Defense:** light armor layer only; no complex resistance matrix at v1 [PROPOSAL].
- **Damage:** data-driven typed pipeline; damage types/tags live in data files (RULES.md §7) and follow the theme (D2) [PROPOSAL].
- **Hit Detection:** hitbox/hurtbox model; **every enemy attack is telegraphed** — no unavoidable damage [PROPOSAL].
- **Status Effects:** tag-based framework with effect *slots* (e.g., damage-over-time, slow, vulnerable). Specific effects require design approval (RULES.md §3) — no effect content is invented here [PROPOSAL, content TBD].

## 5. Weapons

**Philosophy [LOCKED → L6]:** every class supports **multiple weapon categories**, and the category defines the default **attack behavior** (patterns, not just damage):

- **Warrior:** sword, axe, spear, hammer
- **Ranger:** bow, crossbow, throwing weapons
- **Mage:** staff, wand, orb

Behavior examples (locked direction): spear → short piercing projectile; axe → sweeping melee arc; hammer → slower impact attack. Weapon behavior is **data-driven** whenever practical (`weapon.schema.yaml`, `weapon_factory`).

## 6. Abilities & Skills

**Control layout [LOCKED → L5]:** LMB = primary weapon attack · RMB = class skill · Q = active skill 1 · E = active skill 2 · R = ultimate · T = aura / reserved-mana skill · Space = dodge/roll. The input architecture must allow future expansion without redesign.

Framework rules (no specific abilities invented — content requires approval, RULES.md §3):

- Abilities are unlocked through class mastery and village progression (§18), upgraded in ranks, and swapped as a loadout **in the village only**.
- **Passives:** every class has passive abilities that define its identity **[LOCKED → L5]**; class passive pool + a smaller universal pool.
- **Synergy engine:** abilities, passives, boons, and gear share keyword **tags**; components that reference the same tags create emergent build synergies (§19). The tag vocabulary is defined in data.

## 7. Items & Equipment

[PROPOSAL] Item categories:

- **Consumables** (in-run): limited belt slots; bought in the village or found below.
- **Boons** (in-run): run-scoped modifiers picked as choices (§11, D14).
- **Trophies:** boss drops that gate village tiers — not equipment (§9, §18).
- **Quest/unlock items:** drive NPC arrival and content unlocks.
- **Persistent gear [LOCKED → L14]:** a **lightweight permanent equipment layer** — early game = simple items (e.g. "Iron Sword — Attack +5"); late game = advanced items, **runes, enchantments, set bonuses**. Equipment must **never** overshadow skill, build decisions, or roguelite progression.

[PROPOSAL] No inventory-management mini-game; the game is about delving, not hauling.

## 8. Enemies

[PROPOSAL] Framework only — no specific enemies invented (content belongs to the developer):

- **Role taxonomy:** swarmer / charger / ranged / caster / tank / support / trapper. Roles are design slots; each stage family fills them with themed variants.
- **Stage families:** each stage fields one enemy family plus a mechanical twist (hazard, behavior, or arena rule).
- **Elites:** base enemy + visible modifier pack (aura/tell); harder, better rewarded.
- **Encounters:** handcrafted encounter compositions pulled by procedural assembly — authored, not purely random noise (RULES.md §22: intentional design over procedural noise).

## 9. Bosses

[FOUNDATION] Bosses mark progression through stages.

[PROPOSAL] The five jobs of a boss:

1. **Gate:** one boss guards the exit of every stage; the campaign ends at a final boss (D9).
2. **Build check:** each boss tests whether the current build actually works.
3. **Story beat:** short intro; the boss embodies its stage's theme (D2).
4. **Reward spike:** trophy + rare material burst + unlock roll.
5. **Unlock vector:** first kills trigger village milestones — NPC arrivals, new plots, new options (§18).

[PROPOSAL] Structural framework: three-phase arc (learn → pressure → climax), telegraph language consistent with the stage, arena readable at a glance. Specific bosses are developer content, bound to the theme (D2).

## 10. Loot

[PROPOSAL]

- **In-run:** gold, rare materials, boon choices, consumables, event outcomes.
- **Boss:** trophy + material burst + unlock roll.
- **Meta:** unlocked content enters future reward pools (blueprint-analog) [REFERENCE-inspired: HoH II blueprint/attunement model].
- **Loot rules:** no filler drops; rarity communicates *behavior-change magnitude*, not just bigger numbers (pillar 2).

## 11. Progression

### In-Run Progression

DESIGN DECISION REQUIRED (D14): *level-ups / choice-of-3 boons / both.*

[PROPOSAL] Recommendation: experience paces **choice-of-3 boon moments** — every level forces a build decision (pillar 2) instead of auto-applying stats.

### Meta Progression

[PROPOSAL] Adopted layers, each with exactly one job:

| Layer | Name | Job |
|-------|------|-----|
| L1 | Moment-to-moment combat | Player skill — no bar, no number |
| L2 | Run progression | Run-only upgrades/boons + carried currencies; resets on run end (L8) |
| L3 | Permanent progression **[LOCKED → L11]** | Town Level · Building Levels · NPC Progression · Class Mastery · Permanent Equipment/Enchantments/Runes/Inventory |
| L4 | Class mastery **[LOCKED → L13]** | Per-class milestones: small permanent global passives (regular, e.g. every 10 levels), permanent global perk choices affecting **every** class (major, e.g. 25/50/75 — balancing TBD) |
| L5 | Town progression **[LOCKED → L12]** | Buildings unlock via Town Level; building levels unlock services; milestones unlock NPCs/trees/crafting/systems; mutual gating |
| L6 | Content unlocks | New classes, stages, systems, and reward-pool entries |
| L7 | Endgame tiers | Post-campaign difficulty tiers — D10 (open) |

[PROPOSAL] Deliberately **rejected** layers: a separate "build XP" bar (builds are emergent, not a meter) and a separate village XP bar (building tiers already gate progress — avoid double bookkeeping).

**Hero model [mostly LOCKED]:** **one shared town** with global progression (L11/L12) is confirmed; the remaining open detail is the character model — roster of per-class heroes vs. one hero switching classes (D3-detail). The shared town is the unifying meta-progression body, strengthening pillar 1 (no wasted run, regardless of who you play).

## 12. Roguelike Systems

[PROPOSAL] Why "roguelite" (GAME_DESIGN.md §1): the run resets on end, but the meta persists.

- **Permadeath of the run [LOCKED → L8/L15]:** every run starts with all permanent bonuses applied (equipment, runes, enchantments, mastery, town, NPC); run-only upgrades, boons, blessings, curses, and consumables reset on death.
- **Procedural assembly:** handcrafted room templates + encounter sets, arranged procedurally per stage (WORLD_DESIGN.md §10).
- **Reward RNG as choices:** randomness deals the offers; the player makes the decisions (choice-of-3) — agency over luck (pillar 2).
- **Mutators:** modifier rules that remix stages at higher difficulty tiers (D10).
- **Seeds:** supported for reproducibility, debugging, and sharing (PROJECT_STRUCTURE.md already plans `seed.py`).
- **Ending structure:** DESIGN DECISION REQUIRED (D9): authored campaign ending + optional endless "Deepening" mode (recommended) vs. endless-only.

## 13. Difficulty

**Combat evolution [LOCKED → L4]:** difficulty starts deliberate/readable and grows toward fast, build-focused, near-bullet-hell endgame pressure — the transition is earned through progression, not immediate.

[PROPOSAL]

- **In-run depth scaling:** each stage raises pressure through enemy composition, density, and stats — defined in data, not code.
- **Baseline target:** the first boss is reachable in early runs; the final boss is a journey (RULES.md §10 vertical-slice first).
- **Post-campaign tiers:** DESIGN DECISION REQUIRED (D10) — recommended: escalating tiers ("Deepening") stacking mutators + reward multipliers [REFERENCE-inspired: HoH II New Game+].
- **Assists:** accessibility assists (EXPERIENCE_DESIGN.md §16) exist outside the difficulty curve and never disable achievements/unlocks.

## 14. Economy

**Currencies [LOCKED → L9]:** two independent persistent currencies:

| Currency | Earned | Spent |
|----------|--------|-------|
| **Gold** | Combat, rooms, events | Shops, permanent equipment, consumables, character upgrades, general progression |
| **Babylon Relics** (rare construction material) | Stage progression, elites, secrets, bosses | Town upgrades, building construction, village expansion, NPC unlocks |

**Banking [LOCKED → L10]:** **caravan checkpoints** encountered during a run let the player send currencies safely to town. Dying **before** using a caravan: **20%** of carried currencies are lost; **80%** automatically reach town. After defeating a stage boss, returning to town is **without penalty** (L7).

Boss trophies (milestone unlock flags) remain a separate, non-farmable unlock signal (§9) [PROPOSAL].

## 15. Rewards

[PROPOSAL] Reward taxonomy mapped to the loops (§1):

- **Combat drips:** gold, small pickups.
- **Room clears:** boon choices, consumables.
- **Elites:** boosted choices, rare material.
- **Bosses:** trophy + burst + unlock roll.
- **Milestones:** village growth, NPC arrivals, content unlocks.
- **Records:** depth bests, celebrated in the village.

Rule: every reward readable in 2 seconds (EXPERIENCE_DESIGN.md §13); behavior change beats numbers (pillar 2).

## 16. Game Rules

[PROPOSAL] Draft global rules:

1. A run is one continuous attempt; run state is deleted when the run ends.
2. Return to town only after a stage boss (L7); death loses temporary progress and follows the 20/80 caravan rule (L8/L10).
3. No unavoidable damage — every attack telegraphed (pillar 5).
4. All gameplay content lives in data files, not code (RULES.md §7-§8).
5. Nothing enters reward pools without an existing unlock path.
6. **Mid-run save/quit:** DESIGN DECISION REQUIRED (D15): save-and-exit anytime / only between stages (recommended) / never.

## 17. Gameplay Constraints

[FOUNDATION + PROPOSAL]

- Single-player first; multiplayer is an open question (D11) and must not distort single-player balance.
- Session length: 20-45 minutes.
- Readability budget: cap simultaneous major threats; tuned during the vertical slice (pillar 5).
- Vertical slice before content volume (RULES.md §10).
- No gameplay content without explicit human approval (RULES.md §3).

## 18. Village Systems

[FOUNDATION] The village is a real place that visibly grows; NPC progression has meaningful gameplay consequences.

[PROPOSAL] The system concept — **the village is the body of the meta-game**: every persistent system has a physical place and a face.

**Progression structure [LOCKED → L11/L12]:** buildings unlock through **Town Level**; each building has its own upgrade levels; higher building levels unlock new **services**; major building milestones may unlock new NPCs, upgrade trees, crafting options, or progression systems. Town Level gates buildings, and buildings gate Town progression (mutual gating). NPC unlocks use **Babylon Relics** (L9).

- **Service slots (6-8 at v1; names are placeholders, not content):** Smith (gear, L14) · Scholar (abilities/passives/loadout) · Tavern (hero roster, rumors/lore) · Healer (consumables, blessings) · Market (run preparation, modifiers) · Builder (village upgrades) · 1-2 special plots unlocked via milestones.
- **Building tiers:** 3 tiers per building; each tier = visual upgrade **and** functional unlock; gated by rare material + boss trophies.
- **NPC progression — three tracks:** *service tier* (better stock/unlocks), *personal questline* (objectives that send you into the dungeon), *relationship* (dialogue and favor perks). Consequences: new abilities/passives entering reward pools, new run modifiers, new services, lore. Track depth = developer decision.
- **NPC arrival:** milestone-driven — boss first-kills, dungeon rescues, village tier thresholds (ties the dungeon directly to the village: differentiator #1, GAME_DESIGN.md §9).
- **Run preparation:** loadout swap, gear equip (D6), consumable purchase, optional run modifiers [REFERENCE-inspired: HoH II drinks].
- **Visual development:** tiered building sprites, ambient life, lighting/decor upgrades; every investment visible from the village square (pillar 4).

## 19. Build Philosophy

[FOUNDATION] Builds are a meaningful part of the game.

[PROPOSAL] The build formula:

**Build = Class core (weapon category behavior, L6) + ability loadout (Q/E/R/T + class skill, L5) + passive picks + run-only upgrades/boons + permanent layer (equipment/runes/enchantments, L14)**

- **Synergy through tags:** components share keywords; boons/passives referencing the same tags create emergent combos (§6). The tag vocabulary is data-defined.
- **Build rules:**
  1. Every component changes *decisions*, not just numbers (pillar 2).
  2. Target ≥ 3 viable build archetypes per class at v1 (archetypes are developer content).
  3. A specialization is a new *lens* on the class kit (new abilities/passives), never a plain stat upgrade [REFERENCE-inspired: HoH II specializations add abilities/passives].
  4. No mandatory picks — if every player takes it, it is a balance bug.

