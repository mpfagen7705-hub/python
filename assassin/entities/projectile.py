"""Arrows fired by archers."""

from __future__ import annotations

import math

from .. import config
from .entity import Entity


class Projectile(Entity):
    def __init__(self, x: float, y: float, angle: float, damage: int):
        super().__init__(x, y, config.PROJECTILE_RADIUS, config.C_ARROW)
        self.vx = math.cos(angle) * config.PROJECTILE_SPEED
        self.vy = math.sin(angle) * config.PROJECTILE_SPEED
        self.facing = angle
        self.damage = damage
        self.alive = True
        self.life = config.PROJECTILE_LIFETIME

    def update(self, dt: float, world, player) -> str:
        """Advance the arrow. Returns 'hit', 'blocked' (wall), or '' (flying)."""
        if not self.alive:
            return ""
        self.life -= dt
        if self.life <= 0:
            self.alive = False
            return ""
        self.x += self.vx * dt
        self.y += self.vy * dt

        c, r = world.tile_at_px(self.x, self.y)
        if world.blocks_sight(c, r):  # thuds into a building
            self.alive = False
            return "blocked"

        # Arrows fly under the rooftops, so a player up high is safe.
        if not player.on_roof and math.hypot(player.x - self.x, player.y - self.y) <= \
                player.radius + self.radius:
            dmg = self.damage
            if player.blocking:
                dmg = max(1, int(dmg * 0.25))
            player.stats.take_damage(dmg)
            self.alive = False
            return "hit"
        return ""
