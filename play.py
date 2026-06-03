#!/usr/bin/env python3
"""Launch Assassin's Reverie.

Usage:
    python play.py            # random city
    python play.py --seed 42  # reproducible city layout
"""

import argparse

from assassin.game import Game


def main():
    parser = argparse.ArgumentParser(description="Assassin's Reverie — a stealth-action RPG")
    parser.add_argument("--seed", type=int, default=None, help="World generation seed")
    args = parser.parse_args()
    Game(seed=args.seed).run()


if __name__ == "__main__":
    main()
