from assassin.systems.stats import Stats, xp_for_level


def test_xp_curve_is_increasing_and_starts_at_zero():
    assert xp_for_level(1) == 0
    levels = [xp_for_level(n) for n in range(1, 10)]
    assert levels == sorted(levels)
    # gaps grow (super-linear)
    gaps = [levels[i + 1] - levels[i] for i in range(len(levels) - 1)]
    assert gaps == sorted(gaps)


def test_take_damage_clamps_at_zero_and_reports_loss():
    s = Stats(max_hp=50, hp=50)
    assert s.take_damage(20) == 20
    assert s.hp == 30
    assert s.take_damage(999) == 30
    assert s.hp == 0
    assert not s.alive


def test_heal_clamps_at_max():
    s = Stats(max_hp=100, hp=90)
    assert s.heal(50) == 10
    assert s.hp == 100


def test_add_xp_levels_up_and_grants_points_and_heals():
    s = Stats(level=1, xp=0, max_hp=100, hp=10, attack=20)
    gained = s.add_xp(xp_for_level(2))
    assert gained == 1
    assert s.level == 2
    assert s.skill_points == 1
    assert s.attack == 22
    assert s.max_hp == 112
    assert s.hp == s.max_hp  # full heal on level up


def test_add_xp_can_grant_multiple_levels_at_once():
    s = Stats()
    gained = s.add_xp(xp_for_level(5))
    assert gained == 4
    assert s.level == 5
    assert s.skill_points == 4


def test_level_progress_within_unit_interval():
    s = Stats()
    s.add_xp(xp_for_level(2) + 5)
    p = s.level_progress()
    assert 0.0 <= p <= 1.0


def test_add_nonpositive_xp_is_noop():
    s = Stats()
    assert s.add_xp(0) == 0
    assert s.add_xp(-100) == 0
    assert s.level == 1
