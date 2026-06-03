"""Shared base for moving, collidable actors."""

from __future__ import annotations

import math

from .. import config


class Entity:
    """A circular actor positioned in world pixel-space."""

    def __init__(self, x: float, y: float, radius: float, color):
        self.x = float(x)
        self.y = float(y)
        self.radius = radius
        self.color = color
        self.facing = 0.0  # radians, 0 == facing right

    @property
    def pos(self):
        return (self.x, self.y)

    def distance_to(self, other) -> float:
        return math.hypot(other.x - self.x, other.y - self.y)

    def face_towards(self, tx: float, ty: float) -> None:
        if (tx, ty) != (self.x, self.y):
            self.facing = math.atan2(ty - self.y, tx - self.x)

    def move_collide(self, dx: float, dy: float, walkable_px) -> None:
        """Move by (dx, dy), sliding along walls using axis-separated checks.

        ``walkable_px(x, y)`` reports whether a world pixel is standable.
        """
        # X axis
        nx = self.x + dx
        if walkable_px(nx + math.copysign(self.radius, dx if dx else 1), self.y) and \
           walkable_px(nx - math.copysign(self.radius, dx if dx else 1), self.y):
            self.x = nx
        # Y axis
        ny = self.y + dy
        if walkable_px(self.x, ny + math.copysign(self.radius, dy if dy else 1)) and \
           walkable_px(self.x, ny - math.copysign(self.radius, dy if dy else 1)):
            self.y = ny
