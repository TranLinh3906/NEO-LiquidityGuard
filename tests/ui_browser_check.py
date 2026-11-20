"""Manual browser acceptance: python tests/ui_browser_check.py (Streamlit :8503)."""
from pathlib import Path
import json
from playwright.sync_api import sync_playwright, expect

ROOT=Path(__file__).resolve().parents[1]
OUTPUT=ROOT/"outputs/ui"


def main():
    checks=[]
    with sync_playwright() as p:
        browser=p.chromium.launch(headless=True)
        page=browser.new_page(viewport={"width":1448,"height":1086},device_scale_factor=1)
        page.goto("http://localhost:8503")
        page.locator(".lg-hero").wait_for(timeout=30000)
        page.locator(".js-plotly-plot").first.wait_for()
        assert page.locator(".lg-kpi").count()==6
        assert page.locator(".js-plotly-plot").count()==5
        checks.append("Dashboard: 6 KPI, mascot and 5 Plotly charts")
        page.screenshot(path=str(OUTPUT/"dashboard_desktop.png"))
        page.locator(".st-key-lg_card_watchlist").get_by_role("button",name="☆ VPB",exact=True).click()
        page.locator(".lg-hero-badge").get_by_text("VPB · SYNTHETIC_TEST").wait_for()
        checks.append("Watchlist click synchronizes VPB")
        trade=page.locator(".st-key-lg_trade")
        trade.get_by_role("radio",name="SELL",exact=True).click()
        trade.get_by_role("spinbutton").fill("5000")
        trade.get_by_role("spinbutton").press("Enter")
        page.get_by_text("Không đủ",exact=False).count()
        trade.get_by_role("button",name="Mô phỏng",exact=True).click()
        checks.append("SELL and quantity 5000 trigger recalculation; snapshot locked")
        heading={"Market Pulse":"Market Pulse","Simulator":"Mô phỏng theo từng mức giá","Replay":"Replay · chọn đúng snapshot đã lưu","Charts":"Chart Studio","Alerts":"Alerts & Data Trust","Settings":"Settings · Workspace"}
        for name,label in heading.items():
            page.locator(".st-key-lg_header").get_by_role("button",name=name,exact=True).click()
            page.get_by_role("heading",name=label,exact=True).wait_for(timeout=30000)
            page.locator('[data-testid="stStatusWidget"]').wait_for(state="hidden",timeout=30000)
            page.evaluate('new Promise(r=>requestAnimationFrame(()=>requestAnimationFrame(r)))')
            assert page.locator('[data-testid="stException"]').count()==0
            page.screenshot(path=str(OUTPUT/(name.lower().replace(" ","_")+".png")))
            checks.append(name+": renders and preserves global selection")
        page.locator(".st-key-lg_header").get_by_role("button",name="Dashboard",exact=True).click()
        page.locator(".lg-hero").wait_for()
        page.locator(".st-key-lg_mode").get_by_role("radio",name="LIVE",exact=True).click()
        page.locator(".lg-mode-banner").get_by_text("OFFLINE",exact=False).wait_for()
        expect(page.locator(".st-key-lg_trade").get_by_role("button",name="Mô phỏng",exact=True)).to_be_disabled(timeout=10000)
        assert page.locator(".lg-kpi-value").all_text_contents()[-1]=="Blocked"
        expect(page.locator(".js-plotly-plot")).to_have_count(0,timeout=10000)
        page.screenshot(path=str(OUTPUT/"live_blocked.png"))
        checks.append("LIVE offline/unverified: no financial chart or simulation")
        page.locator(".st-key-lg_mode").get_by_role("radio",name="SYNTHETIC_TEST",exact=True).click()
        page.locator(".lg-hero-badge").get_by_text("VPB · SYNTHETIC_TEST").wait_for()
        page.set_viewport_size({"width":390,"height":844})
        page.locator(".st-key-lg_mobile_nav").wait_for(state="visible")
        assert not page.evaluate("document.documentElement.scrollWidth > innerWidth")
        page.screenshot(path=str(OUTPUT/"dashboard_mobile.png"))
        checks.append("390×844: mobile navigation and no horizontal overflow")
        page.set_viewport_size({"width":1366,"height":768})
        page.locator(".lg-hero").wait_for()
        page.screenshot(path=str(OUTPUT/"dashboard_1366.png"))
        checks.append("1366×768 screenshot")
        browser.close()
    (OUTPUT/"browser_checks.json").write_text(json.dumps({"status":"PASS","checks":checks},ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(checks,ensure_ascii=False,indent=2))


if __name__=="__main__":
    main()
