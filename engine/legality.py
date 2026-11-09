"""Legality rules (Stage 1, section 5). All filters on species, moves, abilities and items live here."""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from .data_loader import GameData, toid

# Learn-method codes in learnsets.json:
#   L level-up, T TM, E egg, U tutor, F form-change (granted automatically on form change),
#   X legacy (old Cobblemon versions), S special/event.
LEGACY_MOVES_LEGAL = False          # flip to True to allow "legacy:" moves
SPECIAL_MOVES_LEGAL = False         # "special:" (event) moves
METHODS_ALL = frozenset({"L", "T", "E", "U", "F"})
METHODS_LEVEL_UP_ONLY = frozenset({"L", "F"})

MOVE_SOURCE_ALL = "all"
MOVE_SOURCE_LEVELUP = "levelup"

BANNED_NONSTANDARD = frozenset({"CAP", "Custom", "LGPE", "Pokestar"})
LEGEND_TAGS = frozenset({"Restricted Legendary", "Sub-Legendary", "Mythical"})
LEGEND_LABELS = frozenset({"legendary", "mythical"})
BATTLE_ONLY_FORME_PREFIXES = ("Mega", "Primal", "Gmax", "Eternamax", "Totem")


@dataclass(frozen=True)
class Settings:
    mega: bool = False
    zmoves: bool = False
    dynamax: bool = False
    tera: bool = False
    legendaries: bool = False
    level: int = 50
    move_source: str = MOVE_SOURCE_ALL
    server_list: frozenset[str] | None = field(default=None)  # None = every implemented species

    @classmethod
    def all_on(cls, **kw) -> "Settings":
        return cls(mega=True, zmoves=True, dynamax=True, tera=True, legendaries=True, **kw)


def legal_methods(settings: Settings) -> frozenset[str]:
    methods = set(METHODS_LEVEL_UP_ONLY if settings.move_source == MOVE_SOURCE_LEVELUP else METHODS_ALL)
    if LEGACY_MOVES_LEGAL:
        methods.add("X")
    if SPECIAL_MOVES_LEGAL:
        methods.add("S")
    return frozenset(methods)


def is_legendary(sp: dict) -> bool:
    return bool(LEGEND_TAGS & set(sp.get("tags", ()))) or bool(LEGEND_LABELS & set(sp.get("labels", ())))


def is_battle_only(sp: dict) -> bool:
    return bool(sp.get("battleOnly")) or sp.get("forme", "").startswith(BATTLE_ONLY_FORME_PREFIXES)


def base_allowed(data: GameData, sid: str) -> bool:
    """Implemented in Cobblemon (present in species.json as a selectable form), not CAP/LGPE/... ."""
    sp = data.species.get(sid)
    if not sp or is_battle_only(sp) or sp.get("nonstd") in BANNED_NONSTANDARD:
        return False
    return sid in data.learnsets


def allowed_species(data: GameData, settings: Settings) -> list[str]:
    out = []
    for sid in sorted(data.species):
        if not base_allowed(data, sid):
            continue
        sp = data.species[sid]
        if not settings.legendaries and is_legendary(sp):
            continue
        if settings.server_list is not None and sid not in settings.server_list:
            continue
        out.append(sid)
    return out


def parse_server_list(data: GameData, text: str) -> tuple[frozenset[str] | None, list[str]]:
    """Comma/newline separated names -> species ids. A base-species name also enables its regional forms.
    Returns (ids or None if empty, unrecognized names)."""
    names = [n.strip() for n in re.split(r"[,\n;]+", text or "") if n.strip()]
    if not names:
        return None, []
    by_base: dict[str, list[str]] = {}
    for sid, sp in data.species.items():
        if base_allowed(data, sid):
            by_base.setdefault(toid(sp["baseSpecies"]), []).append(sid)
    ids, unknown = set(), []
    for n in names:
        key = toid(n)
        if key in data.species and base_allowed(data, key):
            ids.add(key)
            if key in by_base:
                ids.update(by_base[key])
        elif key in by_base:
            ids.update(by_base[key])
        else:
            unknown.append(n)
    return frozenset(ids), unknown


def learnset(data: GameData, sid: str) -> dict[str, str]:
    sp = data.species[sid]
    if sid in data.learnsets:
        return data.learnsets[sid]
    base = sp.get("megaOf") or toid(sp.get("baseSpecies", ""))
    return data.learnsets.get(base, {})


def legal_moves(data: GameData, sid: str, settings: Settings) -> list[str]:
    methods = legal_methods(settings)
    return sorted(m for m, codes in learnset(data, sid).items()
                  if m in data.moves and any(c in methods for c in codes))


def legal_abilities(data: GameData, sid: str) -> list[str]:
    return [a for a in data.species[sid]["abilities"] if a in data.abilities]


def is_mega_stone(data: GameData, item: str) -> bool:
    return bool(data.items.get(item, {}).get("megaStone"))


def is_z_crystal(data: GameData, item: str) -> bool:
    return bool(data.items.get(item, {}).get("zMove"))


def item_allowed(data: GameData, item: str, settings: Settings, sid: str | None = None,
                 mega_id: str | None = None) -> bool:
    it = data.items.get(item)
    if not it:
        return False
    if it.get("megaStone"):
        if not settings.mega or sid is None or mega_id is None:
            return False
        return data.species.get(mega_id, {}).get("megaItem") == item and data.species[mega_id].get("megaOf") == sid
    if it.get("zMove"):
        if not settings.zmoves:
            return False
        users = it.get("itemUser")
        if users and sid is not None:
            return data.species[sid]["name"] in users or data.species[sid]["baseSpecies"] in users
        return True
    return bool(it.get("cobblemon"))
