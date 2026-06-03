"""Guard AI: patrol, vision cones, detection states, investigation and combat."""

from __future__ import annotations

import math
import random

from .. import config
from ..systems import combat
from ..systems.detection import (
    Awareness,
    DetectionMeter,
    in_vision_cone,
    line_of_sight,
)
from ..systems.stats import Stats
from .entity import Entity


class GuardState:
    PATROL = "patrol"
    SUSPICIOUS = "suspicious"
    ALERT = "alert"
    SEARCH = "search"


class Guard(Entity):
    def __init__(self, x: float, y: float, waypoints=None):
        super().__init__(x, y, config.GUARD_RADIUS, config.C_GUARD)
        self.stats = Stats(
            max_hp=config.GUARD_BASE_HP,
            hp=config.GUARD_BASE_HP,
            attack=config.GUARD_DAMAGE,
            defense=3,
        )
        self.waypoints = waypoints or [(x, y)]
        self.wp_index = 0
        self.state = GuardState.PATROL
        self.meter = DetectionMeter()
        self.last_seen = None
        self.search_timer = 0.0
        self.attack_cooldown = 0.0
        self.dead = False
        self.is_target = False        # marked assassination target?
        self._assassinated = False    # killed by a stealth strike?
        self._wander_dir = 0.0

    # --- perception -------------------------------------------------------
    def can_see(self, player, world) -> tuple[bool, float]:
        """Return (visible, intensity) for the player this frame."""
        if self.dead or player.noise <= 0.0:
            return False, 0.0
        dist = self.distance_to(player)
        rng = config.GUARD_VISION_RANGE
        if self.state in (GuardState.ALERT, GuardState.SEARCH):
            rng *= 1.15  # heightened awareness once roused
        if not in_vision_cone(self.pos, self.facing, config.GUARD_VISION_FOV, rng, player.pos):
            return False, 0.0
        a = world.tile_at_px(self.x, self.y)
        b = world.tile_at_px(player.x, player.y)
        if not line_of_sight(world.blocks_sight, a, b):
            return False, 0.0
        closeness = 1.0 - min(1.0, dist / rng)
        return True, player.noise * (0.35 + 0.65 * closeness)

    # --- helpers ----------------------------------------------------------
    def _move_towards(self, tx: float, ty: float, speed: float, dt: float, world) -> float:
        dx, dy = tx - self.x, ty - self.y
        d = math.hypot(dx, dy)
        if d > 1e-3:
            self.face_towards(tx, ty)
            step = min(d, speed * dt)
            self.move_collide(dx / d * step, dy / d * step, world.walkable_ground_px)
        return d

    # --- per-frame AI -----------------------------------------------------
    def update(self, dt: float, player, world) -> None:
        if self.dead:
            return
        if self.attack_cooldown > 0:
            self.attack_cooldown -= dt

        visible, intensity = self.can_see(player, world)
        awareness = self.meter.update(dt, visible, intensity)
        if visible:
            self.last_seen = player.pos

        if awareness is Awareness.ALERT:
            self._do_alert(dt, player, world, visible)
        elif awareness is Awareness.SUSPICIOUS:
            self._do_suspicious(dt, world)
        else:
            if self.state == GuardState.ALERT and not visible:
                self.state = GuardState.SEARCH
                self.search_timer = 5.0
            if self.state == GuardState.SEARCH:
                self._do_search(dt, world)
            else:
                self._do_patrol(dt, world)

    def _do_patrol(self, dt, world):
        self.state = GuardState.PATROL
        tx, ty = self.waypoints[self.wp_index]
        if self._move_towards(tx, ty, config.GUARD_PATROL_SPEED, dt, world) < 6.0:
            self.wp_index = (self.wp_index + 1) % len(self.waypoints)

    def _do_suspicious(self, dt, world):
        self.state = GuardState.SUSPICIOUS
        if self.last_seen:
            self._move_towards(*self.last_seen, config.GUARD_PATROL_SPEED * 1.2, dt, world)

    def _do_alert(self, dt, player, world, visible):
        self.state = GuardState.ALERT
        dist = self.distance_to(player)
        if dist <= config.GUARD_ATTACK_RANGE:
            self.face_towards(player.x, player.y)
            if self.attack_cooldown <= 0:
                parried = player.blocking and self._player_facing_me(player)
                combat.resolve_attack(self.stats, player.stats, blocking=parried)
                self.attack_cooldown = config.GUARD_ATTACK_COOLDOWN
                # Counter Strike: a timed parry opens the guard to a riposte.
                if parried and getattr(player, "can_counter", False):
                    self.stats.take_damage(self.stats.hp)
                    self.dead = True
        else:
            target = player.pos if visible else (self.last_seen or player.pos)
            self._move_towards(*target, config.GUARD_CHASE_SPEED, dt, world)

    def _do_search(self, dt, world):
        self.state = GuardState.SEARCH
        self.search_timer -= dt
        if self.last_seen and self.distance_to_point(*self.last_seen) > 10:
            self._move_towards(*self.last_seen, config.GUARD_PATROL_SPEED, dt, world)
        else:
            # Look around at the last known position.
            self._wander_dir += dt * 2.0
            self.facing = self._wander_dir
        if self.search_timer <= 0:
            self.state = GuardState.PATROL
            self.last_seen = None
            self.meter.reset()

    def _player_facing_me(self, player) -> bool:
        ang = math.atan2(self.y - player.y, self.x - player.x)
        d = abs((ang - player.facing + math.pi) % (2 * math.pi) - math.pi)
        return d < 1.2

    def distance_to_point(self, x, y) -> float:
        return math.hypot(x - self.x, y - self.y)

    @property
    def vision_color(self):
        return {
            Awareness.UNAWARE: config.C_VISION_CALM,
            Awareness.SUSPICIOUS: config.C_VISION_SUS,
            Awareness.ALERT: config.C_VISION_ALERT,
        }[self.meter.state]
