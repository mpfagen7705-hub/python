from assassin.systems.skills import Branch, SkillTree
from assassin.systems.stats import Stats


class FakePlayer:
    """Stand-in for the player to capture capability flags."""
    pass


def test_cannot_unlock_without_points():
    tree = SkillTree()
    stats = Stats(skill_points=0)
    assert not tree.can_unlock("silent_step", stats)
    assert not tree.unlock("silent_step", stats)


def test_unlock_spends_points_and_applies_stat_effect():
    tree = SkillTree()
    stats = Stats(skill_points=1, stealth=1.0)
    assert tree.unlock("silent_step", stats)
    assert tree.is_unlocked("silent_step")
    assert stats.skill_points == 0
    assert stats.stealth < 1.0  # sneakier


def test_prerequisites_enforced():
    tree = SkillTree()
    stats = Stats(skill_points=5)
    # "shadow" requires "silent_step"
    assert not tree.can_unlock("shadow", stats)
    tree.unlock("silent_step", stats)
    assert tree.can_unlock("shadow", stats)


def test_flag_granting_skill_sets_player_flag():
    tree = SkillTree()
    stats = Stats(skill_points=3)
    player = FakePlayer()
    tree.unlock("silent_step", stats)
    tree.unlock("shadow", stats)
    assert tree.unlock("air_assassinate", stats, player)
    assert getattr(player, "can_air_assassinate", False) is True


def test_toughness_raises_and_refills_hp():
    tree = SkillTree()
    stats = Stats(skill_points=1, max_hp=100, hp=40)
    tree.unlock("toughness", stats)
    assert stats.max_hp == 125
    assert stats.hp == 125


def test_branches_partition_skills():
    tree = SkillTree()
    total = len(tree.all())
    counted = sum(len(tree.by_branch(b)) for b in (Branch.ASSASSIN, Branch.COMBAT, Branch.AGILITY))
    assert counted == total


def test_cannot_unlock_same_skill_twice():
    tree = SkillTree()
    stats = Stats(skill_points=2)
    assert tree.unlock("silent_step", stats)
    assert not tree.unlock("silent_step", stats)
    assert stats.skill_points == 1
