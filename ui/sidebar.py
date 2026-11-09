"""Sidebar settings (Hebrew labels)."""
from __future__ import annotations

import streamlit as st

from engine.data_loader import GameData
from engine.legality import MOVE_SOURCE_ALL, MOVE_SOURCE_LEVELUP, Settings, parse_server_list

MOVE_SOURCE_LABELS = {
    MOVE_SOURCE_ALL: "הכול (level-up, TM, egg, tutor)",
    MOVE_SOURCE_LEVELUP: "Level-up בלבד",
}


def render_sidebar(data: GameData) -> Settings:
    sb = st.sidebar
    sb.header("הגדרות")
    sb.markdown("**מכניקות קרב**")
    mega = sb.toggle("Mega", value=False, key="opt_mega")
    zmoves = sb.toggle("Z-Moves", value=False, key="opt_z")
    dynamax = sb.toggle("Dynamax", value=False, key="opt_dmax")
    tera = sb.toggle("Tera", value=False, key="opt_tera")
    sb.caption("Tera ו-Dynamax אינם מדומים במנוע — הם מוצגים כהמלצה בלבד.")
    sb.markdown("**פוקימונים**")
    legends = sb.toggle("לכלול אגדיים ומיתיים", value=False, key="opt_legends")
    level = sb.radio("רמה", options=[50, 100], index=0, horizontal=True, key="opt_level")
    source = sb.radio("מקורות מהלכים", options=list(MOVE_SOURCE_LABELS), index=0,
                      format_func=MOVE_SOURCE_LABELS.get, key="opt_source")
    text = sb.text_area("פוקימונים זמינים בשרת שלנו", key="opt_server", height=110,
                        placeholder="Garchomp, Corviknight\nRotom-Wash ...",
                        help="מופרד בפסיקים או בשורות. ריק = כל הפוקימונים שקיימים בקובלמון.")
    server_ids, unknown = parse_server_list(data, text)
    if unknown:
        sb.warning("שמות שלא זוהו: " + ", ".join(unknown))
    elif server_ids is not None:
        sb.caption(f"זוהו {len(server_ids)} פוקימונים מהרשימה.")
    return Settings(mega=mega, zmoves=zmoves, dynamax=dynamax, tera=tera, legendaries=legends,
                    level=int(level), move_source=source, server_list=server_ids)
