"""Deterministic set builder: Smogon set first (cleaned to be legal), otherwise generated."""
from __future__ import annotations

from dataclasses import dataclass, field

from . import moves as mv
from .data_loader import GameData, toid
from .legality import (Settings, is_mega_stone, is_z_crystal, item_allowed, legal_abilities,
                       legal_moves)
from .stats import MAX_EV_STAT, MAX_EV_TOTAL, NATURES, STAT_KEYS, valid_evs
from .types import defensive_profile, effectiveness

# Smogon formats in priority order. Anything not listed (doubles, vgc, hackmons, stabmons,
# almostanyability, godlygift, inheritance, partnersincrime, 1v1, monotype ...) is ignored.
FORMAT_PRIORITY = [
    "nationaldex", "nationaldexubers", "ou", "ubersuu", "nationaldexuu", "uu",
    "nationaldexru", "ru", "nu", "pu", "zu", "battlestadiumsingles", "lc", "nfe",
]
MIN_LEGAL_SMOGON_MOVES = 3   # first Smogon set (in priority order) with at least this many legal moves wins

ROLES = ("phys_att", "spec_att", "phys_wall", "spec_wall", "pivot", "hazard", "support", "speed")
ATTACKER_ROLES = ("phys_att", "spec_att")
WALL_ROLES = ("phys_wall", "spec_wall")

# Base-stat thresholds used to pick roles (heuristics, not Pokémon facts)
BULKY_SUM = 255        # hp + def + spd
FAST_SPEED = 100
SWEEPER_SPEED = 80
FRAIL_SUM = 220


@dataclass
class PokemonSet:
    species: str                 # selectable species id (base form)
    form: str                    # species id actually used in battle (Mega forme id when Mega)
    name: str                    # display name, e.g. "Charizard (Mega X)"
    types: list[str]
    bs: list[int]
    ability: str
    item: str | None
    nature: str
    evs: dict[str, int]
    moves: list[str]
    role: str
    tera: str | None = None
    gmax: bool = False
    is_mega: bool = False
    is_z: bool = False
    source: str = "generated"
    tags: set[str] = field(default_factory=set)

    def key(self) -> tuple:
        return (self.species, self.form, self.item or "")


# ---------------------------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------------------------

def bulk(bs: list[int]) -> int:
    return bs[0] + bs[2] + bs[4]


def base_role(bs: list[int]) -> str:
    hp, atk, de, spa, spd, spe = bs
    off = max(atk, spa)
    if off >= 100 or (off >= 85 and spe >= 85):
        return "phys_att" if atk >= spa else "spec_att"
    if bulk(bs) >= BULKY_SUM:
        return "phys_wall" if de >= spd else "spec_wall"
    if off < 70:
        return "support"
    return "phys_att" if atk >= spa else "spec_att"


def move_value(data: GameData, mid: str, types: list[str], bs: list[int], ability: str | None = None) -> float:
    """Effective power = base power x accuracy x STAB x attacking stat."""
    m = data.moves[mid]
    if not mv.is_damaging(m):
        return 0.0
    stat = bs[1] if m["category"] == "Physical" else bs[3]
    stab = 1.5 if m["type"] in types else 1.0
    if stab > 1 and ability == "adaptability":
        stab = 2.0
    return mv.effective_base_power(m) * mv.accuracy(m) * stab * stat / 100.0


def se_types(data: GameData, move_ids) -> set[str]:
    hit = set()
    for mid in move_ids:
        m = data.moves[mid]
        if not mv.is_damaging(m):
            continue
        for t in data.types:
            if effectiveness(data, m["type"], [t]) > 1:
                hit.add(t)
    return hit


def stealth_rock_weak(data: GameData, types) -> bool:
    return "Rock" in data.types and effectiveness(data, "Rock", types) >= 2


# ---------------------------------------------------------------------------------------------
# generator
# ---------------------------------------------------------------------------------------------

