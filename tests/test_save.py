from assassin.systems import save as savesys
from assassin.systems.quests import Contract, ContractStatus, Objective, ObjectiveStatus
from assassin.systems.skills import SkillTree
from assassin.systems.stats import Stats


class FakePlayer:
    pass


def test_stats_roundtrip():
    s = Stats(level=4, xp=500, max_hp=140, hp=77, attack=30, defense=9,
              stealth=0.5, skill_points=2)
    data = savesys.dump_stats(s)
    out = Stats()
    savesys.load_stats(out, data)
    assert savesys.dump_stats(out) == data
    assert out.level == 4 and out.hp == 77 and out.stealth == 0.5


def test_skills_roundtrip_restores_unlocked_and_flags():
    tree = SkillTree()
    stats = Stats(skill_points=5)
    tree.unlock("free_runner", stats)       # grants fast_climb
    tree.unlock("silent_step", stats)
    dumped = savesys.dump_skills(tree)
    assert "free_runner" in dumped

    new_tree = SkillTree()
    player = FakePlayer()
    savesys.load_skills(new_tree, dumped, player)
    assert new_tree.is_unlocked("free_runner")
    assert new_tree.is_unlocked("silent_step")
    assert getattr(player, "fast_climb", False) is True


def test_load_skills_does_not_reapply_stat_effects():
    # The saved stats already include skill bonuses; loading must not double them.
    tree = SkillTree()
    stats = Stats(skill_points=1, stealth=1.0)
    tree.unlock("silent_step", stats)
    saved_stealth = stats.stealth  # already reduced once

    new_tree = SkillTree()
    new_stats = Stats()
    savesys.load_stats(new_stats, savesys.dump_stats(stats))
    savesys.load_skills(new_tree, savesys.dump_skills(tree))
    assert new_stats.stealth == saved_stealth  # not reduced again


def test_load_skills_ignores_unknown_keys():
    tree = SkillTree()
    savesys.load_skills(tree, ["silent_step", "not_a_real_skill"])
    assert tree.is_unlocked("silent_step")
    assert not tree.is_unlocked("not_a_real_skill")


def test_contract_roundtrip():
    c = Contract("c", "name", "summary",
                 objectives=[Objective("kill", "kill", required=3),
                             Objective("opt", "optional", optional=True)],
                 reward_xp=400)
    c.advance("kill", 2)
    data = savesys.dump_contract(c)

    restored = Contract("c", "name", "summary",
                        objectives=[Objective("kill", "kill", required=3),
                                    Objective("opt", "optional", optional=True)],
                        reward_xp=400)
    savesys.load_contract(restored, data)
    assert restored.objective("kill").progress == 2
    assert restored.status is ContractStatus.ACTIVE


def test_contract_roundtrip_preserves_completion():
    c = Contract("c", "name", "summary",
                 objectives=[Objective("kill", "kill", required=1)], reward_xp=100)
    c.advance("kill", 1)
    assert c.complete
    data = savesys.dump_contract(c)
    restored = Contract("c", "name", "summary",
                        objectives=[Objective("kill", "kill", required=1)], reward_xp=100)
    savesys.load_contract(restored, data)
    assert restored.status is ContractStatus.COMPLETE
    assert restored.objective("kill").status is ObjectiveStatus.COMPLETE
