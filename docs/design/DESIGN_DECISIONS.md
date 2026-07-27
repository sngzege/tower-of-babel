# DESIGN DECISIONS

> **This file is the registry of LOCKED design decisions.** It is the current source of truth for everything listed here (below only RULES.md in the hierarchy).
> Decisions were made by the human developer on **2026-07-27**. They must not be silently changed. Future ideas that would alter them must be recorded as **future design proposals**, never as edits to the locked text.
> Open questions that remain human-owned are listed in §3.

## 1. Locked Decisions

### L1 — Theme and Setting
Dark Fantasy **Babylon**, inspired by the myth of the **Tower of Babel**. Humanity has declared war against the gods. The Tower is both the battlefield and the world's greatest mystery. The player **climbs upward** through the Tower. Later bosses are gods, demigods, or divine beings. Babylonian mythology, occult rituals, ancient magic, cursed architecture, forgotten civilizations, and mysterious relics shape the world. Gameplay-first story; lore discovered gradually; environmental storytelling over long dialogue.

### L2 — Story Foundation
The player awakens in the middle of an ongoing war, initially obeying military orders without understanding the conflict. Climbing higher and defeating increasingly powerful bosses reveals that **neither side can truly win**. The protagonist eventually becomes hostile toward **both** factions. (Foundation only — do not expand significantly yet.)

### L3 — Initial Classes
First release: **Warrior, Ranger, Mage**. The **Warrior** is the primary class for development and the first Vertical Slice. Architecture supports all three from the beginning; future classes arrive through the data-driven pipeline.

### L4 — Combat Philosophy
Combat starts **deliberate and readable**: positioning, blocking, dodging, and timing matter; class identity is felt. With progression into endgame, play gradually evolves toward a **faster, build-focused, almost bullet-hell** style. The transition must feel **earned**, not immediate.

### L5 — Ability Layout (controls)
- **Left Mouse:** primary weapon attack · **Right Mouse:** class skill
- **Q:** active skill 1 · **E:** active skill 2 · **R:** ultimate ability
- **T:** aura / reserved-mana skill · **Space:** dodge / roll
- Classes also have **passive abilities** that define their identity.
- Input architecture must allow future expansion without redesign.

### L6 — Weapon Philosophy
Every class supports **multiple weapon categories**; the category defines the default **attack behavior** (not just damage): Warrior — sword / axe / spear / hammer · Ranger — bow / crossbow / throwing weapons · Mage — staff / wand / orb. Examples: spear → short piercing projectile; axe → sweeping melee arc; hammer → slower impact attack. Behavior is **data-driven** whenever practical.

### L7 — Run Structure
Each **stage = 5 floors**: floors 1-4 normal progression, **floor 5 = boss**. After the boss the player chooses: **Return to Town** or **Continue to the next Stage**. The player **cannot voluntarily leave a run before defeating a boss**. (Resolves D4.)

### L8 — Death
Death **ends the run**. All temporary progress is lost: temporary buffs, blessings, curses, temporary build choices, run-only upgrades. (Resolves D5 — see L10 for currency handling.)

### L9 — Persistent Currencies
Two independent currencies: **Gold** (shops, permanent equipment, consumables, character upgrades, general progression) and **Babylon Relics** (rare construction material: town upgrades, building construction, village expansion, NPC unlocks).

### L10 — Banking System
During a run, **caravan checkpoints** let the player safely send collected currencies back to town. Dying **before** using a caravan loses **20%** of carried currencies; the remaining **80%** automatically reach town. After defeating a stage boss, returning to town is **without penalty**. (This replaces the previously proposed guaranteed pre-boss caravan.)

### L11 — Permanent Progression Structure
Persistent progression = **Town Level · Building Levels · NPC Progression · Class Mastery · Permanent Equipment · Permanent Enchantments · Permanent Runes · Permanent Inventory**. Future progression systems must integrate into this structure.

### L12 — Town Progression
Buildings unlock through **Town Level**; buildings have their own upgrade levels; higher building levels unlock new **services**. Major building milestones may unlock new NPCs, upgrade trees, crafting options, or progression systems. **Town Level gates building progression, and buildings gate Town progression** (mutual gating).

### L13 — Class Mastery
Each class has its own mastery progression. Regular milestones (e.g. every 10 levels) grant small **permanent global passive** bonuses. Major milestones (e.g. 25 / 50 / 75 or another balanced interval) grant meaningful **permanent global perk choices** affecting **every** class. Exact values subject to balancing. (Resolves D13.)

### L14 — Equipment Philosophy
**Hades-style** permanent progression plus a **lightweight equipment layer**: early game = simple permanent items (e.g. "Iron Sword — Attack +5"); late game = advanced items, **runes, enchantments, set bonuses**. Equipment must **never** overshadow skill, build decisions, or roguelite progression. (Resolves D6.)

### L15 — Run Start Rule
Every run begins with all permanent bonuses applied: permanent equipment, runes, enchantments, Class Mastery bonuses, town bonuses, NPC bonuses. Run-only upgrades are acquired during the run and reset on death.

### L16 — Core Design Philosophy
The primary design rule: every gameplay system must answer **"Would I personally enjoy playing this game for hundreds of hours?"** — if not, redesign it. Gameplay quality > realism. Fun > complexity. Architecture supports gameplay, never dictates it.

## 2. Resolved Draft Questions (from the design drafts)

| Draft ID | Resolution |
|----------|------------|
| D2 (theme) | **Locked → L1** (developer's own theme; draft candidates A/B/C superseded) |
| D4 (extraction) | **Locked → L7** (return only after boss) |
| D5 (death penalty) | **Locked → L8 + L10** (temporary progress lost; 20/80 currency rule) |
| D6 (gear depth) | **Locked → L14** (lightweight permanent layer + runes/enchants/sets) |
| D12 (first class) | **Locked → L3** (Warrior first; Warrior/Ranger/Mage at release) |
| D13 (hero progression model) | **Locked → L11 + L13** (class mastery model) |
| D3 (hero roster / shared town) | **Partially resolved:** one shared town with global progression (L11/L12). **Open detail:** character model — roster of per-class heroes vs. one hero switching classes. |
| Framework (technical) | **pygame-ce** (approved 2026-07-27; docs/development/FRAMEWORK_EVALUATION.md) |

## 3. Still Open (human-owned)

| ID | Question |
|----|----------|
| D1 | Game title |
| D3-detail | Character model: roster of heroes vs. one multi-class hero |
| D7 | Floor navigation model (free-roam floors vs. node-map vs. hybrid) — **within** a floor; stage macro-structure is locked (L7) |
| D8 | Stage shortcuts/checkpoints |
| D9 | Ending structure (authored ending vs. endless vs. both) |
| D10 | Post-campaign difficulty tiers |
| D11 | Multiplayer/co-op |
| D14 | In-run growth mechanism (level-ups vs. choice-of-3 boons vs. both) |
| D15 | Mid-run save/quit rules |

**Terminology note:** "Town" and "Village" are synonyms in all project documents; locked names (Town Level, Babylon Relics) are used verbatim.