def generate_moves(data: GameData, legal: list[str], types: list[str], bs: list[int], role: str,
                   fixed: list[str] | None = None, ability: str | None = None, n: int = 4) -> list[str]:
    chosen: list[str] = [m for m in (fixed or []) if m in legal][:n]
    pool = [m for m in legal if not mv.is_unusable(m, data.moves[m])]
    tags = {m: mv.move_tags(data, m) for m in pool}
    value = {m: move_value(data, m, types, bs, ability) for m in pool}
    attacker = role in ATTACKER_ROLES
    pref_cat = "Physical" if bs[1] > bs[3] else "Special" if bs[3] > bs[1] else None
    if pref_cat is None:  # equal attacking stats: use the category with the stronger best move
        def top(cat):
            return max([value[m] for m in pool if data.moves[m]["category"] == cat] or [0])
        pref_cat = "Physical" if top("Physical") >= top("Special") else "Special"

    def damaging(cat_only: bool):
        out = [m for m in pool if value[m] > 0 and m not in chosen]
        if cat_only:
            same = [m for m in out if data.moves[m]["category"] == pref_cat]
            if same:
                return same
        return out

    def best(cands, key):
        cands = [c for c in cands if c not in chosen]
        if not cands:
            return None
        return min(cands, key=lambda m: (-key(m), m))

    def add(m):
        if m and m not in chosen and len(chosen) < n:
            chosen.append(m)

    def has(tag):
        return any(tag in mv.move_tags(data, m) for m in chosen)

    # 1) STAB moves (two for attackers, one for everyone else)
    stab_slots = 2 if attacker else 1
    stab_order = sorted(types, key=lambda t: (-max([value[m] for m in damaging(attacker)
                                                     if data.moves[m]["type"] == t] or [0]), t))
    for t in stab_order[:stab_slots]:
        if any(data.moves[m]["type"] == t and mv.is_damaging(data.moves[m]) for m in chosen):
            continue
        add(best([m for m in damaging(attacker) if data.moves[m]["type"] == t], lambda m: value[m]))
    if not any(mv.is_damaging(data.moves[m]) for m in chosen):
        add(best(damaging(attacker), lambda m: value[m]))

    # 2) Utility by role
    def add_tag(tag, rank=None):
        if not has(tag):
            add(best([m for m in pool if tag in tags[m]], rank or (lambda m: value.get(m, 0) + (1 if data.moves[m].get("heal") else 0))))

    if attacker:
        if bs[5] >= SWEEPER_SPEED and not has("setup"):
            stat = "atk" if pref_cat == "Physical" else "spa"

            def setup_rank(m):
                b = data.moves[m].get("boosts") or {}
                return b.get(stat, 0) * 2 + b.get("spe", 0) + sum(b.values()) * 0.1

            add(best([m for m in pool if "setup" in tags[m] and (data.moves[m].get("boosts") or {}).get(stat, 0) > 0],
                     setup_rank))
        if not has("setup"):
            add_tag("pivot")
        if bs[5] < FAST_SPEED:
            pri = best([m for m in pool if "priority" in tags[m] and data.moves[m]["category"] == pref_cat
                        and value[m] >= 40], lambda m: value[m])
            if pri and not has("priority"):
                add(pri)
    else:
        add_tag("recovery")
        add_tag("hazard", lambda m: (data.moves[m].get("sideCondition") == "stealthrock") * 2 + 1)
        if role in ("support", "speed") or not has("pivot"):
            add_tag("status", lambda m: mv.accuracy(data.moves[m]))
        add_tag("pivot")

    # 3) Fill with coverage-weighted damage
    while len(chosen) < n:
        covered = se_types(data, chosen)
        stab_types = {data.moves[m]["type"] for m in chosen if mv.is_damaging(data.moves[m])}
        cands = damaging(attacker)

        def cov_value(m):
            new = se_types(data, [m]) - covered
            dup = 0.5 if data.moves[m]["type"] in stab_types else 1.0
            return value[m] * dup * (1 + 0.6 * len(new))

        nxt = best(cands, cov_value)
        if nxt is None:  # nothing damaging left: take any remaining legal move with a tag, then anything
            rest = [m for m in pool if m not in chosen]
            nxt = best(rest, lambda m: len(tags[m]) * 10 + (data.moves[m].get("basePower") or 0) / 100)
            if nxt is None:
                rest = [m for m in legal if m not in chosen]
                nxt = rest[0] if rest else None
        if nxt is None:
            break
        add(nxt)
    return chosen


