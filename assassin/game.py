"""The playable game: rendering, input, state machine and mission flow.

This module owns everything pygame-facing. Gameplay rules live in the pure
``systems`` package; this file orchestrates them, draws the world and entities,
and threads input through to the player and menus.
"""

from __future__ import annotations

import json
import math
import os
import random
import sys

import pygame

from . import config, world as worldmod
from .audio import SoundFX
from .camera import Camera
from .entities.guard import Guard, GuardKind, GuardState
from .entities.player import MoveMode, Player
from .entities.projectile import Projectile
from .systems import combat, save as savesys
from .systems.detection import Awareness, in_vision_cone, line_of_sight
from .systems.quests import Contract, Objective, QuestLog
from .ui import hud

SAVE_PATH = os.path.join(os.path.expanduser("~"), ".assassins_reverie_save.json")


class State:
    MENU = "menu"
    CONTROLS = "controls"
    PLAYING = "playing"
    SKILLS = "skills"
    PAUSED = "paused"
    GAMEOVER = "gameover"
    VICTORY = "victory"


class Game:
    def __init__(self, seed=None):
        pygame.init()
        pygame.display.set_caption(config.TITLE)
        self.screen = pygame.display.set_mode((config.SCREEN_WIDTH, config.SCREEN_HEIGHT))
        self.clock = pygame.time.Clock()
        self.fonts = {
            "small": pygame.font.SysFont("consolas,menlo,monospace", 15),
            "font": pygame.font.SysFont("consolas,menlo,monospace", 19),
            "big": pygame.font.SysFont("consolas,menlo,monospace", 48, bold=True),
        }
        self.audio = SoundFX()
        self.seed = seed if seed is not None else random.randint(0, 1_000_000)
        self.state = State.MENU
        self._skill_keymap = {}
        self.menu_index = 0
        self.reset()

    # ------------------------------------------------------------------ setup
    def reset(self):
        self.world = worldmod.generate(self.seed)
        cx, cy = self.world.tile_center_px(*self.world.player_start)
        self.player = Player(cx, cy)
        self.camera = Camera(self.world)
        self.guards: list[Guard] = []
        self.targets: list[Guard] = []
        self.projectiles: list[Projectile] = []
        self.synced: set = set()
        self.notoriety = 0
        self.peak_awareness = Awareness.UNAWARE
        self._prev_awareness = Awareness.UNAWARE
        self._prev_hp = self.player.stats.hp
        self.message = ""
        self.message_timer = 0.0
        self._awarded: set = set()
        self._ghost_intact = True

        self._spawn_guards()
        self._spawn_targets()
        self._build_contracts()
        self.world.reveal_px(self.player.x, self.player.y, 6)

    def _rand_streets(self, rng, n, far_from=None, min_dist=0):
        pool = list(self.world.street_tiles)
        rng.shuffle(pool)
        out = []
        for (c, r) in pool:
            x, y = self.world.tile_center_px(c, r)
            if far_from and math.hypot(x - far_from[0], y - far_from[1]) < min_dist:
                continue
            out.append((c, r))
            if len(out) >= n:
                break
        return out

    def _spawn_guards(self):
        rng = random.Random(self.seed + 1)
        start = (self.player.x, self.player.y)
        kinds = (
            [GuardKind.GUARD] * config.NUM_GUARDS
            + [GuardKind.ARCHER] * config.NUM_ARCHERS
            + [GuardKind.BRUTE] * config.NUM_BRUTES
        )
        anchors = self._rand_streets(rng, len(kinds), far_from=start, min_dist=260)
        for kind, (c, r) in zip(kinds, anchors):
            x, y = self.world.tile_center_px(c, r)
            # Build a small patrol loop from nearby street tiles.
            wps = [(x, y)]
            for _ in range(2):
                nc, nr = c + rng.randint(-4, 4), r + rng.randint(-4, 4)
                if self.world.walkable_ground(nc, nr):
                    wps.append(self.world.tile_center_px(nc, nr))
            g = Guard(x, y, waypoints=wps, kind=kind)
            if g.ranged:
                g.on_shoot = self._enemy_shoot
            self.guards.append(g)

    def _enemy_shoot(self, archer, player):
        ang = math.atan2(player.y - archer.y, player.x - archer.x)
        self.projectiles.append(Projectile(archer.x, archer.y, ang, archer.stats.attack))
        self.audio.play("arrow")

    def _spawn_targets(self):
        rng = random.Random(self.seed + 2)
        spots = self.world.courtyards or self._rand_streets(rng, 3)
        rng.shuffle(spots)
        names = ["The Magistrate", "The Merchant-Prince", "The Inquisitor"]
        for i, (c, r) in enumerate(spots[:3]):
            x, y = self.world.tile_center_px(c, r)
            # Targets pace a tight loop and are guarded by their station.
            wps = [(x, y), (x + 60, y), (x + 60, y + 60), (x, y + 60)]
            t = Guard(x, y, waypoints=[p for p in wps if self.world.walkable_ground_px(*p)] or [(x, y)])
            t.is_target = True
            t.color = config.C_TARGET
            t.name = names[i] if i < len(names) else f"Target {i+1}"
            self.targets.append(t)

    def _build_contracts(self):
        self.quest_log = QuestLog()
        n = len(self.targets)
        self.quest_log.add(Contract(
            "creed", "Order of the Ancients",
            "Eliminate the marked targets across the city.",
            objectives=[
                Objective("eliminate", "Assassinate the targets", required=max(1, n)),
                Objective("ghost", "Bonus: never be detected", required=1, optional=True),
            ],
            reward_xp=config.XP_CONTRACT,
        ))
        vp_needed = min(3, max(1, len(self.world.viewpoints)))
        self.quest_log.add(Contract(
            "eyes", "Eyes of the City",
            "Synchronize viewpoints to chart the streets below.",
            objectives=[Objective("sync", "Synchronize viewpoints", required=vp_needed)],
            reward_xp=config.XP_CONTRACT // 2,
        ))

    # ------------------------------------------------------------------ loop
    def run(self):
        while True:
            dt = self.clock.tick(config.FPS) / 1000.0
            dt = min(dt, 0.05)  # clamp to avoid tunneling on lag spikes
            self._handle_events()
            if self.state == State.PLAYING:
                self._update(dt)
            self._draw()
            pygame.display.flip()

    # --------------------------------------------------------------- events
    def _handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self._quit()
            if self.state == State.MENU and event.type in (pygame.MOUSEBUTTONDOWN, pygame.MOUSEMOTION):
                self._menu_mouse(event)
                continue
            if event.type != pygame.KEYDOWN:
                continue
            k = event.key
            if k == pygame.K_m:  # global mute toggle
                self.audio.toggle_mute()
                continue
            if self.state == State.MENU:
                self._menu_keys(k)
            elif self.state == State.CONTROLS:
                if k in (pygame.K_ESCAPE, pygame.K_RETURN, pygame.K_BACKSPACE):
                    self.state = State.MENU
            elif self.state == State.PLAYING:
                if k == pygame.K_ESCAPE:
                    self.state = State.PAUSED
                elif k == pygame.K_TAB:
                    self.state = State.SKILLS
                elif k == pygame.K_SPACE:
                    self._attempt_attack()
                elif k == pygame.K_e:
                    self._interact()
            elif self.state == State.SKILLS:
                if k in (pygame.K_TAB, pygame.K_ESCAPE):
                    self.state = State.PLAYING
                elif pygame.K_1 <= k <= pygame.K_9:
                    self._unlock_skill(k - pygame.K_0)
            elif self.state == State.PAUSED:
                if k in (pygame.K_ESCAPE, pygame.K_RETURN):
                    self.state = State.PLAYING
                elif k == pygame.K_s:
                    if self.save_to_file():
                        self._flash("Progress saved.")
                        self.audio.play("select")
                elif k == pygame.K_q:
                    self.state = State.MENU
            elif self.state in (State.GAMEOVER, State.VICTORY):
                if k == pygame.K_RETURN:
                    self.seed = random.randint(0, 1_000_000)
                    self.reset()
                    self.state = State.PLAYING
                elif k in (pygame.K_ESCAPE, pygame.K_q):
                    self.state = State.MENU

    # --- main menu --------------------------------------------------------
    def _menu_actions(self):
        actions = []
        if self.has_save():
            actions.append(("Continue", "continue"))
        actions.append(("New Game", "new"))
        actions.append(("Controls", "controls"))
        actions.append(("Quit", "quit"))
        return actions

    def _menu_keys(self, k):
        actions = self._menu_actions()
        if k in (pygame.K_UP, pygame.K_w):
            self.menu_index = (self.menu_index - 1) % len(actions)
            self.audio.play("menu")
        elif k in (pygame.K_DOWN, pygame.K_s):
            self.menu_index = (self.menu_index + 1) % len(actions)
            self.audio.play("menu")
        elif k in (pygame.K_RETURN, pygame.K_SPACE):
            self._select_menu(actions[self.menu_index][1])
        elif k == pygame.K_ESCAPE:
            self._quit()

    def _menu_mouse(self, event):
        for i, rect in enumerate(getattr(self, "_menu_rects", [])):
            if rect.collidepoint(event.pos):
                if event.type == pygame.MOUSEMOTION and self.menu_index != i:
                    self.menu_index = i
                    self.audio.play("menu")
                elif event.type == pygame.MOUSEBUTTONDOWN:
                    self.menu_index = i
                    self._select_menu(self._menu_actions()[i][1])

    def _select_menu(self, action):
        self.audio.play("select")
        if action == "continue":
            if self.load_from_file():
                self.state = State.PLAYING
        elif action == "new":
            self.seed = random.randint(0, 1_000_000)
            self.reset()
            self.state = State.PLAYING
        elif action == "controls":
            self.state = State.CONTROLS
        elif action == "quit":
            self._quit()

    # --- save / load ------------------------------------------------------
    def has_save(self) -> bool:
        return os.path.exists(SAVE_PATH)

    def to_save_dict(self) -> dict:
        return {
            "version": savesys.SAVE_VERSION,
            "seed": self.seed,
            "stats": savesys.dump_stats(self.player.stats),
            "skills": savesys.dump_skills(self.player.skills),
            "player_pos": [self.player.x, self.player.y],
            "on_roof": self.player.on_roof,
            "synced": [list(vp) for vp in self.synced],
            "dead_targets": [i for i, t in enumerate(self.targets) if t.dead],
            "dead_guards": [i for i, g in enumerate(self.guards) if g.dead],
            "contracts": [savesys.dump_contract(c) for c in self.quest_log.contracts],
            "notoriety": self.notoriety,
            "ghost": self._ghost_intact,
        }

    def save_to_file(self, path=SAVE_PATH) -> bool:
        try:
            with open(path, "w") as fh:
                json.dump(self.to_save_dict(), fh)
            return True
        except OSError:
            return False

    def apply_save_dict(self, data: dict) -> None:
        self.seed = data["seed"]
        self.reset()
        savesys.load_stats(self.player.stats, data["stats"])
        savesys.load_skills(self.player.skills, data["skills"], self.player)
        self.player.x, self.player.y = data["player_pos"]
        self.player.on_roof = data.get("on_roof", False)
        self.synced = {tuple(vp) for vp in data.get("synced", [])}
        for vp in self.synced:
            self.world.reveal(vp[0], vp[1], 11)
        for i in data.get("dead_targets", []):
            if i < len(self.targets):
                self.targets[i].dead = True
                self._awarded.add(id(self.targets[i]))
        for i in data.get("dead_guards", []):
            if i < len(self.guards):
                self.guards[i].dead = True
                self._awarded.add(id(self.guards[i]))
        by_key = {c["key"]: c for c in data.get("contracts", [])}
        for c in self.quest_log.contracts:
            if c.key in by_key:
                savesys.load_contract(c, by_key[c.key])
        self.notoriety = data.get("notoriety", 0)
        self._ghost_intact = data.get("ghost", True)
        self._prev_hp = self.player.stats.hp

    def load_from_file(self, path=SAVE_PATH) -> bool:
        try:
            with open(path) as fh:
                data = json.load(fh)
            if data.get("version") != savesys.SAVE_VERSION:
                return False
            self.apply_save_dict(data)
            return True
        except (OSError, ValueError, KeyError):
            return False

    def _delete_save(self):
        try:
            if os.path.exists(SAVE_PATH):
                os.remove(SAVE_PATH)
        except OSError:
            pass

    def _quit(self):
        pygame.quit()
        sys.exit(0)

    # --------------------------------------------------------------- update
    def _read_movement(self):
        keys = pygame.key.get_pressed()
        dx = keys[pygame.K_d] + keys[pygame.K_RIGHT] - keys[pygame.K_a] - keys[pygame.K_LEFT]
        dy = keys[pygame.K_s] + keys[pygame.K_DOWN] - keys[pygame.K_w] - keys[pygame.K_UP]
        if keys[pygame.K_LSHIFT] or keys[pygame.K_RSHIFT]:
            mode = MoveMode.SPRINT
        elif keys[pygame.K_LCTRL] or keys[pygame.K_RCTRL]:
            mode = MoveMode.CROUCH
        else:
            mode = MoveMode.WALK
        blocking = keys[pygame.K_f]
        return dx, dy, mode, blocking

    def _update(self, dt):
        dx, dy, mode, blocking = self._read_movement()
        self.player.set_intent(dx, dy, mode, blocking)
        self.player.update(dt, self.world)
        self.world.reveal_px(self.player.x, self.player.y, 5 if not self.player.on_roof else 7)

        enemies = self.guards + self.targets
        self.peak_awareness = Awareness.UNAWARE
        for g in enemies:
            g.update(dt, self.player, self.world)
            if g.meter.state.value > self.peak_awareness.value:
                self.peak_awareness = g.meter.state

        if self.peak_awareness is Awareness.ALERT:
            self._ghost_intact = False
            self.notoriety = min(3, max(self.notoriety, 1 + len(
                [g for g in enemies if g.state == GuardState.ALERT]) // 4))
        # Alarm sting on the rising edge of being detected.
        if (self.peak_awareness is Awareness.ALERT
                and self._prev_awareness is not Awareness.ALERT):
            self.audio.play("alert")
        self._prev_awareness = self.peak_awareness

        # Arrows in flight.
        for p in self.projectiles:
            p.update(dt, self.world, self.player)
        self.projectiles = [p for p in self.projectiles if p.alive]

        # Wince when the player loses health (melee or arrow).
        if self.player.stats.hp < self._prev_hp:
            self.audio.play("hurt")
        self._prev_hp = self.player.stats.hp

        self._reconcile_deaths()
        self.camera.follow(self.player, dt)

        # contract rewards & win/lose checks
        earned = self.quest_log.collect_rewards()
        if earned:
            self._grant_xp(earned)
        if not self.player.stats.alive:
            if self.state != State.GAMEOVER:
                self.audio.play("death")
            self.state = State.GAMEOVER
        elif self._check_victory():
            if self.state != State.VICTORY:
                self.audio.play("sync")
                self._delete_save()  # contracts done — clear the slot
            self.state = State.VICTORY

        if self.message_timer > 0:
            self.message_timer -= dt
            if self.message_timer <= 0:
                self.message = ""

    def _check_victory(self):
        creed = self.quest_log.contracts[0]
        elim = creed.objective("eliminate")
        if elim and elim.done and self._ghost_intact:
            ghost = creed.objective("ghost")
            if ghost and not ghost.done:
                ghost.advance()
                self._grant_xp(250)
                self._flash("Bonus: Ghost — never detected!  +250 XP")
        return self.quest_log.all_complete()

    def _reconcile_deaths(self):
        for g in self.guards + self.targets:
            if g.stats.hp <= 0:
                g.dead = True
            if g.dead and id(g) not in self._awarded:
                self._awarded.add(id(g))
                xp = config.XP_ASSASSINATION if g._assassinated else config.XP_KILL
                self._grant_xp(xp)
                if g.is_target:
                    self.quest_log.contracts[0].advance("eliminate")
                    self.audio.play("select")
                    self._flash(f"{getattr(g, 'name', 'Target')} eliminated!  +{xp} XP")

    # --------------------------------------------------------------- actions
    def _living_enemies(self):
        return [g for g in self.guards + self.targets if not g.dead]

    def _attempt_attack(self):
        enemies = self._living_enemies()
        if not enemies:
            return
        nearest = min(enemies, key=self.player.distance_to)
        dist = self.player.distance_to(nearest)

        # Air assassination from a rooftop.
        if self.player.on_roof and self.player.can_air_assassinate and dist <= config.ASSASSINATE_RANGE * 1.8:
            self._assassinate(nearest)
            self.player.on_roof = False
            return

        if self.player.on_roof:
            return  # no ground melee while perched

        if dist <= config.ASSASSINATE_RANGE:
            unaware = nearest.meter.state is Awareness.UNAWARE
            behind = combat.is_behind(self.player.pos, nearest.pos, nearest.facing, config.ASSASSINATE_ARC)
            if unaware or behind:
                self._assassinate(nearest)
                return

        # Open combat.
        if dist <= config.GUARD_ATTACK_RANGE + 6:
            self.player.face_towards(nearest.x, nearest.y)
            res = combat.resolve_attack(self.player.stats, nearest.stats)
            self.audio.play("hit")
            if res.lethal:
                nearest.dead = True

    def _assassinate(self, target):
        target._assassinated = True
        combat.resolve_attack(self.player.stats, target.stats,
                              assassination=True, defender_aware=False)
        target.dead = True
        self.audio.play("assassinate")

    def _interact(self):
        # Synchronize a viewpoint when perched on one.
        if self.player.on_roof:
            c, r = self.world.tile_at_px(self.player.x, self.player.y)
            for vp in self.world.viewpoints:
                if abs(vp[0] - c) <= 1 and abs(vp[1] - r) <= 1 and vp not in self.synced:
                    self.synced.add(vp)
                    radius = 16 if self.player.eagle_vision else 11
                    self.world.reveal(vp[0], vp[1], radius)
                    self._grant_xp(config.XP_VIEWPOINT)
                    self.quest_log.contracts[1].advance("sync")
                    self.audio.play("sync")
                    self._flash(f"Viewpoint synchronized!  +{config.XP_VIEWPOINT} XP")
                    return
        # Otherwise attempt to climb up/down.
        self.player.try_climb(self.world)

    def _unlock_skill(self, number):
        key = self._skill_keymap.get(number)
        if key and self.player.skills.unlock(key, self.player.stats, self.player):
            self.audio.play("select")
            self._flash(f"Unlocked: {self.player.skills.get(key).name}")

    def _grant_xp(self, amount):
        levels = self.player.stats.add_xp(amount)
        if levels:
            self.audio.play("levelup")
            self._flash(f"LEVEL UP!  Now level {self.player.stats.level}  (TAB for skills)")

    def _flash(self, text, secs=3.0):
        self.message = text
        self.message_timer = secs

    # ----------------------------------------------------------------- draw
    def _draw(self):
        self.screen.fill(config.C_FOG)
        if self.state == State.MENU:
            self._draw_menu()
            return
        if self.state == State.CONTROLS:
            self._draw_controls()
            return
        self._draw_world()
        self._draw_vision_cones()
        self._draw_entities()
        self._draw_projectiles()
        self._draw_prompts()
        hud.draw_hud(self.screen, self.fonts, self.player, self.quest_log,
                     self.notoriety, self.peak_awareness)
        hud.draw_minimap(self.screen, self.world, self.player, self.guards, self.targets)
        if self.audio.muted:
            self.screen.blit(self.fonts["small"].render("muted (M)", True, config.C_HUD_DIM),
                             (12, 104))
        if self.message:
            self._draw_flash()

        if self.state == State.SKILLS:
            self._skill_keymap = hud.draw_skill_tree(self.screen, self.fonts, self.player)
        elif self.state == State.PAUSED:
            hud.draw_center_message(self.screen, self.fonts, "PAUSED",
                                    "ENTER resume   •   S save   •   Q main menu")
        elif self.state == State.GAMEOVER:
            hud.draw_center_message(self.screen, self.fonts, "CAUGHT",
                                    "You fell to the city guard.\nENTER new contract   •   Q main menu",
                                    color=config.C_GUARD_ALERT)
        elif self.state == State.VICTORY:
            hud.draw_center_message(self.screen, self.fonts, "VICTORY",
                                    "Every contract fulfilled. The Creed endures.\nENTER new city   •   Q main menu",
                                    color=config.C_VIEWPOINT)

    def _draw_menu(self):
        big, font, small = self.fonts["big"], self.fonts["font"], self.fonts["small"]
        t = config.TITLE
        self.screen.blit(big.render(t, True, config.C_GOLD),
                         (config.SCREEN_WIDTH // 2 - big.size(t)[0] // 2, 130))
        tag = "A 2D stealth-action RPG — strike from the shadows, vanish across the rooftops."
        self.screen.blit(font.render(tag, True, config.C_HUD_DIM),
                         (config.SCREEN_WIDTH // 2 - font.size(tag)[0] // 2, 200))

        actions = self._menu_actions()
        self.menu_index = max(0, min(self.menu_index, len(actions) - 1))
        self._menu_rects = []
        for i, (label, _) in enumerate(actions):
            selected = i == self.menu_index
            col = config.C_GOLD if selected else config.C_HUD_TEXT
            text = f">  {label}  <" if selected else label
            surf = font.render(text, True, col)
            x = config.SCREEN_WIDTH // 2 - surf.get_width() // 2
            y = 300 + i * 46
            self.screen.blit(surf, (x, y))
            # Clickable region (use a stable width centered on screen).
            self._menu_rects.append(pygame.Rect(config.SCREEN_WIDTH // 2 - 140, y - 6, 280, 38))

        foot = "↑/↓ or mouse to choose · Enter to select · M mute"
        self.screen.blit(small.render(foot, True, config.C_HUD_DIM),
                         (config.SCREEN_WIDTH // 2 - small.size(foot)[0] // 2,
                          config.SCREEN_HEIGHT - 60))

    def _draw_controls(self):
        big, font, small = self.fonts["big"], self.fonts["font"], self.fonts["small"]
        title = "CONTROLS"
        self.screen.blit(big.render(title, True, config.C_GOLD),
                         (config.SCREEN_WIDTH // 2 - big.size(title)[0] // 2, 70))
        rows = [
            ("W A S D / Arrows", "Move"),
            ("Shift", "Sprint (fast, but easy to spot)"),
            ("Ctrl", "Sneak / crouch — hide inside haystacks"),
            ("Space", "Strike — assassinate if unseen/behind, else attack"),
            ("F", "Block / parry (unlock Counter Strike to riposte)"),
            ("E", "Climb up/down · Synchronize a viewpoint"),
            ("Tab", "Skill tree (spend points with number keys)"),
            ("Esc", "Pause (save from the pause menu)"),
            ("M", "Mute / unmute"),
        ]
        y = 170
        for key, desc in rows:
            self.screen.blit(font.render(key, True, config.C_HUD_XP), (200, y))
            self.screen.blit(font.render(desc, True, config.C_HUD_TEXT), (440, y))
            y += 40
        tips = [
            "Enemies: red guards (melee) · blue archers (ranged) · big orange brutes (heavy).",
            "Rooftops are safe — guards can't follow or easily see you up high.",
        ]
        for i, tip in enumerate(tips):
            self.screen.blit(small.render(tip, True, config.C_HUD_DIM),
                             (config.SCREEN_WIDTH // 2 - small.size(tip)[0] // 2, y + 10 + i * 22))
        foot = "Press ENTER or ESC to go back"
        self.screen.blit(small.render(foot, True, config.C_GOLD),
                         (config.SCREEN_WIDTH // 2 - small.size(foot)[0] // 2,
                          config.SCREEN_HEIGHT - 50))

    def _draw_projectiles(self):
        for p in self.projectiles:
            sx, sy = self.camera.to_screen(p.x, p.y)
            ex = sx - math.cos(p.facing) * 10
            ey = sy - math.sin(p.facing) * 10
            pygame.draw.line(self.screen, config.C_ARROW, (ex, ey), (sx, sy), 2)
            pygame.draw.circle(self.screen, config.C_ARROW, (int(sx), int(sy)), 2)

    def _draw_world(self):
        cam = self.camera
        c0 = max(0, int(cam.x // config.TILE))
        r0 = max(0, int(cam.y // config.TILE))
        c1 = min(self.world.cols, c0 + config.SCREEN_WIDTH // config.TILE + 2)
        r1 = min(self.world.rows, r0 + config.SCREEN_HEIGHT // config.TILE + 2)
        for r in range(r0, r1):
            for c in range(c0, c1):
                sx, sy = cam.to_screen(c * config.TILE, r * config.TILE)
                rect = (sx, sy, config.TILE, config.TILE)
                if not self.world.explored[r][c]:
                    pygame.draw.rect(self.screen, config.C_FOG, rect)
                    continue
                t = self.world.grid[r][c]
                base = {
                    config.T_STREET: config.C_STREET if (c + r) % 2 else config.C_STREET_ALT,
                    config.T_WALL: config.C_WALL,
                    config.T_HAYSTACK: config.C_HAYSTACK,
                    config.T_WATER: config.C_WATER,
                    config.T_GARDEN: config.C_GARDEN,
                }.get(t, config.C_STREET)
                pygame.draw.rect(self.screen, base, rect)
                if self.world.roof[r][c]:
                    pygame.draw.rect(self.screen, config.C_ROOF, rect)
                    pygame.draw.rect(self.screen, config.C_ROOF_EDGE, rect, 1)
                if t == config.T_HAYSTACK:
                    pygame.draw.rect(self.screen, (150, 128, 50), rect, 2)
        # Viewpoints
        for vp in self.world.viewpoints:
            if self.world.explored[vp[1]][vp[0]]:
                wx, wy = self.world.tile_center_px(*vp)
                sx, sy = cam.to_screen(wx, wy)
                done = vp in self.synced
                col = config.C_VISION_CALM if done else config.C_VIEWPOINT
                pygame.draw.circle(self.screen, col, (int(sx), int(sy)), 9, 0 if done else 2)
                pygame.draw.circle(self.screen, (40, 40, 40), (int(sx), int(sy)), 11, 1)

    def _cone_polygon(self, guard):
        rng = guard.vision_range
        if guard.state in (GuardState.ALERT, GuardState.SEARCH):
            rng *= 1.15
        half = config.GUARD_VISION_FOV / 2
        pts = [guard.pos]
        rays = 16
        for i in range(rays + 1):
            a = guard.facing - half + config.GUARD_VISION_FOV * i / rays
            d, step = 0.0, 10.0
            px, py = guard.pos
            while d < rng:
                d += step
                px = guard.x + math.cos(a) * d
                py = guard.y + math.sin(a) * d
                cc, rr = self.world.tile_at_px(px, py)
                if self.world.blocks_sight(cc, rr):
                    break
            pts.append((px, py))
        return pts

    def _draw_vision_cones(self):
        cone_surf = pygame.Surface((config.SCREEN_WIDTH, config.SCREEN_HEIGHT), pygame.SRCALPHA)
        for g in self.guards + self.targets:
            if g.dead:
                continue
            poly = [self.camera.to_screen(x, y) for (x, y) in self._cone_polygon(g)]
            if len(poly) >= 3:
                col = g.vision_color
                pygame.draw.polygon(cone_surf, (*col, 55), poly)
        self.screen.blit(cone_surf, (0, 0))

    def _draw_entities(self):
        cam = self.camera
        for g in self.guards + self.targets:
            if g.dead:
                sx, sy = cam.to_screen(g.x, g.y)
                pygame.draw.circle(self.screen, (40, 30, 30), (int(sx), int(sy)), g.radius)
                pygame.draw.line(self.screen, (120, 30, 30),
                                 (sx - 8, sy - 8), (sx + 8, sy + 8), 2)
                continue
            sx, sy = cam.to_screen(g.x, g.y)
            color = g.color  # keeps each kind's identity while unaware
            if not g.is_target and g.meter.state is Awareness.SUSPICIOUS:
                color = config.C_GUARD_SUS
            elif not g.is_target and g.meter.state is Awareness.ALERT:
                color = config.C_GUARD_ALERT
            pygame.draw.circle(self.screen, color, (int(sx), int(sy)), g.radius)
            # facing nub
            fx = sx + math.cos(g.facing) * g.radius
            fy = sy + math.sin(g.facing) * g.radius
            pygame.draw.line(self.screen, (20, 20, 20), (sx, sy), (fx, fy), 3)
            if g.is_target:
                pygame.draw.circle(self.screen, config.C_TARGET, (int(sx), int(sy)), g.radius + 5, 2)
            # alert "!" bubble
            if g.meter.state is Awareness.ALERT:
                self.screen.blit(self.fonts["font"].render("!", True, config.C_GUARD_ALERT),
                                 (sx - 3, sy - g.radius - 20))
            elif g.meter.state is Awareness.SUSPICIOUS:
                self.screen.blit(self.fonts["font"].render("?", True, config.C_GUARD_SUS),
                                 (sx - 3, sy - g.radius - 20))

        # player
        psx, psy = cam.to_screen(self.player.x, self.player.y)
        pcol = config.C_PLAYER_CROUCH if self.player.mode == MoveMode.CROUCH else config.C_PLAYER
        if self.player.hidden:
            pcol = config.C_HAYSTACK
        pygame.draw.circle(self.screen, pcol, (int(psx), int(psy)), self.player.radius)
        if self.player.on_roof:
            pygame.draw.circle(self.screen, config.C_VIEWPOINT, (int(psx), int(psy)),
                               self.player.radius + 4, 2)
        # hidden blade
        bx = psx + math.cos(self.player.facing) * (self.player.radius + 8)
        by = psy + math.sin(self.player.facing) * (self.player.radius + 8)
        pygame.draw.line(self.screen, config.C_BLADE, (psx, psy), (bx, by), 3)
        if self.player.blocking:
            pygame.draw.circle(self.screen, (150, 180, 230), (int(psx), int(psy)),
                               self.player.radius + 6, 2)

    def _draw_prompts(self):
        # Contextual action hint above the player.
        prompt = None
        if self.player.on_roof:
            c, r = self.world.tile_at_px(self.player.x, self.player.y)
            on_vp = any(abs(vp[0] - c) <= 1 and abs(vp[1] - r) <= 1 and vp not in self.synced
                        for vp in self.world.viewpoints)
            prompt = "E: Synchronize" if on_vp else "E: Descend"
        else:
            c, r = self.world.tile_at_px(self.player.x, self.player.y)
            if any(self.world.walkable_roof(c + dc, r + dr)
                   for dc, dr in ((1, 0), (-1, 0), (0, 1), (0, -1))):
                prompt = "E: Climb"
            enemies = self._living_enemies()
            if enemies:
                nearest = min(enemies, key=self.player.distance_to)
                if self.player.distance_to(nearest) <= config.ASSASSINATE_RANGE:
                    unaware = nearest.meter.state is Awareness.UNAWARE
                    behind = combat.is_behind(self.player.pos, nearest.pos,
                                              nearest.facing, config.ASSASSINATE_ARC)
                    prompt = "SPACE: Assassinate" if (unaware or behind) else "SPACE: Attack"
        if prompt:
            psx, psy = self.camera.to_screen(self.player.x, self.player.y)
            surf = self.fonts["small"].render(prompt, True, config.C_BLADE)
            self.screen.blit(surf, (psx - surf.get_width() // 2, psy - self.player.radius - 22))

    def _draw_flash(self):
        surf = self.fonts["font"].render(self.message, True, config.C_GOLD)
        bg = pygame.Surface((surf.get_width() + 24, surf.get_height() + 12), pygame.SRCALPHA)
        bg.fill((0, 0, 0, 180))
        x = config.SCREEN_WIDTH // 2 - bg.get_width() // 2
        self.screen.blit(bg, (x, 96))
        self.screen.blit(surf, (x + 12, 102))
