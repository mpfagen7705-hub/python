"""Procedurally synthesized sound effects — no external asset files.

Every sound is generated at startup as raw 16-bit PCM samples and handed to
pygame as an in-memory buffer, so the game ships with audio but zero `.wav`
files. The whole subsystem fails safe: if the mixer can't initialize (e.g. a
headless machine), :class:`SoundFX` simply becomes a no-op.
"""

from __future__ import annotations

import array
import math
import random

SAMPLE_RATE = 44100


def _envelope(i: int, n: int, attack: float, decay: float) -> float:
    """A simple attack/decay amplitude envelope over sample ``i`` of ``n``."""
    t = i / n
    if t < attack:
        return t / attack if attack > 0 else 1.0
    # exponential-ish decay after the attack portion
    return max(0.0, (1.0 - (t - attack) / max(1e-6, (1.0 - attack)))) ** (1.0 + decay * 4)


def _tone(freq, dur, vol=0.4, shape="sine", attack=0.01, decay=1.0, sweep=0.0):
    """Generate one tone. ``sweep`` bends the pitch over the duration (Hz delta)."""
    n = max(1, int(SAMPLE_RATE * dur))
    buf = array.array("h")
    phase = 0.0
    for i in range(n):
        f = freq + sweep * (i / n)
        phase += 2 * math.pi * f / SAMPLE_RATE
        if shape == "sine":
            s = math.sin(phase)
        elif shape == "square":
            s = 1.0 if math.sin(phase) >= 0 else -1.0
        elif shape == "saw":
            s = 2.0 * ((f * i / SAMPLE_RATE) % 1.0) - 1.0
        elif shape == "noise":
            s = random.uniform(-1.0, 1.0)
        else:
            s = math.sin(phase)
        s *= _envelope(i, n, attack, decay) * vol
        buf.append(int(max(-1.0, min(1.0, s)) * 32767))
    return buf


def _mix(*buffers):
    """Overlay several equal-or-unequal buffers into one (summed, clipped)."""
    n = max(len(b) for b in buffers)
    out = array.array("h", [0] * n)
    for b in buffers:
        for i in range(len(b)):
            v = out[i] + b[i]
            out[i] = max(-32768, min(32767, v))
    return out


def _concat(*buffers):
    out = array.array("h")
    for b in buffers:
        out.extend(b)
    return out


class SoundFX:
    """Owns the synthesized clips and plays them by name."""

    def __init__(self):
        self.enabled = False
        self._sounds = {}
        self.muted = False
        try:
            import pygame

            if not pygame.mixer.get_init():
                pygame.mixer.init(frequency=SAMPLE_RATE, size=-16, channels=1)
            pygame.mixer.set_num_channels(16)
            self._pygame = pygame
            self._build()
            self.enabled = True
        except Exception:
            # Headless / no audio device — degrade silently to a no-op.
            self.enabled = False

    def _make(self, buf):
        return self._pygame.mixer.Sound(buffer=buf.tobytes())

    def _build(self):
        # Hidden-blade assassination: a soft "shhk" plus a low thunk.
        self._sounds["assassinate"] = self._make(_concat(
            _tone(2400, 0.05, vol=0.25, shape="noise", decay=2.0),
            _tone(140, 0.18, vol=0.5, shape="sine", sweep=-80, decay=2.0),
        ))
        # Sword clash for open combat.
        self._sounds["hit"] = self._make(_mix(
            _tone(900, 0.12, vol=0.4, shape="square", decay=2.5),
            _tone(1700, 0.08, vol=0.2, shape="noise", decay=3.0),
        ))
        # Parry / block — bright metallic ring.
        self._sounds["block"] = self._make(_mix(
            _tone(1500, 0.16, vol=0.35, shape="sine", decay=1.5),
            _tone(2300, 0.16, vol=0.18, shape="sine", decay=1.5),
        ))
        # Alarm stab when a guard goes alert.
        self._sounds["alert"] = self._make(_concat(
            _tone(520, 0.12, vol=0.4, shape="saw", decay=1.0),
            _tone(700, 0.16, vol=0.4, shape="saw", decay=1.0),
        ))
        # Viewpoint synchronize — a rising chime.
        self._sounds["sync"] = self._make(_concat(
            _tone(660, 0.12, vol=0.35, shape="sine", decay=0.5),
            _tone(880, 0.12, vol=0.35, shape="sine", decay=0.5),
            _tone(1320, 0.22, vol=0.35, shape="sine", decay=0.5),
        ))
        # Level up — triumphant arpeggio.
        self._sounds["levelup"] = self._make(_concat(
            _tone(523, 0.10, vol=0.4, shape="square", decay=0.6),
            _tone(659, 0.10, vol=0.4, shape="square", decay=0.6),
            _tone(784, 0.10, vol=0.4, shape="square", decay=0.6),
            _tone(1046, 0.24, vol=0.4, shape="square", decay=0.6),
        ))
        # Arrow loose — a quick whoosh.
        self._sounds["arrow"] = self._make(
            _tone(1200, 0.16, vol=0.3, shape="noise", sweep=-900, decay=2.0))
        # Player takes a hit.
        self._sounds["hurt"] = self._make(_mix(
            _tone(220, 0.18, vol=0.45, shape="saw", sweep=-120, decay=1.5),
            _tone(110, 0.18, vol=0.3, shape="square", decay=1.5),
        ))
        # Death sting.
        self._sounds["death"] = self._make(_concat(
            _tone(330, 0.2, vol=0.5, shape="saw", sweep=-150, decay=0.8),
            _tone(160, 0.4, vol=0.5, shape="sine", sweep=-80, decay=0.6),
        ))
        # Menu move / select.
        self._sounds["menu"] = self._make(
            _tone(880, 0.06, vol=0.3, shape="square", decay=1.5))
        self._sounds["select"] = self._make(_concat(
            _tone(660, 0.06, vol=0.35, shape="square", decay=1.0),
            _tone(990, 0.10, vol=0.35, shape="square", decay=1.0),
        ))

    def play(self, name: str):
        if not self.enabled or self.muted:
            return
        snd = self._sounds.get(name)
        if snd is not None:
            try:
                snd.play()
            except Exception:
                pass

    def toggle_mute(self):
        self.muted = not self.muted
        return self.muted
