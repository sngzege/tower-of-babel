# GAME DESIGN

> **Status:** DRAFT v2 — reviewed by the human developer. Core direction is now **LOCKED** in DESIGN_DECISIONS.md (2026-07-27); remaining [PROPOSAL] items still need approval.
> **Legend:** **[FOUNDATION]** = direction given by the human developer · **[REFERENCE]** = observed in Heroes of Hammerwatch II (inspiration only, never automatically ours) · **[PROPOSAL]** = AI recommendation, needs approval · **[DECISION]** = open question, marked `DESIGN DECISION REQUIRED` (master list in §12).

## 1. Game Identity

- **Game title:** DESIGN DECISION REQUIRED (D1). Naming is reserved for the developer.
- **Setting:** **Dark Fantasy Babylon** — the Tower of Babel myth; humanity at war with the gods; the player climbs the Tower **[LOCKED → DESIGN_DECISIONS.md L1]**
- **Genre (primary):** Action Roguelite RPG [PROPOSAL]
- **Subgenres (secondary):** Top-down Dungeon Crawler · Class-based ARPG / Hack-and-Slash combat · Village/hub progression (meta-builder-lite) [PROPOSAL]
- **Platform:** DESIGN DECISION REQUIRED. Recommendation: PC (Windows) first, full controller + keyboard/mouse support from the start [PROPOSAL]
- **Perspective:** Top-down, 3/4 view [PROPOSAL]
- **Camera:** Player-following camera constrained by room/arena bounds (see EXPERIENCE_DESIGN.md §8) [PROPOSAL]

### Genre reasoning

- **Roguelite, not roguelike:** runs have procedural layouts, run-ending death, and per-run builds — but the player keeps persistent progression (village, unlocks, hero growth) between runs. [PROPOSAL]
- **Action RPG:** real-time combat (attack / dodge / abilities), classes, and build crafting are the core skill expression. [FOUNDATION]
- **Dungeon crawler:** every run takes place inside a multi-stage dungeon frontier. [FOUNDATION]
- **Village progression** is a first-class defining feature, not a menu — our main genre-flavor differentiator (see §9). [FOUNDATION]
- We intentionally do **not** copy the reference game's tag list: Heroes of Hammerwatch II's tags include multiplayer/co-op and a heavier gear-enchant system; here both are open questions (D11, D6), not defaults. [REFERENCE]

## 2. High Concept

[FOUNDATION] — the developer's direction:

> Build your hero. Build your village. Enter the unknown. Push deeper than your last run. Discover new possibilities. Return stronger. Make the village stronger. Try again.

[PROPOSAL] — optional tightened one-liner:

> *Descend into the ever-changing deep. Fight, build, die — and return to a village that grows because you did.*

A pixel-art action roguelite where every run advances two things at once: the hero you build, and the village you call home.

## 3. Core Vision

[FOUNDATION] The player repeatedly enters a dangerous dungeon, pushes as far as possible, and returns to a persistent village that visibly grows and unlocks new possibilities — which in turn enables deeper runs.

[PROPOSAL] The design treats seven entities as one interconnected system — the game's defining relationship:

**PLAYER ↔ CLASS ↔ BUILD ↔ VILLAGE ↔ NPCs ↔ DUNGEON ↔ PROGRESSION**

Every feature must touch at least two of these. Any feature that touches none is a candidate for cutting.

## 4. Player Fantasy

*"You climb the Tower so humanity — and your town — can endure the war of the gods."* **[theme LOCKED → L1/L2]**

- In the Tower: a skilled fighter whose **build** — not just stats — carries them higher than last time.
- In the town: the catalyst of a community. NPCs arrive, grow, and open new doors because of what you did above.
- Story foundation is locked (L2): the player awakens mid-war, obeys orders, and gradually learns neither side can win.

## 5. Design Pillars

[PROPOSAL] Five pillars. Every design decision must serve at least one:

1. **No Wasted Run** — every run feeds two progressions (hero + village), even a failed one.
2. **Builds Over Numbers** — rewards change how you play (synergies, behaviors), not just "+5% stats".
3. **Push Your Luck** — the tension between banking progress and descending deeper defines every run (D4).
4. **The Village Is Alive** — meta progression is a place you walk in, with NPCs who grow; never just a menu.
5. **Readable Combat** — telegraphed, dodge-centric action where player skill matters at every depth.

## 6. Target Experience

[PROPOSAL] Emotional rhythm of one session:

**Anticipation** (prepare in the village) → **Tension/Greed** (push deeper or bank?) → **Triumph or Loss** (boss down / hero down) → **Restoration** (village visibly grows) → **Curiosity** (what changed? what unlocked? how far next time?).

- Session target: 20-45 minutes including village time.
- Long-term feeling: *"my village and my hero are both becoming something."*

## 7. Tone & Atmosphere

Contrast-driven tone: warmth, safety, community (town) against the cursed, divine hostility of the Tower. The higher the climb, the stranger and more oppressive the world feels **[LOCKED → L1]**.

- Register: dark fantasy with hopeful perseverance — Babylonian myth, occult rituals, ancient magic, cursed architecture, forgotten civilizations, mysterious relics.
- Story and lore stay in the background; environmental storytelling over long dialogue.

## 8. Inspirations

### 8.1 Primary reference: Heroes of Hammerwatch II

[REFERENCE] Confirmed facts (official Steam page, app 619820; Crackshell / Team17; released 14 Jan 2025; "Very Positive"):

