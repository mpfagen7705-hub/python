"""The tile world: a procedurally laid-out city of buildings, streets, canals,
rooftops, haystacks and synchronization viewpoints.

Kept free of pygame so the map and its queries can be exercised in tests. The
map has two conceptual layers:

* **ground** — the ``grid`` of tile types pedestrians walk on.
* **roof** — a boolean layer of rooftops the player reaches by climbing; guards
  never go up there, making rooftops the assassin's sanctuary.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import List, Optional, Tuple

from . import config


@dataclass
class World:
    cols: int = config.MAP_COLS
    rows: int = config.MAP_ROWS
    grid: List[List[int]] = field(default_factory=list)      # ground tile types
    roof: List[List[bool]] = field(default_factory=list)     # rooftop layer
    explored: List[List[bool]] = field(default_factory=list)  # fog of war
    viewpoints: List[Tuple[int, int]] = field(default_factory=list)
    street_tiles: List[Tuple[int, int]] = field(default_factory=list)
    courtyards: List[Tuple[int, int]] = field(default_factory=list)
    player_start: Tuple[int, int] = (2, 2)

    # --- coordinate helpers ----------------------------------------------
    def in_bounds(self, c: int, r: int) -> bool:
        return 0 <= c < self.cols and 0 <= r < self.rows

    def tile_at_px(self, x: float, y: float) -> Tuple[int, int]:
        return int(x // config.TILE), int(y // config.TILE)

    def tile_center_px(self, c: int, r: int) -> Tuple[float, float]:
        return (c + 0.5) * config.TILE, (r + 0.5) * config.TILE

    def ground(self, c: int, r: int) -> int:
        if not self.in_bounds(c, r):
            return config.T_WALL
        return self.grid[r][c]

    def has_roof(self, c: int, r: int) -> bool:
        return self.in_bounds(c, r) and self.roof[r][c]

    # --- traversal / sight queries ---------------------------------------
    def blocks_sight(self, c: int, r: int) -> bool:
        return self.ground(c, r) in config.BLOCKS_SIGHT

    def walkable_ground(self, c: int, r: int) -> bool:
        return self.in_bounds(c, r) and self.grid[r][c] in config.WALKABLE_GROUND

    def walkable_roof(self, c: int, r: int) -> bool:
        return self.has_roof(c, r)

    def walkable_ground_px(self, x: float, y: float) -> bool:
        return self.walkable_ground(*self.tile_at_px(x, y))

    def walkable_roof_px(self, x: float, y: float) -> bool:
        return self.walkable_roof(*self.tile_at_px(x, y))

    def is_haystack_px(self, x: float, y: float) -> bool:
        c, r = self.tile_at_px(x, y)
        return self.ground(c, r) == config.T_HAYSTACK

    # --- fog of war -------------------------------------------------------
    def reveal(self, c: int, r: int, radius: int) -> None:
        for rr in range(r - radius, r + radius + 1):
            for cc in range(c - radius, c + radius + 1):
                if self.in_bounds(cc, rr) and (cc - c) ** 2 + (rr - r) ** 2 <= radius * radius:
                    self.explored[rr][cc] = True

    def reveal_px(self, x: float, y: float, radius: int) -> None:
        c, r = self.tile_at_px(x, y)
        self.reveal(c, r, radius)


def generate(seed: Optional[int] = None) -> World:
    """Procedurally generate a walled city of building blocks and streets."""
    rng = random.Random(seed)
    cols, rows = config.MAP_COLS, config.MAP_ROWS
    grid = [[config.T_STREET for _ in range(cols)] for _ in range(rows)]
    roof = [[False for _ in range(cols)] for _ in range(rows)]
    explored = [[False for _ in range(cols)] for _ in range(rows)]

    def fill(c0, r0, c1, r1, tile):
        for r in range(max(0, r0), min(rows, r1)):
            for c in range(max(0, c0), min(cols, c1)):
                grid[r][c] = tile

    # Outer city wall.
    fill(0, 0, cols, 1, config.T_WALL)
    fill(0, rows - 1, cols, rows, config.T_WALL)
    fill(0, 0, 1, rows, config.T_WALL)
    fill(cols - 1, 0, cols, rows, config.T_WALL)

    viewpoints: List[Tuple[int, int]] = []
    courtyards: List[Tuple[int, int]] = []

    # Lay out building blocks on a grid with streets between them.
    block_w, block_h = 8, 7
    margin = 3
    for br in range(margin, rows - margin, block_h):
        for bc in range(margin, cols - margin, block_w):
            # Leave some plots as open courtyards / squares.
            roll = rng.random()
            bw = block_w - rng.choice([2, 3])
            bh = block_h - rng.choice([2, 3])
            c0, r0 = bc, br
            c1, r1 = min(cols - margin, bc + bw), min(rows - margin, br + bh)
            if c1 - c0 < 2 or r1 - r0 < 2:
                continue
            if roll < 0.18:
                # Open courtyard with a garden patch — a likely target location.
                fill(c0, r0, c1, r1, config.T_GARDEN)
                courtyards.append(((c0 + c1) // 2, (r0 + r1) // 2))
                continue
            # A building: solid walls with a rooftop over the footprint.
            for r in range(r0, r1):
                for c in range(c0, c1):
                    grid[r][c] = config.T_WALL
                    roof[r][c] = True
            # Mark a viewpoint on sufficiently large rooftops.
            if (c1 - c0) >= 4 and (r1 - r0) >= 4 and rng.random() < 0.5:
                viewpoints.append(((c0 + c1) // 2, (r0 + r1) // 2))

    # A canal cutting through the city.
    canal_row = rows // 2
    for c in range(2, cols - 2):
        if grid[canal_row][c] != config.T_WALL:
            grid[canal_row][c] = config.T_WATER
            if grid[canal_row - 1][c] == config.T_WALL:
                grid[canal_row - 1][c] = config.T_STREET  # tow-path beside canal
    # Bridges across the canal.
    for c in range(4, cols - 4, 9):
        grid[canal_row][c] = config.T_STREET

    # Scatter haystacks beside buildings (handy hiding spots / soft landings).
    street_tiles = [
        (c, r)
        for r in range(rows)
        for c in range(cols)
        if grid[r][c] == config.T_STREET
    ]
    rng.shuffle(street_tiles)
    placed = 0
    for (c, r) in street_tiles:
        if placed >= 26:
            break
        # Prefer street tiles adjacent to a wall (against a building).
        if any(grid[r + dr][c + dc] == config.T_WALL
               for dr, dc in ((1, 0), (-1, 0), (0, 1), (0, -1))
               if 0 <= r + dr < rows and 0 <= c + dc < cols):
            grid[r][c] = config.T_HAYSTACK
            placed += 1

    # Recompute the open street list for spawning/patrols.
    street_tiles = [
        (c, r)
        for r in range(rows)
        for c in range(cols)
        if grid[r][c] in (config.T_STREET, config.T_GARDEN)
    ]

    # Player starts in the first open street tile near the top-left.
    player_start = next(
        ((c, r) for (c, r) in street_tiles if c < cols // 3 and r < rows // 3),
        street_tiles[0],
    )

    return World(
        cols=cols,
        rows=rows,
        grid=grid,
        roof=roof,
        explored=explored,
        viewpoints=viewpoints,
        street_tiles=street_tiles,
        courtyards=courtyards,
        player_start=player_start,
    )
