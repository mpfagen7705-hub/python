from assassin import config
from assassin import world as worldmod


def test_generation_is_deterministic_with_seed():
    a = worldmod.generate(seed=123)
    b = worldmod.generate(seed=123)
    assert a.grid == b.grid
    assert a.roof == b.roof
    assert a.viewpoints == b.viewpoints


def test_map_is_bordered_by_walls():
    w = worldmod.generate(seed=1)
    for c in range(w.cols):
        assert w.grid[0][c] == config.T_WALL
        assert w.grid[w.rows - 1][c] == config.T_WALL
    for r in range(w.rows):
        assert w.grid[r][0] == config.T_WALL
        assert w.grid[r][w.cols - 1] == config.T_WALL


def test_player_start_is_walkable():
    w = worldmod.generate(seed=7)
    assert w.walkable_ground(*w.player_start)


def test_coordinate_roundtrip():
    w = worldmod.generate(seed=2)
    cx, cy = w.tile_center_px(5, 8)
    assert w.tile_at_px(cx, cy) == (5, 8)


def test_out_of_bounds_reads_as_wall_and_blocks():
    w = worldmod.generate(seed=2)
    assert w.ground(-1, -1) == config.T_WALL
    assert w.blocks_sight(-1, 0)
    assert not w.walkable_ground(-1, 0)


def test_reveal_marks_explored_within_radius():
    w = worldmod.generate(seed=3)
    assert not w.explored[10][10]
    w.reveal(10, 10, 2)
    assert w.explored[10][10]
    assert w.explored[10][11]
    assert not w.explored[10][20]


def test_walls_block_sight_and_movement():
    w = worldmod.generate(seed=4)
    # find a wall tile
    found = next((c, r) for r in range(w.rows) for c in range(w.cols)
                 if w.grid[r][c] == config.T_WALL)
    c, r = found
    assert w.blocks_sight(c, r)
    assert not w.walkable_ground(c, r)
