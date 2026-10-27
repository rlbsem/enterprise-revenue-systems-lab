"""Real browser choices, pinned links, downloads and tamper refusal."""
import hashlib
import json

import pytest
from playwright.sync_api import sync_playwright
from revenue_lab.bundle import ROOT
from revenue_lab.smoke import check_zip
from test_browser import url

CASES = ["estate-assurance", "reliability-operations", "temporal-assurance"]


@pytest.mark.parametrize("case", CASES)
def test_assurance_browser_downloads_navigation_and_read_only(url, tmp_path, case):
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width":1440,"height":1100})
        errors, writes = [], []
        page.on("pageerror", lambda e: errors.append(str(e)))
        page.on("request", lambda r: writes.append(r.url) if r.method != "GET" else None)
        page.goto(url + "/?case=" + case)
        page.locator(".assurance-investigation").wait_for()
        assert page.locator("[data-investigation]").count() == 12
        page.get_by_role("button", name="Validate artifact integrity").click()
        page.locator("#status").filter(has_text="Artifact integrity verified").wait_for()
        # Native buttons remain keyboard-operable; stages are genuine rendered views.
        for button in page.locator("[data-assurance-stage]").all():
            button.focus()
            page.keyboard.press("Enter")
            assert button.get_attribute("aria-pressed") == "true"
            assert page.locator(".assurance-investigation h3").count() >= 1
        pin = json.loads((ROOT/"web/evidence"/case/"bundle.json").read_bytes())["source"]["commit"]
        for a in page.locator(".assurance-investigation a").all():
            assert pin in a.get_attribute("href")
        with page.expect_download() as event:
            page.get_by_role("link", name="Download reproduction ZIP").click()
        archive = tmp_path / "recorded.zip"
        event.value.save_as(archive)
        check_zip(archive.read_bytes(), ROOT/"web/evidence"/case)
        page.get_by_text("Validate a downloaded portable bundle", exact=True).click()
        with page.expect_download() as event:
            page.locator("#portable").click()
        portable_file = tmp_path / "portable.json"
        event.value.save_as(portable_file)
        portable = json.loads(portable_file.read_bytes())
        assert "record.json" in portable["artifacts"] and "projection.json" in portable["artifacts"]
        for tab in ["Source records", "Evidence timeline", "Compare & verify"]:
            page.get_by_role("tab", name=tab, exact=True).click()
            assert page.locator("#panel").inner_text().strip()
        page.set_viewport_size({"width":320,"height":844})
        page.get_by_role("tab", name="Decision & outcome", exact=True).click()
        assert not page.evaluate("document.documentElement.scrollWidth>innerWidth")
        assert page.locator("#fresh").is_hidden()
        assert not errors and not writes
        browser.close()


@pytest.mark.parametrize("case", CASES)
def test_tampered_assurance_refuses_render(url, case):
    with sync_playwright() as p:
        browser=p.chromium.launch()
        page=browser.new_page()
        page.route("**/"+case+"/verification.json", lambda r:r.fulfill(json={"integrity":"fabricated"}))
        page.goto(url+"/?case="+case)
        page.locator("#status").filter(has_text="Verification record integrity mismatch").wait_for()
        assert page.locator(".assurance-investigation").count()==0
        browser.close()


def test_current_capture_is_bound_and_has_no_external_execution():
    report=json.loads((ROOT/"docs/evidence/architecture-assurance/browser.json").read_bytes())
    assert len(report["layouts"])==111 and len(report["accessibility"])==30
    assert not report["http_writes"] and not report["nonlocal_requests"] and not report["page_errors"]
    assert all(not x["overflow"] and not x["contrast"]["failures"] for x in report["layouts"])
    assert all(not x["violations"] for x in report["accessibility"])
    assert all(not x["incomplete"] for x in report["accessibility"])
    assert not any(report[k] for k in ["new_source_engine_execution","new_model_execution","new_vendor_execution"])
    for path, checksum in report["source_sha256"].items():
        assert hashlib.sha256((ROOT/path).read_bytes()).hexdigest()==checksum, path
    assert len(report["images"])==9
    for path, checksum in report["image_sha256"].items():
        assert hashlib.sha256((ROOT/"docs/images/architecture-assurance"/path).read_bytes()).hexdigest()==checksum
