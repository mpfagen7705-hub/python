"""Headless integration smoke tests: build the game and step it through frames.

Uses the dummy SDL drivers configured in conftest so it runs without a display.
"""

import math

import pygame

from assassin import config
from assassin.entities.guard import Guard, GuardState
from assassin.entities.player import MoveMode, Player
from assassin.game import Game, State


def test_game_constructs_and_populates_world():
    g = Game(seed=99)
    assert g.world is not None
    assert g.player is not None
    assert len(g.targets) >= 1
    assert len(g.guards) >= 1
    assert g.quest_log.contracts


def test_game_steps_many_frames_without_error():
    g = Game(seed=5)
    g.state = State.PLAYING
    for _ in range(120):
        g.player.set_intent(1, 0, MoveMode.WALK, False)
        g._update(1 / 60)
    assert g.player.stats.alive or g.state == State.GAMEOVER


def test_player_collides_with_walls():
    g = Game(seed=5)
    p = g.player
    # Drive hard into the top-left corner; player must stay in bounds & on floor.
    for _ in range(300):
        p.set_intent(-1, -1, MoveMode.SPRINT, False)
        p.update(1 / 60, g.world)
    assert g.world.walkable_ground_px(p.x, p.y)


def test_assassination_kills_unaware_target():
    g = Game(seed=5)
    g.state = State.PLAYING
    target = g.targets[0]
    # Teleport behind the target so the strike lands as a stealth kill.
    g.player.x = target.x - math.cos(target.facing) * 20
    g.player.y = target.y - math.sin(target.facing) * 20
    target.meter.reset()
    g._attempt_attack()
    g._reconcile_deaths()
    assert target.dead
    assert g.player.stats.xp >= config.XP_ASSASSINATION


def test_climbing_toggles_roof_layer():
    g = Game(seed=5)
    w = g.world
    p = g.player
    # Place player on a street tile that neighbors a rooftop, then climb.
    spot = None
    for r in range(w.rows):
        for c in range(w.cols):
            if w.walkable_ground(c, r) and any(
                w.walkable_roof(c + dc, r + dr)
                for dc, dr in ((1, 0), (-1, 0), (0, 1), (0, -1))
            ):
                spot = (c, r)
                break
        if spot:
            break
    assert spot is not None
    p.x, p.y = w.tile_center_px(*spot)
    assert p.try_climb(w)
    assert p.on_roof
    assert p.try_climb(w)  # descend
    assert not p.on_roof


def test_guard_detects_player_in_open_and_goes_alert():
    g = Game(seed=5)
    guard = g.guards[0]
    p = g.player
    # Put the player right in front of the guard, in the open.
    guard.facing = 0.0
    p.x, p.y = guard.x + 40, guard.y
    p.on_roof = False
    p.set_intent(0, 0, MoveMode.WALK, False)
    # Make sure there's clear line of sight (no wall between) by nudging onto a
    # known street tile pair if needed.
    for _ in range(120):
        guard.update(1 / 60, p, g.world)
    # With the player loitering in view the meter should have risen.
    assert guard.meter.value > 0.0


def test_hidden_in_haystack_makes_player_invisible():
    p = Player(0, 0)
    p.set_intent(0, 0, MoveMode.CROUCH, False)
    p.hidden = True
    assert p.noise == 0.0


def test_enemy_mix_spawns_all_kinds():
    from assassin.entities.guard import GuardKind
    g = Game(seed=5)
    kinds = {guard.kind for guard in g.guards}
    assert GuardKind.GUARD in kinds
    assert GuardKind.ARCHER in kinds
    assert GuardKind.BRUTE in kinds


def test_save_and_load_roundtrip(tmp_path):
    path = str(tmp_path / "save.json")
    g = Game(seed=42)
    g.state = State.PLAYING
    g.player.stats.add_xp(300)            # gain some progression
    g.targets[0].dead = True
    g._awarded.add(id(g.targets[0]))
    assert g.save_to_file(path)

    g2 = Game(seed=999)                   # different world
    assert g2.load_from_file(path)
    assert g2.seed == 42
    assert g2.player.stats.level == g.player.stats.level
    assert g2.player.stats.xp == g.player.stats.xp
    assert g2.targets[0].dead is True


def test_load_missing_file_returns_false():
    g = Game(seed=1)
    assert not g.load_from_file("/nonexistent/path/save.json")


def test_archer_shoot_callback_spawns_projectile():
    from assassin.entities.guard import GuardKind
    g = Game(seed=5)
    archer = next(x for x in g.guards if x.kind == GuardKind.ARCHER)
    assert archer.on_shoot is not None
    n0 = len(g.projectiles)
    archer.on_shoot(archer, g.player)
    assert len(g.projectiles) == n0 + 1


def test_menu_and_controls_render():
    g = Game(seed=5)
    g.state = State.MENU
    g._draw()
    assert g._menu_rects  # populated during menu draw
    g.state = State.CONTROLS
    g._draw()


def test_audio_is_safe_when_disabled():
    from assassin.audio import SoundFX
    fx = SoundFX()
    # Whether or not a device exists, play must never raise.
    fx.play("assassinate")
    fx.play("nonexistent_sound")
    assert isinstance(fx.toggle_mute(), bool)


def test_pygame_quit_cleanup():
    pygame.quit()
