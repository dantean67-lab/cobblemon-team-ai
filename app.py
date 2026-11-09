"""Cobblemon Team AI — בונה הקבוצות לקובלמון (Stage 1: tab 1, no LLM)."""
from __future__ import annotations

import streamlit as st

from engine.data_loader import GameData, load_data
from engine.legality import Settings, allowed_species
from engine.scoring import make_profile
from engine.search import build_team
from engine.sets import build_candidates
from ui.cards import cards_grid_html, sprite_grid_html
from ui.heatmap import heatmap_html, summary_html
from ui.rtl_css import inject_css
from ui.sidebar import render_sidebar

st.set_page_config(page_title="Cobblemon Team AI", page_icon="⚔️", layout="wide",
                   initial_sidebar_state="collapsed")

# A varied demo selection (filtered to what is allowed under the current settings).
DEMO_SPECIES = ["garchomp", "corviknight", "rotomwash", "toxapex", "volcarona", "dragapult", "blissey",
                "scizor", "gengar", "azumarill", "tyranitar", "gholdengo"]
DEMO_SIZE = 10


@st.cache_resource(show_spinner=False)
def get_data() -> GameData:
    return load_data()


@st.cache_resource(show_spinner=False, max_entries=32)
def get_candidates(settings: Settings, species: tuple[str, ...]):
    return build_candidates(get_data(), list(species), settings)


def load_demo(allowed: list[str]) -> None:
    allowed_set = set(allowed)
    st.session_state["my_pokemon"] = [s for s in DEMO_SPECIES if s in allowed_set][:DEMO_SIZE]
    st.session_state.pop("result", None)


def tab_my_team(data: GameData, settings: Settings) -> None:
    allowed = allowed_species(data, settings)
    if "my_pokemon" in st.session_state:  # drop picks that the new settings made illegal
        st.session_state["my_pokemon"] = [s for s in st.session_state["my_pokemon"] if s in set(allowed)]
    st.markdown("בחרו את הפוקימונים שיש לכם, והמנוע יבנה מהם את הקבוצה הטובה ביותר של עד 6.")
    picked = st.multiselect("הפוקימונים שלי", options=allowed, key="my_pokemon",
                            format_func=lambda sid: data.species[sid]["name"],
                            placeholder="חפשו פוקימון באנגלית…")
    if picked:
        st.markdown(sprite_grid_html(data, picked), unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    c1.button("טען דוגמה", key="demo", on_click=load_demo, args=(allowed,), use_container_width=True)
    build = c2.button("בנה קבוצה", key="build", type="primary", use_container_width=True)

    if build:
        if not picked:
            st.warning("בחרו לפחות פוקימון אחד (או לחצו על \"טען דוגמה\").")
            return
        cands = get_candidates(settings, tuple(sorted(picked)))
        st.session_state["result"] = (settings, tuple(sorted(picked)), build_team(data, cands))

    res = st.session_state.get("result")
    if not res:
        return
    res_settings, res_picked, result = res
    if res_settings != settings or res_picked != tuple(sorted(picked)):
        st.info("ההגדרות או הבחירה השתנו — לחצו שוב על \"בנה קבוצה\" כדי לעדכן.")
    if len(result.members) < 6:
        st.info(f"נבחרו רק {len(result.members)} פוקימונים, אז הקבוצה נבנתה מכולם (פחות מ-6).")
    st.subheader("הקבוצה שלך")
    st.markdown(cards_grid_html(data, result.members, result.contributions, res_settings.level),
                unsafe_allow_html=True)
    profiles = [make_profile(data, s) for s in result.members]
    st.subheader("סיכום")
    st.markdown(summary_html(data, profiles), unsafe_allow_html=True)
    st.subheader("מפת חולשות")
    st.caption("כמה נזק כל סוג התקפה עושה לכל חבר בקבוצה (כולל יכולות כמו Levitate). גללו הצידה בטלפון.")
    st.markdown(heatmap_html(data, profiles), unsafe_allow_html=True)
    st.caption(f"ציון קבוצה: {result.score:.1f} · זמן חישוב: {result.elapsed * 1000:.0f} ms")


def main() -> None:
    inject_css()
    data = get_data()
    st.title("Cobblemon Team AI")
    st.markdown('<div class="app-subtitle">בונה הקבוצות לקובלמון</div>', unsafe_allow_html=True)
    if not data.cobblemon_ok:
        st.warning("⚠️ לא הצלחנו לטעון את נתוני קובלמון. משתמשים בנתוני Showdown בלבד: כל הפוקימונים מוצגים "
                   "(גם כאלה שאולי לא קיימים בקובלמון), והמהלכים הם מכל הדורות.")
    settings = render_sidebar(data)
    t1, t2, t3 = st.tabs(["הקבוצה שלי", "קבוצה מאפס", "נגד יריב"])
    with t1:
        tab_my_team(data, settings)
    with t2:
        st.info("בקרוב — שלב 2")
    with t3:
        st.info("בקרוב — שלב 2")
    tag = data.meta.get("cobblemon_tag") or "—"
    st.markdown(f'<div class="rtl" style="font-size:0.8rem;opacity:0.6">נתונים: '
                f'<span dir="ltr">Pokémon Showdown · Smogon (pkmn) · Cobblemon {tag}</span></div>',
                unsafe_allow_html=True)


main()
