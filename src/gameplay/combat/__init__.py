"""Combat foundation (Phase 4).

Provides:
- Damage pipeline (data-driven damage types/tags, hit resolution, application)
- Attack executor (lifecycle: windup → active → recovery → cooldown)
- Invulnerability service (multiple concurrent sources, event-based)
- Status effect framework (tag-based slots with tick/expire)
- Combat system (orchestrates hit resolution each frame)

Frame-level integration:
  PlaytestScene (or a future CombatComponent) collects active hitboxes and
  vulnerable hurtboxes each frame, calls CombatSystem.resolve_hits(), then
  applies damage results and expired-status-events.

Dependency rules (ARCHITECTURE.md §5):
  - combat/ may import physics, core, registry
  - Must NOT import rendering, audio, ui (publishes events instead)
  - Must NOT import gameplay.player directly (sees interfaces via components)
"""
