from playwright.sync_api import sync_playwright
from revenue_lab.bundle import ROOT
from revenue_lab.smoke import check_zip
from test_browser import url

def test_recorded_financial_journey_and_static_boundary(url,tmp_path):
    with sync_playwright() as p:
        browser=p.chromium.launch();page=browser.new_page(viewport={"width":1440,"height":1100})
        errors,writes=[],[]
        page.on("pageerror",lambda e:errors.append(str(e)))
        page.on("request",lambda r:writes.append(r.url) if r.method!="GET" else None)
        page.goto(url+"/?case=revenue-integrity")
        page.get_by_role("heading",name="Which number should Finance trust?").wait_for()
        page.get_by_role("button",name="Validate artifact integrity").click()
        page.locator("#status").filter(has_text="Artifact integrity verified").wait_for()
        assert page.locator("[data-investigation]").count()==9
        for stage in ["lineage","delivery","recovery","architecture","discrepancy"]:
            button=page.locator(f'[data-integrity-stage="{stage}"]');button.focus();page.keyboard.press("Enter")
            assert button.get_attribute("aria-pressed")=="true"
            assert page.locator("#integrity-detail").inner_text()
        page.locator('[data-integrity-stage="lineage"]').click()
        page.get_by_label("Choose a recorded invoice").select_option(label="EU · canonical-2 · $9,500.00")
        assert '800-synthetic-2' in page.locator(".integrity-chain").inner_text()
        page.locator('[data-integrity-stage="recovery"]').click()
        assert "$45,600.00" in page.locator("#integrity-detail").inner_text()
        assert "$1,500.00" in page.locator("#integrity-detail").inner_text()
        assert "not complete recovery proposal" in page.locator("#integrity-detail").inner_text()
        assert page.get_by_role("button",name="Approve",exact=True).count()==0
        page.get_by_role("tab",name="Evidence timeline",exact=True).click()
        page.get_by_role("button",name="Inspect this event →").first.click()
        assert 'Separate foundation delivery run' in page.locator("#panel pre").inner_text()
        with page.expect_download() as e:page.get_by_role("link",name="Download reproduction ZIP").click()
        target=tmp_path/"integrity.zip";e.value.save_as(target);check_zip(target.read_bytes(),ROOT/"web/evidence/revenue-integrity")
        page.reload();page.get_by_role("heading",name="Which number should Finance trust?").wait_for()
        assert page.locator("#fresh").is_hidden() and not errors and not writes
        browser.close()

def test_integrity_corrupt_verification_fails_before_display(url):
    with sync_playwright() as p:
        browser=p.chromium.launch();page=browser.new_page()
        page.route("**/revenue-integrity/verification.json",lambda r:r.fulfill(json={"integrity":"fabricated"}))
        page.goto(url+"/?case=revenue-integrity")
        page.locator("#status").filter(has_text="Verification record integrity mismatch").wait_for()
        assert page.locator(".integrity-investigation").count()==0
        browser.close()
