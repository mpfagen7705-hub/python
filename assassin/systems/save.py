"""Save/load serialization — pure logic, no pygame, no file IO of game objects.

These helpers convert the progression-bearing objects (stats, skill tree,
contracts) to and from plain dicts. The :class:`~assassin.game.Game` layers the
actual JSON file IO and world reconstruction on top of these primitives.
"""

from __future__ import annotations

from typing import Dict, List

from .quests import Contract, ContractStatus, ObjectiveStatus
from .skills import SkillTree
from .stats import Stats

SAVE_VERSION = 1


# --- stats -----------------------------------------------------------------
def dump_stats(stats: Stats) -> Dict:
    return {
        "level": stats.level,
        "xp": stats.xp,
        "max_hp": stats.max_hp,
        "hp": stats.hp,
        "attack": stats.attack,
        "defense": stats.defense,
        "stealth": stats.stealth,
        "skill_points": stats.skill_points,
    }


def load_stats(stats: Stats, data: Dict) -> None:
    stats.level = data["level"]
    stats.xp = data["xp"]
    stats.max_hp = data["max_hp"]
    stats.hp = data["hp"]
    stats.attack = data["attack"]
    stats.defense = data["defense"]
    stats.stealth = data["stealth"]
    stats.skill_points = data["skill_points"]


# --- skills ----------------------------------------------------------------
def dump_skills(tree: SkillTree) -> List[str]:
    return sorted(tree.unlocked)


def load_skills(tree: SkillTree, unlocked: List[str], player=None) -> None:
    """Restore unlocked skills and re-derive their capability flags.

    Stat effects are *not* re-applied here: the saved :class:`Stats` numbers
    already include them, so doing so would double-count. Only the boolean
    capability flags (which live on the player, not the stats) are re-derived.
    """
    tree.unlocked = set(k for k in unlocked if k in {s.key for s in tree.all()})
    if player is not None:
        for key in tree.unlocked:
            skill = tree.get(key)
            if skill.grants_flag:
                setattr(player, skill.grants_flag, True)


# --- contracts -------------------------------------------------------------
def dump_contract(c: Contract) -> Dict:
    return {
        "key": c.key,
        "status": c.status.name,
        "reward_xp": c.reward_xp,
        "objectives": [
            {"key": o.key, "progress": o.progress, "status": o.status.name}
            for o in c.objectives
        ],
    }


def load_contract(c: Contract, data: Dict) -> None:
    c.status = ContractStatus[data["status"]]
    c.reward_xp = data["reward_xp"]
    by_key = {o["key"]: o for o in data["objectives"]}
    for o in c.objectives:
        if o.key in by_key:
            od = by_key[o.key]
            o.progress = od["progress"]
            o.status = ObjectiveStatus[od["status"]]
