"""RTL + mobile CSS, injected once. RTL is applied to text blocks, labels, tabs and the sidebar only —
never to the whole Streamlit root (that breaks widgets)."""
from __future__ import annotations

import html

import streamlit as st

TYPE_COLORS = {
    "Normal": "#A8A77A", "Fire": "#EE8130", "Water": "#6390F0", "Electric": "#F7D02C", "Grass": "#7AC74C",
    "Ice": "#96D9D6", "Fighting": "#C22E28", "Poison": "#A33EA1", "Ground": "#E2BF65", "Flying": "#A98FF3",
    "Psychic": "#F95587", "Bug": "#A6B91A", "Rock": "#B6A136", "Ghost": "#735797", "Dragon": "#6F35FC",
    "Dark": "#705746", "Steel": "#B7B7CE", "Fairy": "#D685AD", "Stellar": "#40B5A5",
}
DARK_TEXT_TYPES = {"Electric", "Ice", "Ground", "Steel", "Normal", "Grass", "Bug", "Rock", "Fairy", "Flying"}

CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Rubik:wght@400;500;700&display=swap');
html, body, .stApp, .stMarkdown, [data-testid="stMarkdownContainer"], [data-testid="stWidgetLabel"],
.stTabs [data-baseweb="tab"] p, button p, input, textarea, h1, h2, h3 {
  font-family: 'Rubik', 'Heebo', 'Segoe UI', Arial, sans-serif;
}
/* Hebrew text blocks */
[data-testid="stMarkdownContainer"], [data-testid="stCaptionContainer"], .stAlert,
[data-testid="stWidgetLabel"], [data-testid="stHeading"], .rtl { direction: rtl; text-align: right; }
[data-testid="stSidebar"] [data-testid="stSidebarContent"] { direction: rtl; text-align: right; }
[data-testid="stSidebar"] textarea { direction: ltr; text-align: left; }
.stTabs [data-baseweb="tab-list"] { direction: rtl; gap: 0.25rem; flex-wrap: wrap; }
.stTabs [data-baseweb="tab"] { padding: 0.4rem 0.7rem; }
/* Toggles / checkboxes: the Hebrew label stays RTL, but BaseWeb places the switch knob and the
   checkbox mark with physical offsets, so the switch element itself must stay LTR. Under RTL the
   knob sat on the right when OFF (so OFF looked ON) and the ON transform (translateX) pushed it
   outside the track. ([data-testid="stToggle"] does not exist in Streamlit 1.67 — it is stCheckbox.) */
.stRadio [role="radiogroup"], .stCheckbox, [data-testid="stCheckbox"] { direction: rtl; }
[data-testid="stCheckbox"] label > div:not([data-testid="stWidgetLabel"]) { direction: ltr; }
/* Same class of problem inside the RTL sidebar: keep physically ordered controls LTR. */
[data-testid="stSidebar"] [data-testid="stNumberInputContainer"] { direction: ltr; }
[data-testid="stSidebar"] [data-testid="stMultiSelectTagsContainer"] [data-tag] { direction: ltr; }
.block-container { padding-top: 2.2rem; padding-left: 1rem; padding-right: 1rem; max-width: 1200px; }
.app-subtitle { font-size: 1.15rem; opacity: 0.85; margin-top: -0.6rem; margin-bottom: 0.4rem; }
[dir="ltr"] { unicode-bidi: isolate; }

/* sprite grid under the multiselect */
.sprite-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(76px, 1fr)); gap: 6px; margin: 6px 0 12px; }
.sprite-cell { background: rgba(255,255,255,0.04); border-radius: 10px; text-align: center; padding: 4px 2px; }
.sprite-cell img { width: 64px; height: 64px; image-rendering: pixelated; }
.sprite-cell div { font-size: 0.72rem; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }

