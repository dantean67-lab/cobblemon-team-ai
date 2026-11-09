"""Team search: greedy build to 6, then best-improvement swaps until nothing improves."""
from __future__ import annotations

import time
from dataclasses import dataclass, field

from .data_loader import GameData
from .scoring import WEIGHTS, Profile, explain_member, make_profile, score_parts
from .sets import PokemonSet

TEAM_SIZE = 6
PREFILTER_TOP = 60          # strongest candidates kept when the pool is large
PREFILTER_PER_TYPE = 3      # plus the strongest few of every type
PREFILTER_ROLE = 6          # plus the strongest speed-control members and pivots
PREFILTER_THRESHOLD = 90    # prefilter only when more unique species than this
MAX_SWAP_PASSES = 50
EPS = 1e-9


@dataclass
class TeamResult:
    members: list[PokemonSet]
    score: float
    parts: dict[str, float]
    contributions: list[dict]
    elapsed: float
    pool_size: int
    searched: int
    notes: list[str] = field(default_factory=list)


def _valid(team: list[Profile]) -> bool:
    species = [p.species for p in team]
    if len(set(species)) != len(species):
        return False
    return sum(p.is_mega for p in team) <= 1 and sum(p.is_z for p in team) <= 1


def prefilter(profiles: list[Profile], data: GameData, keep: set | None = None) -> list[Profile]:
    if len({p.species for p in profiles}) <= PREFILTER_THRESHOLD:
        return profiles
    order = sorted(profiles, key=lambda p: (-p.strength, p.key))
    chosen = {p.key for p in order[:PREFILTER_TOP]}
    for t in data.types:
        for p in [q for q in order if t in q.types][:PREFILTER_PER_TYPE]:
            chosen.add(p.key)
    for p in [q for q in order if q.speed_control][:PREFILTER_ROLE]:
        chosen.add(p.key)
    for p in [q for q in order if q.pivot][:PREFILTER_ROLE]:
        chosen.add(p.key)
    keep = keep or set()
    return [p for p in profiles if p.key in chosen or p.species in keep]


def build_team(data: GameData, candidates: list[PokemonSet], size: int = TEAM_SIZE,
               must_include: list[str] | None = None, weights: dict | None = None) -> TeamResult:
    """candidates: set variants (several per species allowed). must_include: species ids that must be in
    the team (Stage 2). weights: override WEIGHTS (style weights in Stage 2)."""
    t0 = time.perf_counter()
    w = {**WEIGHTS, **(weights or {})}
    n = len(data.types)
    must = list(dict.fromkeys(must_include or []))
    profiles = sorted((make_profile(data, c, w) for c in candidates), key=lambda p: p.key)
    pool_species = {p.species for p in profiles}
    pool = prefilter(profiles, data, set(must))
    size = min(size, len(pool_species))

    def total(team):
        return sum(score_parts(team, n, w).values())

    team: list[Profile] = []
    for sid in must:  # best variant of each must-include species
        opts = [p for p in pool if p.species == sid and _valid(team + [p])]
        if opts:
            team.append(max(opts, key=lambda p: (total(team + [p]), [-ord(c) for c in p.species])))
    locked = {p.species for p in team}

    while len(team) < size:
        best, best_s = None, None
        for p in pool:
            cand = team + [p]
            if not _valid(cand):
                continue
            s = total(cand)
            if best_s is None or s > best_s + EPS:
                best, best_s = p, s
        if best is None:
            break
        team.append(best)

    cur = total(team)
    for _ in range(MAX_SWAP_PASSES):
        best_swap, best_s = None, cur
        for i, old in enumerate(team):
            if old.species in locked:
                continue
            rest = team[:i] + team[i + 1:]
            for p in pool:
                if p.key == old.key:
                    continue
                cand = rest[:i] + [p] + rest[i:]
                if not _valid(cand):
                    continue
                s = total(cand)
                if s > best_s + EPS:
                    best_swap, best_s = (i, p), s
        if best_swap is None:
            break
        i, p = best_swap
        team[i] = p
        cur = best_s

    team.sort(key=lambda p: (p.species not in locked, -p.strength, p.key))
    contributions = [explain_member(data, team, i, w) for i in range(len(team))]
    return TeamResult(members=[p.set for p in team], score=cur, parts=score_parts(team, n, w),
                      contributions=contributions, elapsed=time.perf_counter() - t0,
                      pool_size=len(pool_species), searched=len(pool))


def team_profiles(data: GameData, members: list[PokemonSet], weights: dict | None = None) -> list[Profile]:
    return [make_profile(data, s, weights) for s in members]
