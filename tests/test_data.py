import json
from pathlib import Path

from engine.data_loader import FILES, PROCESSED

ROOT = Path(__file__).resolve().parent.parent


def test_processed_files_load(data):
    for name in FILES:
        assert (PROCESSED / f"{name}.json").exists()
    assert len(data.species) > 500 and len(data.moves) > 500 and len(data.items) > 100
    assert len(data.typechart["types"]) == 18


def test_processed_size_budget():
    total = sum(p.stat().st_size for p in PROCESSED.glob("*.json"))
    assert total < 15_000_000


def test_species_mapping_coverage(data):
    raw = json.loads((ROOT / "data" / "raw" / "cobblemon_species.json").read_text())
    implemented = [d for d in raw.values() if d.get("implemented")]
    report = data.meta["report"]
    unmapped = report["unmapped_species"]
    mapped_bases = sum(1 for d in implemented if d["name"] not in {u.split(" (")[0] for u in unmapped})
    coverage = mapped_bases / len(implemented)
    print(f"species mapping coverage: {coverage:.1%} ({mapped_bases}/{len(implemented)}), unmapped: {unmapped}")
    assert coverage >= 0.99
    assert data.meta["cobblemon_ok"] is True
    assert data.meta["cobblemon_tag"]


def test_learnsets_only_known_moves(data):
    for sid, ls in data.learnsets.items():
        assert set(ls) <= set(data.moves), sid
