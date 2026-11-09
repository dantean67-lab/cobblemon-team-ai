"""Team weakness heatmap (18 attacking types x team members) and the short team summary."""
from __future__ import annotations

import html

from engine.data_loader import GameData
from engine.scoring import Profile, pivot_member

from .rtl_css import ltr, type_badge
from .sprites import img_tag

CELL = {4.0: ("c4", "4×"), 2.0: ("c2", "2×"), 1.0: ("c1", "1"), 0.5: ("ch", "½"), 0.25: ("cq", "¼"), 0.0: ("c0", "0")}


def _cell(x: float) -> str:
    if x in CELL:
        cls, txt = CELL[x]
    elif x > 2:
        cls, txt = "c4", f"{x:g}×"
    elif x > 1:
        cls, txt = "c2", f"{x:g}×"
    elif x == 0:
        cls, txt = "c0", "0"
    else:
        cls, txt = "ch", f"{x:g}"
    return f'<td class="{cls}">{txt}</td>'


def heatmap_html(data: GameData, team: list[Profile]) -> str:
    head = "".join(f'<th>{img_tag(data.species[p.set.form], p.set.name)}<div class="hm-name">{html.escape(p.set.name)}</div></th>'
                   for p in team)
    rows = []
    for i, t in enumerate(data.types):
        cells = "".join(_cell(p.defense[i]) for p in team)
        weak = sum(1 for p in team if p.defense[i] > 1)
        res = sum(1 for p in team if p.defense[i] < 1)
        rows.append(f'<tr><td class="atk">{type_badge(t)}</td>{cells}'
                    f'<td class="tot-w">{weak or ""}</td><td class="tot-r">{res or ""}</td></tr>')
    return (f'<div class="hm-wrap"><table class="hm"><thead><tr><th>סוג תוקף</th>{head}'
            f'<th>חולשות</th><th>עמידויות</th></tr></thead><tbody>{"".join(rows)}</tbody></table></div>')


def team_summary(data: GameData, team: list[Profile]) -> dict:
    types = data.types
    shared = []
    for i, t in enumerate(types):
        weak = sum(1 for p in team if p.defense[i] > 1)
        res = sum(1 for p in team if p.defense[i] < 1)
        if weak >= 2 and weak > res:
            shared.append((weak - res, weak, t, res))
    shared.sort(key=lambda x: (-x[0], -x[1], x[2]))
    uncovered = [t for i, t in enumerate(types) if max(p.offense[i] for p in team) < 2]
    unhittable = [t for i, t in enumerate(types) if max(p.offense[i] for p in team) < 1]
    speed = [p.set.name for p in team if p.speed_control]
    piv = pivot_member(team, data)
    return {"shared": shared[:4], "uncovered": uncovered, "unhittable": unhittable, "speed": speed,
            "pivot": piv.set.name if piv else None, "pivot_full": bool(piv and piv.pivot)}


def summary_html(data: GameData, team: list[Profile]) -> str:
    s = team_summary(data, team)
    lines = []
    if s["shared"]:
        parts = [f"{type_badge(t)} ({w} חלשים, {r} עמידים)" for _, w, t, r in s["shared"]]
        lines.append("⚠️ <b>חולשות משותפות:</b> " + " ".join(parts))
    else:
        lines.append('<span class="ok">✔</span> אין חולשה משותפת חמורה')
    if s["uncovered"]:
        lines.append("🎯 <b>סוגים שאף אחד לא פוגע בהם חזק:</b> " + " ".join(type_badge(t) for t in s["uncovered"]))
    else:
        lines.append('<span class="ok">✔</span> הקבוצה פוגעת חזק בכל 18 הסוגים')
    if s["unhittable"]:
        lines.append('<span class="bad">✘</span> <b>סוגים שהקבוצה לא פוגעת בהם אפילו רגיל:</b> '
                     + " ".join(type_badge(t) for t in s["unhittable"]))
    if s["speed"]:
        lines.append('<span class="ok">✔</span> <b>שליטה במהירות:</b> ' + ", ".join(ltr(n) for n in s["speed"]))
    else:
        lines.append('<span class="bad">✘</span> <b>אין שליטה במהירות</b>')
    if s["pivot"]:
        tail = "" if s["pivot_full"] else " (בלי מהלך Pivot או Regenerator)"
        lines.append(f'<span class="ok">✔</span> <b>Pivot הגנתי:</b> {ltr(s["pivot"])}{tail}')
    else:
        lines.append('<span class="bad">✘</span> <b>אין Pivot הגנתי</b>')
    return '<div class="summary">' + "<br>".join(lines) + "</div>"
