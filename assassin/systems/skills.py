"""The skill tree — three branches the player invests skill points into.

Each :class:`Skill` may require prerequisite skills and applies its effect to a
:class:`~assassin.systems.stats.Stats` object (and/or sets capability flags on
the owning player) when unlocked. Pure logic; no pygame.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional

from .stats import Stats


class Branch:
    ASSASSIN = "Assassin"
    COMBAT = "Combat"
    AGILITY = "Agility"


@dataclass
class Skill:
    key: str
    name: str
    branch: str
    description: str
    cost: int = 1
    requires: tuple = ()  # keys of prerequisite skills
    # Mutates the player's stats when unlocked (optional).
    apply_stats: Optional[Callable[[Stats], None]] = None
    # Capability flag name this skill grants on the player (optional).
    grants_flag: Optional[str] = None


def _default_skills() -> List[Skill]:
    """The canonical skill list. Kept in a function so tests get a fresh copy."""
    return [
        # --- Assassin branch: stealth & lethality -------------------------
        Skill("silent_step", "Silent Step", Branch.ASSASSIN,
              "Move more quietly; guards fill their detection slower.",
              apply_stats=lambda s: setattr(s, "stealth", s.stealth * 0.75)),
        Skill("shadow", "One With Shadows", Branch.ASSASSIN,
              "Further reduce your visibility to enemies.",
              requires=("silent_step",),
              apply_stats=lambda s: setattr(s, "stealth", s.stealth * 0.7)),
        Skill("air_assassinate", "Leap of Faith Strike", Branch.ASSASSIN,
              "Assassinate from rooftops by dropping onto a target.",
              requires=("shadow",), grants_flag="can_air_assassinate"),

        # --- Combat branch: durability & damage ---------------------------
        Skill("toughness", "Toughness", Branch.COMBAT,
              "+25 maximum health.",
              apply_stats=lambda s: (setattr(s, "max_hp", s.max_hp + 25),
                                     setattr(s, "hp", s.max_hp))),
        Skill("blade_master", "Blade Master", Branch.COMBAT,
              "+6 attack power.", requires=("toughness",),
              apply_stats=lambda s: setattr(s, "attack", s.attack + 6)),
        Skill("counter", "Counter Strike", Branch.COMBAT,
              "Parrying an attack opens the foe to an instant riposte.",
              requires=("blade_master",), grants_flag="can_counter"),

        # --- Agility branch: mobility & utility ---------------------------
        Skill("free_runner", "Free Runner", Branch.AGILITY,
              "Climb and sprint faster.",
              grants_flag="fast_climb"),
        Skill("eagle_eye", "Eagle Vision", Branch.AGILITY,
              "Reveal a wider area when synchronizing viewpoints; sense targets.",
              requires=("free_runner",), grants_flag="eagle_vision"),
        Skill("vault", "Vault & Roll", Branch.AGILITY,
              "Take no damage from long drops; recover faster.",
              requires=("eagle_eye",), grants_flag="safe_fall"),
    ]


class SkillTree:
    """Owns the set of skills and tracks which the player has unlocked."""

    def __init__(self, skills: Optional[List[Skill]] = None) -> None:
        self._skills: Dict[str, Skill] = {s.key: s for s in (skills or _default_skills())}
        self.unlocked: set[str] = set()

    # --- queries ----------------------------------------------------------
    def get(self, key: str) -> Skill:
        return self._skills[key]

    def all(self) -> List[Skill]:
        return list(self._skills.values())

    def by_branch(self, branch: str) -> List[Skill]:
        return [s for s in self._skills.values() if s.branch == branch]

    def is_unlocked(self, key: str) -> bool:
        return key in self.unlocked

    def prereqs_met(self, key: str) -> bool:
        return all(r in self.unlocked for r in self._skills[key].requires)

    def can_unlock(self, key: str, stats: Stats) -> bool:
        if key not in self._skills or key in self.unlocked:
            return False
        skill = self._skills[key]
        return self.prereqs_met(key) and stats.skill_points >= skill.cost

    # --- mutation ---------------------------------------------------------
    def unlock(self, key: str, stats: Stats, player=None) -> bool:
        """Spend points to unlock ``key``. Returns False if not permitted.

        Applies the skill's stat changes to ``stats`` and sets any capability
        flag on ``player`` (when provided).
        """
        if not self.can_unlock(key, stats):
            return False
        skill = self._skills[key]
        stats.skill_points -= skill.cost
        self.unlocked.add(key)
        if skill.apply_stats is not None:
            skill.apply_stats(stats)
        if skill.grants_flag and player is not None:
            setattr(player, skill.grants_flag, True)
        return True
