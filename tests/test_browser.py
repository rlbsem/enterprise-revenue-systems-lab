import functools
import json
import os
import shutil
import threading
import zipfile
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest
from playwright.sync_api import sync_playwright
from revenue_lab.bundle import ROOT
from revenue_lab.site import build


class Quiet(SimpleHTTPRequestHandler):
    def log_message(self, *_):
        pass


@pytest.fixture(scope="module")
def url():
    server = ThreadingHTTPServer(
        ("127.0.0.1", 0), functools.partial(Quiet, directory=str(ROOT / "web"))
    )
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{server.server_port}"
    server.shutdown()
    server.server_close()
    thread.join()


def test_browser_evidence_integrity_review_download_and_mobile(url, tmp_path):
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1440, "height": 1000})
        errors = []
        page.on("pageerror", lambda e: errors.append(str(e)))
        page.goto(url)
        page.get_by_role(
            "heading", name="Can this AI seller action be trusted?"
        ).wait_for()
        page.get_by_role("button", name="Validate artifact integrity").click()
        page.get_by_role("status").filter(
            has_text="Artifact integrity verified"
        ).wait_for()
        page.get_by_label("CHOOSE AN EVIDENCE CASE").select_option(
            "seller-support-review"
        )
        page.get_by_text(
            "Review finding · unsupported availability", exact=True
        ).wait_for()
        page.get_by_role("tab", name="Compare & verify").click()
        page.get_by_role("heading", name="Template baseline").wait_for()
        page.get_by_role("tab", name="Source records").click()
        assert page.get_by_text(
            "Customer inquiry and call evidence", exact=True
        ).is_visible()
        with page.expect_download() as event:
            page.get_by_role("link", name="Download reproduction ZIP").click()
        event.value.save_as(tmp_path / "bundle.zip")
        assert (tmp_path / "bundle.zip").stat().st_size > 1000
        page.get_by_role("tab", name="Decision & outcome").click()
        image_dir = Path(
            os.environ.get("LAB_SCREENSHOT_DIR", str(ROOT / "docs/images"))
        )
        screenshot = image_dir / "seller-investigation.png"
        screenshot.parent.mkdir(parents=True, exist_ok=True)
        page.screenshot(path=str(screenshot), full_page=True)
        page.set_viewport_size({"width": 390, "height": 844})
        assert page.evaluate(
            "document.documentElement.scrollWidth <= window.innerWidth"
        )
        page.get_by_role("button", name="Validate artifact integrity").click()
        page.get_by_role("status").filter(
            has_text="Artifact integrity verified"
        ).wait_for()
        page.screenshot(path=str(image_dir / "seller-mobile.png"), full_page=True)
        page.keyboard.press("Tab")
        assert page.evaluate("document.activeElement.tagName") != "BODY"
        assert errors == []
        browser.close()


def test_all_scenarios_and_three_investigations(url):
    catalog = json.loads((ROOT / "web/catalog.json").read_text())
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1440, "height": 1000})
        errors = []
        page.on("pageerror", lambda e: errors.append(str(e)))
        for case in catalog["scenarios"]:
            page.goto(url + "/?case=" + case["id"])
            page.get_by_role("heading", name=case["title"], exact=True).wait_for()
            page.get_by_role("button", name="Validate artifact integrity").click()
            page.get_by_role("status").filter(
                has_text="Artifact integrity verified"
            ).wait_for()
            for tab in [
                "Source records",
                "Evidence timeline",
                "Compare & verify",
                "Decision & outcome",
            ]:
                page.get_by_role("tab", name=tab, exact=True).click()
                assert page.locator("#panel").inner_text().strip()
            assert page.get_by_text("RECORDED EVIDENCE", exact=True).is_visible()
            if case["id"] in (
                "control-recovery",
                "revenue-correction",
                "seller-application",
            ):
                image_dir = Path(
                    os.environ.get("LAB_SCREENSHOT_DIR", str(ROOT / "docs/images"))
                )
                image_dir.mkdir(parents=True, exist_ok=True)
                page.screenshot(
                    path=str(image_dir / (case["investigation"] + "-overview.png")),
                    full_page=True,
                )
        assert errors == []
        browser.close()


