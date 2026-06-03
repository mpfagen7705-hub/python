"""Global configuration: screen, tiles, colors, and tunable gameplay constants.

This module is intentionally free of any pygame import so it can be loaded by the
headless logic tests as well as the game.
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Display
# ---------------------------------------------------------------------------
SCREEN_WIDTH = 1024
SCREEN_HEIGHT = 720
FPS = 60
TITLE = "Assassin's Reverie"

# ---------------------------------------------------------------------------
# World / tiles
# ---------------------------------------------------------------------------
TILE = 32  # pixels per tile
MAP_COLS = 64
MAP_ROWS = 48

# Tile types (ground layer)
T_STREET = 0    # walkable ground
T_WALL = 1      # building wall — blocks movement and line of sight
T_HAYSTACK = 2  # hiding spot — invisible to guards while crouched inside
T_WATER = 3     # blocks movement, does not block sight
T_GARDEN = 4    # walkable decorative ground (bushes), light concealment

WALKABLE_GROUND = {T_STREET, T_HAYSTACK, T_GARDEN}
BLOCKS_SIGHT = {T_WALL}
BLOCKS_MOVE_GROUND = {T_WALL, T_WATER}

# ---------------------------------------------------------------------------
# Player tuning
# ---------------------------------------------------------------------------
PLAYER_RADIUS = 11
PLAYER_WALK_SPEED = 150.0      # px / second
PLAYER_SPRINT_SPEED = 260.0
PLAYER_CROUCH_SPEED = 80.0
PLAYER_BASE_HP = 100

# How "loud"/visible the player is in each movement mode. Feeds the detection
# meter fill-rate as a multiplier.
NOISE_CROUCH = 0.45
NOISE_WALK = 1.0
NOISE_SPRINT = 1.7

ASSASSINATE_RANGE = 34.0       # px; must be this close to a target to assassinate
ASSASSINATE_ARC = 2.4          # radians; target must be facing roughly away
INTERACT_RANGE = 40.0

# ---------------------------------------------------------------------------
# Guard tuning
# ---------------------------------------------------------------------------
GUARD_RADIUS = 11
GUARD_PATROL_SPEED = 70.0
GUARD_CHASE_SPEED = 175.0
GUARD_VISION_RANGE = 200.0     # px
GUARD_VISION_FOV = 1.4         # radians (~80 degrees) total cone width
GUARD_ATTACK_RANGE = 30.0
GUARD_ATTACK_COOLDOWN = 0.9    # seconds
GUARD_BASE_HP = 60
GUARD_DAMAGE = 14

# Enemy variants ------------------------------------------------------------
# Archers: fragile, keep their distance and fire arrows.
ARCHER_HP = 35
ARCHER_DAMAGE = 16
ARCHER_SHOOT_RANGE = 280.0
ARCHER_SHOOT_COOLDOWN = 1.6     # seconds between shots
ARCHER_KEEP_DISTANCE = 150.0    # tries to stay at least this far from the player
ARCHER_VISION_MULT = 1.25
# Brutes: slow, heavily armored, hit like a battering ram.
BRUTE_HP = 150
BRUTE_DAMAGE = 28
BRUTE_SPEED_MULT = 0.7
BRUTE_DEFENSE = 8

PROJECTILE_SPEED = 430.0
PROJECTILE_RADIUS = 4
PROJECTILE_LIFETIME = 2.2

# How many of each enemy kind to scatter through the city.
NUM_GUARDS = 10
NUM_ARCHERS = 5
NUM_BRUTES = 3

# Detection meter (0..1). Crossing SUSPICIOUS makes guards investigate; crossing
# ALERT makes them hostile.
DETECT_FILL_RATE = 1.25        # per second at full intensity
DETECT_DECAY_RATE = 0.55       # per second when not seen
DETECT_SUSPICIOUS = 0.45
DETECT_ALERT = 1.0

# ---------------------------------------------------------------------------
# RPG progression
# ---------------------------------------------------------------------------
XP_ASSASSINATION = 150         # stealth kill
XP_KILL = 70                   # open-combat kill
XP_VIEWPOINT = 120             # synchronizing a viewpoint
XP_CONTRACT = 400              # completing a contract
SKILL_POINTS_PER_LEVEL = 1

# ---------------------------------------------------------------------------
# Colors (R, G, B)
# ---------------------------------------------------------------------------
C_STREET = (58, 54, 50)
C_STREET_ALT = (52, 48, 45)
C_WALL = (96, 88, 78)
C_ROOF = (140, 96, 70)
C_ROOF_EDGE = (108, 72, 52)
C_HAYSTACK = (196, 170, 70)
C_WATER = (44, 78, 110)
C_GARDEN = (54, 92, 58)
C_VIEWPOINT = (240, 224, 120)
C_FOG = (10, 10, 14)

C_PLAYER = (235, 235, 240)
C_PLAYER_CROUCH = (170, 190, 220)
C_GUARD = (180, 60, 60)
C_GUARD_SUS = (220, 170, 60)
C_GUARD_ALERT = (235, 70, 70)
C_ARCHER = (90, 150, 205)
C_BRUTE = (150, 80, 40)
C_TARGET = (210, 80, 200)
C_BLADE = (220, 230, 255)
C_ARROW = (235, 225, 200)

C_VISION_CALM = (90, 200, 120)
C_VISION_SUS = (235, 200, 70)
C_VISION_ALERT = (235, 70, 70)

C_HUD_BG = (18, 18, 24)
C_HUD_HP = (200, 60, 60)
C_HUD_HP_BG = (60, 28, 28)
C_HUD_XP = (90, 170, 235)
C_HUD_TEXT = (235, 235, 240)
C_HUD_DIM = (150, 150, 160)
C_GOLD = (240, 210, 110)
