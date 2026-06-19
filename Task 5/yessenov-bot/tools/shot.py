"""Screenshot the running Streamlit app for visual QA. Not part of the product."""
import sys
from playwright.sync_api import sync_playwright

URL = "http://localhost:8501"
OUT = sys.argv[1] if len(sys.argv) > 1 else "shot.png"
ASK = sys.argv[2] if len(sys.argv) > 2 else ""
LANG = sys.argv[3] if len(sys.argv) > 3 else ""  # e.g. "English" / "Қазақша"

with sync_playwright() as p:
    b = p.chromium.launch()
    page = b.new_page(viewport={"width": 1100, "height": 1000})
    page.goto(URL, wait_until="networkidle")
    page.wait_for_selector("img[alt='Yessenov Foundation']", timeout=30000)
    page.wait_for_timeout(1500)
    if LANG:
        page.get_by_text(LANG, exact=True).first.click()
        page.wait_for_timeout(2500)
    if ASK:
        box = page.locator('[data-testid="stChatInput"] textarea').first
        box.click()
        box.fill(ASK)
        box.press("Enter")
        # wait for the assistant answer to render (sources expander or spinner gone)
        page.wait_for_timeout(12000)
    page.wait_for_timeout(1000)
    page.screenshot(path=OUT, full_page=True)
    b.close()
print("saved", OUT)
