# CLAUDE.md — Cobblemon Team AI (בונה הקבוצות לקובלמון)

Permanent rules for every stage of this project. Read before doing anything.

## 0. Who we work with
- The owner, Eitan, is not a programmer and never edits code by hand. Never ask him to edit files. Do everything yourself.
- He tests on a Samsung Galaxy S23 Ultra, so every screen must work well at about 390px width.
- Free tools only: GitHub free, Streamlit Community Cloud, Groq free API (Stage 3 only). No paid services or APIs.
- If something in a prompt turns out wrong or impossible, don't quietly work around it. Do the closest correct thing and list it in the report.

## 1. Core principle: DATA DECIDES, AI EXPLAINS
- Every Pokémon fact (types, stats, abilities, learnsets, moves, type chart, items) comes from the data files in /data. Never hard-code facts from memory.
- Team selection, sets and scores come from deterministic, unit-tested Python. Same input gives the same output (break ties by species id).
- The language model (Stage 3, Groq) only *explains*. It never decides team members, moves, items or abilities.

## 2. UI language
- All UI text is in Hebrew and RTL.
- Pokémon, move, item, ability, nature and type names stay in English (wrap them in `<span dir="ltr">`).
- Do not put `direction: rtl` on the whole Streamlit root — it breaks widgets. Apply RTL to text blocks, labels, tabs and the sidebar only.

## 3. Secrets
- `GROQ_API_KEY` lives only in `st.secrets`.
- `.streamlit/secrets.toml` is git-ignored and never committed.

## 4. Tests and pushing
- Run `pytest` before every push. Never push failing tests.
- The app never downloads anything at runtime. Data is refreshed only by `python scripts/update_data.py` (needs Node at update time only).

## 5. Reporting
- At the end of every stage, STOP and write a Hebrew report in `reports/STAGE<N>_REPORT.md` (wrapped in `<div dir="rtl">`) and in the terminal. Do not start the next stage.

## 6. The plan
- **Stage 1:** structure, data, RTL layout, tab 1 ("הקבוצה שלי") working without the LLM, tests.
- **Stage 2:** tabs 2 ("קבוצה מאפס") and 3 ("נגד יריב"), reusing the engine (must-include, style weights, custom candidate pools).
- **Stage 3:** Groq Hebrew strategy plus validation (any move, ability or item it names that isn't in the team data gets regenerated once, then removed), Showdown export, polish, Hebrew README, deploy to Streamlit Community Cloud.

## 7. Layout
- `app.py` — Streamlit entry point
- `engine/` — pure Python, no Streamlit imports (data_loader, types, stats, legality, sets, scoring, search)
- `ui/` — Streamlit/HTML helpers (rtl_css, cards, heatmap, sidebar)
- `scripts/update_data.py` — downloads raw data and builds `data/processed/`
- `tests/` — pytest
