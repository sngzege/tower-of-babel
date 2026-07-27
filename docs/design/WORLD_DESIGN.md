# WORLD DESIGN

> **Status:** DRAFT v2 — reviewed by the human developer. Core direction is now **LOCKED** in DESIGN_DECISIONS.md (2026-07-27); remaining [PROPOSAL] items still need approval.
> **Legend:** **[FOUNDATION]** = developer-given direction · **[REFERENCE]** = observed in Heroes of Hammerwatch II (inspiration only) · **[PROPOSAL]** = AI recommendation, needs approval · **[DECISION D#]** = open question (master list: GAME_DESIGN.md §12).

## 1. World Overview

[FOUNDATION] The world exists to serve the loop: **one safe home** (the persistent town) vs. **one ever-ascending unknown** (the Tower). Story and lore support the gameplay; they never interrupt it.

**THEME [LOCKED → L1]: Dark Fantasy Babylon.** The central inspiration is the myth of the **Tower of Babel**:

- Humanity has **declared war against the gods**. The Tower is both the battlefield and the world's greatest mystery.
- The player **climbs upward** through the Tower; later bosses are **gods, demigods, or divine beings**.
- Babylonian mythology, occult rituals, ancient magic, cursed architecture, forgotten civilizations, and mysterious relics shape the world.
- The story remains **gameplay-first**: lore is discovered gradually, with **environmental storytelling** preferred over long dialogue.

How the locked theme supports the systems:

- **Town:** the human war-effort's foothold near the Tower — it exists because of the war and the climb.
- **Tower / Stages:** vertical strata of cursed architecture; each stage is a distinct layer of the Tower with its own identity.
- **Bosses:** divine gatekeepers — demigods and gods — each embodying their stage's identity.
- **NPCs:** soldiers, scholars, priests, relic-hunters, survivors — the human side of the war.
- **Progression:** height is the shared language of progress — "how high can you climb?"
- **Lore:** murals, rituals, relics, and ruins tell the story of the war and of what the Tower really is.

*(The three draft theme candidates A/B/C from v1 are superseded by the developer's own theme — DESIGN_DECISIONS.md §2.)*

## 2. Setting

**Setting [LOCKED → L1]:** a Dark Fantasy Babylon universe at war — humanity against the gods.

- One persistent **town** (the war-effort foothold); one endless climb: **the Tower**.
- The Tower's interior rearranges between climbs (diegetic cover for procedural generation).
- Fighting in the Tower is the hero's duty and profession — initially under military orders (L2).

## 3. World Rules

**World rules [LOCKED-aligned]:**

1. The Tower changes; the town persists and remembers.
2. **Height** equals danger **and** reward — always both.
3. Boss trophies carry power the town can use (justifies trophy-gated village tiers, GAMEPLAY_DESIGN.md §18).
4. People — and things — can be found and rescued in the Tower (justifies milestone NPC arrival).
5. The world never explains itself through cutscenes; it explains itself through places, objects, and people (L1).

## 4. History

**Foundation [LOCKED → L2]:** humanity is at war with the gods — a war already raging when the player awakens. Details of the war's origin are lore to be discovered in the Tower, not exposition. Keep history compressed to what the player can *see* in stages and hear from NPCs.

## 5. Story

**Foundation [LOCKED → L2]:** the player awakens in the middle of the ongoing war and initially obeys military orders without understanding the conflict. Climbing higher and defeating increasingly powerful bosses reveals that **neither side can truly win** — and the protagonist eventually becomes hostile toward **both** factions. (Foundation only; do not expand significantly yet.)

Story delivery framework [PROPOSAL]:

- **Channels:** environmental storytelling (stage set dressing), evolving NPC dialogue, short boss intros, flavor text on boons/items/enemies, optional codex (decision).
- **Rule:** story never pauses the loop; everything skippable; lore rewards attention but is never required for progress.

## 6. Lore

**Direction [LOCKED → L1]:** Babylonian mythology, occult rituals, ancient magic, cursed architecture, forgotten civilizations, mysterious relics.

Lore slots to fill gradually (content TBD, developer-owned): what the Tower really is, why the war started, who the divine bosses are, what height records mean, why the hero fights. One line of lore per slot is enough for the vertical slice.

## 7. Regions

[PROPOSAL] Structural framework (not content):

- **The Town** — hub region; persistent; visually evolving (GAMEPLAY_DESIGN.md §18).
- **Tower stages** — one themed Tower layer per stage; macro order is linear ascent (§9).
- **Region template:** identity / enemy family / mechanic twist / boss (a divine being, L1) / palette + audio signature.
- **Count for v1:** 4-5 stage regions + final confrontation (planning target, GAME_DESIGN.md §10).

## 8. Biomes

[PROPOSAL] A biome is a stage's identity layer: palette, tileset, enemy family, hazards, music — all infused with cursed Babylonian architecture and occult character (L1).

- Illustrative strata concepts (NOT content): ruined siege-scarred base → flooded foundations → overgrown hanging terraces → sanctified upper shrines. *Examples only; final biomes are developer-owned.*
- Each biome is defined in data, not code (RULES.md §7).

## 9. Map Structure

**Macro structure [LOCKED → L7]:**

```text
Town → Tower Entry → Stage 1 (Floors 1-4 + Floor 5 Boss) → Return or Continue
→ Stage 2 (Floors 1-4 + Floor 5 Boss) → ... → Final Stage / Final Boss / Maximum Height
```

- **Macro:** linear stage ascent — progression clarity and a clean "how high this time" axis.
- **Micro:** branching *within* a floor (route choices, optional wings). DESIGN DECISION REQUIRED (D7, open): free-roam floors vs. node-map routing vs. hybrid.
- **Boss = the gate** between stages; *Return-or-Continue* choice after each gate (L7, GAMEPLAY_DESIGN.md §2).

## 10. Level Structure

[PROPOSAL]

- A stage = **5 floors: floors 1-4 normal progression, floor 5 the boss arena [LOCKED → L7]**.
- A floor = handcrafted **room templates** procedurally assembled — authored pieces, randomized arrangement (RULES.md §7 data-driven; §22 intentional design).
- Every floor: one critical path + optional side wings; an antechamber before the boss; secret rooms off the beaten path.

## 11. Room Types

[PROPOSAL] Taxonomy (contents are developer content):

| Type | Purpose |
|------|---------|
| Combat | The core gameplay space |
| Elite | Harder encounter, better rewards |
| Event | Short choice vignette with risk/reward |
| Shop | Spend gold mid-run |
| Shrine / Challenge | Trade risk for power |
| Secret | Reward curiosity |
| Rest | Scarce healing and a breath |
| Boss | Stage gate |

## 12. Exploration

[PROPOSAL] Optional content is always a risk/reward trade: side wings cost time and health, and pay in boons, materials, or lore.

- Height records are tracked and celebrated — the "how high this time?" engine (GAME_DESIGN.md §6).
- Exploration serves the push-deeper fantasy; wandering never feels like wasting a run.

## 13. NPCs

[FOUNDATION] The village has NPCs; NPC progression has meaningful gameplay consequences.

[PROPOSAL] Framework (the cast itself belongs to the developer):

- **Town service NPCs:** each owns a service and three progression tracks (GAMEPLAY_DESIGN.md §18); NPC unlocks use Babylon Relics (L9).
- **Tower-encounter NPCs:** met in the Tower through rescue/events; may relocate to the town — the strongest town↔Tower coupling (differentiator #1, GAME_DESIGN.md §9).
- **Dialogue = the primary story channel** (§5): lines evolve with town state, boss kills, and height records.
- Arrival is milestone-driven, never random.

## 14. Events

[PROPOSAL]

- **In-run events:** short, readable choice vignettes with explicit risk/reward (event rooms, §11).
- **Village milestone scenes:** 10-30 second skippable beats when the village changes (building completed, NPC arrived).
- Events never punish the player for engaging with them — unclear gambles are bad events.

## 15. Secrets

[PROPOSAL]

- Secret rooms (hidden entries/conditions), hidden unlocks, lore secrets.
- Secrets reward curiosity; they are never required for baseline progression.
- Subtly telegraphed — secrets should feel discoverable, not like pixel-hunting.

## 16. Factions

DESIGN DECISION REQUIRED — optional layer.

[PROPOSAL] At most two at v1: the village itself + one dungeon-side presence (theme-bound, D2). Recommend deferring this layer until the theme is locked; do not build faction systems without approved content.

## 17. Narrative Progression

[FOUNDATION] Story and lore integrate into the background; narrative progression ties naturally to gameplay.

Milestone-driven narrative, aligned with the locked story foundation (L2):

1. First boss kill → town unlock beat (new plot/NPC).
2. Each stage completion → new dialogue tiers and town changes; the truth about the war surfaces gradually (L2).
3. Final boss → campaign resolution. DESIGN DECISION REQUIRED (D9, open): authored ending + optional endless mode (recommended) vs. endless-only.
4. Post-campaign → framing for difficulty tiers (D10, open).
- The story serves the loop; it never gates grinding behind cutscenes (L1).