def pick_ability(data: GameData, sid_for_usage: str, legal: list[str], preferred: list[str] | None = None) -> str:
    for a in preferred or []:
        if toid(a) in legal:
            return toid(a)
    usage = data.usage.get(sid_for_usage, {}).get("abilities", {})
    for a, _pct in sorted(usage.items(), key=lambda kv: (-kv[1], kv[0])):
        if a in legal:
            return a
    return min(legal, key=lambda a: (-data.abilities[a].get("rating", 0), a))


def defensive_spread(evs: dict[str, int] | None) -> bool:
    evs = evs or {}
    return evs.get("hp", 0) >= 128 and max(evs.get("def", 0), evs.get("spd", 0)) >= 100


def final_role(data: GameData, base: str, bs: list[int], moves: list[str], ability: str,
               evs: dict[str, int] | None = None) -> str:
    tags = set().union(*(mv.move_tags(data, m) for m in moves)) if moves else set()
    n_dmg = sum(1 for m in moves if mv.is_damaging(data.moves[m]))
    bulky = bulk(bs) >= BULKY_SUM
    defensive = base not in ATTACKER_ROLES or defensive_spread(evs)
    if "hazard" in tags and (n_dmg <= 1 or (defensive and n_dmg <= 2)):
        return "hazard"
    if bulky and ("pivot" in tags or ability == "regenerator") and defensive:
        return "pivot"
    speed_moves = [m for m in moves if "speed_control" in mv.move_tags(data, m)
                   and data.moves[m]["category"] == "Status" and data.moves[m]["target"] != "self"]
    if speed_moves and n_dmg <= 2:
        return "speed"
    if n_dmg <= 1:
        return "support"
    if base in WALL_ROLES or (base == "support" and bulky) or (bulky and defensive_spread(evs)):
        return "phys_wall" if bs[2] >= bs[4] else "spec_wall"
    phys = sum(1 for m in moves if data.moves[m]["category"] == "Physical")
    spec = sum(1 for m in moves if data.moves[m]["category"] == "Special")
    if phys == spec:
        return "phys_att" if bs[1] >= bs[3] else "spec_att"
    return "phys_att" if phys > spec else "spec_att"


def generated_item(data: GameData, settings: Settings, sid: str, sp: dict, role: str, moves: list[str],
                   types: list[str], bs: list[int]) -> str | None:
    n_dmg = sum(1 for m in moves if mv.is_damaging(data.moves[m]))
    tags = set().union(*(mv.move_tags(data, m) for m in moves)) if moves else set()
    sr_weak = stealth_rock_weak(data, types)
    order: list[str] = []
    if sp.get("nfe"):
        order.append("eviolite")
    if role in ATTACKER_ROLES:
        if n_dmg == 4:
            if 60 <= bs[5] < FAST_SPEED:
                order.append("choicescarf")
            if bulk(bs) >= BULKY_SUM:
                order.append("assaultvest")
            order.append("choiceband" if role == "phys_att" else "choicespecs")
        if sr_weak:
            order.append("heavydutyboots")
        order.append("lifeorb")
    else:
        if role == "hazard" and bulk(bs) < FRAIL_SUM:
            order.append("focussash")
        if sr_weak:
            order.append("heavydutyboots")
        if "Poison" in types:
            order.append("blacksludge")
        order.append("leftovers")
    order += ["leftovers", "lifeorb"]
    for it in order:
        if item_allowed(data, it, settings, sid):
            return it
    return None


def generated_spread(role: str, bs: list[int]) -> tuple[str, dict[str, int]]:
    atk_first = bs[1] >= bs[3]
    if role in ATTACKER_ROLES:
        phys = role == "phys_att"
        if bs[5] < 50:
            return ("Brave" if phys else "Quiet"), {"hp": 252, ("atk" if phys else "spa"): 252, "spd": 4}
        if bs[5] >= SWEEPER_SPEED:
            return ("Jolly" if phys else "Timid"), {"hp": 4, ("atk" if phys else "spa"): 252, "spe": 252}
        return ("Adamant" if phys else "Modest"), {"hp": 4, ("atk" if phys else "spa"): 252, "spe": 252}
    phys_def = bs[2] >= bs[4] if role not in WALL_ROLES else role == "phys_wall"
    if phys_def:
        return ("Impish" if atk_first else "Bold"), {"hp": 252, "def": 252, "spd": 4}
    return ("Careful" if atk_first else "Calm"), {"hp": 252, "spd": 252, "def": 4}


