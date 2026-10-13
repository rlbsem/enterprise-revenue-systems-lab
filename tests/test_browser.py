import functools
import json
import os
import threading
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest
from playwright.sync_api import sync_playwright
from revenue_lab.bundle import ROOT


class Quiet(SimpleHTTPRequestHandler):
    def log_message(self, *_):
        pass


@pytest.fixture(scope="module")
def url():
    server = ThreadingHTTPServer(("127.0.0.1", 0), functools.partial(Quiet, directory=str(ROOT / "web")))
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{server.server_port}"
    server.shutdown(); server.server_close(); thread.join()


def test_browser_evidence_integrity_review_download_and_mobile(url, tmp_path):
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1440, "height": 1000})
        errors = []
        page.on("pageerror", lambda e: errors.append(str(e)))
        page.goto(url)
        page.get_by_role("heading", name="Can this AI seller action be trusted?").wait_for()
        page.get_by_role("button", name="Validate artifact integrity").click()
        page.get_by_role("status").filter(has_text="Artifact integrity verified").wait_for()
        page.get_by_label("CHOOSE AN EVIDENCE CASE").select_option("seller-support-review")
        page.get_by_text("Review finding · unsupported availability", exact=True).wait_for()
        page.get_by_role("tab", name="Compare & verify").click()
        page.get_by_role("heading", name="Template baseline").wait_for()
        page.get_by_role("tab", name="Source records").click()
        assert page.get_by_text("Customer inquiry and call evidence", exact=True).is_visible()
        with page.expect_download() as event:
            page.get_by_role("link", name="Download reproduction ZIP").click()
        event.value.save_as(tmp_path / "bundle.zip")
        assert (tmp_path / "bundle.zip").stat().st_size > 1000
        page.get_by_role("tab", name="Decision & outcome").click()
        screenshot = ROOT / "docs/images/seller-investigation.png"
        screenshot.parent.mkdir(parents=True, exist_ok=True)
        page.screenshot(path=str(screenshot), full_page=True)
        page.set_viewport_size({"width": 390, "height": 844})
        assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth")
        page.get_by_role("button", name="Validate artifact integrity").click()
        page.get_by_role("status").filter(has_text="Artifact integrity verified").wait_for()
        page.screenshot(path=str(ROOT / "docs/images/seller-mobile.png"), full_page=True)
        page.keyboard.press("Tab")
        assert page.evaluate("document.activeElement.tagName") != "BODY"
        assert errors == []
        browser.close()
