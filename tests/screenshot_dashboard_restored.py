"""Browser evidence for the restored seven-page dashboard."""
from pathlib import Path
import json
import os

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "outputs/ui/dashboard_restored_live_replay.png"
REPORT = ROOT / "outputs/ui/dashboard_restored_checks.json"


def main():
    port = os.environ.get("LIQUIDITYGUARD_TEST_PORT", "8503")
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1672, "height": 941}, device_scale_factor=1)
        page.goto(f"http://127.0.0.1:{port}/", wait_until="networkidle", timeout=90_000)
        page.locator(".lg-hero").wait_for(timeout=60_000)
        # Plotly is hydrated after Streamlit has rendered the surrounding
        # cards.  Wait for a real chart instead of capturing empty shells.
        page.locator(".js-plotly-plot").first.wait_for(timeout=60_000)
        page.wait_for_timeout(2_000)
        body = page.locator("body").inner_text()
        report = {
            "page": "Dashboard",
            "mode": "REPLAY",
            "navigation_buttons": page.locator(".st-key-lg_header button").count(),
            "mascot_visible": page.locator(".lg-mascot").count() == 1,
            "synthetic_option_visible": "SYNTHETIC_TEST" in body,
            "streamlit_exceptions": page.locator('[data-testid="stException"]').all_inner_texts(),
            "plotly_charts": page.locator(".js-plotly-plot").count(),
            "horizontal_scroll": page.evaluate("document.documentElement.scrollWidth > innerWidth"),
        }
        assert report["navigation_buttons"] == 7
        assert report["mascot_visible"]
        assert not report["synthetic_option_visible"]
        assert not report["streamlit_exceptions"]
        assert report["plotly_charts"] >= 3
        assert not report["horizontal_scroll"]
        page.screenshot(path=str(OUTPUT), full_page=True)
        REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
        browser.close()


if __name__ == "__main__":
    main()
