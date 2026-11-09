import pytest

from engine.types import defensive_multiplier, effectiveness


@pytest.mark.parametrize("atk,defn,expected", [
    ("Electric", ["Ground"], 0.0),
    ("Fire", ["Grass", "Bug"], 4.0),
    ("Ghost", ["Normal"], 0.0),
    ("Water", ["Fire"], 2.0),
    ("Grass", ["Fire", "Flying"], 0.25),
    ("Ice", ["Dragon", "Ground"], 4.0),           # Garchomp
    ("Ground", ["Electric", "Flying"], 0.0),      # Zapdos
    ("Fighting", ["Normal", "Ghost"], 0.0),
    ("Fairy", ["Dragon", "Dark"], 4.0),           # Hydreigon
    ("Rock", ["Fire", "Flying"], 4.0),            # Charizard
    ("Water", ["Water", "Dragon"], 0.25),          # Kingdra
    ("Electric", ["Water", "Flying"], 4.0),       # Gyarados
    ("Fire", ["Steel", "Bug"], 4.0),              # Scizor
    ("Poison", ["Steel", "Fairy"], 0.0),
    ("Dragon", ["Fairy", "Steel"], 0.0),
])
def test_type_chart(data, atk, defn, expected):
    assert effectiveness(data, atk, defn) == expected


def test_eighteen_types(data):
    assert len(data.types) == 18


def test_ability_modifiers(data):
    assert defensive_multiplier(data, "Ground", ["Ghost", "Poison"], "levitate") == 0.0   # Gengar
    assert defensive_multiplier(data, "Water", ["Water"], "waterabsorb") == 0.0
    assert defensive_multiplier(data, "Fire", ["Ice"], "thickfat") == 1.0
    assert defensive_multiplier(data, "Fire", ["Bug", "Ghost"], "wonderguard") == 2.0     # Shedinja
    assert defensive_multiplier(data, "Water", ["Bug", "Ghost"], "wonderguard") == 0.0
