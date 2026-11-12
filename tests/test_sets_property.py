"""Property test over EVERY allowed species, default settings and all toggles on."""
import pytest

from engine.legality import (Settings, allowed_species, is_mega_stone, is_z_crystal, item_allowed,
                             legal_abilities, legal_moves)
from engine.stats import NATURES, valid_evs


def _check(data, s, settings):
    legal = set(legal_moves(data, s.species, settings))
    assert len(set(s.moves)) == len(s.moves), s
    assert len(s.moves) == min(4, len(legal)), (s.name, s.moves, len(legal))
    assert set(s.moves) <= legal, (s.name, set(s.moves) - legal)
    assert not any(data.moves[m].get("isZ") or data.moves[m].get("isMax") for m in s.moves)
    abil_src = s.form if s.is_mega else s.species
    assert s.ability in legal_abilities(data, abil_src), (s.name, s.ability)
    if s.item is not None:
        assert item_allowed(data, s.item, settings, s.species, s.form if s.is_mega else None), (s.name, s.item)
    assert valid_evs(s.evs), (s.name, s.evs)
    assert s.nature in NATURES
    if not settings.mega:
        assert not s.is_mega and not (s.item and is_mega_stone(data, s.item))
    if not settings.zmoves:
        assert not (s.item and is_z_crystal(data, s.item))
    if not settings.tera:
        assert s.tera is None
    elif s.item and (is_z_crystal(data, s.item) or is_mega_stone(data, s.item)):
        assert s.tera is None, (s.name, s.item, s.tera)   # see test_tera_blocked_by_item
    else:
        assert s.tera in data.types
    if not settings.dynamax:
        assert not s.gmax


def test_every_species_default(data, default_settings, default_candidates):
    assert len(default_candidates) == len(allowed_species(data, default_settings))
    for s in default_candidates:
        _check(data, s, default_settings)


def test_every_species_all_toggles(data, all_on_settings, all_on_candidates):
    species = {s.species for s in all_on_candidates}
    assert species == set(allowed_species(data, all_on_settings))
    assert any(s.is_mega for s in all_on_candidates)
    for s in all_on_candidates:
        _check(data, s, all_on_settings)


@pytest.mark.parametrize("level", [50, 100])
def test_levelup_only_sets(data, level):
    st = Settings(level=level, move_source="levelup")
    from engine.sets import build_set
    for sid in allowed_species(data, st)[::25]:
        s = build_set(data, sid, st)
        _check(data, s, st)
        for m in s.moves:
            assert set(data.learnsets[sid][m]) & {"L", "F"}


def test_tera_blocked_by_item(data, all_on_candidates, all_on_settings):
    """Pokemon Showdown, sim/battle-actions.ts:

        canTerastallize(pokemon) {
            if (pokemon.getItem().zMove || pokemon.canMegaEvo || this.dex.gen !== 9) return null;
            return pokemon.teraType;
        }

    A Pokemon holding a Z-Crystal (item.zMove) or able to Mega Evolve (its own item.megaStone)
    may not Terastallize, so no Tera type is suggested on those sets."""
    assert all_on_settings.tera and all_on_settings.mega and all_on_settings.zmoves
    megas = [s for s in all_on_candidates if s.item and is_mega_stone(data, s.item)]
    zs = [s for s in all_on_candidates if s.item and is_z_crystal(data, s.item)]
    assert megas, "fixture never produced a Mega Stone set"
    assert zs, "fixture never produced a Z-Crystal set"
    for s in megas + zs:
        assert s.tera is None, (s.name, s.item, s.tera)
    others = [s for s in all_on_candidates
              if not (s.item and (is_mega_stone(data, s.item) or is_z_crystal(data, s.item)))]
    assert others
    for s in others:
        assert s.tera in data.types, (s.name, s.item, s.tera)
