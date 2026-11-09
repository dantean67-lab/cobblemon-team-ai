"""Stat formula and natures.

The 25 natures are a fixed game mechanic and are not published in any of the Showdown data files
this project downloads, so they are defined here (documented in the Stage 1 report).
"""
from __future__ import annotations

import math

STAT_KEYS = ("hp", "atk", "def", "spa", "spd", "spe")
MAX_EV_TOTAL = 510
MAX_EV_STAT = 252
DEFAULT_IV = 31

# nature -> (raised stat, lowered stat); neutral natures have (None, None)
NATURES: dict[str, tuple[str | None, str | None]] = {
    "Hardy": (None, None), "Docile": (None, None), "Serious": (None, None), "Bashful": (None, None), "Quirky": (None, None),
    "Lonely": ("atk", "def"), "Brave": ("atk", "spe"), "Adamant": ("atk", "spa"), "Naughty": ("atk", "spd"),
    "Bold": ("def", "atk"), "Relaxed": ("def", "spe"), "Impish": ("def", "spa"), "Lax": ("def", "spd"),
    "Timid": ("spe", "atk"), "Hasty": ("spe", "def"), "Jolly": ("spe", "spa"), "Naive": ("spe", "spd"),
    "Modest": ("spa", "atk"), "Mild": ("spa", "def"), "Quiet": ("spa", "spe"), "Rash": ("spa", "spd"),
    "Calm": ("spd", "atk"), "Gentle": ("spd", "def"), "Sassy": ("spd", "spe"), "Careful": ("spd", "spa"),
}


def nature_multiplier(nature: str, stat: str) -> float:
    up, down = NATURES[nature]
    if stat == up:
        return 1.1
    if stat == down:
        return 0.9
    return 1.0


def calc_stat(stat: str, base: int, level: int, ev: int = 0, iv: int = DEFAULT_IV, nature: str = "Hardy") -> int:
    core = math.floor((2 * base + iv + math.floor(ev / 4)) * level / 100)
    if stat == "hp":
        if base == 1:  # Shedinja
            return 1
        return core + level + 10
    return math.floor((core + 5) * nature_multiplier(nature, stat))


def calc_all(base_stats: list[int], level: int, evs: dict[str, int], nature: str) -> dict[str, int]:
    return {k: calc_stat(k, base_stats[i], level, evs.get(k, 0), DEFAULT_IV, nature) for i, k in enumerate(STAT_KEYS)}


def valid_evs(evs: dict[str, int]) -> bool:
    return (all(k in STAT_KEYS and 0 <= v <= MAX_EV_STAT for k, v in evs.items())
            and sum(evs.values()) <= MAX_EV_TOTAL)
