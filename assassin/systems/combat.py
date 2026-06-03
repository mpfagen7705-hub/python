"""Combat resolution — pure logic, no pygame.

Two flavors of lethality, mirroring the source material:

* **Assassination** — a stealth strike on an unaware foe (ideally from behind).
  It is instantly lethal, the assassin's signature move.
* **Open combat** — trading blows once you've been spotted. Damage is a function
  of attack vs. defense, mitigated heavily by a well-timed block/parry.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from .stats import Stats


@dataclass
class AttackResult:
    """Outcome of a single attack, returned for UI/feedback and testing."""

    damage: int
    lethal: bool
    assassination: bool = False
    blocked: bool = False


def is_behind(attacker_pos, target_pos, target_facing, arc: float) -> bool:
    """True if the attacker stands within ``arc`` radians of the target's back.

    The target's "back" is ``target_facing + pi``. ``arc`` is the total width of
    the rear vulnerable cone.
    """
    dx = attacker_pos[0] - target_pos[0]
    dy = attacker_pos[1] - target_pos[1]
    if dx == 0 and dy == 0:
        return True
    ang = math.atan2(dy, dx)
    back = target_facing + math.pi
    d = (ang - back) % (2 * math.pi)
    if d > math.pi:
        d -= 2 * math.pi
    return abs(d) <= arc / 2.0


def resolve_attack(
    attacker: Stats,
    defender: Stats,
    *,
    assassination: bool = False,
    defender_aware: bool = True,
    blocking: bool = False,
) -> AttackResult:
    """Compute and apply the damage of one attack against ``defender``.

    A stealth ``assassination`` against an unaware defender is always lethal. An
    attempted assassination on an *aware* defender degrades into a strong but
    survivable strike (a botched stealth kill). Blocking quarters incoming
    open-combat damage.
    """
    if assassination and not defender_aware:
        dealt = defender.take_damage(defender.hp)  # guarantee a kill
        return AttackResult(damage=dealt, lethal=True, assassination=True)

    base = attacker.attack
    if assassination:
        base = int(base * 1.5)  # the strike still lands hard, just not silent

    raw = base - defender.defense * 0.5
    if blocking:
        raw *= 0.25
    raw = max(1.0, raw)

    dealt = defender.take_damage(raw)
    return AttackResult(
        damage=dealt,
        lethal=not defender.alive,
        assassination=assassination,
        blocked=blocking,
    )
