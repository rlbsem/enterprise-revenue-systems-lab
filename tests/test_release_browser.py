"""Recorded states, genuine downloads, keyboard interaction and refusal on corruption."""
import json

from playwright.sync_api import sync_playwright

from revenue_lab.bundle import ROOT
from revenue_lab.smoke import check_zip
from test_browser import url


def test_recorded_release_progression_is_inspectable_and_read_only(url,tmp_path):
    with sync_playwright() as p:
        browser=p.chromium.launch();page=browser.new_page(viewport={"width":1440,"height":1050})
        errors,writes=[],[]
        page.on("pageerror",lambda e:errors.append(str(e)))
        page.on("request",lambda r:writes.append(r.url) if r.method!="GET" else None)
        page.goto(url+"/?case=release-assurance")
        page.get_by_role("heading",name="A passing model needs a controlled release.").wait_for()
        page.get_by_role("button",name="Validate artifact integrity").click()
        page.locator("#status").filter(has_text="Artifact integrity verified").wait_for()
        assert page.locator("[data-investigation]").count()==13
        for stage in ["original","blocked","eligible","shadow","canary","promoted","rollback"]:
            button=page.locator(f'[data-stage="{stage}"]');button.focus();page.keyboard.press("Enter")
            assert button.get_attribute("aria-pressed")=="true"
            assert page.locator("#release-detail").inner_text()
        assert "ungrounded_claim" in page.locator("#release-detail").inner_text()
        assert "qwen3-14b-reasoning1024-reference" in page.locator("#release-detail").inner_text()
        page.locator('[data-stage="blocked"]').click()
        assert "injected-source-priority-0" in page.locator("tbody").inner_text()
        page.get_by_text("Inspect the actual length-limited response and partial effects",exact=True).click()
        assert '"finish_reason": "length"' in page.locator("#release-detail pre").inner_text()
        page.locator('[data-stage="eligible"]').click()
        assert page.locator("tbody tr").count()==48
        page.get_by_label("Show unsuccessful tasks only").check()
        assert "No unsuccessful tasks" in page.locator("#release-detail").inner_text()
        page.locator('[data-stage="promoted"]').click()
        life=json.loads((ROOT/"web/evidence/release-assurance/lifecycle.json").read_text())
        assert life["independent_effects"][0]["hash"] in page.locator("#release-receipt").inner_text()
        with page.expect_download() as e:page.get_by_role("link",name="Download reproduction ZIP").click()
        target=tmp_path/"release.zip";e.value.save_as(target)
        check_zip(target.read_bytes(),ROOT/"web/evidence/release-assurance")
        page.reload();page.get_by_role("heading",name="A passing model needs a controlled release.").wait_for()
        assert page.locator("#fresh").is_hidden()
        assert not errors and not writes
        browser.close()


def test_release_corrupted_verification_does_not_render_success(url):
    with sync_playwright() as p:
        browser=p.chromium.launch();page=browser.new_page()
        page.route("**/release-assurance/verification.json",lambda r:r.fulfill(json={"integrity":"fabricated"}))
        page.goto(url+"/?case=release-assurance")
        page.locator("#status").filter(has_text="Verification record integrity mismatch").wait_for()
        assert page.locator(".release-investigation").count()==0
        browser.close()
