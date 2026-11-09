"""Screenshot tab 1 with the demo team (needs a running app: streamlit run app.py)."""
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

URL = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8501"
OUT = Path(__file__).resolve().parent.parent / "reports" / "screenshots"
OUT.mkdir(parents=True, exist_ok=True)

with sync_playwright() as p:
    browser = p.chromium.launch()
    for width, height, name in ((390, 844, "mobile_390"), (1280, 900, "desktop_1280")):
        page = browser.new_page(viewport={"width": width, "height": height}, device_scale_factor=2 if width < 500 else 1)
        page.goto(URL)
        page.get_by_role("button", name="טען דוגמה").click()
        page.wait_for_timeout(1500)
        page.get_by_role("button", name="בנה קבוצה").click()
        page.wait_for_selector(".poke-card", timeout=30000)
        page.wait_for_timeout(3000)  # let sprites load
        overflow = page.evaluate("document.documentElement.scrollWidth - document.documentElement.clientWidth")
        print(name, "horizontal page overflow px:", overflow, "cards:", page.locator(".poke-card").count())
        # Streamlit scrolls inside its own container, so grow the viewport to the content height
        full = page.evaluate("""() => { const m = document.querySelector('[data-testid="stMain"]') ||
            document.querySelector('section.main'); return m ? m.scrollHeight : document.body.scrollHeight; }""")
        page.set_viewport_size({"width": width, "height": int(full) + 40})
        page.wait_for_timeout(1500)
        page.screenshot(path=str(OUT / f"tab1_{name}.png"), full_page=True)
        page.close()
    # sidebar on mobile
    page = browser.new_page(viewport={"width": 390, "height": 844}, device_scale_factor=2)
    page.goto(URL)
    page.wait_for_selector("text=Cobblemon Team AI")
    page.locator('[data-testid="stExpandSidebarButton"], [data-testid="stSidebarCollapsedControl"] button').first.click()
    page.wait_for_timeout(1500)
    page.screenshot(path=str(OUT / "sidebar_mobile_390.png"))
    page.close()
    browser.close()
