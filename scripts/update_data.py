#!/usr/bin/env python3
"""Download all raw data and build the compact files the app loads at runtime.

Usage:
    python scripts/update_data.py            # download + build
    python scripts/update_data.py --offline  # rebuild data/processed from data/raw only

Needs network, git and Node.js (Node only converts Showdown's .js data files).
The app itself never downloads anything.
"""
from __future__ import annotations

import argparse
import datetime as _dt
import json
import re
import shutil
import subprocess
import sys
import tempfile
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
OUT = ROOT / "data" / "processed"

SHOWDOWN = "https://play.pokemonshowdown.com/data/"
SHOWDOWN_JSON = ["pokedex.json", "moves.json", "learnsets.json"]
SHOWDOWN_JS = {  # file -> exported object name
    "typechart.js": "BattleTypeChart",
    "abilities.js": "BattleAbilities",
    "items.js": "BattleItems",
    "formats-data.js": "BattleFormatsData",
}
PKMN = {
    "smogon_sets_gen9.json": "https://data.pkmn.cc/sets/gen9.json",
    "usage_gen9nationaldex.json": "https://data.pkmn.cc/stats/gen9nationaldex.json",
    "usage_gen9ou.json": "https://data.pkmn.cc/stats/gen9ou.json",
}
COBBLEMON_REPO = "https://gitlab.com/cable-mc/cobblemon.git"
COBBLEMON_TAGS_API = "https://gitlab.com/api/v4/projects/cable-mc%2Fcobblemon/repository/tags?per_page=100"
COB_SPECIES_DIR = "common/src/main/resources/data/cobblemon/species"
COB_LANG = "common/src/main/resources/assets/cobblemon/lang/en_us.json"

# Smogon formats to keep, in priority order (engine/sets.py uses the same order).
SET_FORMATS = [
    "nationaldex", "nationaldexubers", "ou", "ubersuu", "nationaldexuu", "uu",
    "nationaldexru", "ru", "nu", "pu", "zu", "battlestadiumsingles", "lc", "nfe",
]

# Cobblemon -> Showdown id exceptions (after toID). Keep this small.
SPECIES_ALIASES: dict[str, str] = {}

# Cobblemon move-list prefix -> compact method letter.
METHOD_CODES = {"tm": "T", "egg": "E", "tutor": "U", "legacy": "X", "special": "S", "form_change": "F"}
LEVEL_CODE = "L"

UA = {"User-Agent": "cobblemon-team-ai-data-updater"}


def toid(s: str) -> str:
    return re.sub(r"[^a-z0-9]", "", str(s).lower())


def fetch(url: str, dest: Path) -> tuple[bool, str]:
    try:
        req = urllib.request.Request(url, headers=UA)
        with urllib.request.urlopen(req, timeout=120) as r:  # follows redirects
            data = r.read()
        dest.write_bytes(data)
        return True, f"OK ({len(data):,} bytes)"
    except Exception as e:  # noqa: BLE001
        return False, f"FAIL ({e})"


def js_to_json(js_path: Path, export: str, dest: Path) -> None:
    code = "process.stdout.write(JSON.stringify(require(process.argv[1])[process.argv[2]]))"
    out = subprocess.run(["node", "-e", code, str(js_path.resolve()), export],
                         check=True, capture_output=True, text=True).stdout
    dest.write_text(out, encoding="utf-8")


def latest_stable_tag() -> str:
    req = urllib.request.Request(COBBLEMON_TAGS_API, headers=UA)
    with urllib.request.urlopen(req, timeout=60) as r:
        tags = json.load(r)
    stable = []
    for t in tags:
        name = t["name"]
        if re.search(r"alpha|beta|rc|snapshot|demo", name, re.I):
            continue
        m = re.fullmatch(r"v?(\d+)\.(\d+)\.(\d+)", name)  # strict x.y.z only (skips e.g. v1.4.0a)
        if m:
            stable.append((tuple(int(x) for x in m.groups()), name))
    stable.sort()
    return stable[-1][1]


