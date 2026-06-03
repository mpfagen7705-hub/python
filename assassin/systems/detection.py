"""Stealth detection math: vision cones, line of sight, and detection meters.

All functions operate on plain numbers / callables so they are trivially unit
tested without a running game. Coordinates are screen-space pixels with the y
axis pointing *down* (the pygame convention).
"""

from __future__ import annotations

import math
from enum import Enum
from typing import Callable, Tuple

from .. import config

Vec = Tuple[float, float]


def angle_to(origin: Vec, target: Vec) -> float:
    """Angle (radians) from ``origin`` to ``target``."""
    return math.atan2(target[1] - origin[1], target[0] - origin[0])


def angle_diff(a: float, b: float) -> float:
    """Smallest absolute difference between two angles, in [0, pi]."""
    d = (a - b) % (2 * math.pi)
    if d > math.pi:
        d -= 2 * math.pi
    return abs(d)


def in_vision_cone(
    observer: Vec,
    facing: float,
    fov: float,
    vision_range: float,
    target: Vec,
) -> bool:
    """True if ``target`` falls within the observer's view cone.

    ``fov`` is the *total* cone width in radians; ``facing`` is its center.
    """
    dx = target[0] - observer[0]
    dy = target[1] - observer[1]
    dist = math.hypot(dx, dy)
    if dist > vision_range:
        return False
    if dist == 0:
        return True
    return angle_diff(math.atan2(dy, dx), facing) <= fov / 2.0


def line_of_sight(is_blocked: Callable[[int, int], bool], a: Vec, b: Vec) -> bool:
    """Tile-grid line of sight test between two *tile* coordinates.

    ``is_blocked(col, row)`` returns True for sight-blocking tiles. The endpoints
    themselves are never treated as blockers (you can see your own/your target's
    tile). Uses an integer supercover-style traversal.
    """
    x0, y0 = int(a[0]), int(a[1])
    x1, y1 = int(b[0]), int(b[1])
    dx = abs(x1 - x0)
    dy = abs(y1 - y0)
    x, y = x0, y0
    n = 1 + dx + dy
    x_inc = 1 if x1 > x0 else -1
    y_inc = 1 if y1 > y0 else -1
    error = dx - dy
    dx *= 2
    dy *= 2
    for _ in range(n):
        if (x, y) != (x0, y0) and (x, y) != (x1, y1):
            if is_blocked(x, y):
                return False
        if error > 0:
            x += x_inc
            error -= dy
        else:
            y += y_inc
            error += dx
    return True


class Awareness(Enum):
    """Discrete awareness state derived from a guard's detection meter."""

    UNAWARE = 0
    SUSPICIOUS = 1
    ALERT = 2


class DetectionMeter:
    """A 0..1 detection accumulator with hysteresis.

    Fills while the target is visible (scaled by ``intensity`` for distance,
    crouch/sprint noise, etc.) and decays otherwise. Once it reaches
    :data:`config.DETECT_ALERT` the guard latches to ``ALERT`` and stays hostile
    until the meter fully drains — modeling a guard who, once he's seen you,
    won't simply forget.
    """

    def __init__(
        self,
        fill_rate: float = config.DETECT_FILL_RATE,
        decay_rate: float = config.DETECT_DECAY_RATE,
    ) -> None:
        self.fill_rate = fill_rate
        self.decay_rate = decay_rate
        self.value = 0.0
        self._latched_alert = False

    def update(self, dt: float, visible: bool, intensity: float = 1.0) -> Awareness:
        """Advance the meter by ``dt`` seconds and return the resulting state."""
        if visible:
            self.value += self.fill_rate * max(0.0, intensity) * dt
        else:
            self.value -= self.decay_rate * dt
        self.value = max(0.0, min(1.0, self.value))

        if self.value >= config.DETECT_ALERT:
            self._latched_alert = True
        elif self.value <= 0.0:
            self._latched_alert = False
        return self.state

    def reset(self) -> None:
        self.value = 0.0
        self._latched_alert = False

    @property
    def state(self) -> Awareness:
        if self._latched_alert or self.value >= config.DETECT_ALERT:
            return Awareness.ALERT
        if self.value >= config.DETECT_SUSPICIOUS:
            return Awareness.SUSPICIOUS
        return Awareness.UNAWARE