/* team cards */
.card-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(min(100%, 330px), 1fr)); gap: 12px; direction: rtl; }
.poke-card { background: #1c2230; border: 1px solid #2c3446; border-radius: 14px; padding: 12px; direction: rtl; text-align: right; min-width: 0; }
.pc-head { display: flex; gap: 10px; align-items: center; }
.pc-head img { width: 84px; height: 84px; flex: 0 0 84px; image-rendering: pixelated; background: rgba(255,255,255,0.05); border-radius: 12px; }
.pc-name { font-size: 1.12rem; font-weight: 700; }
.pc-sub { font-size: 0.85rem; opacity: 0.85; margin-top: 2px; }
.role { display: inline-block; background: #2f3b55; border-radius: 999px; padding: 1px 9px; font-size: 0.8rem; margin-top: 4px; }
.badge-row { display: flex; gap: 4px; flex-wrap: wrap; margin-top: 4px; }
.tbadge { display: inline-block; border-radius: 6px; padding: 1px 7px; font-size: 0.74rem; font-weight: 600; color: #fff; direction: ltr; text-shadow: 0 1px 1px rgba(0,0,0,0.35); }
.tbadge.dark { color: #1b1b1b; text-shadow: none; }
.gmax { background: linear-gradient(90deg,#e0245e,#7b2ff7); }
.pc-rows { margin-top: 8px; font-size: 0.9rem; line-height: 1.55; }
.pc-rows b { opacity: 0.75; font-weight: 500; }
.moves { display: grid; grid-template-columns: 1fr 1fr; gap: 5px; margin-top: 8px; }
.move { background: rgba(255,255,255,0.05); border-radius: 8px; padding: 3px 6px; font-size: 0.86rem; direction: ltr; text-align: left;
        border-left: 5px solid #888; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.stats { display: grid; grid-template-columns: repeat(6, 1fr); gap: 3px; margin-top: 6px; direction: ltr; }
.stats div { background: rgba(255,255,255,0.05); border-radius: 6px; text-align: center; font-size: 0.78rem; padding: 2px 0; }
.stats span { display: block; font-size: 0.66rem; opacity: 0.65; }
.why { margin-top: 8px; font-size: 0.86rem; background: rgba(110,160,255,0.10); border-radius: 8px; padding: 5px 8px; }

/* heatmap */
.hm-wrap { overflow-x: auto; -webkit-overflow-scrolling: touch; margin: 8px 0; border-radius: 10px; }
table.hm { border-collapse: collapse; font-size: 0.8rem; direction: rtl; min-width: 100%; }
table.hm th, table.hm td { padding: 3px 5px; text-align: center; border: 1px solid #2a3142; white-space: nowrap; }
table.hm th { background: #1c2230; position: sticky; top: 0; }
table.hm th img { width: 40px; height: 40px; image-rendering: pixelated; display: block; margin: 0 auto; }
table.hm th .hm-name { font-size: 0.68rem; max-width: 70px; overflow: hidden; text-overflow: ellipsis; direction: ltr; }
table.hm td.atk { position: sticky; right: 0; background: #151a24; z-index: 1; }
.c4 { background: #b3261e; color: #fff; font-weight: 700; } .c2 { background: #e3605a; color: #fff; }
.c1 { background: transparent; opacity: 0.45; } .ch { background: #3f8f5b; color: #fff; } .cq { background: #22704a; color: #fff; font-weight: 700; }
.c0 { background: #3c3f58; color: #fff; font-weight: 700; }
.tot-w { color: #ff8a80; font-weight: 700; } .tot-r { color: #81e6a1; font-weight: 700; }

/* summary */
.summary { background: #1c2230; border: 1px solid #2c3446; border-radius: 12px; padding: 10px 14px; direction: rtl; line-height: 1.8; }
.ok { color: #81e6a1; font-weight: 700; } .bad { color: #ff8a80; font-weight: 700; }

@media (max-width: 640px) {
  .block-container { padding-left: 0.6rem; padding-right: 0.6rem; }
  h1 { font-size: 1.7rem !important; }
  .moves { grid-template-columns: 1fr 1fr; }
}
</style>
"""


def inject_css() -> None:
    st.markdown(CSS, unsafe_allow_html=True)


def ltr(text: str) -> str:
    """Wrap an English name for display inside Hebrew text."""
    return f'<span dir="ltr">{html.escape(str(text))}</span>'


def type_badge(t: str) -> str:
    color = TYPE_COLORS.get(t, "#777")
    cls = "tbadge dark" if t in DARK_TEXT_TYPES else "tbadge"
    return f'<span class="{cls}" style="background:{color}">{html.escape(t)}</span>'
