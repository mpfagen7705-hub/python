from assassin.systems.quests import (
    Contract,
    ContractStatus,
    Objective,
    ObjectiveStatus,
    QuestLog,
)


def make_contract():
    return Contract(
        "c1", "Test Contract", "do the thing",
        objectives=[
            Objective("kill", "Eliminate targets", required=2),
            Objective("ghost", "Stay hidden", required=1, optional=True),
        ],
        reward_xp=400,
    )


def test_objective_advances_and_completes():
    o = Objective("k", "kill", required=2)
    o.advance()
    assert not o.done
    o.advance()
    assert o.done
    assert o.status is ObjectiveStatus.COMPLETE
    # advancing past required does not overflow
    o.advance()
    assert o.progress == 2


def test_contract_completes_when_required_objectives_done():
    c = make_contract()
    c.advance("kill", 2)
    assert c.complete
    assert c.status is ContractStatus.COMPLETE


def test_optional_objective_does_not_block_completion():
    c = make_contract()
    c.advance("kill", 2)
    # ghost (optional) never advanced, contract still complete
    assert c.complete


def test_failed_required_objective_fails_contract():
    c = make_contract()
    c.fail_objective("kill")
    assert c.status is ContractStatus.FAILED
    assert not c.complete


def test_failed_optional_objective_does_not_fail_contract():
    c = make_contract()
    c.fail_objective("ghost")
    c.advance("kill", 2)
    assert c.status is ContractStatus.COMPLETE


def test_quest_log_tracks_active_and_completed():
    log = QuestLog()
    a = log.add(make_contract())
    b = log.add(make_contract())
    assert len(log.active) == 2
    a.advance("kill", 2)
    assert len(log.completed) == 1
    assert not log.all_complete()
    b.advance("kill", 2)
    assert log.all_complete()


def test_rewards_collected_once():
    log = QuestLog()
    c = log.add(make_contract())
    c.advance("kill", 2)
    assert log.collect_rewards() == 400
    assert log.collect_rewards() == 0  # already paid out
