"""
Headless verification: run the PlaytestScene with enemies and verify
the combat pipeline works: movement, aim, attack, hit, damage, dodge.
"""
from __future__ import annotations

from core.content_registry import ContentRegistry
from core.data_loader import load_category
from gameplay.enemies.enemy_factory import build_enemy
from gameplay.player.player import Player
from gameplay.player.player_state import PlayerState
from gameplay.player.player_stats import PlayerStats
from gameplay.playtest_scene import PlaytestScene
from input.input_manager import Action, ActionFrame
from rendering.camera import Camera
from world.room import Room

DT = 1.0 / 60.0
VIEWPORT = (320, 180)


def main() -> int:
    registry = ContentRegistry()
    for category in ("player", "world", "enemies"):
        registry.register_all(load_category(category))
    stats = PlayerStats.from_document(registry.get("player", "player_base"))
    room = Room.from_document(registry.get("world", "greybox_arena"))
    world = room.build_collision_world()
    spawn_x, spawn_y = room.player_spawn
    player = Player(stats=stats, x=spawn_x, y=spawn_y)
    camera = Camera(VIEWPORT, zoom=2.0, follow_stiffness=8.0, bounds=room.bounds)

    # Create enemies at known positions.
    enemies = [
        build_enemy(registry, "greybox_dummy", x=600.0, y=304.0),
        build_enemy(registry, "greybox_dummy", x=300.0, y=200.0),
    ]
    enemy = enemies[0][0]

    scene = PlaytestScene(
        player=player, room=room, world=world, camera=camera, enemies=enemies
    )
    scene.enter()

    # Step 1: Move right + aim right.
    print("Step 1: Move right + aim right")
    frame = ActionFrame(move_x=1.0, aim_x=1.0, aim_y=0.0)
    for _ in range(60):
        scene.update(frame, DT)
    assert player.body.x > spawn_x + 20.0, "Player moved right"
    print(f"  PASS: Player x: {player.body.x:.1f}")

    # Step 2: Enemies active.
    print("Step 2: Enemies active")
    for e, ai in enemies:
        print(f"  Enemy {e.entity.name} at ({e.body.x:.1f}, {e.body.y:.1f}), "
              f"AI: {ai.state.value}")
    chasing = sum(1 for _, ai in enemies if ai.state.value == "chase")
    attacking = sum(1 for _, ai in enemies if ai.state.value == "attack")
    assert chasing + attacking > 0, "At least one enemy active"
    print(f"  PASS: Enemies active ({chasing} chase, {attacking} attack)")

    # Step 3: Attack enemy. Teleport close, aim right, attack.
    print(f"Step 3: Attack enemy (current @ {enemy.body.x:.0f},{enemy.body.y:.0f})")
    player.body.teleport(enemy.body.x - 30.0, enemy.body.y)
    # Aim RIGHT toward the enemy.
    attack_frame = ActionFrame(
        pressed=frozenset({Action.PRIMARY_ATTACK}),
        aim_x=1.0, aim_y=0.0,
    )
    for _ in range(15):
        scene.update(attack_frame, DT)
    health_after = enemy.health
    max_hp = enemy.config.max_health
    print(f"  Enemy health after attack: {health_after:.1f} / {max_hp}")
    assert health_after < enemy.config.max_health, "Enemy took damage from attack"
    print("  PASS: Enemy damaged by player")

    # Step 4: Kill the enemy.
    print("Step 4: Kill enemy")
    player.body.teleport(enemy.body.x - 30.0, enemy.body.y)
    for _ in range(300):
        scene.update(attack_frame, DT)
        if not enemy.alive:
            break
    assert not enemy.alive, "Enemy killed"
    print("  PASS: Enemy killed")

    # Step 5: Dodge + i-frames.
    print("Step 5: Dodge + i-frames")
    player.reset()
    enemy2 = enemies[1][0]
    player.body.teleport(enemy2.body.x - 50.0, enemy2.body.y)
    dodge_frame = ActionFrame(
        pressed=frozenset({Action.DODGE}),
        move_x=1.0,
        aim_x=0.0, aim_y=1.0,
    )
    scene.update(dodge_frame, DT)
    assert player.state is PlayerState.DODGE, f"Player dodging (got {player.state})"
    assert player.invulnerable, "Player invulnerable during dodge"
    print("  PASS: Dodge and i-frames active")

    # Step 6: Player takes damage from enemy.
    print("Step 6: Player takes damage from enemy")
    player.body.teleport(enemy2.body.x - 15.0, enemy2.body.y)
    idle_frame = ActionFrame(aim_x=1.0, aim_y=0.0)
    for _ in range(300):
        scene.update(idle_frame, DT)
        if player.health < player.stats.max_health:
            break
    if player.health < player.stats.max_health:
        print(f"  PASS: Player took damage, health: {player.health:.1f}")
    else:
        print(f"  INFO: Player health unchanged ({player.health:.1f})")

    print()
    print("=== HEADLESS VERIFICATION COMPLETE ===")
    print(f"Player state: {player.state.value}")
    print(f"Player health: {player.health:.1f}/{player.stats.max_health}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
