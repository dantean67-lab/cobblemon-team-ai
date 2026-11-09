"""Team member cards and the Hebrew "why chosen" line (fixed templates, no LLM)."""
from __future__ import annotations

import html

from engine.data_loader import GameData
from engine.sets import PokemonSet
from engine.stats import STAT_KEYS, calc_all

from .rtl_css import TYPE_COLORS, ltr, type_badge
from .sprites import img_tag

ROLE_HE = {
    "phys_att": "תוקף פיזי", "spec_att": "תוקף מיוחד", "phys_wall": "חומה פיזית", "spec_wall": "חומה מיוחדת",
    "pivot": "Pivot", "hazard": "מניח מלכודות", "support": "תמיכה", "speed": "שליטה במהירות",
}
STAT_LABEL = {"hp": "HP", "atk": "Atk", "def": "Def", "spa": "SpA", "spd": "SpD", "spe": "Spe"}
SPEED_REASON_HE = {
    "fast": "מהיר מאוד", "scarf": "מחזיק Choice Scarf", "priority": "יש לו מהלך עדיפות",
    "move": "יש לו מהלך שליטה במהירות",
}


def _types(ts) -> str:
    return ", ".join(ltr(t) for t in ts)


def why_line(c: dict) -> str:
    """Up to two reasons, chosen in a fixed order of importance."""
    reasons = []
    if c.get("only_speed"):
        reasons.append(f"השליטה במהירות היחידה בקבוצה ({SPEED_REASON_HE.get(c.get('speed_reason'), '')})")
    if c.get("is_pivot"):
        reasons.append("ה-Pivot ההגנתי של הקבוצה")
    if c.get("covers_weak"):
        reasons.append(f"עמיד ל-{_types(c['covers_weak'][:3])} ששאר הקבוצה חלשה אליהם")
    if c.get("unique_cover"):
        reasons.append(f"היחיד שפוגע חזק ב-{_types(c['unique_cover'][:3])}")
    if not reasons:
        if c.get("speed_control"):
            reasons.append(f"מוסיף מהירות לקבוצה ({SPEED_REASON_HE.get(c.get('speed_reason'), '')})")
        reasons.append("פוקימון חזק במיוחד (סטטים ושימוש גבוהים)" if c.get("strength", 0) >= 1.0
                       else "מאזן את הקבוצה")
    return " · ".join(reasons[:2])


def evs_text(evs: dict) -> str:
    return " / ".join(f"{evs[k]} {STAT_LABEL[k]}" for k in STAT_KEYS if evs.get(k))


def card_html(data: GameData, s: PokemonSet, contribution: dict | None, level: int) -> str:
    form = data.species[s.form]
    badges = "".join(type_badge(t) for t in s.types)
    if s.gmax:
        badges += '<span class="tbadge gmax">G-Max</span>'
    item_name = data.items[s.item]["name"] if s.item else "—"
    ability = data.abilities.get(s.ability, {}).get("name", s.ability)
    stats = calc_all(s.bs, level, s.evs, s.nature)
    moves = []
    for m in s.moves:
        mv = data.moves[m]
        color = TYPE_COLORS.get(mv["type"], "#888")
        moves.append(f'<div class="move" style="border-left-color:{color}" title="{html.escape(mv["type"])}">'
                     f'{html.escape(mv["name"])}</div>')
    rows = [
        f"<b>פריט:</b> {ltr(item_name)}",
        f"<b>יכולת:</b> {ltr(ability)}",
        f"<b>טבע:</b> {ltr(s.nature)}",
        f"<b>{ltr('EVs')}:</b> {ltr(evs_text(s.evs))}",
    ]
    if s.tera:
        rows.append(f"<b>Tera מומלץ:</b> {type_badge(s.tera)}")
    stat_grid = '<div class="stats">' + "".join(
        f"<div><span>{STAT_LABEL[k]}</span>{stats[k]}</div>" for k in STAT_KEYS) + "</div>"
    why = f'<div class="why">💡 {why_line(contribution)}</div>' if contribution else ""
    return (f'<div class="poke-card"><div class="pc-head">{img_tag(form, s.name)}<div>'
            f'<div class="pc-name">{ltr(s.name)}</div><div class="badge-row">{badges}</div>'
            f'<span class="role">{ROLE_HE.get(s.role, s.role)}</span></div></div>'
            f'<div class="pc-rows">{"<br>".join(rows)}</div>'
            f'<div class="rtl" style="font-size:0.78rem;opacity:0.75;margin-top:6px">סטטים ברמה {level}</div>{stat_grid}'
            f'<div class="moves">{"".join(moves)}</div>{why}</div>')


def cards_grid_html(data: GameData, members: list[PokemonSet], contributions: list[dict], level: int) -> str:
    cards = [card_html(data, s, c, level) for s, c in zip(members, contributions)]
    return f'<div class="card-grid">{"".join(cards)}</div>'


def sprite_grid_html(data: GameData, species_ids: list[str]) -> str:
    cells = []
    for sid in species_ids:
        sp = data.species[sid]
        cells.append(f'<div class="sprite-cell">{img_tag(sp, sp["name"])}<div dir="ltr">{html.escape(sp["name"])}</div></div>')
    return f'<div class="sprite-grid">{"".join(cells)}</div>'
