from pathlib import Path

from streamlit.testing.v1 import AppTest

APP = str(Path(__file__).resolve().parent.parent / "app.py")


def test_tab1_demo_builds_six_cards():
    at = AppTest.from_file(APP, default_timeout=30)
    at.run()
    assert not at.exception
    at.button(key="demo").click().run()
    assert not at.exception
    assert len(at.multiselect(key="my_pokemon").value) >= 6
    at.button(key="build").click().run()
    assert not at.exception
    html = "".join(m.value for m in at.markdown)
    assert html.count('class="poke-card"') == 6
    assert 'class="hm"' in html
    assert [t.label for t in at.tabs] == ["הקבוצה שלי", "קבוצה מאפס", "נגד יריב"]
