"""Pokémon Showdown sprite URLs (gen5 style) with Showdown's sprite-id rules."""
from __future__ import annotations

from engine.data_loader import toid

SPRITE_BASE = "https://play.pokemonshowdown.com/sprites/gen5/"
FALLBACK = "https://play.pokemonshowdown.com/sprites/gen5/0.png"


def sprite_id(species: dict) -> str:
    """'Charizard-Mega-X' -> 'charizard-megax', 'Mr. Mime' -> 'mrmime', 'Urshifu-Rapid-Strike' -> 'urshifu-rapidstrike'."""
    base = toid(species.get("baseSpecies") or species["name"])
    forme = species.get("forme") or ""
    return f"{base}-{toid(forme)}" if forme else base


def sprite_url(species: dict) -> str:
    return f"{SPRITE_BASE}{sprite_id(species)}.png"


def img_tag(species: dict, alt: str = "", cls: str = "") -> str:
    onerr = f"this.onerror=null;this.src='{FALLBACK}'"
    c = f' class="{cls}"' if cls else ""
    return f'<img{c} src="{sprite_url(species)}" alt="{alt}" loading="lazy" onerror="{onerr}">'