def download_cobblemon(status: dict) -> str | None:
    """Sparse-clone Cobblemon at the latest stable tag and merge species + item list into data/raw."""
    try:
        tag = latest_stable_tag()
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "cob"
            subprocess.run(["git", "clone", "-q", "--depth", "1", "--branch", tag, "--filter=blob:none",
                            "--sparse", COBBLEMON_REPO, str(repo)], check=True, capture_output=True)
            subprocess.run(["git", "-C", str(repo), "sparse-checkout", "set", "--no-cone",
                            f"/{COB_SPECIES_DIR}/", f"/{COB_LANG}"], check=True, capture_output=True)
            species = {}
            for f in sorted((repo / COB_SPECIES_DIR).glob("*/*.json")):
                d = json.loads(f.read_text(encoding="utf-8"))
                d["_file"] = f"{f.parent.name}/{f.name}"
                species[f"{f.parent.name}/{f.stem}"] = d
            lang = json.loads((repo / COB_LANG).read_text(encoding="utf-8"))
        items = {k.split(".", 2)[2]: v for k, v in lang.items()
                 if re.fullmatch(r"item\.cobblemon\.[a-z0-9_]+", k)}
        (RAW / "cobblemon_species.json").write_text(json.dumps(species, ensure_ascii=False), encoding="utf-8")
        (RAW / "cobblemon_items.json").write_text(json.dumps(items, ensure_ascii=False, indent=0), encoding="utf-8")
        (RAW / "cobblemon_tag.txt").write_text(tag, encoding="utf-8")
        status[COBBLEMON_REPO + f" (tag {tag})"] = f"OK ({len(species)} species files, {len(items)} item keys)"
        return tag
    except Exception as e:  # noqa: BLE001
        status[COBBLEMON_REPO] = f"FAIL ({e})"
        return None


def download_all() -> dict:
    RAW.mkdir(parents=True, exist_ok=True)
    status: dict[str, str] = {}
    for f in SHOWDOWN_JSON:
        ok, msg = fetch(SHOWDOWN + f, RAW / f)
        status[SHOWDOWN + f] = msg
    for f, export in SHOWDOWN_JS.items():
        ok, msg = fetch(SHOWDOWN + f, RAW / f)
        status[SHOWDOWN + f] = msg
        if ok:
            js_to_json(RAW / f, export, RAW / f.replace(".js", ".json"))
    for f, url in PKMN.items():
        status[url] = fetch(url, RAW / f)[1]
    download_cobblemon(status)
    (RAW / "download_status.json").write_text(json.dumps(status, indent=1), encoding="utf-8")
    return status


# ----------------------------------------------------------------------------------------------
# Build
# ----------------------------------------------------------------------------------------------

def load(name: str):
    return json.loads((RAW / name).read_text(encoding="utf-8"))


def dump(name: str, obj) -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    p = OUT / name
    p.write_text(json.dumps(obj, ensure_ascii=False, separators=(",", ":"), sort_keys=True), encoding="utf-8")
    return p.stat().st_size


STAT_KEYS = ["hp", "atk", "def", "spa", "spd", "spe"]
MOVE_KEYS = ["name", "type", "category", "basePower", "accuracy", "priority", "target", "selfSwitch",
             "status", "volatileStatus", "sideCondition", "pseudoWeather", "weather", "terrain", "heal",
             "boosts", "multihit", "recoil", "drain", "ohko", "selfdestruct", "damage", "isNonstandard",
             "secondary", "self", "willCrit", "forceSwitch", "breaksProtect", "stallingMove"]
MOVE_FLAGS = ["charge", "recharge", "heal", "sound", "contact", "punch", "bite", "slicing", "pulse",
              "bullet", "futuremove", "protect"]


def build_moves(moves: dict) -> dict:
    out = {}
    for mid, m in moves.items():
        if m.get("isZ") or m.get("isMax") or m.get("isNonstandard") in ("CAP", "LGPE", "Custom"):
            continue
        rec = {k: m[k] for k in MOVE_KEYS if k in m}
        rec["flags"] = sorted(k for k in m.get("flags", {}) if k in MOVE_FLAGS)
        sec = m.get("secondary")
        if sec:
            rec["secondary"] = {k: v for k, v in sec.items() if k in ("chance", "boosts", "status", "volatileStatus")}
        if m.get("self"):
            rec["self"] = {k: v for k, v in m["self"].items() if k in ("boosts", "volatileStatus")}
        out[mid] = rec
    return out


