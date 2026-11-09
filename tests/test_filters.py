import json
from pathlib import Path

from engine.data_loader import toid
from engine.legality import (Settings, allowed_species, is_legendary, legal_moves, parse_server_list)


def test_legendaries_toggle(data):
    off = allowed_species(data, Settings())
    on = allowed_species(data, Settings(legendaries=True))
    assert not any(is_legendary(data.species[s]) for s in off)
    assert set(off) < set(on)
    assert any(is_legendary(data.species[s]) for s in on)


def test_ultra_beasts_and_paradox_are_regular(data):
    off = set(allowed_species(data, Settings()))
    regular = [s for s, sp in data.species.items()
               if {"ultra_beast", "paradox"} & set(sp.get("labels", [])) and not is_legendary(sp)]
    assert regular, "expected some implemented Ultra Beasts / Paradox Pokémon"
    assert set(regular) <= off


def test_server_list(data):
    ids, unknown = parse_server_list(data, "Garchomp, corviknight\nRotom Wash ; notapokemon, MR. MIME")
    assert unknown == ["notapokemon"]
    assert {"garchomp", "corviknight", "rotomwash", "mrmime"} <= ids
    allowed = allowed_species(data, Settings(server_list=ids))
    assert set(allowed) <= ids and "garchomp" in allowed
    assert "blissey" not in allowed


def test_empty_server_list_means_all(data):
    ids, unknown = parse_server_list(data, "  \n , ")
    assert ids is None and unknown == []


def test_levelup_only(data):
    all_moves = set(legal_moves(data, "garchomp", Settings()))
    lvl = set(legal_moves(data, "garchomp", Settings(move_source="levelup")))
    assert lvl < all_moves
    assert all(set(data.learnsets["garchomp"][m]) & {"L", "F"} for m in lvl)


def test_legacy_moves_not_legal(data):
    for sid in allowed_species(data, Settings())[:200]:
        legal = set(legal_moves(data, sid, Settings()))
        for m, codes in data.learnsets[sid].items():
            if set(codes) <= {"X"}:
                assert m not in legal


def test_unimplemented_species_never_appear(data):
    raw = json.loads((Path(__file__).resolve().parent.parent / "data" / "raw" / "cobblemon_species.json").read_text())
    not_impl = {toid(d["name"]) for d in raw.values() if not d.get("implemented")}
    impl = {toid(d["name"]) for d in raw.values() if d.get("implemented")}
    not_impl -= impl
    assert not_impl, "expected some unimplemented species in Cobblemon data"
    allowed = set(allowed_species(data, Settings.all_on()))
    assert not (allowed & not_impl)
    for sid in allowed:  # every allowed form belongs to an implemented Cobblemon species
        assert toid(data.species[sid]["baseSpecies"]) in impl or sid in impl


def test_battle_only_formes_not_selectable(data):
    allowed = set(allowed_species(data, Settings.all_on()))
    assert "charizardmegax" not in allowed
    assert not any(data.species[s].get("battleOnly") for s in allowed)
