"""The player-controlled assassin: movement modes, climbing, stealth and skills."""

from __future__ import annotations

import math

from .. import config
from ..systems.skills import SkillTree
from ..systems.stats import Stats
from .entity import Entity


class MoveMode:
    WALK = "walk"
    SPRINT = "sprint"
    CROUCH = "crouch"


class Player(Entity):
    def __init__(self, x: float, y: float):
        super().__init__(x, y, config.PLAYER_RADIUS, config.C_PLAYER)
        self.stats = Stats(
            max_hp=config.PLAYER_BASE_HP,
            hp=config.PLAYER_BASE_HP,
            attack=22,
            defense=5,
            stealth=1.0,
        )
        self.skills = SkillTree()
        self.mode = MoveMode.WALK
        self.on_roof = False
        self.hidden = False  # currently concealed in a haystack
        self.blocking = False

        # Capability flags granted by the skill tree.
        self.can_air_assassinate = False
        self.can_counter = False
        self.fast_climb = False
        self.eagle_vision = False
        self.safe_fall = False

        self._move = (0.0, 0.0)

    # --- input intent -----------------------------------------------------
    def set_intent(self, dx: float, dy: float, mode: str, blocking: bool) -> None:
        self._move = (dx, dy)
        self.mode = mode
        self.blocking = blocking

    @property
    def speed(self) -> float:
        if self.mode == MoveMode.SPRINT:
            base = config.PLAYER_SPRINT_SPEED
        elif self.mode == MoveMode.CROUCH:
            base = config.PLAYER_CROUCH_SPEED
        else:
            base = config.PLAYER_WALK_SPEED
        if self.on_roof and self.fast_climb:
            base *= 1.15
        return base

    @property
    def noise(self) -> float:
        """Visibility multiplier feeding enemy detection meters."""
        if self.hidden:
            return 0.0
        if self.mode == MoveMode.SPRINT:
            n = config.NOISE_SPRINT
        elif self.mode == MoveMode.CROUCH:
            n = config.NOISE_CROUCH
        else:
            n = config.NOISE_WALK
        if self.on_roof:
            n *= 0.4  # harder to spot a figure up on the rooftops
        return n * self.stats.stealth

    # --- update -----------------------------------------------------------
    def update(self, dt: float, world) -> None:
        dx, dy = self._move
        if dx or dy:
            mag = math.hypot(dx, dy)
            dx, dy = dx / mag, dy / mag
            self.face_towards(self.x + dx, self.y + dy)
            step = self.speed * dt
            walkable = world.walkable_roof_px if self.on_roof else world.walkable_ground_px
            self.move_collide(dx * step, dy * step, walkable)

        self.hidden = (
            not self.on_roof
            and self.mode == MoveMode.CROUCH
            and world.is_haystack_px(self.x, self.y)
        )

    # --- climbing ---------------------------------------------------------
    def try_climb(self, world) -> bool:
        """Mount the adjacent rooftop, or dismount to adjacent ground.

        Returns True if a climb happened. Looks at the four tile neighbors for a
        valid destination on the opposite layer.
        """
        c, r = world.tile_at_px(self.x, self.y)
        if not self.on_roof:
            for dc, dr in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                if world.walkable_roof(c + dc, r + dr):
                    cx, cy = world.tile_center_px(c + dc, r + dr)
                    self.x, self.y = cx, cy
                    self.on_roof = True
                    return True
        else:
            for dc, dr in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                if world.walkable_ground(c + dc, r + dr):
                    cx, cy = world.tile_center_px(c + dc, r + dr)
                    self.x, self.y = cx, cy
                    self.on_roof = False
                    return True
        return False
