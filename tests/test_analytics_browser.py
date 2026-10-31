from playwright.sync_api import sync_playwright
from revenue_lab.bundle import ROOT
from revenue_lab.smoke import check_zip
from test_browser import url


def test_analytics_lineage_metrics_benchmarks_native_and_download(url, tmp_path):
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1440, "height": 1100})
        errors, writes = [], []
        page.on("pageerror", lambda e: errors.append(str(e)))
        page.on("request", lambda r: writes.append(r.url) if r.method != "GET" else None)
        page.goto(url + "/?case=analytics-engineering")
        page.get_by_role("heading", name="What is one row supposed to mean?").wait_for()
        assert page.locator("[data-investigation]").count() == 13
        page.get_by_role("button", name="Validate artifact integrity").click()
        page.locator("#status").filter(has_text="Artifact integrity verified").wait_for()
        page.get_by_role("button", name="mart_pipeline", exact=True).click()
        assert page.get_by_label("Choose a dbt model", exact=True).input_value() == "mart_pipeline"
        page.get_by_label("Choose a dbt model", exact=True).select_option("fct_invoice_lines")
        rows = page.get_by_text("Inspect typed model columns and recorded rows", exact=True)
        rows.click()
        assert "line_id" in rows.locator("..").locator("pre").inner_text()
        sql = page.get_by_text("Inspect exact SQL · fct_invoice_lines", exact=True)
        sql.click()
        assert "invoice_lines" in sql.locator("..").locator("pre").inner_text()
        page.locator('[data-analytics-stage="metrics"]').focus(); page.keyboard.press("Enter")
        page.get_by_label("Choose a metric definition and version").select_option(label="Period-end ARR · v2.0")
        assert "2.0" in page.locator("#analytics-detail").inner_text()
        page.locator('[data-analytics-stage="quality"]').click()
        page.get_by_label("Filter recorded regression tests").fill("fanout")
        assert "test_fanout_is_detected_by_dbt" in page.locator("#analytics-detail table").inner_text()
        page.locator('[data-analytics-stage="performance"]').click()
        assert "37,375,442" in page.locator("#analytics-detail").inner_text()
        page.get_by_label("Choose a recorded benchmark scale").select_option("enterprise")
        assert "+54.3%" in page.locator("#analytics-detail").inner_text()
        page.get_by_label("Inspect one measured repetition").select_option("3")
        assert "12.770s" in page.locator("#analytics-detail").inner_text()
        page.locator('[data-analytics-stage="native"]').click()
        assert "461" in page.locator("#analytics-detail").inner_text()
        assert "predates the USD" in page.locator("#analytics-detail").inner_text()
        page.get_by_text("All archived query IDs", exact=True).click()
        assert "01c7bc94" in page.locator("#analytics-detail").inner_text()
        with page.expect_download() as event: page.get_by_role("link", name="Download reproduction ZIP").click()
        target = tmp_path / "analytics.zip"; event.value.save_as(target)
        check_zip(target.read_bytes(), ROOT / "web/evidence/analytics-engineering")
        for tab in ["Source records", "Evidence timeline", "Compare & verify"]:
            page.get_by_role("tab", name=tab, exact=True).click()
            assert page.locator("#panel").inner_text().strip()
        page.reload(); page.get_by_role("heading", name="What is one row supposed to mean?").wait_for()
        assert page.locator("#fresh").is_hidden() and not errors and not writes
        browser.close()


def test_tampered_analytics_verification_is_not_rendered(url):
    with sync_playwright() as p:
        browser = p.chromium.launch(); page = browser.new_page()
        page.route("**/analytics-engineering/verification.json", lambda r: r.fulfill(json={"integrity": "fabricated"}))
        page.goto(url + "/?case=analytics-engineering")
        page.locator("#status").filter(has_text="Verification record integrity mismatch").wait_for()
        assert page.locator(".analytics-investigation").count() == 0
        browser.close()