def build_items(items: dict, cob_items: dict | None) -> dict:
    cob_ids = {toid(k) for k in (cob_items or {})}
    out = {}
    for iid, it in items.items():
        in_cob = iid in cob_ids if cob_items is not None else it.get("isNonstandard") is None
        mega = it.get("megaStone")
        z = it.get("zMove")
        if not (in_cob or mega or z):
            continue
        rec = {"name": it["name"], "cobblemon": bool(in_cob)}
        if mega:
            rec["megaStone"] = mega if isinstance(mega, dict) else {it.get("megaEvolves", ""): mega}
        if z:
            rec["zMove"] = z
            if it.get("zMoveType"):
                rec["zMoveType"] = it["zMoveType"]
            if it.get("zMoveFrom"):
                rec["zMoveFrom"] = it["zMoveFrom"]
        if it.get("itemUser"):
            rec["itemUser"] = it["itemUser"]
        if it.get("isNonstandard"):
            rec["isNonstandard"] = it["isNonstandard"]
        out[iid] = rec
    return out


def build_typechart(tc: dict, dex: dict) -> dict:
    real_types = sorted({t for s in dex.values() for t in s.get("types", []) if toid(t) in tc})
    # damageTaken codes: 0 neutral, 1 weak (2x), 2 resist (0.5x), 3 immune
    code = {0: 1.0, 1: 2.0, 2: 0.5, 3: 0.0}
    chart = {}
    for dtype in real_types:
        taken = tc[toid(dtype)]["damageTaken"]
        chart[dtype] = {atk: code[taken[atk]] for atk in real_types}
    return {"types": real_types, "defense": chart}  # defense[defending][attacking]


def resolve_prevo(ref: str, by_name: dict) -> str | None:
    """Cobblemon preEvolution like 'meowth alolan' or 'rockruff wolf_form=dusk' -> showdown id."""
    parts = ref.split()
    base = by_name.get(toid(parts[0]))
    if not base:
        return None
    for aspect in parts[1:]:
        for form_aspect, sid in base["aspect_ids"].items():
            if aspect == form_aspect:
                return sid
    return base["id"]


