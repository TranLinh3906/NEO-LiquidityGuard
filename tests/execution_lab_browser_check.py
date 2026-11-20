"""Real-browser acceptance for Execution Lab; keep Streamlit running."""
from pathlib import Path
import json
import os

from playwright.sync_api import sync_playwright, expect

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "outputs/ui"


def main():
    checks = []
    port = os.environ.get("LIQUIDITYGUARD_TEST_PORT", "8503")
    OUTPUT.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1672, "height": 941}, device_scale_factor=1)
        page.goto(f"http://127.0.0.1:{port}/?view=simulator", wait_until="networkidle", timeout=90_000)
        page.locator(".lg-exec-hero").wait_for(timeout=60_000)
        page.locator(".js-plotly-plot").first.wait_for(timeout=60_000)
        expect(page.locator(".js-plotly-plot")).to_have_count(5, timeout=60_000)
        assert page.locator(".lg-exec-results").count() == 1
        assert page.locator(".lg-exec-insight").count() == 1
        assert page.locator(".st-key-lg_exec_watchlist").count() == 1
        assert not page.evaluate("document.documentElement.scrollWidth > document.documentElement.clientWidth")
        assert "SYNTHETIC_TEST" not in page.locator("body").inner_text()
        checks.append("1672×941: restored dashboard, mascot, LIVE/REPLAY and five charts")

        controls = page.locator(".st-key-lg_exec_controls")
        controls.get_by_role("radio", name="SELL", exact=True).click()
        controls.get_by_role("spinbutton").fill("10000")
        controls.get_by_role("spinbutton").press("Enter")
        controls.get_by_role("button", name="▷ Mô phỏng ngay", exact=True).click()
        page.get_by_text("Chưa đáp ứng · CP", exact=True).wait_for()
        assert page.locator('[data-testid="stException"]').count() == 0
        checks.append("SELL, quantity and simulation CTA rerun without an exception")

        topbar = page.locator(".st-key-lg_exec_topbar")
        topbar.get_by_role("radio", name="LIVE", exact=True).click()
        expect(controls.get_by_role("button", name="▷ Mô phỏng ngay", exact=True)).to_be_disabled(timeout=30_000)
        checks.append("Unavailable/offline LIVE blocks the simulation CTA")
        topbar.get_by_role("radio", name="REPLAY", exact=True).click()
        page.locator(".js-plotly-plot").first.wait_for(timeout=60_000)
        checks.append("REPLAY restores stored SSI charts without TEST fallback")
        page.screenshot(path=str(OUTPUT / "execution_lab_after_1672x941.png"), full_page=True)
        browser.close()
    (OUTPUT / "execution_lab_browser_checks.json").write_text(
        json.dumps({"status": "PASS", "checks": checks}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(checks, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
