import random
import time

from engine.legality import Settings
from engine.scoring import WEIGHTS, make_profile, score_parts, score_team
from engine.search import build_team
from engine.sets import build_set


def test_full_pool_team_default(data, default_candidates):
    r = build_team(data, default_candidates)
    assert len(r.members) == 6
    assert len({m.species for m in r.members}) == 6
    assert len(r.contributions) == 6


def test_deterministic(data, default_candidates):
    a = build_team(data, default_candidates)
    shuffled = list(default_candidates)
    random.Random(7).shuffle(shuffled)
    b = build_team(data, shuffled)
    assert [m.key() for m in a.members] == [m.key() for m in b.members]
    assert a.score == b.score


def test_mega_and_z_limits(data, all_on_candidates):
    r = build_team(data, all_on_candidates)
    assert len({m.species for m in r.members}) == 6
    assert sum(m.is_mega for m in r.members) <= 1
    assert sum(m.is_z for m in r.members) <= 1


def test_mega_z_limits_when_pool_is_all_megas(data, all_on_candidates):
    megas = [c for c in all_on_candidates if c.is_mega or c.is_z]
    r = build_team(data, megas)
    assert sum(m.is_mega for m in r.members) <= 1
    assert sum(m.is_z for m in r.members) <= 1


def test_full_pool_under_one_second(data, default_candidates, all_on_candidates):
    for cands in (default_candidates, all_on_candidates):
        t = time.perf_counter()
        build_team(data, cands)
        assert time.perf_counter() - t < 1.0


def test_small_selection(data):
    st = Settings()
    cands = [build_set(data, s, st) for s in ("garchomp", "corviknight", "blissey")]
    r = build_team(data, cands)
    assert sorted(m.species for m in r.members) == ["blissey", "corviknight", "garchomp"]


def _fire_team(data, st):
    fire = sorted((sid for sid, sp in data.species.items()
                   if sp["types"] == ["Fire"] and not sp.get("battleOnly") and sid in data.learnsets),
                  key=lambda s: (-sum(data.species[s]["bs"]), s))[:6]
    return [build_set(data, s, st) for s in fire]


def test_mono_fire_scores_lower_than_balanced(data):
    st = Settings()
    n = len(data.types)
    mono = [make_profile(data, s) for s in _fire_team(data, st)]
    balanced_ids = ["garchomp", "corviknight", "rotomwash", "toxapex", "volcarona", "azumarill"]
    balanced = [make_profile(data, build_set(data, s, st)) for s in balanced_ids]
    assert len(mono) == 6
    assert score_team(mono, n) < score_team(balanced, n)


def test_no_speed_control_penalized(data, default_candidates):
    n = len(data.types)
    profiles = sorted((make_profile(data, c) for c in default_candidates), key=lambda p: p.key)
    slow = [p for p in profiles if not p.speed_control][:6]
    fast = next(p for p in profiles if p.speed_control)
    parts = score_parts(slow, n)
    assert parts["speed"] == -WEIGHTS["no_speed_control"]
    assert score_parts(slow[:5] + [fast], n)["speed"] == 0
    # the search always delivers speed control when the pool has it
    r = build_team(data, default_candidates)
    assert any(make_profile(data, m).speed_control for m in r.members)