def computed_tera(data: GameData, role: str, types: list[str], bs: list[int], moves: list[str], ability: str) -> str:
    if role in ATTACKER_ROLES:
        dmg = [m for m in moves if mv.is_damaging(data.moves[m])]
        if dmg:
            top = min(dmg, key=lambda m: (-move_value(data, m, [data.moves[m]["type"]], bs, ability), m))
            return data.moves[top]["type"]
    own = defensive_profile(data, types, ability)
    weak_to = [t for t, x in own.items() if x > 1]

    def score(t):
        prof = defensive_profile(data, [t], ability)
        return sum(1 for w in weak_to if prof[w] < 1) * 2 - sum(1 for x in prof.values() if x > 1)

    return min(data.types, key=lambda t: (-score(t), t))


# ---------------------------------------------------------------------------------------------
# Smogon sets
# ---------------------------------------------------------------------------------------------

def smogon_candidates(data: GameData, sid: str) -> list[dict]:
    order = {f: i for i, f in enumerate(FORMAT_PRIORITY)}
    sets = [s for s in data.sets.get(sid, []) if s["format"] in order]
    return sorted(sets, key=lambda s: order[s["format"]])  # stable: keeps file order inside a format


def _smogon_moves(data: GameData, st: dict, legal: set[str]) -> list[str]:
    out: list[str] = []
    for slot in st["moves"]:
        for opt in slot:
            mid = toid(opt)
            if mid in legal and mid not in out:
                out.append(mid)
                break
    return out[:4]


def choose_smogon_set(data: GameData, sid: str, legal: set[str], mega_item: str | None) -> dict | None:
    """First set (format priority order) with enough legal moves. If mega_item is given, only sets
    holding that Mega Stone; otherwise sets that don't rely on a Mega Stone."""
    cands = smogon_candidates(data, sid)
    if mega_item:
        cands = [s for s in cands if mega_item in [toid(i) for i in s["item"]]]
    else:
        cands = [s for s in cands if not all(is_mega_stone(data, toid(i)) for i in s["item"]) or not s["item"]]
    for s in cands:
        if len(_smogon_moves(data, s, legal)) >= min(MIN_LEGAL_SMOGON_MOVES, len(legal)):
            return s
    return None


# ---------------------------------------------------------------------------------------------
# public API
# ---------------------------------------------------------------------------------------------

def display_name(data: GameData, sid: str, mega_id: str | None) -> str:
    name = data.species[sid]["name"]
    if not mega_id:
        return name
    forme = data.species[mega_id].get("forme", "Mega")
    suffix = forme.replace("-", " ") if forme not in ("Mega",) else "Mega"
    return f"{name} ({suffix})"