def build_cobblemon(cob: dict, dex: dict, fmt: dict, learn_sd: dict, abilities: dict, report: dict):
    """Returns (species, learnsets) from Cobblemon data mapped onto Showdown ids."""
    species: dict[str, dict] = {}
    own_moves: dict[str, dict[str, str]] = {}
    prevo_ref: dict[str, str] = {}
    by_name: dict[str, dict] = {}
    unmapped, cosmetic, battle_only_skipped = [], [], []

    def parse_moves(lst):
        res: dict[str, set] = {}
        for entry in lst or []:
            pre, _, mv = entry.partition(":")
            code = LEVEL_CODE if pre.isdigit() else METHOD_CODES.get(pre)
            if code is None:
                report.setdefault("unknown_move_prefixes", set()).add(pre)
                continue
            res.setdefault(toid(mv), set()).add(code)
        return res

    def map_abilities(lst):
        out, hidden = [], None
        for a in lst or []:
            h = a.startswith("h:")
            aid = toid(a[2:] if h else a)
            if aid not in abilities:
                report.setdefault("unknown_abilities", set()).add(aid)
                continue
            if h:
                hidden = aid
            if aid not in out:
                out.append(aid)
        return out, hidden

    for key, d in sorted(cob.items()):
        if not d.get("implemented"):
            continue
        base_id = SPECIES_ALIASES.get(toid(d["name"]), toid(d["name"]))
        entries = [(base_id, d, None)]
        for fo in d.get("forms", []):
            fid = SPECIES_ALIASES.get(toid(d["name"] + fo["name"]), toid(d["name"] + fo["name"]))
            entries.append((fid, d, fo))
        by_name[toid(d["name"])] = {"id": base_id, "aspect_ids": {}}
        for sid, d0, fo in entries:
            if fo is not None and fo.get("battleOnly"):
                if sid not in dex:
                    battle_only_skipped.append(f"{d0['name']} ({fo['name']})")
                continue  # Megas / G-Max etc. are attached to their base species below
            if sid not in dex or "baseStats" not in dex[sid]:  # stub entries = cosmetic formes
                same_stats = fo is not None and fo.get("baseStats") in (None, d0.get("baseStats")) \
                    and fo.get("primaryType", d0["primaryType"]) == d0["primaryType"] \
                    and fo.get("secondaryType", d0.get("secondaryType")) == d0.get("secondaryType")
                if same_stats:
                    cosmetic.append(f"{d0['name']} ({fo['name']})")
                else:
                    unmapped.append(f"{d0['name']}" + (f" ({fo['name']})" if fo else ""))
                continue
            src = fo or {}
            if fo is not None:
                for asp in fo.get("aspects", []):
                    by_name[toid(d0["name"])]["aspect_ids"][asp] = sid
            moves = src.get("moves") or d0.get("moves")  # a form with no list uses the base form's
            own_moves[sid] = {m: "".join(sorted(c)) for m, c in parse_moves(moves).items()}
            abil, hidden = map_abilities(src.get("abilities") or d0.get("abilities"))
            labels = sorted(set(d0.get("labels", [])) | set(src.get("labels", [])))
            pre = src.get("preEvolution") or d0.get("preEvolution")  # forms without one use the base's
            if pre:
                prevo_ref[sid] = pre
            species[sid] = {"cobblemon_name": d0["name"] + (f" ({fo['name']})" if fo else ""),
                            "abilities_cob": abil, "hidden_cob": hidden, "labels": labels,
                            "dynamaxBlocked": bool(src.get("dynamaxBlocked", d0.get("dynamaxBlocked", False))),
                            "cob_gmax": any(f.get("name", "").lower() == "gmax" for f in d0.get("forms", []))
                            and fo is None}

    # Learnsets with pre-evolution inheritance.
    prevo_id = {sid: resolve_prevo(ref, by_name) for sid, ref in prevo_ref.items()}
    learnsets: dict[str, dict[str, str]] = {}
    for sid in species:
        merged: dict[str, set] = {}
        seen, cur = set(), sid
        while cur and cur not in seen and cur in own_moves:
            seen.add(cur)
            for m, codes in own_moves[cur].items():
                merged.setdefault(m, set()).update(codes)
            cur = prevo_id.get(cur)
        learnsets[sid] = {m: "".join(sorted(c)) for m, c in sorted(merged.items())}
        species[sid]["prevo_cob"] = prevo_id.get(sid)
    report["unmapped_species"] = unmapped
    report["cosmetic_forms_merged"] = cosmetic
    report["battle_only_forms_without_showdown_entry"] = battle_only_skipped
    return species, learnsets


def build_fallback(dex: dict, fmt: dict, learn_sd: dict):
    """Showdown-only fallback: every species, moves learnable in any generation."""
    species, learnsets = {}, {}
    code = {"L": "L", "M": "T", "E": "E", "T": "U", "S": "S", "V": "S", "D": "S", "R": "S"}
    for sid, s in dex.items():
        if s.get("battleOnly") or s.get("forme", "").startswith(("Mega", "Primal", "Gmax")):
            continue
        species[sid] = {"cobblemon_name": s["name"], "abilities_cob": None, "hidden_cob": None,
                        "labels": [], "dynamaxBlocked": False, "cob_gmax": False, "prevo_cob": None}
        chain, cur = [], sid
        while cur and cur in dex and cur not in chain:
            chain.append(cur)
            cur = toid(dex[cur].get("prevo", "")) or None
        merged: dict[str, set] = {}
        for c in chain + ([toid(s["baseSpecies"])] if s.get("baseSpecies") else []):
            for m, srcs in (learn_sd.get(c, {}).get("learnset") or {}).items():
                for src in srcs:
                    merged.setdefault(m, set()).add(code.get(src[1], "S"))
        learnsets[sid] = {m: "".join(sorted(c)) for m, c in sorted(merged.items())}
    return species, learnsets


