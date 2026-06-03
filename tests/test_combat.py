import math

from assassin.systems.combat import is_behind, resolve_attack
from assassin.systems.stats import Stats


def test_stealth_assassination_is_lethal_on_unaware():
    attacker = Stats(attack=20)
    defender = Stats(max_hp=80, hp=80)
    res = resolve_attack(attacker, defender, assassination=True, defender_aware=False)
    assert res.lethal
    assert res.assassination
    assert defender.hp == 0


def test_assassination_on_aware_defender_is_not_instant():
    attacker = Stats(attack=20)
    defender = Stats(max_hp=200, hp=200, defense=4)
    res = resolve_attack(attacker, defender, assassination=True, defender_aware=True)
    assert not res.lethal
    assert defender.hp > 0
    assert res.damage > 0


def test_blocking_reduces_damage():
    atk = Stats(attack=40)
    open_def = Stats(max_hp=200, hp=200, defense=0)
    blk_def = Stats(max_hp=200, hp=200, defense=0)
    open_res = resolve_attack(atk, open_def)
    blk_res = resolve_attack(atk, blk_def, blocking=True)
    assert blk_res.damage < open_res.damage


def test_minimum_one_damage():
    atk = Stats(attack=1)
    d = Stats(max_hp=50, hp=50, defense=999)
    res = resolve_attack(atk, d)
    assert res.damage >= 1


def test_lethal_flag_when_hp_hits_zero():
    atk = Stats(attack=100)
    d = Stats(max_hp=5, hp=5, defense=0)
    res = resolve_attack(atk, d)
    assert res.lethal
    assert not d.alive


def test_is_behind_detects_rear_and_front():
    # target at origin facing +x (0 rad); back is -x direction
    target = (0.0, 0.0)
    facing = 0.0
    assert is_behind((-10, 0), target, facing, arc=math.pi / 2)   # directly behind
    assert not is_behind((10, 0), target, facing, arc=math.pi / 2)  # directly in front
