

# 2. `PROJECT_STRUCTURE.md`

Bu dosya projenin **kuş bakışı mimarisi** olacak.

```text
project-root/
│
├── RULES.md
├── IMPLEMENTATION_PLAN.md
├── PROJECT_STRUCTURE.md
├── README.md
├── CHANGELOG.md
├── LICENSE
│
├── pyproject.toml
├── uv.lock
├── .gitignore
├── .editorconfig
├── .pre-commit-config.yaml
│
├── config/
│   ├── game.yaml
│   ├── display.yaml
│   ├── audio.yaml
│   ├── input.yaml
│   ├── debug.yaml
│   └── development.yaml
│
├── data/
│   │
│   ├── combat/                  # Phase 4 combat data (added 2026-07-27)
│   │   └── attacks/
│   │
│   ├── player/
│   │   ├── stats.yaml
│   │   ├── abilities.yaml
│   │   └── progression.yaml
│   │
│   ├── weapons/
│   │   ├── melee/
│   │   └── ranged/
│   │
│   ├── items/
│   │   ├── consumables/
│   │   ├── equipment/
│   │   └── relics/
│   │
│   ├── enemies/
│   │   ├── common/
│   │   ├── elite/
│   │   └── bosses/
│   │
│   ├── loot/
│   │   ├── tables/
│   │   └── pools/
│   │
│   ├── world/
│   │   ├── biomes/
│   │   ├── rooms/
│   │   ├── encounters/
│   │   ├── events/
│   │   └── stages/
│   │
│   ├── localization/
│   │   └── en.yaml
│   │
│   ├── schemas/                 # data contracts (added 2026-07-26)
│   ├── classes/                 # provisional category (added 2026-07-26)
│   ├── abilities/               # provisional category (added 2026-07-26)
│   ├── passives/                # provisional category (added 2026-07-26)
│   ├── npcs/                    # provisional category (added 2026-07-26)
│   ├── unlocks/                 # provisional category (added 2026-07-26)
│   └── village/
│       ├── buildings/
│       └── upgrades/
│
├── assets/
│   │
│   ├── sprites/
│   │   ├── player/
│   │   ├── enemies/
│   │   ├── bosses/
│   │   ├── weapons/
│   │   ├── items/
│   │   └── effects/
│   │
│   ├── tilesets/
│   │   ├── world/
│   │   ├── dungeon/
│   │   └── biome/
│   │
│   ├── maps/
│   │   ├── rooms/
│   │   ├── prefabs/
│   │   └── backgrounds/
│   │
│   ├── animations/
│   │   ├── player/
│   │   ├── enemies/
│   │   └── bosses/
│   │
│   ├── audio/
│   │   ├── music/
│   │   ├── sfx/
│   │   └── ambient/
│   │
│   ├── fonts/
│   │
│   └── ui/
│       ├── icons/
│       ├── panels/
│       └── menus/
│
├── src/
│   │
│   ├── main.py
│   │
│   ├── engine/
│   │   ├── game_loop.py
│   │   ├── game.py
│   │   ├── scene.py
│   │   ├── scene_manager.py
│   │   ├── entity.py
│   │   ├── component.py
│   │   └── system.py
│   │
│   ├── core/
│   │   ├── constants.py
│   │   ├── enums.py
│   │   ├── events.py
│   │   ├── signals.py
│   │   ├── state_machine.py
│   │   ├── dependency_container.py
│   │   ├── data_loader.py
│   │   └── content_registry.py
│   │
│   ├── input/
│   │   ├── input_manager.py
│   │   ├── keyboard.py
│   │   └── controller.py
│   │
│   ├── rendering/
│   │   ├── renderer.py
│   │   ├── camera.py
│   │   ├── sprite_renderer.py
│   │   ├── animation.py
│   │   ├── particles.py
│   │   └── effects.py
│   │
│   ├── audio/
│   │   ├── audio_manager.py
│   │   ├── music_manager.py
│   │   └── sfx_manager.py
│   │
│   ├── physics/
│   │   ├── collision.py
│   │   ├── hitbox.py
│   │   ├── hurtbox.py
│   │   └── movement.py
│   │
│   ├── gameplay/
│   │   │
│   │   ├── player/
│   │   │   ├── player.py
│   │   │   ├── player_controller.py
│   │   │   ├── player_stats.py
│   │   │   ├── player_state.py
│   │   │   └── abilities.py
│   │   │
│   │   ├── combat/
│   │   │   ├── combat_system.py
│   │   │   ├── damage.py
│   │   │   ├── attack.py
│   │   │   ├── status_effects.py
│   │   │   └── invulnerability.py
│   │   │
│   │   ├── weapons/
│   │   │   ├── weapon.py
│   │   │   ├── weapon_factory.py
│   │   │   └── weapon_system.py
│   │   │
│   │   ├── enemies/
│   │   │   ├── enemy.py
│   │   │   ├── enemy_ai.py
│   │   │   ├── enemy_factory.py
│   │   │   └── behaviors/
│   │   │
│   │   ├── bosses/
│   │   │   ├── boss.py
│   │   │   ├── boss_ai.py
│   │   │   └── phases/
│   │   │
│   │   ├── items/
│   │   │   ├── item.py
│   │   │   ├── inventory.py
│   │   │   └── equipment.py
│   │   │
│   │   ├── loot/
│   │   │   ├── loot_generator.py
│   │   │   └── loot_table.py
│   │   │
│   │   ├── progression/
│   │   │   ├── xp.py
│   │   │   ├── leveling.py
│   │   │   └── meta_progression.py
│   │   │
│   │   ├── roguelike/
│   │   │   ├── run.py
│   │   │   ├── run_manager.py
│   │   │   ├── seed.py
│   │   │   └── reward_selection.py
│   │   │
│   │   └── village/
│   │       ├── village.py
│   │       ├── building.py
│   │       ├── npc.py
│   │       └── village_scene.py
│   │
│   ├── world/
│   │   ├── world.py
│   │   ├── biome.py
│   │   ├── room.py
│   │   ├── room_manager.py
│   │   ├── dungeon_generator.py
│   │   ├── encounter_manager.py
│   │   └── map_generator.py
│   │
│   ├── ui/
│   │   ├── hud.py
│   │   ├── menus.py
│   │   ├── inventory_ui.py
│   │   ├── pause_menu.py
│   │   └── death_screen.py
│   │
│   ├── save/
│   │   ├── save_manager.py
│   │   ├── save_schema.py
│   │   └── migrations.py
│   │
│   ├── debug/
│   │   ├── debug_overlay.py
│   │   ├── debug_commands.py
│   │   └── profiler.py
│   │
│   └── utils/
│       ├── logger.py
│       ├── config_loader.py
│       ├── asset_loader.py
│       ├── random_utils.py
│       └── file_utils.py
│
├── tests/
│   ├── conftest.py
│   ├── unit/
│   │   ├── test_*.py          # infrastructure tests (added 2026-07-26)
│   │   ├── combat/
│   │   ├── player/
│   │   ├── enemies/
│   │   ├── loot/
│   │   ├── progression/
│   │   └── save/
│   │
│   ├── integration/
│   │   ├── gameplay/
│   │   ├── world/
│   │   └── save/
│   │
│   └── fixtures/
│
├── tools/
│   ├── asset_tools/
│   ├── map_tools/
│   ├── data_validation/
│   └── development/
│
├── docs/
│   │
│   ├── design/
│   │   ├── GAME_DESIGN.md
│   │   ├── CORE_LOOP.md
│   │   ├── COMBAT_DESIGN.md
│   │   ├── PLAYER_DESIGN.md
│   │   ├── ENEMY_DESIGN.md
│   │   ├── BOSS_DESIGN.md
│   │   ├── ITEM_DESIGN.md
│   │   ├── PROGRESSION_DESIGN.md
│   │   └── WORLD_DESIGN.md
│   │
│   ├── architecture/
│   │   ├── ARCHITECTURE.md
│   │   ├── DATA_FLOW.md
│   │   └── SAVE_SYSTEM.md
│   │
│   ├── development/
│   │   ├── SETUP.md
│   │   ├── CONTRIBUTING.md
│   │   ├── DEBUGGING.md
│   │   ├── DEVELOPMENT.md
│   │   └── VERTICAL_SLICE.md
│   │
│   └── decisions/
│       └── ADR/
│
├── saves/
│
├── logs/
│
└── scripts/
    ├── run.py
    ├── test.py
    ├── validate_data.py
    └── build.py
```