def build_species_records(base: dict, dex: dict, fmt: dict, items_out: dict) -> dict:
    mega_items: dict[str, str] = {}
    for iid, it in items_out.items():
        for _base, mega_name in (it.get("megaStone") or {}).items():
            mega_items[toid(mega_name)] = iid
    out = {}

    def rec(sid: str) -> dict:
        s = dex[sid]
        f = fmt.get(sid, {})
        return {"name": s["name"], "num": s["num"], "types": s["types"],
                "bs": [s["baseStats"][k] for k in STAT_KEYS],
                "abilities": [toid(a) for a in s["abilities"].values()],
                "hidden": toid(s["abilities"]["H"]) if "H" in s["abilities"] else None,
                "tags": s.get("tags", []), "nonstd": f.get("isNonstandard", s.get("isNonstandard")),
                "baseSpecies": s.get("baseSpecies", s["name"]), "forme": s.get("forme", ""),
                "nfe": bool(s.get("evos")), "weightkg": s.get("weightkg", 0),
                "tier": f.get("natDexTier") or f.get("tier") or s.get("tier")}

    for sid, cob in sorted(base.items()):
        r = rec(sid)
        if cob["abilities_cob"]:
            r["abilities"] = cob["abilities_cob"]
            r["hidden"] = cob["hidden_cob"]
        r["labels"] = cob["labels"]
        r["prevo"] = cob["prevo_cob"]
        s = dex[sid]
        megas = []
        for other in s.get("otherFormes", []):
            oid = toid(other)
            o = dex.get(oid, {})
            if o.get("forme", "").startswith("Mega") and oid in mega_items:
                megas.append(oid)
                m = rec(oid)
                m["megaItem"] = mega_items[oid]
                m["megaOf"] = sid
                m["battleOnly"] = True
                out[oid] = m
        r["megas"] = megas
        r["gmax"] = bool(s.get("canGigantamax")) and not cob["dynamaxBlocked"]
        r["battleOnly"] = bool(s.get("battleOnly")) or s.get("forme", "").startswith(("Mega", "Primal", "Gmax"))
        out[sid] = r
    return out


def flatten_sets(raw_sets: dict, species_ids: set) -> dict:
    out: dict[str, list] = {}

    def as_list(v):
        if v is None:
            return []
        return v if isinstance(v, list) else [v]

    for name, by_fmt in raw_sets.items():
        sid = toid(name)
        if sid not in species_ids:
            continue
        lst = []
        for fmt_name in SET_FORMATS:
            for set_name, st in (by_fmt.get(fmt_name) or {}).items():
                lst.append({"format": fmt_name, "name": set_name,
                            "moves": [as_list(m) for m in st.get("moves", [])],
                            "ability": as_list(st.get("ability")), "item": as_list(st.get("item")),
                            "nature": as_list(st.get("nature")), "evs": as_list(st.get("evs")),
                            "tera": as_list(st.get("teratypes"))})
        if lst:
            out[sid] = lst
    return out


def compact_usage(nd: dict, ou: dict, species_ids: set) -> dict:
    out = {}

    def top(d, n):
        return {toid(k): round(v, 4) for k, v in sorted(d.items(), key=lambda kv: (-kv[1], kv[0]))[:n]
                if toid(k) not in ("nothing", "")}

    for src_name, src in (("gen9ou", ou), ("gen9nationaldex", nd)):  # natdex overrides ou
        for name, p in src["pokemon"].items():
            sid = toid(name)
            if sid not in species_ids:
                continue
            out[sid] = {"usage": round(p["usage"]["weighted"], 5), "src": src_name,
                        "abilities": top(p.get("abilities", {}), 3), "items": top(p.get("items", {}), 6),
                        "moves": top(p.get("moves", {}), 12), "tera": top(p.get("teraTypes", {}), 3)}
    return out