def test_browser_import_refuses_altered_artifacts(url, tmp_path):
    portable = json.loads(
        (ROOT / "web/evidence/seller-application/portable.json").read_text()
    )
    portable["artifacts"]["application.json"] += " "
    imported = tmp_path / "tampered.json"
    imported.write_text(json.dumps(portable))
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(url)
        page.get_by_role("heading", name="Reviewed discovery action").wait_for()
        page.get_by_text("Validate a downloaded portable bundle", exact=True).click()
        page.get_by_label("Portable evidence JSON").set_input_files(imported)
        page.get_by_role("status").filter(has_text="Verification refused").wait_for()
        assert "Artifact integrity mismatch" in page.get_by_role("status").inner_text()
        browser.close()


def test_keyboard_tabs_and_latest_navigation_preserve_evidence_identity(url):
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(url)
        page.get_by_role("heading", name="Reviewed discovery action").wait_for()
        page.get_by_role("tab", name="Decision & outcome").focus()
        page.keyboard.press("ArrowRight")
        assert (
            page.get_by_role("tab", name="Source records").get_attribute(
                "aria-selected"
            )
            == "true"
        )
        page.keyboard.press("End")
        assert (
            page.get_by_role("tab", name="Compare & verify").get_attribute(
                "aria-selected"
            )
            == "true"
        )
        page.keyboard.press("Home")
        assert (
            page.get_by_role("tab", name="Decision & outcome").get_attribute(
                "aria-selected"
            )
            == "true"
        )
        page.get_by_role("button", name="03 Reconcile the numbers").click()
        page.get_by_role("heading", name="Installed ARR and quarterly flows").wait_for()
        assert "revenue-metrics-platform" in page.locator("#source-link").inner_text()
        page.get_by_role("button", name="01 Trust the seller action").click()
        page.get_by_role("heading", name="Reviewed discovery action").wait_for()
        assert "customer-signal-activation" in page.locator("#source-link").inner_text()
        browser.close()


def test_displayed_verification_record_cannot_be_silently_replaced(url):
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.route(
            "**/seller-application/verification.json",
            lambda route: route.fulfill(
                status=200,
                content_type="application/json",
                body='{"integrity":"invented success"}',
            ),
        )
        page.goto(url)
        page.get_by_role("status").filter(
            has_text="Verification record integrity mismatch"
        ).wait_for()
        browser.close()


def test_revenue_ui_uses_neutral_dollar_display(url):
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(url + "/?case=revenue-correction")
        page.get_by_role(
            "heading", name="Late correction and equivalent rebuild"
        ).wait_for()
        page.get_by_role("status").filter(
            has_text="Recorded evidence loaded"
        ).wait_for()
        metrics = page.locator("#metrics").inner_text()
        assert "$754.39M" in metrics
        assert "CAD" not in metrics
        panel = page.locator("#panel").inner_text()
        assert "$754,389,953.40" in panel
        assert "CAD" not in panel
        browser.close()


def test_selected_account_bridge_uses_original_model_and_source_rows(url):
    source = json.loads(
        (ROOT / "web/evidence/revenue-correction/models.json").read_text()
    )["full"]["bridge"]
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(url + "/?case=revenue-correction")
        choice = page.get_by_label("Selected revenue account")
        choice.wait_for()
        choice.select_option(source[1]["account_id"])
        panel = page.locator("#account-bridge")
        assert f"${source[1]['bookings']:,.2f}" in panel.inner_text()
        panel.get_by_text(
            "Inspect this account's original source rows", exact=True
        ).click()
        assert source[1]["account_id"] in panel.locator("pre").inner_text()
        assert source[0]["account_id"] not in panel.locator("pre").inner_text()
        browser.close()


