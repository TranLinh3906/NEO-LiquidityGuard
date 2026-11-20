"""Render-only browser QA for the locked Execution Lab layout."""
from pathlib import Path
import json
import os

from playwright.sync_api import sync_playwright


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "outputs/ui/execution_lab_after_1672x941.png"
GEOMETRY = ROOT / "outputs/ui/execution_lab_geometry.json"


def main():
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1672, "height": 941}, device_scale_factor=1)
        errors = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        port = os.environ.get("LIQUIDITYGUARD_TEST_PORT", "8503")
        page.goto(f"http://127.0.0.1:{port}/?view=simulator", wait_until="networkidle", timeout=90_000)
        page.locator(".lg-exec-hero").wait_for(timeout=60_000)
        page.locator(".js-plotly-plot").first.wait_for(timeout=60_000)
        page.screenshot(path=str(OUTPUT), full_page=True)
        selectors = {
            "sidebar": ".st-key-lg_exec_sidebar",
            "topbar": ".st-key-lg_exec_topbar",
            "hero": ".lg-exec-hero",
            "controls": ".st-key-lg_exec_controls",
            "results": ".lg-exec-results",
            "insight": ".lg-exec-insight",
            "chart_row1": ".st-key-lg_chart_exec_depth",
            "chart_row2": ".st-key-lg_chart_exec_spread",
            "formula": "[data-testid='stExpander']",
            "watchlist": ".st-key-lg_exec_watchlist",
            "session": ".st-key-lg_exec_session",
            "trust": ".st-key-lg_exec_trust",
        }
        geometry = {name: page.locator(selector).bounding_box() for name, selector in selectors.items()}
        geometry["computed"] = {
            name: page.locator(selector).evaluate(
                "el => ({background:getComputedStyle(el).background, height:getComputedStyle(el).height, marginTop:getComputedStyle(el).marginTop, opacity:getComputedStyle(el).opacity})"
            ) for name, selector in selectors.items()
        }
        geometry.update(
            viewport=page.viewport_size,
            plot_count=page.locator(".js-plotly-plot").count(),
            horizontal_scroll=page.evaluate("document.documentElement.scrollWidth > document.documentElement.clientWidth"),
            page_errors=errors,
        )
        geometry["chart_depth_nodes"] = page.locator(".st-key-lg_chart_exec_depth").evaluate_all(
            "els => els.map(el => ({tag:el.tagName, cls:el.className, box:el.getBoundingClientRect().toJSON(), boxSizing:getComputedStyle(el).boxSizing, height:getComputedStyle(el).height, padding:getComputedStyle(el).padding}))"
        )
        GEOMETRY.write_text(json.dumps(geometry, ensure_ascii=False, indent=2))
        browser.close()


if __name__ == "__main__":
    main()
