"""Move classification derived from moves.json fields (no per-move facts hard-coded,
except the short heuristic list of situational moves the generator should not pick)."""
from __future__ import annotations

from .data_loader import GameData

# Moves whose usefulness depends on conditions the generator can't model (first-turn only,
# target must be asleep / attacking, needs an item/berry, sacrifices the user ...).
SITUATIONAL_MOVES = frozenset({
    "fakeout", "firstimpression", "focuspunch", "dreameater", "lastresort", "belch", "synchronoise",
    "snore", "sleeptalk", "upperhand", "feint", "spitup", "naturalgift", "fling", "revivalblessing",
    "healingwish", "lunardance", "memento", "finalgambit", "mistyexplosion", "steelbeam", "mindblown",
    "counter", "mirrorcoat", "metalburst", "bide", "endeavor", "present", "beatup", "skydrop",
    "shelltrap", "burnup", "doubleshock", "hyperspacefury", "holdback", "falseswipe", "celebrate",
    "splash", "hiddenpower", "magikarpsrevenge", "teleport", "suckerpunch", "thunderclap",
})
VARIABLE_POWER_DEFAULT = 60  # Low Kick, Gyro Ball, Heavy Slam ... (power depends on the target)
FIXED_DAMAGE_EQUIV = 65      # Seismic Toss / Night Shade style fixed damage


def is_damaging(m: dict) -> bool:
    return m["category"] != "Status"


def is_unusable(mid: str, m: dict) -> bool:
    """Moves the generator should never pick."""
    if mid in SITUATIONAL_MOVES or m.get("ohko") or m.get("selfdestruct"):
        return True
    if "charge" in m.get("flags", ()) or "recharge" in m.get("flags", ()):
        return True
    if (m.get("self") or {}).get("volatileStatus") == "mustrecharge":
        return True
    return False


def accuracy(m: dict) -> float:
    acc = m.get("accuracy", True)
    return 1.0 if acc is True else acc / 100.0


def effective_base_power(m: dict) -> float:
    bp = m.get("basePower", 0)
    if bp == 0:
        if not is_damaging(m):
            return 0.0
        bp = FIXED_DAMAGE_EQUIV if m.get("damage") else VARIABLE_POWER_DEFAULT
    hits = m.get("multihit")
    if isinstance(hits, list):
        bp *= 3.0
    elif isinstance(hits, int):
        bp *= hits
    drops = (m.get("self") or {}).get("boosts") or {}
    if any(v <= -2 for v in drops.values()):
        bp *= 0.85
    elif any(v < 0 for v in drops.values()):
        bp *= 0.95
    if m.get("recoil"):
        bp *= 0.95
    return float(bp)


def is_recovery(mid: str, m: dict) -> bool:
    if m["category"] != "Status" or "heal" not in m.get("flags", ()) or mid in SITUATIONAL_MOVES:
        return False
    if m["target"] == "self":
        return True
    # Strength Sap style: heals the user by lowering the target
    return m["target"] == "normal" and any(v < 0 for v in (m.get("boosts") or {}).values())


def is_pivot(mid: str, m: dict) -> bool:
    return m.get("selfSwitch") is True and mid not in SITUATIONAL_MOVES


def is_hazard(m: dict) -> bool:
    return m["target"] == "foeSide" and bool(m.get("sideCondition"))


def is_status_move(m: dict) -> bool:
    return (m["category"] == "Status" and m["target"] == "normal"
            and m.get("status") in ("par", "brn", "tox", "psn", "slp") and accuracy(m) >= 0.75)


def is_setup(m: dict) -> bool:
    if m["category"] != "Status" or m["target"] != "self":
        return False
    b = m.get("boosts") or {}
    return sum(v for v in b.values() if v > 0) >= 2 and any(b.get(s, 0) > 0 for s in ("atk", "spa", "spe"))


def is_priority_attack(mid: str, m: dict) -> bool:
    return is_damaging(m) and m.get("priority", 0) > 0 and mid not in SITUATIONAL_MOVES


def is_speed_control(m: dict) -> bool:
    """Tailwind, Trick Room, Sticky Web, paralysis, guaranteed Speed drops, or boosting own Speed."""
    if m.get("sideCondition") in ("tailwind", "stickyweb") or m.get("pseudoWeather") == "trickroom":
        return True
    if m["category"] == "Status" and m.get("status") == "par" and m["target"] == "normal":
        return True
    sec = m.get("secondary") or {}
    if sec.get("chance") == 100 and ((sec.get("boosts") or {}).get("spe", 0) < 0 or sec.get("status") == "par"):
        return True
    if m["category"] == "Status" and m["target"] == "normal" and (m.get("boosts") or {}).get("spe", 0) < 0:
        return True
    if m["category"] == "Status" and m["target"] == "self" and (m.get("boosts") or {}).get("spe", 0) > 0:
        return True
    return False


def move_tags(data: GameData, mid: str) -> set[str]:
    m = data.moves[mid]
    tags = set()
    if is_recovery(mid, m):
        tags.add("recovery")
    if is_pivot(mid, m):
        tags.add("pivot")
    if is_hazard(m):
        tags.add("hazard")
    if is_status_move(m):
        tags.add("status")
    if is_setup(m):
        tags.add("setup")
    if is_priority_attack(mid, m):
        tags.add("priority")
    if is_speed_control(m):
        tags.add("speed_control")
    return tags
