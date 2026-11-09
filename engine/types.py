"""Type effectiveness from typechart.json, plus defensive ability modifiers."""
from __future__ import annotations

from .data_loader import GameData

# Defensive abilities that change incoming type damage. ONE place, data-driven.
# Value = multiplier applied on top of the type chart for that attacking type.
ABILITY_TYPE_MODIFIERS: dict[str, dict[str, float]] = {
    "levitate": {"Ground": 0.0},
    "eartheater": {"Ground": 0.0},
    "flashfire": {"Fire": 0.0},
    "wellbakedbody": {"Fire": 0.0},
    "waterabsorb": {"Water": 0.0},
    "stormdrain": {"Water": 0.0},
    "dryskin": {"Water": 0.0, "Fire": 1.25},
    "voltabsorb": {"Electric": 0.0},
    "lightningrod": {"Electric": 0.0},
    "motordrive": {"Electric": 0.0},
    "sapsipper": {"Grass": 0.0},
    "thickfat": {"Fire": 0.5, "Ice": 0.5},
    "heatproof": {"Fire": 0.5},
    "waterbubble": {"Fire": 0.5},
    "purifyingsalt": {"Ghost": 0.5},
    "fluffy": {"Fire": 2.0},
}
# Abilities that scale every super-effective hit.
ABILITY_SE_MODIFIERS: dict[str, float] = {"filter": 0.75, "solidrock": 0.75, "prismarmor": 0.75}
# Wonder Guard: only super-effective hits land.
WONDER_GUARD = "wonderguard"


def effectiveness(data: GameData, atk_type: str, def_types: list[str] | tuple[str, ...]) -> float:
    chart = data.typechart["defense"]
    mult = 1.0
    for t in def_types:
        mult *= chart[t][atk_type]
    return mult


def defensive_multiplier(data: GameData, atk_type: str, def_types, ability: str | None = None) -> float:
    mult = effectiveness(data, atk_type, def_types)
    if not ability:
        return mult
    if ability == WONDER_GUARD:
        return mult if mult > 1 else 0.0
    mult *= ABILITY_TYPE_MODIFIERS.get(ability, {}).get(atk_type, 1.0)
    if mult > 1:
        mult *= ABILITY_SE_MODIFIERS.get(ability, 1.0)
    return mult


def defensive_profile(data: GameData, def_types, ability: str | None = None) -> dict[str, float]:
    return {t: defensive_multiplier(data, t, def_types, ability) for t in data.types}
