"""Actual static browser navigation and hostile/broken evidence behavior."""
import json

from playwright.sync_api import sync_playwright
from revenue_lab.bundle import ROOT
from test_browser import url  # shared static HTTP fixture


def test_sdr_research_interactions_are_recorded_and_read_only(url, tmp_path):
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width":1440,"height":1000})
        errors, writes = [], []
        page.on("pageerror", lambda e: errors.append(str(e)))
        page.on("request", lambda r: writes.append(r.url) if r.method != "GET" else None)
        page.goto(url + "/?case=gtm-research")
        page.get_by_role("heading", name="Give the seller a reason to investigate.").wait_for()
        assert page.get_by_role("button", name="Northline Systems", exact=False).get_attribute("aria-pressed") == "true"
        page.get_by_role("button", name="Validate artifact integrity").click()
        page.locator("#status").filter(has_text="Artifact integrity verified").wait_for()
        assert page.get_by_label("Research context").locator("option").count() == 10
        assert page.get_by_label("Recorded evaluation approach").locator("option").count() == 4
        for option in page.get_by_label("Research context").locator("option").evaluate_all("o=>o.map(x=>x.value)"):
            page.get_by_label("Research context").select_option(option)
            for index in range(4):
                page.get_by_label("Recorded evaluation approach").select_option(str(index))
                assert page.locator(".research-selection").inner_text()
        page.get_by_label("Research context").select_option("champion-change")
        page.get_by_label("Recorded evaluation approach").select_option("0")
        page.get_by_text("Rejected recommendation preserved", exact=True).wait_for()
        page.get_by_label("Research context").select_option("stale-hiring")
        page.get_by_label("Recorded evaluation approach").select_option("3")
        assert "Model abstained" in page.locator(".research-selection").inner_text()
        # Keyboard native select and queue buttons remain operable.
        page.get_by_label("Research context").focus()
        page.keyboard.press("Home")
        page.keyboard.press("Enter")
        page.get_by_role("button", name="Meridian Cloud", exact=False).focus()
        page.keyboard.press("Enter")
        assert page.get_by_label("Research context").input_value() == "duplicate-alerts"
        op=json.loads((ROOT / "web/evidence/gtm-research/operator-proof.json").read_text(encoding="utf-8"))
        assert op["review"]["opening"] in page.locator("#research-saved-review").inner_text()
        assert page.locator("textarea,[contenteditable=true]").count() == 0
        page.get_by_role("link", name="Inspect native Salesforce Task proof →").click()
        page.get_by_text("Inspect original native API operations", exact=True).click()
        page.get_by_label("Recorded Salesforce request").wait_for()
        page.get_by_role("link", name="SDR account intelligence", exact=True).click()
        page.get_by_label("Research context").wait_for()
        with page.expect_download() as event:
            page.get_by_role("link", name="Download reproduction ZIP").click()
        event.value.save_as(tmp_path / "research.zip")
        assert (tmp_path / "research.zip").stat().st_size > 10000
        page.get_by_role("tab", name="Source records").focus()
        page.keyboard.press("End")
        assert page.get_by_role("tab", name="Compare & verify").get_attribute("aria-selected") == "true"
        assert page.locator("#fresh").is_hidden()
        assert not errors and not writes
        browser.close()


def test_research_fails_closed_on_corrupted_verification(url):
    with sync_playwright() as p:
        browser=p.chromium.launch()
        page=browser.new_page()
        page.route("**/gtm-research/verification.json", lambda r:r.fulfill(json={"fabricated":"success"}))
        page.goto(url + "/?case=gtm-research")
        page.locator("#status").filter(has_text="Verification record integrity mismatch").wait_for()
        assert page.locator(".research-case").count() == 0
        browser.close()
