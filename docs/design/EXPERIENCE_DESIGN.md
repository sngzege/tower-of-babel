# EXPERIENCE DESIGN

> **Status:** DRAFT v2 — reviewed by the human developer. Core direction is now **LOCKED** in DESIGN_DECISIONS.md (2026-07-27); remaining [PROPOSAL] items still need approval.
> **Legend:** **[FOUNDATION]** = developer-given direction · **[REFERENCE]** = observed in Heroes of Hammerwatch II (inspiration only) · **[PROPOSAL]** = AI recommendation, needs approval · **[DECISION D#]** = open question (master list: GAME_DESIGN.md §12).

## 1. Art Direction

[FOUNDATION] Pixel-art based game.

**Direction [LOCKED-aligned → L1]:** readable pixel-art action with a **two-worlds contrast**: warm, lived-in human town vs. the cursed, divine Tower — Babylonian architecture, occult symbolism, ancient-magic glow, corrupted grandeur intensifying with height.

- **Readability hierarchy (highest first):** player > boss attacks/telegraphs > elites > enemies > projectiles > pickups > environment.
- Beauty must never reduce combat clarity (pillar 5, GAME_DESIGN.md §5).

## 2. Pixel Art Style

DESIGN DECISION REQUIRED — final style belongs to the developer.

[PROPOSAL] Direction: clean 16-bit-class sprites with modern effects (lighting, particles) — matches reference-era expectations [REFERENCE: HoH II pixel presentation] while supporting strong silhouettes.

- Consistent sprite scale across all content.
- Silhouette-first design: every enemy role readable from outline alone.

## 3. Resolution

DESIGN DECISION REQUIRED — options [PROPOSAL]:

- 320×180 (chunky, fastest to produce) / 426×240 (middle) / 480×270 (detailed, harder to animate).
- Recommendation: **480×270** internal, integer-scaled to the display; validate with an early technical prototype before locking.
- UI may render at a higher internal scale than world sprites for text crispness.

## 4. Color Language

[PROPOSAL] Global gameplay colors stay consistent across **all** stages:

- Enemy telegraphs / hazards: one warm family, never reused for decoration.
- Player and friendly effects: cool family.
- Interactables: one consistent highlight; healing: one distinct color.
- Each stage gets a dominant palette for identity; bosses use accent colors reserved from common enemies.

## 5. Lighting

[PROPOSAL] Cheap-first lighting: per-stage ambient tint + gameplay highlights (telegraph glow, interactable shimmer).

- Darkness as a mood tool in deep stages (fits Theme A, WORLD_DESIGN.md §1).
- No dynamic shadows before profiling proves budget (RULES.md §15).

## 6. Animation Style

[PROPOSAL] Snappy and honest: clear anticipation → fast active frames → readable recovery.

- Telegraph clarity beats flourish; hit reactions instant.
- Player dodge favors responsiveness over realism (pillar 5).

## 7. Visual Effects

[PROPOSAL] VFX budget rules:

- Effects never obscure telegraphs or silhouettes.
- Impact feedback = short flashes + few, well-placed particles.
- Richness scales with rarity: common enemies minimal, elites richer, bosses richest.
- Effects density may grow toward endgame as combat evolves from deliberate to near-bullet-hell (L4) — the readability budget still rules.
- All effects pooled/data-driven (RULES.md §7, §15).

## 8. Camera Feel

[PROPOSAL] Top-down follow camera:

- Soft deadzone + slight lookahead toward movement/aim; clamped to room bounds.
- Boss arenas use composed framing so the whole arena reads at once.
- Screen shake: short, rare, and toggleable (§16).

## 9. Audio Direction

DESIGN DECISION REQUIRED — final audio identity follows the theme (D2).

[PROPOSAL] The contrast principle mirrors the art: village = warm, acoustic, humane; stages = per-biome identity that grows more alien with depth.

- Music and SFX are treated as gameplay channels (telegraph cues), not decoration only.

## 10. Music

[PROPOSAL] Adaptive, loop-friendly, low-fatigue:

- **Village theme:** safe and warm; gains instrumental layers as the village grows — the music literally builds like the village does.
- **Stage themes:** base exploration layer + combat intensity layer; boss proximity adds tension.
- **Boss themes:** one distinct motif per stage family; final confrontation gets its own theme.

## 11. Sound Effects

[PROPOSAL] Priority order:

1. **Combat feedback:** hits, telegraph cues, dodge, player-hurt — must be readable with eyes closed.
2. **Reward feedback:** pickups, choices, unlocks, trophy moments.
3. **Ambience:** per-stage beds; village life sounds (hammering, chatter) that grow with village tiers.

Telegraph audio doubles as an accessibility channel (redundant with visuals, §16).

## 12. UI

[FOUNDATION] The village is not a menu — interactions there are diegetic (walk to the NPC, stand at the anvil).

[PROPOSAL]

- Menus exist only for true management tasks: loadout, gear, meta overview, settings.
- Pixel-styled, chunky, readable UI; full controller and keyboard/mouse parity.
- Every choice screen readable at a glance (choice-of-3 cards, big icons, short text).

## 13. UX

[PROPOSAL] UX rules:

- Any single choice understandable in ≤ 2 seconds.
- Run status always visible: current depth, stage objective, resources.
- On return, the village communicates *what changed* through world cues (new construction, a waiting NPC) rather than popup spam.
- Zero unskippable interruptions, anywhere.

## 14. Menus

[PROPOSAL]

- **Main menu:** continue / new run / settings.
- **Pause:** resume, view loadout, settings, quit-to-village (behavior per D15, GAMEPLAY_DESIGN.md §16).
- **Settings:** video, audio, controls, accessibility.
- Nothing critical nested deeper than two levels.

## 15. HUD

[PROPOSAL] Minimal combat HUD:

- Health, class resource, 3 ability cooldowns, gold/material counter, depth indicator.
- Boss HP bar with phase marks; optional damage numbers (toggle, §16).
- No minimap at launch (floors are compact) — revisit if vertical-slice playtests demand it.

## 16. Accessibility

[PROPOSAL] Baseline set:

- Full input remapping (keyboard/mouse + controller).
- Toggles: screen shake, flash intensity, damage numbers.
- Colorblind redundancy: telegraphs communicate through **shape + color**, never color alone.
- Text size option; assist options (damage-taken scalar, longer telegraph windows) — assist depth is a developer decision.

## 17. Feedback & Game Feel

[PROPOSAL] The game-feel toolkit:

- **Combat:** small hit-stop, impact flashes, knockback, hurt/heal cues, crunchy hit sounds.
- **Rewards:** pickup chimes, choice fanfare, boss-intro stinger, depth-record celebration.
- **Village:** building-completion ceremony, NPC-arrival beat, ambient life scaling with tiers.
- **Targets:** dodge feels generous, hits feel physical, rewards feel earned, and coming home feels warm.