def test_static_pages_subpath_has_attribution_and_no_execution_api(
    tmp_path, monkeypatch
):
    # ZIP container metadata differs across operating systems. Build in isolation
    # so the test cannot rewrite the checked-in recorded artifact bytes.
    workspace = tmp_path / "build"
    shutil.copytree(ROOT / "web", workspace / "web")
    monkeypatch.setattr("revenue_lab.site.ROOT", workspace)
    build()
    # Serve only the deployment artifact under the same repository prefix as Pages.
    directory = tmp_path / "enterprise-revenue-systems-lab"
    shutil.copytree(workspace / "dist", directory)
    expected = {
        p.relative_to(ROOT / "web") for p in (ROOT / "web").rglob("*") if p.is_file()
    }
    actual = {p.relative_to(directory) for p in directory.rglob("*") if p.is_file()}
    # The connected native evidence download is built deterministically from its
    # pinned source bundle. It is generated at build time, not tracked as binary.
    generated = Path("evidence/connected-roundtrip/reproduction.zip")
    assert actual == expected | {generated}
    with zipfile.ZipFile(directory / generated) as packaged:
        assert packaged.testzip() is None
        assert packaged.read("bundle.json") == (
            directory / "evidence/connected-roundtrip/bundle.json"
        ).read_bytes()
        assert "REPRODUCE.txt" in packaged.namelist()
    assert not any(p.is_symlink() for p in directory.rglob("*"))
    server = ThreadingHTTPServer(
        ("127.0.0.1", 0), functools.partial(Quiet, directory=str(tmp_path))
    )
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base = f"http://127.0.0.1:{server.server_port}/enterprise-revenue-systems-lab/"
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page(viewport={"width": 1440, "height": 1000})
            errors = []
            page.on("pageerror", lambda error: errors.append(str(error)))
            catalog = json.loads((directory / "catalog.json").read_text())
            for case in catalog["scenarios"]:
                page.goto(base + "?case=" + case["id"])
                page.get_by_role("heading", name=case["title"], exact=True).wait_for()
                page.get_by_role("button", name="Validate artifact integrity").click()
                page.get_by_role("status").filter(
                    has_text="Artifact integrity verified"
                ).wait_for()
                author = page.get_by_role(
                    "link", name="Built by Richard Butts", exact=True
                )
                assert author.is_visible()
                assert author.get_attribute("href") == "https://github.com/rlbsem"
                expected_label = (
                    "Verify this native record offline"
                    if case["investigation"] == "connected"
                    else "Reproduce this investigation · fresh local execution"
                )
                page.get_by_text(expected_label, exact=True).click()
                assert page.locator("#fresh").is_hidden()
            assert page.request.get(base + "api/config").status == 404
            assert (
                page.request.post(
                    base + "api/runs", data={"scenario": "seller-live"}
                ).status
                == 501
            )
            with page.expect_download() as event:
                page.get_by_role("link", name="Download reproduction ZIP").click()
            event.value.save_as(tmp_path / "static-bundle.zip")
            assert (tmp_path / "static-bundle.zip").stat().st_size > 1000
            page.set_viewport_size({"width": 390, "height": 844})
            assert author.is_visible()
            assert page.evaluate(
                "document.documentElement.scrollWidth <= window.innerWidth"
            )
            assert errors == []
            browser.close()
    finally:
        server.shutdown()
        server.server_close()
        thread.join()


def test_connected_vendor_investigation_navigation_and_integrity(url):
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1280, "height": 880})
        outside = []
        page.on("request", lambda r: outside.append(r.url) if any(
            host in r.url for host in ("salesforce.com", "snowflakecomputing.com")
        ) else None)
        page.goto(url)
        page.get_by_role("button", name="Connect CRM and warehouse").click()
        page.get_by_role("heading", name="Salesforce and Snowflake round trip").wait_for()
        page.get_by_text("Recovery with one real CRM effect").wait_for()
        page.get_by_text("clarify_need", exact=True).first.wait_for()
        page.get_by_text("hold", exact=True).first.wait_for()
        page.get_by_role("button", name="Validate artifact integrity").click()
        page.get_by_role("status").filter(has_text="Artifact integrity verified").wait_for()
        for tab in ("Source records", "Evidence timeline", "Compare & verify"):
            page.get_by_role("tab", name=tab).click()
            assert page.locator("#panel").inner_text().strip()
        page.get_by_role("tab", name="Evidence timeline").click()
        page.get_by_text("Read-only cleanup confirmation").wait_for()
        assert not outside
        assert page.locator("#fresh").is_hidden()
        browser.close()
