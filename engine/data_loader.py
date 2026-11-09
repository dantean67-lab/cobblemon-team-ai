"""Load the processed data files (data/processed/*.json). Never touches the network."""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

PROCESSED = Path(__file__).resolve().parent.parent / "data" / "processed"
FILES = ("species", "learnsets", "moves", "abilities", "items", "typechart", "sets", "usage", "meta")


def toid(s: str) -> str:
    """Showdown's toID: lowercase, keep only a-z and 0-9."""
    return re.sub(r"[^a-z0-9]", "", str(s).lower())


@dataclass(frozen=True)
class GameData:
    species: dict
    learnsets: dict
    moves: dict
    abilities: dict
    items: dict
    typechart: dict
    sets: dict
    usage: dict
    meta: dict

    @property
    def types(self) -> list[str]:
        return self.typechart["types"]

    @property
    def cobblemon_ok(self) -> bool:
        return bool(self.meta.get("cobblemon_ok"))


@lru_cache(maxsize=2)
def load_data(path: str | None = None) -> GameData:
    base = Path(path) if path else PROCESSED
    parts = {name: json.loads((base / f"{name}.json").read_text(encoding="utf-8")) for name in FILES}
    return GameData(**parts)