- *"A rogue-lite action-rpg that offers extensive persistent progression. Build your town, upgrade and equip your heroes, before taking on the ever-changing Dark Citadel — either solo or with a team of friends."*
- 7 classes: Warrior, Paladin, Ranger, Wizard at start; Rogue, Warlock, Sorcerer unlocked through gameplay. Each class has **3 specializations** adding new abilities and passives.
- 8 distinct, randomly generated floor types with unique enemies, traps, challenges.
- Town building: upgrade the town to unlock run-enhancing NPCs, item stash, adventure customization.
- Gear: enchantable weapons/gear; blueprints unlock enchants; attunements permanently upgrade trinkets; drinks modify runs.
- New Game+: infinite progression, rising difficulty, better gear/buffs, unlimited leveling.
- Online co-op up to 4 players; top-down pixel art.

[REFERENCE] Design principles worth learning from (why its systems work together):

1. **Dual progression axes** — hero depth × town growth; even failure progresses you.
2. **Unlocks enter reward pools** (blueprints/attunements) — meta progression widens run variety instead of only adding stats.
3. **Town as a physical place** — abstract upgrades become visible buildings and NPCs.
4. **Class × specialization × gear × in-run RNG** — emergent build variety per run.
5. **NG+ tiers** — the mastery curve extends far beyond the first victory.
6. **Readable telegraphed combat** — player skill stays relevant as numbers grow.

[PROPOSAL] Adopt / adapt / avoid (explicitly *not* automatic adoption):

- **Adopt as inspiration:** persistent hub meta; class specializations; unlocks entering reward pools; NG+-style tiers (D10); varied themed floors.
- **Adapt to our game:** town → *living village* with NPC personal progression coupled to builds (deeper than the reference); drinks → run preparation at the village; gear system → open question (D6).
- **Avoid copying:** 7 launch classes (fewer, deeper for us); heavy gear-enchant complexity; co-op as a launch assumption (D11).

### 8.2 Secondary inspirations

[PROPOSAL] Reference only — nothing copied without developer approval:

- **Hades:** clarity of choice-based run rewards; story through evolving NPC relationships.
- **Slay the Spire:** legible risk/reward routing decisions.
- **Moonlighter:** the town-home as an emotional anchor for dungeon loops.

## 9. Differentiation

[PROPOSAL] What makes this game its own game, not a HoH II clone:

1. **Village-NPC-build coupling:** NPCs arrive through dungeon milestones, and their growth directly unlocks build options (abilities, passives, loadouts) — the village is part of the build system, not just a shop row.
2. **Extraction tension:** an explicit *Return-or-Descend* decision after every stage boss (D4).
3. **Fewer classes, deeper each:** specialization evolution over roster size.
4. **Story in the walls:** lore through environmental storytelling and an evolving village — never cutscene interruptions.

## 10. Scope

[PROPOSAL] Planning targets, not commitments:

- **Vertical slice first (RULES.md §10):** the **Warrior** [LOCKED → L3], 1 stage (5 floors incl. boss floor per L7), 3 village service NPCs, one closed core loop.
- **Full v1:** **3 classes [LOCKED → L3: Warrior, Ranger, Mage]** with specializations, 4-5 stages + final confrontation, village with ~6-8 service slots, post-campaign difficulty tiers (D10).
- Everything beyond this is out of scope until explicitly approved.

## 11. Non-Goals

[PROPOSAL]

- Not a reproduction of Heroes of Hammerwatch II.
- No open world; no cutscene-heavy narrative; no survival/crafting simulation.
- No dozens of classes; no content volume before the core loop is proven fun (RULES.md §9-§10).
- No PvP; no monetization/microtransactions; offline single-player unless D11 changes that.

## 12. Open Design Decisions

> Locked decisions now live in **DESIGN_DECISIONS.md** (source of truth, 2026-07-27). The remaining items below are still **DESIGN DECISION REQUIRED**.

| ID | Question | Status |
|----|----------|--------|
| D1 | Game title / working title | **open** |
| ~~D2~~ | World theme | **RESOLVED → L1:** Dark Fantasy Babylon (Tower of Babel) |
| D3 | Hero roster / shared town | **mostly resolved** (one shared town, L11/L12); open detail: hero roster vs. one multi-class hero |
| ~~D4~~ | Extraction rule | **RESOLVED → L7:** return to town only after a stage boss |
| ~~D5~~ | Death penalty | **RESOLVED → L8/L10:** temporary progress lost; 20% of unbanked currencies lost |
| ~~D6~~ | Gear depth | **RESOLVED → L14:** lightweight permanent equipment + runes/enchantments/sets |
| D7 | Floor navigation **within** a floor (stage macro-structure locked per L7) | **open** |
| D8 | Stage shortcuts / checkpoints for later runs | **open** |
| D9 | Final campaign ending + endless mode, or endless-only | **open** |
| D10 | Post-campaign difficulty tiers | **open** |
| D11 | Multiplayer / co-op | **open** |
| ~~D12~~ | Slice / launch classes | **RESOLVED → L3:** Warrior (slice); Warrior/Ranger/Mage (v1) |
| ~~D13~~ | Hero progression model | **RESOLVED → L11/L13:** class mastery + permanent progression structure |
| D14 | In-run growth: level-ups, choice-of-3 boons, or both | **open** |
| D15 | Mid-run save / quit rules | **open** |

**Remaining decision priority:** D3-detail → D7 → D14 → D9/D10 → D8/D15 → D1/D11.

