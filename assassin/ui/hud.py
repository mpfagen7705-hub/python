"""HUD: health, XP, the detection "eye", objectives, minimap and menus."""

from __future__ import annotations

import math

import pygame

from .. import config
from ..systems.detection import Awareness
from ..systems.skills import Branch


def _bar(surface, x, y, w, h, frac, fg, bg):
    pygame.draw.rect(surface, bg, (x, y, w, h), border_radius=3)
    fw = int(w * max(0.0, min(1.0, frac)))
    if fw > 0:
        pygame.draw.rect(surface, fg, (x, y, fw, h), border_radius=3)


def draw_hud(surface, fonts, player, quest_log, notoriety, peak_awareness):
    font, big, small = fonts["font"], fonts["big"], fonts["small"]
    st = player.stats

    # --- top-left: health + xp + level -----------------------------------
    panel = pygame.Surface((250, 86), pygame.SRCALPHA)
    panel.fill((*config.C_HUD_BG, 200))
    surface.blit(panel, (12, 12))
    surface.blit(small.render(f"Lvl {st.level}", True, config.C_GOLD), (22, 18))
    surface.blit(small.render(f"HP {st.hp}/{st.max_hp}", True, config.C_HUD_TEXT), (80, 18))
    _bar(surface, 22, 38, 228, 12, st.hp / max(1, st.max_hp), config.C_HUD_HP, config.C_HUD_HP_BG)
    _bar(surface, 22, 58, 228, 8, st.level_progress(), config.C_HUD_XP, (30, 40, 55))
    surface.blit(small.render(f"XP to next: {st.xp_to_next()}", True, config.C_HUD_DIM), (22, 70))
    if st.skill_points > 0:
        surface.blit(small.render(f"{st.skill_points} skill pt(s) — press TAB",
                                  True, config.C_GOLD), (270, 18))

    # --- detection eye (top-center) --------------------------------------
    cx, cy = config.SCREEN_WIDTH // 2, 40
    color = {
        Awareness.UNAWARE: config.C_VISION_CALM,
        Awareness.SUSPICIOUS: config.C_VISION_SUS,
        Awareness.ALERT: config.C_VISION_ALERT,
    }[peak_awareness]
    pygame.draw.circle(surface, (0, 0, 0), (cx, cy), 20)
    pygame.draw.circle(surface, color, (cx, cy), 18, 3)
    pygame.draw.circle(surface, color, (cx, cy), 6)
    label = {
        Awareness.UNAWARE: "HIDDEN",
        Awareness.SUSPICIOUS: "SUSPICIOUS",
        Awareness.ALERT: "DETECTED!",
    }[peak_awareness]
    surface.blit(small.render(label, True, color), (cx - small.size(label)[0] // 2, cy + 22))
    if player.hidden:
        h = "IN COVER"
        surface.blit(small.render(h, True, config.C_HAYSTACK),
                     (cx - small.size(h)[0] // 2, cy + 38))

    # --- objectives (top-right) ------------------------------------------
    ox = config.SCREEN_WIDTH - 300
    surface.blit(small.render("CONTRACTS", True, config.C_GOLD), (ox, 16))
    y = 38
    for c in quest_log.contracts:
        mark = "✓" if c.complete else ("✗" if c.status.name == "FAILED" else "•")
        surface.blit(small.render(f"{mark} {c.name}", True, config.C_HUD_TEXT), (ox, y))
        y += 18
        for obj in c.objectives:
            done = obj.status.name == "COMPLETE"
            col = config.C_VISION_CALM if done else config.C_HUD_DIM
            txt = f"   - {obj.description} ({obj.progress}/{obj.required})"
            surface.blit(small.render(txt, True, col), (ox, y))
            y += 16
        y += 4

    # --- notoriety (bottom-left) -----------------------------------------
    surface.blit(small.render(f"Notoriety: {'★' * notoriety}{'☆' * (3 - notoriety)}",
                              True, config.C_GUARD_SUS), (16, config.SCREEN_HEIGHT - 28))

    # --- controls hint ----------------------------------------------------
    hint = "WASD move  |  Shift sprint  |  Ctrl sneak  |  Space strike  |  E climb/interact  |  Tab skills"
    surface.blit(small.render(hint, True, config.C_HUD_DIM),
                 (config.SCREEN_WIDTH // 2 - small.size(hint)[0] // 2,
                  config.SCREEN_HEIGHT - 24))


def draw_minimap(surface, world, player, guards, targets):
    mm_w, mm_h = 168, 130
    mx, my = config.SCREEN_WIDTH - mm_w - 12, config.SCREEN_HEIGHT - mm_h - 12
    scale_x = mm_w / world.cols
    scale_y = mm_h / world.rows
    mini = pygame.Surface((mm_w, mm_h))
    mini.fill(config.C_FOG)
    for r in range(world.rows):
        for c in range(world.cols):
            if not world.explored[r][c]:
                continue
            t = world.grid[r][c]
            col = {
                config.T_STREET: (70, 66, 60),
                config.T_WALL: (110, 100, 88),
                config.T_HAYSTACK: config.C_HAYSTACK,
                config.T_WATER: config.C_WATER,
                config.T_GARDEN: config.C_GARDEN,
            }.get(t, (70, 66, 60))
            pygame.draw.rect(mini, col, (c * scale_x, r * scale_y,
                                         math.ceil(scale_x), math.ceil(scale_y)))
    for vp in world.viewpoints:
        if world.explored[vp[1]][vp[0]]:
            pygame.draw.circle(mini, config.C_VIEWPOINT,
                               (int(vp[0] * scale_x), int(vp[1] * scale_y)), 3)
    for t in targets:
        if not t.dead:
            tc, tr = world.tile_at_px(t.x, t.y)
            pygame.draw.circle(mini, config.C_TARGET,
                               (int(tc * scale_x), int(tr * scale_y)), 3)
    pc, pr = world.tile_at_px(player.x, player.y)
    pygame.draw.circle(mini, config.C_PLAYER, (int(pc * scale_x), int(pr * scale_y)), 3)
    surface.blit(mini, (mx, my))
    pygame.draw.rect(surface, (90, 84, 76), (mx, my, mm_w, mm_h), 2)


def draw_skill_tree(surface, fonts, player):
    font, big, small = fonts["font"], fonts["big"], fonts["small"]
    overlay = pygame.Surface((config.SCREEN_WIDTH, config.SCREEN_HEIGHT), pygame.SRCALPHA)
    overlay.fill((6, 6, 10, 235))
    surface.blit(overlay, (0, 0))
    title = "SKILL TREE"
    surface.blit(big.render(title, True, config.C_GOLD),
                 (config.SCREEN_WIDTH // 2 - big.size(title)[0] // 2, 30))
    surface.blit(font.render(f"Skill points: {player.stats.skill_points}", True, config.C_HUD_TEXT),
                 (config.SCREEN_WIDTH // 2 - 80, 76))

    branches = [Branch.ASSASSIN, Branch.COMBAT, Branch.AGILITY]
    col_w = config.SCREEN_WIDTH // 3
    hotkey = 1
    keymap = {}
    for i, branch in enumerate(branches):
        bx = i * col_w + 40
        surface.blit(font.render(branch, True, config.C_HUD_XP), (bx, 120))
        y = 160
        for skill in player.skills.by_branch(branch):
            unlocked = player.skills.is_unlocked(skill.key)
            can = player.skills.can_unlock(skill.key, player.stats)
            if unlocked:
                col, tag = config.C_VISION_CALM, "[OWNED]"
            elif can:
                col, tag = config.C_GOLD, f"[{hotkey}] unlock"
                keymap[hotkey] = skill.key
                hotkey += 1
            else:
                col, tag = config.C_HUD_DIM, "[locked]"
            surface.blit(font.render(f"{skill.name}  {tag}", True, col), (bx, y))
            y += 22
            # wrap description
            for line in _wrap(skill.description, 34):
                surface.blit(small.render(line, True, config.C_HUD_DIM), (bx + 10, y))
                y += 16
            y += 12
    foot = "Press number keys to unlock  |  TAB / ESC to resume"
    surface.blit(small.render(foot, True, config.C_HUD_DIM),
                 (config.SCREEN_WIDTH // 2 - small.size(foot)[0] // 2,
                  config.SCREEN_HEIGHT - 36))
    return keymap


def draw_center_message(surface, fonts, title, subtitle, color=config.C_GOLD):
    font, big, small = fonts["font"], fonts["big"], fonts["small"]
    overlay = pygame.Surface((config.SCREEN_WIDTH, config.SCREEN_HEIGHT), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 200))
    surface.blit(overlay, (0, 0))
    surface.blit(big.render(title, True, color),
                 (config.SCREEN_WIDTH // 2 - big.size(title)[0] // 2, config.SCREEN_HEIGHT // 2 - 60))
    for i, line in enumerate(subtitle.split("\n")):
        surface.blit(font.render(line, True, config.C_HUD_TEXT),
                     (config.SCREEN_WIDTH // 2 - font.size(line)[0] // 2,
                      config.SCREEN_HEIGHT // 2 + i * 28))


def _wrap(text, width):
    words = text.split()
    lines, cur = [], ""
    for w in words:
        if len(cur) + len(w) + 1 <= width:
            cur = f"{cur} {w}".strip()
        else:
            lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines
