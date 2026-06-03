"""A camera that smoothly follows a target and converts world <-> screen space."""

from __future__ import annotations

from . import config


class Camera:
    def __init__(self, world):
        self.x = 0.0
        self.y = 0.0
        self.world_w = world.cols * config.TILE
        self.world_h = world.rows * config.TILE

    def follow(self, target, dt: float) -> None:
        # Desired top-left so the target sits centered.
        tx = target.x - config.SCREEN_WIDTH / 2
        ty = target.y - config.SCREEN_HEIGHT / 2
        # Smooth (exponential) follow.
        lerp = min(1.0, 8.0 * dt)
        self.x += (tx - self.x) * lerp
        self.y += (ty - self.y) * lerp
        # Clamp to world bounds.
        self.x = max(0.0, min(self.x, self.world_w - config.SCREEN_WIDTH))
        self.y = max(0.0, min(self.y, self.world_h - config.SCREEN_HEIGHT))

    def to_screen(self, wx: float, wy: float):
        return wx - self.x, wy - self.y
