"""Check Showdown gen5 sprite URLs for ~30 tricky species (network needed; dev tool only)."""
import json
import sys
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from engine.data_loader import load_data  # noqa: E402
from ui.sprites import sprite_url  # noqa: E402

TRICKY = ["mrmime", "mrmimegalar", "mimejr", "hooh", "porygonz", "porygon2", "farfetchd", "sirfetchd",
          "charizardmegax", "charizardmegay", "urshifurapidstrike", "urshifu", "raichualola", "ninetalesalola",
          "typenull", "jangmoo", "kommoo", "tapukoko", "nidoranf", "nidoranm", "flabebe", "rotomwash",
          "taurospaldeacombat", "zygarde10", "necrozmaduskmane", "calyrexshadow", "ironvaliant", "greattusk",
          "wochien", "chiyu", "basculegionf", "indeedeef", "lycanrocmidnight", "oricorio", "oricoriopompom",
          "darmanitangalar", "slowkinggalar", "ogerponwellspring"]

data = load_data()
raw_dex = json.loads((Path(__file__).resolve().parent.parent / "data" / "raw" / "pokedex.json").read_text())
bad = 0
for sid in TRICKY:
    sp = data.species.get(sid) or raw_dex.get(sid)  # raw dex for species not implemented in Cobblemon
    if not sp:
        print(f"SKIP {sid}")
        continue
    url = sprite_url(sp)
    try:
        req = urllib.request.Request(url, method="HEAD", headers={"User-Agent": "cobblemon-team-ai-sprite-check"})
        code = urllib.request.urlopen(req, timeout=20).status
    except Exception as e:  # noqa: BLE001
        code = getattr(e, "code", str(e))
    ok = code == 200
    bad += not ok
    print(f"{'OK  ' if ok else 'FAIL'} {sid:22} {url}")
print("failures:", bad)
