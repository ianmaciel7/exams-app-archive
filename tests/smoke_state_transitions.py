"""Run original assessment demo in an actual Chromium browser."""
from pathlib import Path
from playwright.sync_api import sync_playwright, expect
ROOT = Path(__file__).resolve().parents[1]
DEMO = ROOT / "docs/references/ui-ux-research-sources/state-transition-example-2026-11-26.html"

def check():
    with sync_playwright() as p:
        browser = p.chromium.launch()
        for reduced in ("no-preference", "reduce"):
            page = browser.new_page(viewport={"width":390,"height":844}, reduced_motion=reduced)
            errors = []
            page.on("pageerror", lambda error: errors.append(str(error)))
            page.goto(DEMO.as_uri())
            status = page.get_by_role("status")
            send = page.locator("#send")
            cancel = page.locator("#cancel")
            expect(send).to_be_disabled()
            page.get_by_role("radio", name="2", exact=True).check()
            expect(send).to_be_enabled()
            send.click()
            expect(cancel).to_be_focused()
            cancel.click()
            expect(status).to_contain_text("cancelled")
            page.wait_for_timeout(600)
            expect(status).to_contain_text("cancelled")
            expect(send).to_be_focused()
            page.locator("#fail").check()
            send.click()
            expect(status).to_contain_text("failed")
            expect(send).to_be_enabled()
            send.click()
            expect(status).to_contain_text("Correct:")
            page.locator("#reset").click()
            page.get_by_role("radio", name="3", exact=True).check()
            send.click()
            expect(status).to_contain_text("Incorrect:")
            page.locator("#reset").click()
            page.get_by_role("radio", name="2", exact=True).check()
            send.click()
            page.locator("#reset").click()
            page.wait_for_timeout(600)
            expect(status).to_have_text("Choose an answer.")
            assert not errors, errors
            page.close()
        browser.close()
    print("Assessment browser smoke: selection, cancel, retry, correct/incorrect, stale response and reduced motion passed")

if __name__ == "__main__":
    check()
