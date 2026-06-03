# Assassin's Reverie

A 2D top-down **stealth-action RPG** inspired by *Assassin's Creed*, built in
Python with pygame. Stalk a procedurally-generated city, strike your targets
from the shadows, vanish across the rooftops, and grow from a novice into a
master assassin through an XP-driven skill tree.

![genre: stealth-action RPG](https://img.shields.io/badge/genre-stealth--action%20RPG-555)
![python](https://img.shields.io/badge/python-3.10%2B-blue)
![tests](https://img.shields.io/badge/tests-66%20passing-brightgreen)

## Features

- **Stealth detection** — guards have real vision cones with line-of-sight
  blocked by buildings, a fill/decay detection meter, and four AI states:
  *patrol → suspicious → alert/chase → search*. Once a guard has truly seen
  you, he stays roused until he loses the trail.
- **Three enemy types** — red **guards** (melee patrols), blue **archers**
  (fragile, keep their distance and rain arrows you can block or dodge behind
  cover), and big orange **brutes** (slow, armored, hit like a battering ram).
- **Stealth assassinations** — slip behind an unaware target (or strike anyone
  who hasn't spotted you) for a silent, instant kill. Botch it in the open and
  it turns into a noisy brawl.
- **Open combat** — trade blows with attack/defense math, block to quarter
  incoming damage, and unlock **Counter Strike** to riposte a parried blow.
- **Parkour & rooftops** — climb onto building rooftops where ground guards
  can't reach or easily see you, and where arrows fly harmlessly below.
- **Synchronization viewpoints** — perch on high points to chart the city and
  push back the fog of war (XP reward included).
- **RPG progression** — earn XP from kills, viewpoints and contracts; level up
  to raise HP/attack and earn skill points.
- **Skill tree** — three branches (*Assassin*, *Combat*, *Agility*) with
  prerequisites and real gameplay effects (stealth, durability, air
  assassination, eagle vision, safe-fall, and more).
- **Contracts** — assassinate the marked targets, with optional bonus
  objectives like *never be detected* and *synchronize viewpoints*.
- **Save & continue** — save your progress from the pause menu; the title
  screen offers **Continue** to pick up where you left off.
- **Title-screen menu** — a navigable main menu (Continue / New Game /
  Controls / Quit) with keyboard *and* mouse support.
- **Procedural sound** — every effect (blade strike, assassination, alarm,
  arrow, viewpoint chime, level-up, …) is synthesized at runtime from raw
  samples — no audio asset files. Press **M** to mute.
- **Procedural city** — buildings, streets, a canal with bridges, courtyards,
  haystacks (hide while crouched), fog of war and a live minimap. Use
  `--seed` for a reproducible layout.

## Install & run

```bash
pip install -r requirements.txt
python play.py            # random city
python play.py --seed 42  # reproducible layout
```

> The game opens a window and needs a display. Run it on your local machine
> (not a headless server). On Linux you may need system SDL libraries that
> ship with the `pygame` wheel automatically.

## Controls

| Key | Action |
| --- | --- |
| `W A S D` / Arrows | Move |
| `Shift` | Sprint (fast, but easy to spot) |
| `Ctrl` | Sneak / crouch (slow, quiet; hide inside haystacks) |
| `Space` | Strike — assassinate if unseen or from behind, else attack |
| `F` | Block / parry |
| `E` | Climb up/down · Synchronize a viewpoint |
| `Tab` | Open the skill tree (spend points with number keys) |
| `Esc` | Pause (save with `S` from the pause menu) |
| `M` | Mute / unmute |
| `Enter` | Confirm menu selection · start a new contract after win/lose |
| `↑` / `↓` / mouse | Navigate the main menu |

## How to play

1. **Stay unseen.** The eye at the top of the screen shows the highest alert
   level any guard has on you — green (hidden), amber (suspicious), red
   (detected). Crouch to move quietly and duck into golden haystacks to vanish.
2. **Assassinate your targets** (magenta markers / minimap dots). Approach from
   behind while they're unaware and press `Space` for a silent kill.
3. **Use the rooftops.** Press `E` next to a building to climb. Guards lose you
   up top. Find glowing **viewpoints** and press `E` to synchronize.
4. **Grow stronger.** Spend skill points in the `Tab` menu. Unlock
   *Leap of Faith Strike* to assassinate from rooftops, or *Counter Strike* to
   punish attackers.
5. **Fulfill every contract** to win. Try to finish without ever being detected
   for the *Ghost* bonus.

## Project layout

```
assassin/
  config.py            # all tunable constants & colors (no pygame import)
  world.py             # procedural city, tiles, fog of war, queries
  camera.py            # smooth follow camera
  audio.py             # procedural sound-effect synthesis (fails safe headless)
  game.py              # main loop, rendering, input, menus, save/load, flow
  entities/
    entity.py          # base collidable actor
    player.py          # movement modes, climbing, stealth, skills
    guard.py           # guard/archer/brute AI: vision & detection states
    projectile.py      # arrows fired by archers
  systems/             # pure logic — no pygame, fully unit tested
    stats.py           # HP, XP curve, leveling
    detection.py       # vision cones, line of sight, detection meter
    combat.py          # assassination & open-combat resolution
    skills.py          # skill tree with prerequisites & effects
    quests.py          # contracts, objectives, quest log
    save.py            # serialize/deserialize stats, skills & contracts
  ui/
    hud.py             # HUD, minimap, skill-tree & menu screens
tests/                 # 66 tests (logic + headless integration smoke tests)
play.py                # entry point
```

The **`systems/` package contains all gameplay rules and has no pygame
dependency**, so it is exercised by fast, deterministic unit tests. The
rendering and entity code is covered by headless integration smoke tests that
run pygame under the dummy SDL driver.

## Running the tests

```bash
pip install pytest
SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy python -m pytest -q
```

(The `conftest.py` sets the dummy drivers automatically, so plain
`pytest -q` works too.)

## Design notes

- **Two-layer world.** Tiles carry a ground type plus a boolean *roof* layer.
  The player swaps layers by climbing; guards are confined to the ground, which
  makes rooftops a safe haven — a deliberate nod to the source material.
- **Latching detection.** The detection meter latches to `ALERT` so a guard who
  spots you commits to the chase and only relents once the meter fully drains.
- **Pure logic vs. rendering.** Keeping rules out of the render loop makes the
  game both testable and easy to retune from `config.py`.
