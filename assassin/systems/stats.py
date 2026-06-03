"""Character stats and XP/leveling — pure logic, no pygame.

The leveling curve is a smooth super-linear ramp: each level costs more than the
last so the early game progresses quickly and later levels feel earned.
"""

from __future__ import annotations

from dataclasses import dataclass, field


def xp_for_level(level: int) -> int:
    """Cumulative XP required to *reach* ``level`` (level 1 == 0 XP)."""
    if level <= 1:
        return 0
    return int(100 * ((level - 1) ** 1.5))


@dataclass
class Stats:
    """Combatant stats shared by the player and guards.

    ``attack`` and ``defense`` feed :mod:`assassin.systems.combat`; ``stealth``
    lowers how quickly the player fills enemy detection meters.
    """

    level: int = 1
    xp: int = 0
    max_hp: int = 100
    hp: int = 100
    attack: int = 18
    defense: int = 4
    stealth: float = 1.0  # multiplier on detection fill rate (lower == sneakier)
    skill_points: int = 0

    # --- health -----------------------------------------------------------
    @property
    def alive(self) -> bool:
        return self.hp > 0

    def take_damage(self, amount: float) -> int:
        """Apply ``amount`` damage (>=0) and return the actual HP lost."""
        amount = max(0, int(round(amount)))
        before = self.hp
        self.hp = max(0, self.hp - amount)
        return before - self.hp

    def heal(self, amount: float) -> int:
        amount = max(0, int(round(amount)))
        before = self.hp
        self.hp = min(self.max_hp, self.hp + amount)
        return self.hp - before

    def heal_full(self) -> None:
        self.hp = self.max_hp

    # --- progression ------------------------------------------------------
    def xp_to_next(self) -> int:
        """XP still needed to reach the next level."""
        return max(0, xp_for_level(self.level + 1) - self.xp)

    def level_progress(self) -> float:
        """Fraction (0..1) of the way through the current level."""
        base = xp_for_level(self.level)
        nxt = xp_for_level(self.level + 1)
        span = nxt - base
        if span <= 0:
            return 0.0
        return max(0.0, min(1.0, (self.xp - base) / span))

    def add_xp(self, amount: int) -> int:
        """Grant XP and resolve any level-ups.

        Returns the number of levels gained. Each level raises max HP and
        attack a little and grants skill points so the player keeps growing.
        """
        if amount <= 0:
            return 0
        self.xp += amount
        gained = 0
        while self.xp >= xp_for_level(self.level + 1):
            self.level += 1
            gained += 1
            self.max_hp += 12
            self.attack += 2
            self.hp = self.max_hp  # full heal on level up
            self.skill_points += 1
        return gained
