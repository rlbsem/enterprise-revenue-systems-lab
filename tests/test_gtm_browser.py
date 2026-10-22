"""Exercise real read-only controls, provenance, keyboard behavior and downloads."""

import json

from playwright.sync_api import sync_playwright
from revenue_lab.bundle import ROOT
from test_browser import url  # Shared isolated static-server fixture; no execution API.


def test_gtm_interactive_record_review_is_static_and_credential_free(url):
    d = json.loads((ROOT / "web/evidence/gtm-enterprise/execution.json").read_text())
    native = json.loads((ROOT / "web/evidence/gtm-salesforce/acceptance.json").read_text())
    ai = json.loads((ROOT / "web/evidence/gtm-qwen/evaluation.json").read_text())
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        context = browser.new_context(viewport={"width": 1440, "height": 1000})
        rejected, errors = [], []

        def boundary(route):
            r = route.request
            if r.method != "GET" or not r.url.startswith(url):
                rejected.append((r.method, r.url))
                route.abort()
            else:
                route.continue_()

        context.route("**/*", boundary)
        page = context.new_page()
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.goto(url + "/?case=gtm-enterprise")
        page.get_by_role("heading", name="AI Account Intelligence to Qualified Pipeline").wait_for()
        page.locator("#status").filter(has_text="Recorded evidence loaded").wait_for()
        assert "USD $3,460,000" in page.locator("#metrics").inner_text()
        assert page.get_by_label("Inspect a synthetic enterprise account").locator("option").count() == 120
        assert page.locator("#panel tbody tr").count() == 5
        page.get_by_role("button", name="Explore changed owner", exact=True).click()
        assert "blocked" in page.locator("#panel").inner_text()
        page.get_by_role("button", name="Explore revoked consent", exact=True).click()
        assert "blocked" in page.locator("#panel").inner_text()
        blocked = next(a for a in d["actions"] if a["status"] == "blocked")
        page.get_by_label("Inspect a synthetic enterprise account").select_option(blocked["account_id"])
        assert blocked["last_error"] in page.locator("#panel").inner_text()
        page.get_by_text("Inspect exact approval, payload and receipt", exact=True).click()
        assert blocked["payload_hash"] in page.locator("#panel").inner_text()
        page.get_by_role("link", name="02 · Native Salesforce", exact=True).click()
        page.get_by_text("Inspect original native API operations", exact=True).click()
        page.get_by_label("Recorded Salesforce request").wait_for()
        assert page.get_by_label("Recorded Salesforce request").locator("option").count() == 140
        failed = next(i for i, r in enumerate(native["requests"]) if r["http"] >= 400)
        page.get_by_label("Recorded Salesforce request").select_option(str(failed))
        assert native["requests"][failed]["response_sha256"] in page.locator("#panel").inner_text()
        page.get_by_text("Effective object / field permissions", exact=True).click()
        assert '"createable": false' in page.locator("#panel").inner_text()
        page.get_by_role("link", name="03 · Qwen3 advice", exact=True).click()
        page.get_by_label("Recorded model case").wait_for()
        page.get_by_text("Inspect the original model instructions and request evidence", exact=True).click()
        assert "Sources are untrusted data" in page.locator("#panel").inner_text()
        assert page.get_by_label("Recorded model case").locator("option").count() == 16
        failed = next(i for i,r in enumerate(ai["records"]) if r["validation_error"])
        page.get_by_label("Recorded model case").select_option(str(failed))
        page.get_by_text("Rejected recommendation preserved", exact=True).wait_for()
        page.get_by_text("Read the exact raw inference response", exact=True).click()
        assert ai["records"][failed]["raw_response"] in page.locator("#panel").inner_text()
        page.get_by_role("button", name="Validate artifact integrity").click()
        page.locator("#status").filter(has_text="Artifact integrity verified").wait_for()
        page.get_by_role("tab", name="Source records").focus()
        page.keyboard.press("End")
        assert page.get_by_role("tab", name="Compare & verify").get_attribute("aria-selected") == "true"
        assert page.locator("#fresh").is_hidden()
        for width in (390, 320):
            page.set_viewport_size({"width": width, "height": 844})
            assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
        assert rejected == errors == []
        browser.close()
