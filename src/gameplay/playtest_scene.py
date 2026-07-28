"""
Playtest scene: greybox vertical slice with full run lifecycle,
encounter system, rewards, boss, and restart.

Phase 8 integrates:
  - Run lifecycle (RunManager)
  - Room encounter (clear detection, door locking)
  - Reward system (3-choice, data-driven buffs)
  - Boss encounter with phase transitions
  - Death/victory states with restart

Phase 9 adds:
  - BuildState integration (weapon, boons, passives)
  - Weapon-specific attack behavior
  - Boon → BuildState pipeline
"""

from __future__ import annotations

import random

from core.content_registry import ContentRegistry
from core.enums import SceneID
from engine.scene import Scene
from gameplay.bosses.boss_ai import BossAI, BossPhase
from gameplay.builds.ability import AbilityExecutor
from gameplay.builds.boon import BoonData, apply_boon_to_build
from gameplay.builds.weapon import WeaponData
from gameplay.combat.attack import AttackData
from gameplay.combat.combat_system import (
    CombatEntity,
    CombatSystem,
)
from gameplay.combat.damage import DamageInstance
from gameplay.combat.encounter import RoomEncounter
from gameplay.enemies.enemy import Enemy
from gameplay.enemies.enemy_ai import SimpleAI
from gameplay.enemies.enemy_factory import build_boss, build_enemy
from gameplay.player.aim_controller import AimController
from gameplay.player.player import Player
from gameplay.player.player_controller import PlayerController
from gameplay.player.player_state import PlayerState
from gameplay.roguelike.run import RunManager
from input.input_manager import Action, ActionFrame
from physics.collision import AABB, CollisionWorld
from rendering.camera import Camera
from rendering.renderer import Color, Renderer
from utils.logger import get_logger
from world.room import Room
from world.stage_manager import StageManager

_logger = get_logger(__name__)

_FLOOR_COLOR: Color = (34, 34, 40)
_WALL_COLOR: Color = (92, 92, 112)
_ATTACK_HITBOX_COLOR: Color = (255, 120, 50)
_ENEMY_COLOR: Color = (200, 60, 60)
_ENEMY_ATTACK_COLOR: Color = (255, 80, 80)
_ENEMY_HURTBOX_ALPHA: Color = (200, 60, 60)
_HEALTH_BAR_BG: Color = (50, 50, 50)
_HEALTH_BAR_FG: Color = (80, 200, 80)
_HEALTH_BAR_WIDTH = 24.0
_HEALTH_BAR_HEIGHT = 3.0
_HEALTH_BAR_ENEMY_Y_OFFSET = 20.0
_BOSS_COLOR: Color = (180, 60, 200)
_BOSS_ATTACK_COLOR: Color = (200, 80, 255)
_BOSS_HURTBOX_COLOR: Color = (180, 60, 200)
_BOSS_HEALTH_BAR_WIDTH = 80.0
_BOSS_HEALTH_BAR_HEIGHT = 6.0
_BOSS_HEALTH_BAR_Y_OFFSET = 40.0
_PHASE_2_COLOR: Color = (255, 60, 60)
_REWARD_COLORS: list[Color] = [
    (200, 80, 80),
    (80, 160, 200),
    (80, 200, 100),
]

_STATE_COLORS: dict[PlayerState, Color] = {
    PlayerState.IDLE: (190, 190, 215),
    PlayerState.MOVE: (150, 195, 250),
    PlayerState.DODGE: (250, 225, 130),
    PlayerState.HIT: (245, 120, 120),
    PlayerState.DEAD: (90, 90, 90),
}
_INVULNERABLE_TINT: Color = (255, 255, 255)

PROTOTYPE_WEAPONS = ["warrior_sword", "warrior_spear", "warrior_axe"]


def _fallback_enemy_spawns(room: Room) -> list[tuple[float, float]]:
    cx, cy = room.width / 2.0, room.height / 2.0
    return [
        (cx + 160.0, cy - 60.0),
        (cx + 160.0, cy + 60.0),
        (cx + 260.0, cy),
    ]


