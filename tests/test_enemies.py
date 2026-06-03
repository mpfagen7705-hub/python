"""Tests for enemy variants and projectiles."""

import math

from assassin import config
from assassin.entities.guard import Guard, GuardKind
from assassin.entities.player import Player
from assassin.entities.projectile import Projectile
from assassin import world as worldmod


def test_guard_kinds_have_distinct_stats():
    g = Guard(0, 0, kind=GuardKind.GUARD)
    a = Guard(0, 0, kind=GuardKind.ARCHER)
    b = Guard(0, 0, kind=GuardKind.BRUTE)
    assert a.ranged and not g.ranged and not b.ranged
    assert b.stats.max_hp > g.stats.max_hp > a.stats.max_hp
    assert b.chase_speed < g.chase_speed       # brutes are slow
    assert a.vision_range > g.vision_range      # archers see farther


def test_projectile_hits_player_and_deals_damage():
    w = worldmod.generate(seed=1)
    p = Player(*w.tile_center_px(*w.player_start))
    p.on_roof = False
    before = p.stats.hp
    # Arrow spawned one pixel to the left, flying right into the player.
    proj = Projectile(p.x - 5, p.y, 0.0, damage=20)
    result = ""
    for _ in range(10):
        result = proj.update(1 / 60, w, p)
        if result:
            break
    assert result == "hit"
    assert p.stats.hp < before
    assert not proj.alive


def test_projectile_blocked_by_wall():
    w = worldmod.generate(seed=1)
    p = Player(*w.tile_center_px(*w.player_start))
    # Find a wall and fire an arrow straight at it from an open tile beside it.
    wall = next((c, r) for r in range(w.rows) for c in range(w.cols)
                if w.grid[r][c] == config.T_WALL and w.walkable_ground(c - 1, r))
    c, r = wall
    sx, sy = w.tile_center_px(c - 1, r)
    proj = Projectile(sx, sy, 0.0, damage=20)  # flying +x into the wall
    result = ""
    for _ in range(30):
        result = proj.update(1 / 60, w, p)
        if result:
            break
    assert result == "blocked"
    assert not proj.alive


def test_projectile_misses_player_on_roof():
    w = worldmod.generate(seed=1)
    p = Player(*w.tile_center_px(*w.player_start))
    p.on_roof = True  # arrows fly under the rooftops
    before = p.stats.hp
    proj = Projectile(p.x - 5, p.y, 0.0, damage=20)
    for _ in range(10):
        proj.update(1 / 60, w, p)
    assert p.stats.hp == before


def test_projectile_expires_after_lifetime():
    w = worldmod.generate(seed=1)
    p = Player(0, 0)
    proj = Projectile(5000, 5000, 0.0, damage=5)  # far away in the void
    proj.life = 0.05
    proj.update(0.1, w, p)
    assert not proj.alive
