"""Team scoring. Every weight lives in WEIGHTS (documented below)."""
from __future__ import annotations

import math
from dataclasses import dataclass

from . import moves as mv
from .data_loader import GameData
from .sets import BULKY_SUM, PokemonSet, bulk
from .types import defensive_profile, effectiveness

WEIGHTS: dict[str, float] = {
    # Defense, per attacking type: penalty = shared_weakness * (weak - resists)^2 when >= 2 members are weak.
    "shared_weakness": 4.0,
    "quad_weak_factor": 1.5,   # a 4x weakness counts as 1.5 weak members
    "resist": 1.0,             # reward per resisting/immune member per attacking type ...
    "resist_cap": 2,           # ... counting at most this many members per type
    "immune": 1.0,             # extra reward per attacking type the team has an immunity to
    # Offense, per defending (single) type
    "coverage": 2.0,           # reward if some member hits it super-effectively
    "unhittable": 4.0,         # penalty if no member hits it at least neutrally
    # Individual strength: strength = clamp((BST-300)/300, 0, 1.3) + sqrt(usage share) + ability term
    "strength": 10.0,
    # Ability quality: strength += ability_rating * (min(rating, 3) - 3); punishes Truant / Slow Start / Defeatist
    "ability_rating": 0.2,
    # Required roles
    "no_speed_control": 25.0,  # no fast member (base Spe >= fast_speed), Choice Scarf, priority or speed-control move
    "fast_speed": 100,
    "no_pivot": 25.0,          # no bulky member at all
    "pivot_partial": 0.4,      # fraction of no_pivot applied when bulky members exist but none has a pivot move / Regenerator
    # Type stacking: per member beyond 2 sharing one type
    "type_stack": 8.0,
}


@dataclass
class Profile:
    key: tuple
    species: str
    types: tuple[str, ...]
    defense: tuple[float, ...]
    offense: tuple[float, ...]
    strength: float
    speed_control: bool
    bulky: bool
    pivot: bool
    is_mega: bool
    is_z: bool
    speed_reason: str | None
    set: PokemonSet


def make_profile(data: GameData, s: PokemonSet, weights: dict | None = None) -> Profile:
    w = weights or WEIGHTS
    types = data.types
    dprof = defensive_profile(data, s.types, s.ability)
    dmg_types = {data.moves[m]["type"] for m in s.moves if mv.is_damaging(data.moves[m])}
    offense = tuple(max([effectiveness(data, a, [t]) for a in dmg_types] or [0.0]) for t in types)
    bst = sum(s.bs)
    usage = data.usage.get(s.species, {}).get("usage", 0.0)
    rating = data.abilities.get(s.ability, {}).get("rating", 3)
    strength = (min(max((bst - 300) / 300, 0.0), 1.3) + math.sqrt(max(usage, 0.0))
                + w["ability_rating"] * (min(rating, 3) - 3))
    reason = None
    if s.bs[5] >= w["fast_speed"]:
        reason = "fast"
    elif s.item == "choicescarf":
        reason = "scarf"
    elif "priority" in s.tags:
        reason = "priority"
    elif "speed_control" in s.tags:
        reason = "move"
    is_bulky = bulk(s.bs) >= BULKY_SUM
    return Profile(key=s.key(), species=s.species, types=tuple(s.types),
                   defense=tuple(dprof[t] for t in types), offense=offense, strength=strength,
                   speed_control=reason is not None, bulky=is_bulky,
                   pivot=is_bulky and ("pivot" in s.tags or s.ability == "regenerator"),
                   is_mega=s.is_mega, is_z=s.is_z, speed_reason=reason, set=s)


def score_parts(team: list[Profile], ntypes: int, weights: dict | None = None) -> dict[str, float]:
    w = weights or WEIGHTS
    parts = {"defense": 0.0, "offense": 0.0, "strength": 0.0, "speed": 0.0, "pivot": 0.0, "stacking": 0.0}
    if not team:
        return parts
    d = 0.0
    qf, cap = w["quad_weak_factor"], w["resist_cap"]
    for i in range(ntypes):
        weak = 0.0
        res = 0
        imm = 0
        for p in team:
            x = p.defense[i]
            if x > 1:
                weak += qf if x > 2 else 1.0
            elif x < 1:
                res += 1
                if x == 0:
                    imm += 1
        if weak >= 2:
            net = weak - res
            if net > 0:
                d -= w["shared_weakness"] * net * net
        d += w["resist"] * min(res, cap) + (w["immune"] if imm else 0.0)
    parts["defense"] = d
    o = 0.0
    for i in range(ntypes):
        best = max(p.offense[i] for p in team)
        if best >= 2:
            o += w["coverage"]
        elif best < 1:
            o -= w["unhittable"]
    parts["offense"] = o
    parts["strength"] = w["strength"] * sum(p.strength for p in team)
    if not any(p.speed_control for p in team):
        parts["speed"] = -w["no_speed_control"]
    if not any(p.pivot for p in team):
        parts["pivot"] = -w["no_pivot"] * (w["pivot_partial"] if any(p.bulky for p in team) else 1.0)
    counts: dict[str, int] = {}
    for p in team:
        for t in p.types:
            counts[t] = counts.get(t, 0) + 1
    parts["stacking"] = -w["type_stack"] * sum(c - 2 for c in counts.values() if c >= 3)
    return parts


def score_team(team: list[Profile], ntypes: int, weights: dict | None = None) -> float:
    return sum(score_parts(team, ntypes, weights).values())


def pivot_member(team: list[Profile], data: GameData) -> Profile | None:
    """The member acting as defensive pivot: bulky + pivot move/Regenerator, else best-resisting bulky member."""
    full = [p for p in team if p.pivot]
    pool = full or [p for p in team if p.bulky]
    if not pool:
        return None
    return min(pool, key=lambda p: (-sum(1 for x in p.defense if x < 1), -bulk(p.set.bs), p.species))


def explain_member(data: GameData, team: list[Profile], idx: int, weights: dict | None = None) -> dict:
    """Score contribution of member idx and the concrete facts behind it (for the "why chosen" line)."""
    types = data.types
    n = len(types)
    me = team[idx]
    others = [p for j, p in enumerate(team) if j != idx]
    with_me = score_parts(team, n, weights)
    without = score_parts(others, n, weights)
    delta = {k: with_me[k] - without[k] for k in with_me}
    # types only this member hits super-effectively
    unique_cover = [types[i] for i in range(n)
                    if me.offense[i] >= 2 and all(p.offense[i] < 2 for p in others)]
    # team weaknesses (>=2 teammates weak) that this member resists
    covers_weak = [types[i] for i in range(n)
                   if me.defense[i] < 1 and sum(1 for p in others if p.defense[i] > 1) >= 2]
    only_speed = me.speed_control and not any(p.speed_control for p in others)
    piv = pivot_member(team, data)
    return {
        "total": sum(delta.values()), "parts": delta, "unique_cover": unique_cover,
        "covers_weak": covers_weak, "speed_control": me.speed_control, "only_speed": only_speed,
        "speed_reason": me.speed_reason, "is_pivot": piv is me, "strength": me.strength,
    }