def build_set(data: GameData, sid: str, settings: Settings, mega_id: str | None = None,
              allow_z: bool = True) -> PokemonSet:
    sp = data.species[sid]
    form_sp = data.species[mega_id] if mega_id else sp
    types, bs = list(form_sp["types"]), list(form_sp["bs"])
    legal_list = legal_moves(data, sid, settings)
    legal = set(legal_list)
    mega_item = form_sp.get("megaItem") if mega_id else None
    abilities = legal_abilities(data, mega_id) if mega_id else legal_abilities(data, sid)
    if not abilities:
        abilities = legal_abilities(data, sid)

    st = choose_smogon_set(data, sid, legal, mega_item)
    role0 = base_role(bs)
    source = f"smogon:{st['format']}/{st['name']}" if st else "generated"

    # ability
    ability = pick_ability(data, mega_id or sid, abilities, st["ability"] if st else None)

    # moves
    fixed = _smogon_moves(data, st, legal) if st else []
    moves = generate_moves(data, legal_list, types, bs, role0, fixed=fixed, ability=ability)
    smogon_evs = None
    if st and st["evs"]:
        cand = {k: int(v) for k, v in st["evs"][0].items() if k in STAT_KEYS}
        if valid_evs(cand) and sum(cand.values()) > 0:
            smogon_evs = cand
    role = final_role(data, role0, bs, moves, ability, smogon_evs)

    # item
    item = None
    is_z = False
    if mega_item:
        item = mega_item
    else:
        for opt in (st["item"] if st else []):
            iid = toid(opt)
            if is_mega_stone(data, iid):
                continue
            if is_z_crystal(data, iid):
                if not allow_z or not item_allowed(data, iid, settings, sid):
                    continue
                zf = data.items[iid].get("zMoveFrom")
                if zf and toid(zf if isinstance(zf, str) else zf[0]) not in moves:
                    continue
                if not any(mv.is_damaging(data.moves[m]) and data.moves[m]["type"] == data.items[iid].get("zMoveType")
                           for m in moves) and data.items[iid].get("zMoveType"):
                    continue
            if item_allowed(data, iid, settings, sid):
                item = iid
                break
        if item is None:
            item = generated_item(data, settings, sid, sp, role, moves, types, bs)
        is_z = bool(item and is_z_crystal(data, item))
    # Choice items lock into one move: only keep them if every move attacks
    if item in ("choicescarf", "choiceband", "choicespecs") and \
            not all(mv.is_damaging(data.moves[m]) for m in moves):
        if not st or toid(item) not in [toid(i) for i in st["item"]]:
            item = generated_item(data, settings, sid, sp, "phys_wall", moves, types, bs)

    # nature / EVs
    gen_nature, gen_evs = generated_spread(role if role in ATTACKER_ROLES + WALL_ROLES else role0, bs)
    nature = next((n for n in (st["nature"] if st else []) if n in NATURES), gen_nature)
    evs = smogon_evs or gen_evs

    # Pokemon Showdown, sim/battle-actions.ts:
    #     canTerastallize(pokemon) {
    #         if (pokemon.getItem().zMove || pokemon.canMegaEvo || this.dex.gen !== 9) return null;
    #         return pokemon.teraType;
    #     }
    # canMegaEvo (same file) is non-null only when the held item's `megaStone` maps this species,
    # which is the only way this engine ever hands out a Mega Stone. So a Pokemon holding a
    # Z-Crystal (item.zMove) or its own Mega Stone (item.megaStone) cannot Terastallize.
    tera = None
    if settings.tera and not (item and (is_z_crystal(data, item) or is_mega_stone(data, item))):
        tera = next((t for t in (st["tera"] if st else []) if t in data.types), None) or \
            computed_tera(data, role, types, bs, moves, ability)

    tags = set().union(*(mv.move_tags(data, m) for m in moves)) if moves else set()
    return PokemonSet(
        species=sid, form=mega_id or sid, name=display_name(data, sid, mega_id), types=types, bs=bs,
        ability=ability, item=item, nature=nature, evs=evs, moves=moves, role=role, tera=tera,
        gmax=bool(settings.dynamax and sp.get("gmax")), is_mega=bool(mega_id), is_z=is_z,
        source=source, tags=tags,
    )


def build_candidates(data: GameData, species_ids: list[str], settings: Settings) -> list[PokemonSet]:
    """All set variants for the given species: the normal set, a non-Z backup when the normal set
    holds a Z-Crystal, and one Mega variant per Mega forme when Mega is on."""
    out: list[PokemonSet] = []
    for sid in sorted(species_ids):
        s = build_set(data, sid, settings)
        out.append(s)
        if s.is_z:
            out.append(build_set(data, sid, settings, allow_z=False))
        if settings.mega:
            for mega_id in data.species[sid].get("megas", []):
                if mega_id in data.species and item_allowed(data, data.species[mega_id]["megaItem"], settings, sid, mega_id):
                    out.append(build_set(data, sid, settings, mega_id=mega_id))
    return out


__all__ = ["PokemonSet", "build_set", "build_candidates", "ROLES", "FORMAT_PRIORITY", "MAX_EV_STAT", "MAX_EV_TOTAL"]