def build(status: dict | None = None) -> dict:
    report: dict = {}
    dex = load("pokedex.json")
    fmt = load("formats-data.json")
    moves_raw = load("moves.json")
    learn_sd = load("learnsets.json")
    abil_raw = load("abilities.json")
    items_raw = load("items.json")
    tc = load("typechart.json")

    abilities = {aid: {"name": a["name"], "rating": a.get("rating", 0), "num": a.get("num", 0),
                       **({"isNonstandard": a["isNonstandard"]} if a.get("isNonstandard") else {})}
                 for aid, a in abil_raw.items() if aid != "noability" and a.get("num", 0) >= 0}

    cob_ok = (RAW / "cobblemon_species.json").exists() and (RAW / "cobblemon_items.json").exists()
    cob_tag = (RAW / "cobblemon_tag.txt").read_text().strip() if (RAW / "cobblemon_tag.txt").exists() else None
    cob_error = None
    try:
        if not cob_ok:
            raise FileNotFoundError("Cobblemon raw files missing")
        cob = load("cobblemon_species.json")
        cob_items = load("cobblemon_items.json")
        base, learnsets = build_cobblemon(cob, dex, fmt, learn_sd, abilities, report)
        if len(base) < 100:
            raise ValueError(f"only {len(base)} Cobblemon species parsed")
    except Exception as e:  # noqa: BLE001 - fall back loudly, never silently
        cob_ok, cob_error, cob_items = False, str(e), None
        print(f"!!! Cobblemon data unavailable ({e}); FALLING BACK to Showdown learnsets", file=sys.stderr)
        base, learnsets = build_fallback(dex, fmt, learn_sd)

    items = build_items(items_raw, cob_items)
    species = build_species_records(base, dex, fmt, items)
    moves = build_moves(moves_raw)
    # drop learnset entries for moves we don't know (Z/Max/CAP or typos) and report them
    unknown_moves = set()
    for sid, ls in learnsets.items():
        for m in list(ls):
            if m not in moves:
                unknown_moves.add(m)
                del ls[m]
    report["unknown_moves_dropped"] = sorted(unknown_moves)
    for k in ("unknown_move_prefixes", "unknown_abilities"):
        if k in report:
            report[k] = sorted(report[k])

    sets = flatten_sets(load("smogon_sets_gen9.json"), set(species))
    usage = compact_usage(load("usage_gen9nationaldex.json"), load("usage_gen9ou.json"), set(species))
    typechart = build_typechart(tc, dex)

    sizes = {
        "species.json": dump("species.json", species),
        "learnsets.json": dump("learnsets.json", learnsets),
        "moves.json": dump("moves.json", moves),
        "abilities.json": dump("abilities.json", abilities),
        "items.json": dump("items.json", items),
        "typechart.json": dump("typechart.json", typechart),
        "sets.json": dump("sets.json", sets),
        "usage.json": dump("usage.json", usage),
    }
    if status is None and (RAW / "download_status.json").exists():
        status = json.loads((RAW / "download_status.json").read_text())
    meta = {
        "sources": status or {},
        "cobblemon_ok": cob_ok,
        "cobblemon_error": cob_error,
        "cobblemon_tag": cob_tag if cob_ok else None,
        "built_at": _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "downloaded_at": (RAW / "download_status.json").stat().st_mtime if (RAW / "download_status.json").exists() else None,
        "counts": {
            "species_records": len(species),
            "selectable_species": sum(1 for s in species.values() if not s.get("battleOnly")),
            "moves": len(moves), "abilities": len(abilities),
            "items_in_cobblemon": sum(1 for i in items.values() if i["cobblemon"]),
            "mega_stones": sum(1 for i in items.values() if i.get("megaStone")),
            "z_crystals": sum(1 for i in items.values() if i.get("zMove")),
            "species_with_smogon_sets": len(sets), "species_with_usage": len(usage),
        },
        "report": report,
        "sizes_bytes": sizes,
    }
    if isinstance(meta["downloaded_at"], float):
        meta["downloaded_at"] = _dt.datetime.fromtimestamp(meta["downloaded_at"], _dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    sizes["meta.json"] = dump("meta.json", meta)
    print(json.dumps({k: v for k, v in meta.items() if k != "report"}, indent=1))
    print("unmapped species:", report.get("unmapped_species"))
    print("total processed size: %.2f MB" % (sum(sizes.values()) / 1e6))
    return meta


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--offline", action="store_true", help="skip downloads, rebuild from data/raw")
    args = ap.parse_args()
    status = None
    if not args.offline:
        if not shutil.which("node"):
            sys.exit("Node.js is required to convert Showdown .js data files")
        status = download_all()
        for url, msg in status.items():
            print(f"{msg.split()[0]:4} {url}")
    build(status)


if __name__ == "__main__":
    main()
