# Data sources

The app never downloads anything at runtime. It only reads `data/processed/*.json`,
which `scripts/update_data.py` builds from the raw files in `data/raw/`.

## Sources

| What | URL | Used for |
|---|---|---|
| Pokémon Showdown pokedex | https://play.pokemonshowdown.com/data/pokedex.json | types, base stats, formes, tags (legendary etc.) |
| Pokémon Showdown moves | https://play.pokemonshowdown.com/data/moves.json | move data (type, power, accuracy, effects) |
| Pokémon Showdown learnsets | https://play.pokemonshowdown.com/data/learnsets.json | **fallback only** (if Cobblemon data can't be loaded) |
| Pokémon Showdown type chart | https://play.pokemonshowdown.com/data/typechart.js | 18x18 type effectiveness |
| Pokémon Showdown abilities | https://play.pokemonshowdown.com/data/abilities.js | ability names and ratings |
| Pokémon Showdown items | https://play.pokemonshowdown.com/data/items.js | item data, Mega Stones, Z-Crystals |
| Pokémon Showdown formats data | https://play.pokemonshowdown.com/data/formats-data.js | tiers, non-standard flags (CAP, LGPE ...) |
| Smogon sets (via pkmn) | https://data.pkmn.cc/sets/gen9.json | preferred competitive sets |
| Smogon usage (via pkmn) | https://data.pkmn.cc/stats/gen9nationaldex.json | usage %, common abilities |
| Smogon usage (via pkmn) | https://data.pkmn.cc/stats/gen9ou.json | usage % (fallback when not in National Dex stats) |
| Cobblemon (latest stable tag) | https://gitlab.com/cable-mc/cobblemon | which species/forms are implemented, Cobblemon learnsets, which held items exist |

The exact Cobblemon tag, download time, per-URL status and record counts are in `data/processed/meta.json`.

Cobblemon files used (from the tag):
- `common/src/main/resources/data/cobblemon/species/**.json` → merged into `data/raw/cobblemon_species.json`
- `common/src/main/resources/assets/cobblemon/lang/en_us.json` → `item.cobblemon.<id>` keys → `data/raw/cobblemon_items.json`

## Credits

- **Pokémon Showdown** (Smogon / Guangcong Luo and contributors) — battle data and sprites.
- **Smogon University**, via **pkmn** (data.pkmn.cc) — sets and usage statistics.
- **Cobblemon** (cable-mc) — species, learnsets and items that exist in the mod.

Pokémon and all related names are trademarks of Nintendo, Game Freak and The Pokémon Company.
This is a fan project and is not affiliated with any of them.

## Re-running the update

Requirements: Python 3.11+, `git`, Node.js (only to convert Showdown's `.js` data files) and network access.

```bash
python scripts/update_data.py            # download everything and rebuild data/processed
python scripts/update_data.py --offline  # rebuild data/processed from data/raw only
pytest                                   # must pass before pushing
```

If the Cobblemon download or parsing fails, the script prints a loud warning and builds a
Showdown-only fallback (`cobblemon_ok: false` in meta.json); the app then shows a Hebrew warning banner.