class PlaytestScene(Scene):
    """Greybox vertical slice: full run lifecycle, combat, rewards, boss, restart."""

    scene_id = SceneID.DUNGEON

    def __init__(
        self,
        player: Player,
        room: Room,
        world: CollisionWorld,
        camera: Camera,
        registry: ContentRegistry | None = None,
        stage_manager: StageManager | None = None,
        enemies: list[tuple[Enemy, SimpleAI]] | None = None,
        controller: PlayerController | None = None,
    ) -> None:
        self.player = player
        self.room = room
        self.world = world
        self.camera = camera
        self._controller = controller or PlayerController()
        self._aim = AimController(screen_to_world=camera.screen_to_world)
        self._combat = CombatSystem(events=None)
        self._registry = registry
        self._enemies: list[tuple[Enemy, SimpleAI]] = enemies or []
        self._boss: Enemy | None = None
        self._boss_ai: BossAI | None = None
        self.stage_completed = False

        self._stage_manager = stage_manager
        if stage_manager is not None:
            stage_manager.on_transition(self._on_room_transition)
            stage_manager.on_stage_complete(self._on_stage_complete)

        self._run = RunManager()
        self._encounter: RoomEncounter = RoomEncounter()
        self._reward_options: list[BoonData] = []
        self._reward_pending = False
        self._is_paused = False
        self._game_over_message = ""

        # Phase 9: weapon choice on first room clear.
        self._pending_weapon_choice: list[str] = []

        # Phase 10: class loadout.
        self._apply_class_loadout("warrior")
        self._temp_ability_hitbox: tuple[AABB, DamageInstance] | None = None
        self._pending_buffs: list[dict] = []
        self._toggle_states: dict[str, bool] = {
            "skill_q": False, "skill_e": False,
            "skill_r": False, "aura": False,
        }

        # Phase B: damage number popups and visual feedback.
        self._damage_numbers: list[dict] = []
        self._enemy_flash_timers: dict[str, float] = {}
        self._enemy_death_fx: dict[str, float] = {}  # enemy_name → timer
        self._temp_knockback_origin: tuple[float, float] | None = None
        self._temp_knockback_force: float = 0.0
        # Track reward state to prevent re-offering on the same room.
        self._reward_offered_in_room: bool = False

        # If enemies were provided directly, activate the encounter.
        if self._enemies:
            total = len(self._enemies) + (1 if self._boss is not None else 0)
            if total > 0:
                self._encounter.activate(total)

    @property
    def enemies(self) -> tuple[tuple[Enemy, SimpleAI], ...]:
        return tuple(self._enemies)

    # -- Build system helpers --

    def _apply_class_loadout(self, class_id: str = "warrior") -> None:
        """Load a class definition and apply its starting loadout."""
        if self._registry is None:
            return
        try:
            doc = self._registry.get("classes", class_id)
        except Exception:
            _logger.warning("Class '%s' not found", class_id)
            return
        # Apply starting weapon.
        weapon_id = str(doc.get("starting_weapon", "warrior_sword"))
        self._apply_weapon_to_player(weapon_id)

        # Apply starting abilities.
        abilities = doc.get("starting_abilities", {})
        for slot, ability_id in abilities.items():
            if slot in ("skill_1", "skill_2", "ultimate", "aura"):
                self._run.build.ability_ids.append(ability_id)

        self._apply_abilities_to_player()

        # Apply starting passives.
        passives = doc.get("starting_passives", [])
        for pid in passives:
            if pid not in self._run.build.passive_ids:
                self._run.build.passive_ids.append(pid)

        self._apply_passives_to_player()
        self._apply_build_to_player()
        _logger.info("Applied class loadout: %s", class_id)

    def _apply_weapon_to_player(self, weapon_id: str) -> None:
        """Equip a weapon: update build state and player attack."""
        if self._registry is None:
            return
        try:
            doc = self._registry.get("weapons", weapon_id)
            WeaponData.from_document(doc)  # validate it loads
        except Exception:
            _logger.warning("Weapon '%s' not found, using defaults", weapon_id)
            return

        self._run.build.weapon_id = weapon_id
        self._reapply_weapon()

    def _reapply_weapon(self) -> None:
        """Re-apply current weapon + upgrades from build state."""
        if self._registry is None:
            return
        weapon_id = self._run.build.weapon_id
        if weapon_id == "unarmed":
            return
        try:
            doc = self._registry.get("weapons", weapon_id)
            weapon = WeaponData.from_document(doc)
        except Exception:
            _logger.warning("Weapon '%s' missing", weapon_id)
            return

        base_attack = AttackData.from_document(
            self._registry.get("combat", weapon.attack_ref)
        )
        # Apply weapon modifiers.
        modified = weapon.apply_to_attack(base_attack)

        # Apply weapon upgrades.
        upgrades = self._run.build.weapon_upgrades
        from dataclasses import replace
        if upgrades:
            dmg_bonus = upgrades.get("damage", 0.0)
            spd_bonus = upgrades.get("attack_speed", 0.0)
            reach_bonus = upgrades.get("reach", 0.0)
            spread_bonus = upgrades.get("spread", 0.0)
            if dmg_bonus:
                from dataclasses import replace
                modified = replace(modified, damage=modified.damage * (1.0 + dmg_bonus))
            if spd_bonus:
                modified = replace(modified, cooldown=modified.cooldown / (1.0 + spd_bonus))
            if reach_bonus:
                modified = replace(modified, hitbox_reach=modified.hitbox_reach * (1.0 + reach_bonus))  # noqa: E501
            if spread_bonus:
                modified = replace(modified, hitbox_spread=modified.hitbox_spread * (1.0 + spread_bonus))  # noqa: E501

        self.player.attack_executor = self.player.attack_executor.__class__(modified)
        _logger.info("Re-applied weapon with upgrades: %s", weapon_id)

    def _apply_abilities_to_player(self) -> None:
        """Load abilities from BuildState into player's ability slots."""
        if self._registry is None:
            return
        slot_order = ["skill_q", "skill_e", "skill_r", "aura"]
        # Map human-readable slot names to executor keys.
        slot_to_key = {
            "skill_q": "skill_q",
            "skill_e": "skill_e",
            "skill_r": "skill_r",
            "aura": "aura",
        }
        for i, ability_id in enumerate(self._run.build.ability_ids):
            if i >= 4:
                break
            slot = slot_order[i]
            try:
                doc = self._registry.get("abilities", ability_id)
                from gameplay.builds.ability import AbilityData, AbilityExecutor
                ad = AbilityData.from_document(doc)
                slot_key = slot_to_key.get(slot, "")
                if slot_key and slot_key in self.player.ability_executors:
                    self.player.ability_executors[slot_key] = AbilityExecutor(ad)
                    _logger.info("Applied ability '%s' to slot %s", ability_id, slot_key)
            except Exception as exc:
                _logger.warning("Failed to load ability '%s': %s", ability_id, exc)

    def _apply_passives_to_player(self) -> None:
        """Apply passive modifiers from BuildState."""
        if self._registry is None:
            return
        build = self._run.build
        for pid in build.passive_ids:
            try:
                doc = self._registry.get("passives", pid)
                from gameplay.builds.passive import PassiveData
                passive = PassiveData.from_document(doc)
                for mod in passive.modifiers:
                    # Check for conditional passives.
                    condition = getattr(mod, 'condition', '')
                    if condition:
                        build.register_conditional({
                            "condition": condition,
                            "value": mod.value,
                            "stat": mod.stat,
                            "_active": False,
                            "pid": pid,
                        })
                    else:
                        tag_str = next(iter(mod.tags)) if mod.tags else ""
                        build.apply_passive_modifier(
                            mod.stat, mod.value, mod.is_percent, tag_str
                        )
            except Exception as exc:
                _logger.warning("Failed to apply passive '%s': %s", pid, exc)

    def _apply_build_to_player(self) -> None:
        """Apply current BuildState modifiers to the player."""
        build = self._run.build

        # Apply move speed.
        base_speed = self.player.stats.move_speed
        self.player.stats = self._patch_stats(  # type: ignore[assignment]
            self.player.stats,
            move_speed=build.total_speed_for(base_speed),
        )

        # Apply max health bonus.
        if build.max_health_bonus > 0:
            self.player.stats = self._patch_stats(  # type: ignore[assignment]
                self.player.stats,
                max_health=self.player.stats.max_health + build.max_health_bonus,
            )
            self.player.health += build.max_health_bonus

    def _patch_stats(self, stats: object, **kwargs: object) -> object:
        from dataclasses import replace  # noqa: F811

        # mypy workaround: replace works at runtime on dataclasses
        return replace(stats, **kwargs)  # type: ignore

    def _update_stat(self, stats: object, **kwargs: object) -> object:
        """Update a player stat field by returning a new stats object."""
        result = self._patch_stats(stats, **kwargs)
        return result

    # -- Transitions --

    def _on_room_transition(self, new_room: Room, sx: float, sy: float) -> None:
        self.room = new_room
        self.world = new_room.build_collision_world()
        self.player.body.teleport(sx, sy)
        self.camera.center_on(sx, sy)
        self.camera.set_bounds(self.room.bounds)
        # Create fresh encounter BEFORE spawning enemies so
        # _spawn_room_enemies can activate it.
        self._encounter = RoomEncounter()
        self._spawn_room_enemies()
        self._reward_pending = False
        self._reward_offered_in_room = False
        self._pending_buffs.clear()
        self._damage_numbers.clear()
        self._enemy_flash_timers.clear()
        self._enemy_death_fx.clear()
        self._toggle_states.update({"skill_q": False, "skill_e": False, "skill_r": False, "aura": False})  # noqa: E501
        # Reset toggle executors.
        for executor in self.player.ability_executors.values():
            executor.state.toggle_on = False

        # Re-apply build state on transition.
        self._reapply_weapon()
        self._apply_build_to_player()

        if new_room.kind == "boss":
            self._run.start_boss()

    def _on_stage_complete(self) -> None:
        self.stage_completed = True
        _logger.info("Stage complete!")

    def _spawn_room_enemies(self) -> None:
        self._enemies.clear()
        self._boss = None
        self._boss_ai = None
        if self._registry is None or self._stage_manager is None:
            return
        encounter = self._stage_manager.current_floor.encounters.get(
            self.room.room_id, ()
        )
        if not encounter:
            return
        spawns = list(self.room.enemy_spawns) or _fallback_enemy_spawns(self.room)
        idx = 0
        for eid, count in encounter:
            if count == 1 and eid == "first_boss":
                boss_primary = AttackData.from_document(
                    self._registry.get("combat", "boss_primary_attack")
                )
                boss_aoe = AttackData.from_document(
                    self._registry.get("combat", "boss_aoe_attack")
                )
                bx, by = spawns[idx % len(spawns)]
                enemy, boss_ai = build_boss(
                    self._registry, eid, x=bx, y=by,
                    primary_attack=boss_primary, aoe_attack=boss_aoe,
                )
                self._boss = enemy
                self._boss_ai = boss_ai
                idx += 1
            else:
                for _ in range(count):
                    x, y = spawns[idx % len(spawns)]
                    self._enemies.append(build_enemy(self._registry, eid, x=x, y=y))
                    idx += 1
        total = len(self._enemies) + (1 if self._boss is not None else 0)
        if total > 0:
            self._encounter.activate(total)

    def _restart_run(self) -> None:
        self.player.reset()
        self._run.reset()
        # Re-apply class loadout after reset.
        self._apply_class_loadout("warrior")
        self._pending_buffs.clear()
        self._game_over_message = ""
        self._pending_weapon_choice = []
        self._damage_numbers.clear()
        self._enemy_flash_timers.clear()
        self._enemy_death_fx.clear()
        self._toggle_states.update({"skill_q": False, "skill_e": False, "skill_r": False, "aura": False})  # noqa: E501
        for executor in self.player.ability_executors.values():
            executor.state.toggle_on = False
        self._temp_ability_hitbox = None
        if self._stage_manager is not None:
            self._stage_manager.start()
            start = self._stage_manager.current_room
            if start is not None:
                self.room = start
                self.world = start.build_collision_world()
                self.player.body.teleport(*start.player_spawn)
                self.camera.center_on(*start.player_spawn)
                self.camera.set_bounds(self.room.bounds)
                self._spawn_room_enemies()
        self._encounter = RoomEncounter()
        self._reward_options = []
        self._reward_pending = False
        self._reward_offered_in_room = False
        self.stage_completed = False
        self._pending_buffs.clear()

    def _handle_reward_selection(self, frame: ActionFrame) -> None:
        """Select reward based on keyboard aim direction (1/2/3)."""
        # Weapon choice.
        if self._pending_weapon_choice:
            idx = self._weapon_choice_index(frame)
            if idx >= 0 and idx < len(self._pending_weapon_choice):
                weapon_id = self._pending_weapon_choice[idx]
                self._apply_weapon_to_player(weapon_id)
                self._pending_weapon_choice = []
                self._reward_pending = False
            return

        if not self._reward_options:
            self._reward_pending = False
            return
        idx = -1
        if frame.aim_x < -0.5:
            idx = 0
        elif frame.aim_y > 0.5 or frame.aim_y < -0.5:
            idx = 1
        elif frame.aim_x > 0.5:
            idx = 2
        if idx >= 0 and idx < len(self._reward_options):
            boon = self._reward_options[idx]
            apply_boon_to_build(boon, self._run.build)
            self._run.state.rewards_collected.append(boon.id)
            self._reward_options = []
            self._reward_pending = False
            # Re-apply all build systems.
            self._reapply_weapon()
            self._apply_abilities_to_player()
            self._apply_passives_to_player()
            self._apply_build_to_player()
            _logger.info("Applied reward: %s", boon.name)

    def _weapon_choice_index(self, frame: ActionFrame) -> int:
        """Map aim direction to weapon choice index."""
        if frame.aim_x < -0.5:
            return 0
        elif frame.aim_y > 0.5 or frame.aim_y < -0.5:
            return 1
        elif frame.aim_x > 0.5:
            return 2
        return -1

    def _generate_boon_options(self, count: int = 3) -> list[BoonData]:
        """Generate random boon options from registry."""
        if self._registry is None:
            return []
        try:
            all_boons = self._registry.all("boons")
            if not all_boons:
                return []
            selected = random.sample(all_boons, min(count, len(all_boons)))
            return [BoonData.from_document(doc) for doc in selected]
        except Exception:
            return []

    def _update_boss(self, dt: float) -> None:
        if self._boss is None or self._boss_ai is None:
            return
        if not self._boss.alive:
            return
        self._boss_ai.update(self.player.body.x, self.player.body.y, dt)
        self._boss.update(dt)
        self._boss.integrate(dt)

    def _collect_boss_hitboxes(self) -> list[tuple[str, AABB, DamageInstance]]:
        results: list[tuple[str, AABB, DamageInstance]] = []
        if self._boss is None or self._boss_ai is None or not self._boss.alive:
            return results
        hb = self._boss_ai.get_hitbox_aabb()
        if hb is not None:
            results.append((
                self._boss.entity.name, hb,
                DamageInstance(
                    value=self._boss.attack_executor.data.damage,
                    types=self._boss.attack_executor.data.damage_types,
                    source_layer=self._boss.attack_executor.data.layer,
                ),
            ))
        return results

    def _collect_enemy_hitboxes(self) -> list[tuple[str, AABB, DamageInstance]]:
        results: list[tuple[str, AABB, DamageInstance]] = []
        for enemy, _ai in self._enemies:
            if not enemy.alive:
                continue
            ha = enemy.hitbox_aabb
            if ha is not None:
                results.append((
                    enemy.entity.name, ha,
                    DamageInstance(
                        value=enemy.attack_executor.data.damage,
                        types=enemy.attack_executor.data.damage_types,
                        source_layer=enemy.attack_executor.data.layer,
                    ),
                ))
        return results

    def _is_boss_active(self) -> bool:
        if self._boss is None or self._boss_ai is None:
            return False
        return self._boss.alive and self._boss_ai.alive

    # -- Main update --

    def _process_ability_effects(self, dt: float) -> None:
        """Execute effects for any abilities activated this frame.

        Handles:
          - instant: fire once, cooldown (Q/E/R)
          - toggle: apply/remove sustained effect (T/aura)
        """
        if self._registry is None:
            return
        for slot_key, executor in self.player.ability_executors.items():
            is_toggle = executor.data.ability_type == "toggle"

            if is_toggle:
                # Check for toggle state change.
                current_toggle = executor.state.toggle_on
                previous = self._toggle_states.get(slot_key, False)
                if current_toggle == previous:
                    continue  # no change this frame
                self._toggle_states[slot_key] = current_toggle

                if current_toggle:
                    # Toggle ON → apply sustained effect.
                    self._apply_toggle_effect(slot_key, executor, on=True)
                else:
                    # Toggle OFF → remove sustained effect.
                    self._apply_toggle_effect(slot_key, executor, on=False)
            else:
                # Instant: fire once.
                if not executor.state.just_activated:
                    continue
                executor.state.just_activated = False
                self._fire_instant_ability(executor)

    def _fire_instant_ability(self, executor: AbilityExecutor) -> None:
        """Execute one-shot ability effects (dash, aoe, knockback, buff)."""
        effects = executor.data.effects
        if not effects:
            return

        fx, fy = self.player.aim_vector
        length = (fx * fx + fy * fy) ** 0.5
        if length > 0.001:
            fx, fy = fx / length, fy / length
        else:
            fx, fy = 0.0, -1.0

        px, py = self.player.body.x, self.player.body.y

        for effect in effects:
            etype = str(effect.get("type", ""))
            if etype == "dash":
                distance = float(effect.get("distance", 120.0))
                dmg = float(effect.get("damage", 0))
                dmg_types = frozenset(effect.get("damage_types", ["physical"]))
                self.player.body.x += fx * distance
                self.player.body.y += fy * distance
                self.camera.center_on(self.player.body.x, self.player.body.y)
                if dmg > 0:
                    self._temp_ability_hitbox = (
                        AABB(px + fx * distance * 0.3 - 20.0,
                             py + fy * distance * 0.3 - 12.0, 40.0, 24.0),
                        DamageInstance(value=dmg, types=dmg_types, source_layer="player_hitbox",
                                       knockback=(fx * 200.0, fy * 200.0)),
                    )
            elif etype == "aoe":
                range_val = float(effect.get("range", 60.0))
                dmg = float(effect.get("damage", 0))
                if dmg > 0:
                    self._temp_ability_hitbox = (
                        AABB(px - range_val, py - range_val, range_val * 2, range_val * 2),
                        DamageInstance(value=dmg, types=frozenset(effect.get("damage_types", ["physical"])), source_layer="player_hitbox"),  # noqa: E501
                    )
            elif etype == "knockback":
                range_val = float(effect.get("range", 60.0))
                dmg = float(effect.get("damage", 0))
                if dmg > 0:
                    # Radial outward knockback from player position.
                    self._temp_ability_hitbox = (
                        AABB(px - range_val, py - range_val, range_val * 2, range_val * 2),
                        DamageInstance(value=dmg, types=frozenset(effect.get("damage_types", ["physical"])), source_layer="player_hitbox",  # noqa: E501
                                       knockback=(0.0, 0.0)),  # radial — computed per-target in hit resolution  # noqa: E501
                    )
                    self._temp_knockback_origin = (px, py)
                    self._temp_knockback_force = 300.0
            elif etype == "buff":
                # Instant timed buff (e.g. Shield Bash temp armor).
                stat = str(effect.get("stat", "damage"))
                value = float(effect.get("value", 0.0))
                duration = float(effect.get("duration", 3.0))
                is_pct = bool(effect.get("is_percent", False))
                if stat == "damage" and is_pct:
                    self._pending_buffs.append({
                        "slot": "attack_executor",
                        "original_damage": self.player.attack_executor.data.damage,
                        "buffed_damage": self.player.attack_executor.data.damage * (1.0 + value),
                        "timer": duration,
                    })
                    from dataclasses import replace
                    buffed = replace(self.player.attack_executor.data,
                                     damage=self.player.attack_executor.data.damage * (1.0 + value))
                    self.player.attack_executor = self.player.attack_executor.__class__(buffed)
                    self._add_damage_number(px, py - 30.0,
                                            f"+{int(value * 100)}% ATK", (200, 200, 80))
                    _logger.info("Buff: damage +%.0f%% for %.1fs", value * 100, duration)
                elif stat == "defense":
                    # Track "defense" dummy buff (visual-only placeholder).
                    self._add_damage_number(px, py - 30.0,
                                            "DEF+", (80, 180, 255))

    def _apply_toggle_effect(self, slot_key: str, executor: AbilityExecutor, on: bool) -> None:
        """Apply or remove a toggle/sustained effect."""
        effects = executor.data.effects
        for effect in effects:
            etype = str(effect.get("type", ""))
            stat = str(effect.get("stat", "damage"))
            value = float(effect.get("value", 0.0))
            is_pct = bool(effect.get("is_percent", False))

            if on and etype == "buff":
                # Apply buff.
                if stat == "damage" and is_pct:
                    old = self.player.attack_executor.data.damage
                    from dataclasses import replace
                    buffed = replace(self.player.attack_executor.data, damage=old * (1.0 + value))
                    self.player.attack_executor = self.player.attack_executor.__class__(buffed)
                    _logger.info("Toggle ON: damage buff active (+%.0f%%)", value * 100)
            elif not on and etype == "buff":
                # Remove buff — restore original.
                if stat == "damage" and is_pct:
                    original = self.player.attack_executor.data.damage / (1.0 + value)
                    from dataclasses import replace
                    restored = replace(self.player.attack_executor.data, damage=original)
                    self.player.attack_executor = self.player.attack_executor.__class__(restored)
                    _logger.info("Toggle OFF: damage buff removed")

    def update(self, frame: ActionFrame, dt: float) -> None:
        if self._run.ended:
            if Action.PRIMARY_ATTACK in frame.pressed:
                self._restart_run()
            return

        # Weapon choice pending.
        if self._pending_weapon_choice:
            self._handle_reward_selection(frame)
            return

        # Reward selection.
        if self._reward_pending:
            self._handle_reward_selection(frame)
            return

        aim = self._aim.resolve(frame, self.player.body.x, self.player.body.y)
        self.player.set_aim(aim.direction[0], aim.direction[1])
        intent = self._controller.build_intent(frame)
        self.player.update(intent, self.world, dt)

        # Process ability effects (dash, aoe, knockback, buff).
        self._process_ability_effects(dt)

        # Update conditional modifiers (Fury below 50% HP).
        self._run.build.update_conditionals(self.player.health, self.player.stats.max_health)

        # Tick pending buffs.
        expired = []
        for i, buf in enumerate(self._pending_buffs):
            buf["timer"] -= dt
            if buf["timer"] <= 0:
                expired.append(i)
                if buf["slot"] == "attack_executor":
                    from dataclasses import replace
                    restored = replace(
                        self.player.attack_executor.data,
                        damage=buf["original_damage"],
                    )
                    self.player.attack_executor = self.player.attack_executor.__class__(restored)
                    _logger.info("Buff expired: damage restored to %.1f", buf["original_damage"])
        for i in reversed(expired):
            self._pending_buffs.pop(i)

        for enemy, ai in self._enemies:
            if not enemy.alive:
                continue
            ai.update(self.player.body.x, self.player.body.y, dt)
            enemy.update(dt)
            enemy.integrate(dt)

        self._update_boss(dt)

        # Player hitbox.
        player_hitboxes: list[tuple[str, AABB, DamageInstance]] = []
        if self.player.attack_executor.hitbox_active():
            ax, ay = self.player.aim_vector
            hb = self.player.attack_executor.hitbox_for(
                self.player.body.x, self.player.body.y, facing_x=ax, facing_y=ay,
            )
            if hb is not None:
                player_hitboxes.append((
                    "player", hb,
                    DamageInstance(
                        value=self.player.attack_executor.data.damage,
                        types=self.player.attack_executor.data.damage_types,
                        source_layer=self.player.attack_executor.data.layer,
                    ),
                ))

        # Ability hitbox (dash, aoe, knockback effects).
        if self._temp_ability_hitbox is not None:
            hb, dmg = self._temp_ability_hitbox
            player_hitboxes.append(("ability", hb, dmg))
            self._temp_ability_hitbox = None

        all_enemy_hitboxes = self._collect_enemy_hitboxes() + self._collect_boss_hitboxes()

        # Resolve player hits.
        if player_hitboxes and (self._enemies or self._boss is not None):
            ents = []
            for e, _ in self._enemies:
                if e.alive:
                    ents.append(self._make_combat_entity(e.entity.name, e.body.x, e.body.y, e.hurtbox, e.alive, e, e.invuln_service))  # noqa: E501
            if self._boss is not None and self._boss.alive:
                ents.append(self._make_combat_entity(
                    self._boss.entity.name, self._boss.body.x, self._boss.body.y,
                    self._boss.hurtbox, self._boss.alive, self._boss, self._boss.invuln_service,
                ))
            hits = self._combat.resolve_hits(player_hitboxes, ents)
            kb_origin = self._temp_knockback_origin
            kb_force = self._temp_knockback_force
            self._temp_knockback_origin = None
            self._temp_knockback_force = 0.0
            for hit in hits:
                if hit.result.dealt > 0:
                    hx, hy = self._hit_target_pos(hit.target_id)
                    self._add_damage_number(hx, hy, f"-{int(hit.result.dealt)}", (255, 255, 200))
                    # Mark enemy for damage flash.
                    self._enemy_flash_timers[hit.target_id] = 0.1
                    if hit.instance.knockback != (0.0, 0.0):
                        # Apply collision-aware knockback to hit enemy.
                        self._apply_knockback(hit.target_id, hit.instance)
                    elif kb_origin is not None and kb_force > 0.0:
                        # Radial knockback from knockback_origin.
                        self._apply_radial_knockback(hit.target_id, kb_origin, kb_force)
                if hit.result.killed:
                    self._encounter.on_enemy_died()
                    self._run.on_enemy_kill()
                    # Record death FX for this enemy.
                    self._enemy_death_fx[hit.target_id] = 0.5
                    # Spawn death text popup.
                    self._add_damage_number(
                        *self._hit_target_pos(hit.target_id), "KILL!", (255, 100, 100),
                    )

        # Resolve enemy hits.
        if all_enemy_hitboxes and self.player.alive:
            pe = [CombatEntity(
                id="player", body_x=self.player.body.x, body_y=self.player.body.y,
                hurtbox_aabb=self.player.hurtbox.box_at(self.player.body.x, self.player.body.y),
                vulnerable=self.player.alive, damage_target=self.player,
                invuln_service=self.player.invuln_service,
            )]
            hits = self._combat.resolve_hits(all_enemy_hitboxes, pe)
            for hit in hits:
                if hit.result.dealt > 0:
                    self.player.set_hitstun(0.15)
                    self.player.on_hit(0.15)
                    if self.player.health <= 0.0:
                        self.player.die()
                        self._run.on_death()

        # Room cleared → reward or weapon choice.
        if self._encounter.cleared and not self._reward_pending and self._boss is None and not self._reward_offered_in_room:  # noqa: E501
            self._run.on_room_clear()
            self._reward_offered_in_room = True
            # On first room clear (unarmed), offer weapon choice.
            if self._run.build.weapon_id == "unarmed" and not self._pending_weapon_choice:
                self._pending_weapon_choice = list(PROTOTYPE_WEAPONS)
                self._reward_pending = True
            else:
                self._reward_options = self._generate_boon_options(3)
                if self._reward_options:
                    self._reward_pending = True

        # Boss cleared.
        if self._encounter.cleared and not self._reward_pending and self._boss is not None and not self._boss.alive and self.room.kind == "boss":  # noqa: E501
            self._run.on_room_clear()
            self.stage_completed = True
            self._on_stage_complete()

        if self.player.state is PlayerState.DEAD and not self._run.ended:
            self._run.on_death()

        if self.stage_completed and not self._run.ended:
            self._run.on_victory()

        if self._stage_manager is not None and not self._reward_pending and not self._is_boss_active():  # noqa: E501
            door = self._stage_manager.check_transition(self.player.body.box)
            if door is not None:
                self._stage_manager.transition(door)

        self.camera.follow(self.player.body.x, self.player.body.y, dt)

        # Tick damage numbers.
        expired_nums = []
        for i, dn in enumerate(self._damage_numbers):
            dn["timer"] -= dt
            dn["wy"] += dn["vy"] * dt
            if dn["timer"] <= 0:
                expired_nums.append(i)
        for i in reversed(expired_nums):
            self._damage_numbers.pop(i)

        # Tick flash timers and death FX.
        expired_flashes = []
        for eid, timer in self._enemy_flash_timers.items():
            self._enemy_flash_timers[eid] = timer - dt
            if timer - dt <= 0:
                expired_flashes.append(eid)
        for eid in expired_flashes:
            self._enemy_flash_timers.pop(eid, None)

        expired_death = []
        for eid, timer in self._enemy_death_fx.items():
            self._enemy_death_fx[eid] = timer - dt
            if timer - dt <= 0:
                expired_death.append(eid)
        for eid in expired_death:
            self._enemy_death_fx.pop(eid, None)

    def _make_combat_entity(self, eid, bx, by, hurtbox, vulnerable, target, invuln):
        return CombatEntity(
            id=eid, body_x=bx, body_y=by,
            hurtbox_aabb=hurtbox.box_at(bx, by),
            vulnerable=vulnerable, damage_target=target,
            invuln_service=invuln,
        )

    def _add_damage_number(self, wx: float, wy: float, text: str, color: Color = (255, 255, 200)) -> None:  # noqa: E501
        """Add a floating damage number at a world position."""
        self._damage_numbers.append({
            "text": text,
            "wx": wx,
            "wy": wy,
            "color": color,
            "timer": 1.2,
            "vy": -30.0,  # float upward pixels/sec
        })

    def _apply_knockback(self, target_id: str, instance: DamageInstance) -> None:
        """Apply collision-aware knockback to an enemy by id."""
        for e, _ai in self._enemies:
            if e.entity.name == target_id and e.alive:
                kx, ky = instance.knockback
                if kx != 0.0 or ky != 0.0:
                    self._push_entity_with_collision(e, kx * 0.01, ky * 0.01)
                break
        if self._boss is not None and self._boss.entity.name == target_id and self._boss.alive:
            kx, ky = instance.knockback
            if kx != 0.0 or ky != 0.0:
                self._push_entity_with_collision(self._boss, kx * 0.01, ky * 0.01)

    def _apply_radial_knockback(self, target_id: str, origin: tuple[float, float], force: float) -> None:  # noqa: E501
        """Apply radial outward knockback from an origin point."""
        for e, _ai in self._enemies:
            if e.entity.name == target_id and e.alive:
                dx = e.body.x - origin[0]
                dy = e.body.y - origin[1]
                length = (dx * dx + dy * dy) ** 0.5
                if length > 1.0:
                    self._push_entity_with_collision(e, dx / length * force * 0.01, dy / length * force * 0.01)  # noqa: E501
                break
        if self._boss is not None and self._boss.entity.name == target_id and self._boss.alive:
            dx = self._boss.body.x - origin[0]
            dy = self._boss.body.y - origin[1]
            length = (dx * dx + dy * dy) ** 0.5
            if length > 1.0:
                self._push_entity_with_collision(self._boss, dx / length * force * 0.01, dy / length * force * 0.01)  # noqa: E501

    def _push_entity_with_collision(self, entity: Enemy, vx: float, vy: float) -> None:
        """Push an entity with collision awareness — stop at walls."""
        test_x = entity.body.x + vx
        test_y = entity.body.y + vy
        test_box = AABB(test_x, test_y, entity.body.width, entity.body.height)
        blocked = False
        for solid in self.room.solids:
            if test_box.intersects(solid):
                blocked = True
                break
        if not blocked:
            entity.body.x = test_x
            entity.body.y = test_y

    def _hit_target_pos(self, target_id: str) -> tuple[float, float]:
        """Get world position of a target by name."""
        for e, _ai in self._enemies:
            if e.entity.name == target_id:
                return (e.body.x, e.body.y)
        if self._boss is not None and self._boss.entity.name == target_id:
            return (self._boss.body.x, self._boss.body.y)
        return (0.0, 0.0)

    def render(self, renderer: Renderer) -> None:
        renderer.draw_rect(self.camera.screen_rect(self.room.bounds), _FLOOR_COLOR)
        for solid in self.room.solids:
            renderer.draw_rect(self.camera.screen_rect(solid), _WALL_COLOR)

        for enemy, _ai in self._enemies:
            # Death FX (show fading marker for dead enemies).
            death_timer = self._enemy_death_fx.get(enemy.entity.name, 0.0)
            if death_timer > 0:
                ratio = max(0.1, death_timer / 0.5)
                size = int(enemy.body.width * ratio)
                sx, sy = self.camera.world_to_screen(enemy.body.x, enemy.body.y)
                offset = size // 2
                renderer.draw_rect((sx - offset, sy - offset, size, size), (255, 50, 50))
                cross_size = int(size * 0.7)
                renderer.draw_rect((sx - cross_size, sy - 1, cross_size * 2, 3), (255, 150, 50))
                renderer.draw_rect((sx - 1, sy - cross_size, 3, cross_size * 2), (255, 150, 50))
                continue

            if not enemy.alive:
                continue
            # Damage flash.
            flash_color = (255, 255, 255) if self._enemy_flash_timers.get(enemy.entity.name, 0) > 0 else _ENEMY_COLOR  # noqa: E501
            renderer.draw_rect(self.camera.screen_rect(enemy.body.box), flash_color)
            ha = enemy.hurtbox.box_at(enemy.body.x, enemy.body.y)
            renderer.draw_rect(self.camera.screen_rect(ha), _ENEMY_HURTBOX_ALPHA)
            ratio = enemy.health / enemy.config.max_health
            bx = enemy.body.x - _HEALTH_BAR_WIDTH / 2.0
            by = enemy.body.y - _HEALTH_BAR_ENEMY_Y_OFFSET
            bg = AABB(bx, by, _HEALTH_BAR_WIDTH, _HEALTH_BAR_HEIGHT)
            renderer.draw_rect(self.camera.screen_rect(bg), _HEALTH_BAR_BG)
            if ratio > 0.0:
                fg = AABB(bx, by, _HEALTH_BAR_WIDTH * ratio, _HEALTH_BAR_HEIGHT)
                renderer.draw_rect(self.camera.screen_rect(fg), _HEALTH_BAR_FG)
            eha = enemy.hitbox_aabb
            if eha is not None:
                renderer.draw_rect(self.camera.screen_rect(eha), _ENEMY_ATTACK_COLOR)

        # Boss.
        if self._boss is not None and self._boss.alive:
            boss_color = _BOSS_COLOR
            if self._boss_ai is not None and self._boss_ai.phase is BossPhase.PHASE_2:
                boss_color = _PHASE_2_COLOR
            renderer.draw_rect(self.camera.screen_rect(self._boss.body.box), boss_color)
            ha = self._boss.hurtbox.box_at(self._boss.body.x, self._boss.body.y)
            renderer.draw_rect(self.camera.screen_rect(ha), _BOSS_HURTBOX_COLOR)
            ratio = self._boss.health / self._boss.config.max_health
            bx = self._boss.body.x - _BOSS_HEALTH_BAR_WIDTH / 2.0
            by = self._boss.body.y - _BOSS_HEALTH_BAR_Y_OFFSET
            bg = AABB(bx, by, _BOSS_HEALTH_BAR_WIDTH, _BOSS_HEALTH_BAR_HEIGHT)
            renderer.draw_rect(self.camera.screen_rect(bg), _HEALTH_BAR_BG)
            if ratio > 0.0:
                fg = AABB(bx, by, _BOSS_HEALTH_BAR_WIDTH * ratio, _BOSS_HEALTH_BAR_HEIGHT)
                renderer.draw_rect(self.camera.screen_rect(fg), _BOSS_COLOR)
            if self._boss_ai is not None:
                phase_color = _BOSS_COLOR
                if self._boss_ai.phase is BossPhase.PHASE_2:
                    phase_color = _PHASE_2_COLOR
                dot = AABB(bx - 12, by, 6, _BOSS_HEALTH_BAR_HEIGHT)
                renderer.draw_rect(self.camera.screen_rect(dot), phase_color)
            if self._boss_ai is not None:
                hb = self._boss_ai.get_hitbox_aabb()
                if hb is not None:
                    renderer.draw_rect(self.camera.screen_rect(hb), _BOSS_ATTACK_COLOR)

        # Player.
        pose = self.player.animation_pose
        px, py = self.player.body.x, self.player.body.y
        pw, ph = self.player.body.width, self.player.body.height
        color = _STATE_COLORS[pose.state]
        if self.player.invulnerable:
            color = _INVULNERABLE_TINT

        # Draw player as a directional shape: body rectangle + arrow head.
        body_rect = self.camera.screen_rect(self.player.body.box)
        renderer.draw_rect(body_rect, color)

        # Draw an inner border to distinguish from enemies.
        inner = (body_rect[0] + 2, body_rect[1] + 2, body_rect[2] - 4, body_rect[3] - 4)
        inner_color = (
            min(255, color[0] + 40),
            min(255, color[1] + 40),
            min(255, color[2] + 60),
        )
        renderer.draw_rect(inner, inner_color)

        # Facing arrow: 3 stacked rectangles forming a directional arrow.
        fx, fy = pose.facing.vector
        screen_scale = max(1, int(self.camera.zoom * 0.5))
        for step in range(1, 4):
            tip_x = int(px + fx * (ph / 2 + step * 5) - 3)
            tip_y = int(py + fy * (ph / 2 + step * 5) - 3)
            arr_size = max(2, 8 - step * 1)
            sx, sy = self.camera.world_to_screen(tip_x, tip_y)
            renderer.draw_rect((sx, sy, arr_size * screen_scale, arr_size * screen_scale), (255, 255, 255))  # noqa: E501

        # Dodge indicator (small trail when dodging).
        if pose.state is PlayerState.DODGE:
            trail_color = (255, 255, 100)
            for t in range(1, 4):
                tx = int(px - fx * t * 6)
                ty = int(py - fy * t * 6)
                ts = max(1, int(6 - t))
                sx, sy = self.camera.world_to_screen(tx, ty)
                renderer.draw_rect((sx, sy, ts * screen_scale, ts * screen_scale), trail_color)

        # Attack hitbox visualization (debug).
        if self.player.attack_executor.hitbox_active():
            ax, ay = self.player.aim_vector
            hb = self.player.attack_executor.hitbox_for(
                self.player.body.x, self.player.body.y, facing_x=ax, facing_y=ay,
            )
            if hb is not None:
                renderer.draw_rect(self.camera.screen_rect(hb), _ATTACK_HITBOX_COLOR)

        # Damage numbers (world → screen).
        for dn in self._damage_numbers:
            sx, sy = self.camera.world_to_screen(dn["wx"], dn["wy"])
            alpha = max(0.3, min(1.0, dn["timer"] / 0.5))
            r = min(255, int(255 / max(0.3, alpha)))
            g = min(255, int(200 / max(0.3, alpha)))
            b = min(255, int(100 / max(0.3, alpha)))
            renderer.draw_text(dn["text"], int(sx), int(sy), (r, g, b), 14)

        # === HP BAR (top-left, larger) ===
        w, h = renderer.size
        hp_bar_x, hp_bar_y = 20, 20
        hp_bar_w, hp_bar_h = 220, 28
        hp_ratio = max(0.0, min(1.0, self.player.health / self.player.stats.max_health))

        # HP bar background.
        renderer.draw_rect((hp_bar_x, hp_bar_y, hp_bar_w, hp_bar_h), (40, 20, 20))
        # HP bar fill.
        if hp_ratio > 0:
            fill_w = int((hp_bar_w - 4) * hp_ratio)
            hp_fill_color = (80, 220, 80) if hp_ratio > 0.3 else (220, 60, 60) if hp_ratio > 0.15 else (180, 40, 40)  # noqa: E501
            renderer.draw_rect((hp_bar_x + 2, hp_bar_y + 2, fill_w, hp_bar_h - 4), hp_fill_color)
        # HP text.
        hp_text = f"HP {int(self.player.health)}/{int(self.player.stats.max_health)}"
        renderer.draw_text(hp_text, hp_bar_x + 8, hp_bar_y + 6, (255, 255, 255), 14)

        # Dodge charges indicator (below HP bar).
        dodge_info = f"Dodge: {self.player.dodge_charges.current}/{self.player.dodge_charges.max_charges}"  # noqa: E501
        renderer.draw_text(dodge_info, hp_bar_x, hp_bar_y + hp_bar_h + 4, (200, 200, 100), 12)

        # === BUILD INFO (left side, below HP) ===
        bi_y = hp_bar_y + hp_bar_h + 22
        weapon_name = self._run.build.weapon_id.replace("warrior_", "").title() if self._run.build.weapon_id != "unarmed" else "Unarmed"  # noqa: E501
        renderer.draw_text(f"Weapon: {weapon_name}", hp_bar_x, bi_y, (220, 200, 180), 12)

        bi_y += 18
        if self._run.build.passive_ids:
            renderer.draw_text("Passives:", hp_bar_x, bi_y, (180, 220, 200), 12)
            bi_y += 16
            for pid in self._run.build.passive_ids:
                pname = pid.replace("_", " ").title()
                # Look up description from registry.
                pdesc = ""
                if self._registry is not None:
                    try:
                        doc = self._registry.get("passives", pid)
                        pdesc = str(doc.get("description", ""))
                    except Exception:
                        pass
                renderer.draw_text(f"  {pname}", hp_bar_x, bi_y, (200, 220, 210), 12)
                bi_y += 14
                if pdesc:
                    renderer.draw_text(f"  {pdesc}", hp_bar_x, bi_y, (160, 190, 180), 11)
                    bi_y += 14

        bi_y += 18
        # Fury status.
        if self._run.build._fury_active:
            renderer.draw_text("⚡ FURY ACTIVE (+15% DMG)", hp_bar_x, bi_y, (255, 200, 50), 12)

        # === ROOM INFO (below build info) ===
        ri_y = hp_bar_y + hp_bar_h + 88
        room_label = self.room.kind.upper() if self.room.kind else "UNKNOWN"
        renderer.draw_text(f"[ {room_label} ]", hp_bar_x, ri_y, (180, 180, 200), 12)
        if self._stage_manager:
            floor_str = f"Floor {self._stage_manager.floor_index + 1}/{len(self._stage_manager.stage_data.floors)}"  # noqa: E501
            renderer.draw_text(floor_str, hp_bar_x, ri_y + 18, (160, 160, 180), 12)

        # Enemy count.
        alive_count = sum(1 for e, _ in self._enemies if e.alive)
        boss_active = 1 if self._boss is not None and self._boss.alive else 0
        total_alive = alive_count + boss_active
        if total_alive > 0:
            renderer.draw_text(f"Enemies: {total_alive}", hp_bar_x, ri_y + 36, (220, 160, 160), 12)

        # === ABILITY BAR (top-right, large) ===
        slot_w, slot_h = 240, 36
        slot_start_x = w - slot_w - 20
        slot_start_y = 20
        slot_labels = ["Q", "E", "R", "T"]
        slot_keys = ["skill_q", "skill_e", "skill_r", "aura"]
        ability_names = {
            "skill_q": "Charge",
            "skill_e": "Shield Bash",
            "skill_r": "Whirlwind",
            "aura": "War Cry",
        }

        for i, (label, slot_key) in enumerate(zip(slot_labels, slot_keys)):
            exec_ = self.player.ability_executors.get(slot_key)
            if exec_ is None:
                continue
            sx = slot_start_x
            sy = slot_start_y + i * (slot_h + 6)

            # Background slot.
            renderer.draw_rect((sx, sy, slot_w, slot_h), (25, 25, 35))

            # Key label (Q/E/R/T circle).
            key_color = (200, 200, 220)
            renderer.draw_text(f" [{label}] ", sx + 6, sy + 8, key_color, 14)

            # Ability name.
            ability_name = ability_names.get(slot_key, "")
            renderer.draw_text(ability_name, sx + 44, sy + 8, (200, 200, 220), 14)

            # Cooldown / toggle state.
            if exec_.data.ability_type == "toggle":
                if exec_.state.toggle_on:
                    renderer.draw_rect((sx + slot_w - 80, sy + 4, 74, slot_h - 8), (220, 200, 60))
                    renderer.draw_text("ON", sx + slot_w - 62, sy + 8, (255, 255, 200), 14)
                else:
                    renderer.draw_rect((sx + slot_w - 80, sy + 4, 74, slot_h - 8), (50, 50, 50))
                    renderer.draw_text("OFF", sx + slot_w - 62, sy + 8, (150, 150, 150), 14)
            else:
                frac = exec_.ready_fraction
                cd_w = slot_w - 120
                cd_x = sx + 120
                cd_y = sy + 6
                cd_h = slot_h - 12
                renderer.draw_rect((cd_x, cd_y, cd_w, cd_h), (40, 40, 50))
                if frac < 1.0:
                    fill_w = max(2, int(cd_w * frac))
                    # Gradient from blue (just activated) to green (almost ready).
                    fill_color = (60, 80 + int(160 * frac), 200 - int(140 * frac))
                    renderer.draw_rect((cd_x + 1, cd_y + 1, fill_w, cd_h - 2), fill_color)
                    cd_left = exec_.data.cooldown * (1.0 - frac)
                    renderer.draw_text(f"{cd_left:.1f}s", cd_x + cd_w + 6, sy + 8, (160, 200, 255), 12)  # noqa: E501
                else:
                    renderer.draw_rect((cd_x + 1, cd_y + 1, cd_w - 2, cd_h - 2), (60, 200, 60))
                    renderer.draw_text("READY", cd_x + cd_w + 6, sy + 8, (100, 255, 100), 12)

        # Reward overlay.
        if self._reward_pending:
            w, h = renderer.size
            is_weapon_choice = bool(self._pending_weapon_choice)
            if is_weapon_choice:
                options_raw = self._pending_weapon_choice
            else:
                options_raw = self._reward_options
            for i, opt in enumerate(options_raw):
                rx = 60 + i * 180
                ry = h // 3
                rw, rh = 160, 80
                # Reward card background.
                renderer.draw_rect((rx, ry, rw, rh), _REWARD_COLORS[i % 3])
                renderer.draw_rect((rx + 3, ry + 3, rw - 6, rh - 6), (20, 20, 30))
                # Name and description.
                if is_weapon_choice:
                    opt_str = str(opt)
                    label = opt_str.replace("warrior_", "").replace("_", " ").title()
                    desc = ""
                    if self._registry is not None:
                        try:
                            doc = self._registry.get("weapons", opt_str)
                            desc = str(doc.get("description", ""))
                        except Exception:
                            pass
                else:
                    boon: BoonData = opt  # type: ignore
                    label = boon.name
                    desc = boon.description
                renderer.draw_text(label, rx + 8, ry + 8, (220, 220, 230), 14)
                # Description (truncate if too long).
                if desc:
                    if len(desc) > 28:
                        desc = desc[:26] + ".."
                    renderer.draw_text(desc, rx + 8, ry + 26, (160, 160, 180), 11)
                # Choice hint.
                hints = ["← Left", "↓ Down", "Right →"]
                renderer.draw_text(hints[i], rx + 8, ry + 50, (160, 160, 180), 12)

        # Game-over overlay.
        if self._run.ended:
            w, h = renderer.size
            # Full darkness overlay.
            renderer.draw_rect((0, 0, w, h), (0, 0, 0))
            cx, cy = w // 2, h // 3

            if self._run.state.phase.value == "victory":
                # Green panel.
                pw, ph = 360, 160
                renderer.draw_rect((cx - pw // 2, cy - ph // 2, pw, ph), (0, 60, 0))
                renderer.draw_rect((cx - pw // 2 + 2, cy - ph // 2 + 2, pw - 4, ph - 4), (0, 40, 0))
                renderer.draw_text("STAGE COMPLETE!", cx - 120, cy - 30, (100, 255, 100), 22)
                renderer.draw_text("Click to continue", cx - 80, cy + 10, (200, 255, 200), 14)
            elif self._run.state.phase.value == "death":
                # Red panel.
                pw, ph = 360, 160
                renderer.draw_rect((cx - pw // 2, cy - ph // 2, pw, ph), (60, 0, 0))
                renderer.draw_rect((cx - pw // 2 + 2, cy - ph // 2 + 2, pw - 4, ph - 4), (40, 0, 0))
                renderer.draw_text("YOU DIED", cx - 80, cy - 30, (255, 80, 80), 22)
                renderer.draw_text("Click to retry", cx - 70, cy + 10, (255, 200, 200), 14)

            # Stats summary.
            kills = self._run.state.enemies_killed
            rooms = self._run.state.rooms_cleared
            floor_num = self._run.state.current_floor + 1
            stats_text = f"Kills: {kills}  Rooms: {rooms}  Depth: Floor {floor_num}"
            renderer.draw_text(stats_text, cx - 140, cy + 50, (180, 180, 180), 14)
