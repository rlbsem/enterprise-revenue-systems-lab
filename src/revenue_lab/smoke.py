"""Read-only browser assurance for a static deployment, pinned to a checkout.

No engine execution, inference, vendor API calls or HTTP writes are permitted.
The same checks run against an isolated Pages-shaped local build in regression CI.
"""

import hashlib
import io
import json
import re
import tempfile
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit

from playwright.sync_api import sync_playwright

from .bundle import verify, write_json

PUBLIC_URL = "https://rlbsem.github.io/enterprise-revenue-systems-lab/"


def check_zip(raw, expected):
    """Verify contents before writing trusted names; never extract arbitrary ZIPs."""
    manifest_raw = (expected / "bundle.json").read_bytes()
    manifest = json.loads(manifest_raw)
    expected_names = {"bundle.json", "REPRODUCE.txt"} | {
        item["path"] for item in manifest["artifacts"]
    }
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        names = archive.namelist()
        assert len(names) == len(set(names)), "duplicate ZIP member"
        assert set(names) == expected_names, "unexpected ZIP inventory"
        for item in manifest["artifacts"]:
            assert archive.getinfo(item["path"]).file_size == item["bytes"], "ZIP member size mismatch"
        assert archive.getinfo("bundle.json").file_size == len(manifest_raw)
        assert archive.getinfo("REPRODUCE.txt").file_size <= 16384
        assert archive.testzip() is None, "ZIP CRC failure"
        assert archive.read("bundle.json") == manifest_raw, "ZIP manifest mismatch"
        assert b"revenue_lab.cli verify" in archive.read("REPRODUCE.txt")
        with tempfile.TemporaryDirectory() as temporary:
            destination = Path(temporary)
            (destination / "bundle.json").write_bytes(manifest_raw)
            for item in manifest["artifacts"]:
                name = item["path"]
                assert re.fullmatch(r"[a-zA-Z0-9_-]+(?:/[a-zA-Z0-9_-]+)*\.[a-zA-Z0-9]+", name)
                data = archive.read(name)
                assert data == (expected / name).read_bytes(), "ZIP artifact mismatch: " + name
                target = destination / name
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(data)
            result = verify(destination)
    return {"members": len(names), "sha256": hashlib.sha256(raw).hexdigest(), "domain_verification": result}


def check_site(base, expected, output, *, source_links=False):
    """Collect failures as failures; persist observations even when checks fail."""
    parsed = urlsplit(base)
    assert base.endswith("/") and not parsed.query and not parsed.fragment
    assert base == PUBLIC_URL or (
        parsed.scheme == "http" and parsed.hostname == "127.0.0.1"
    ), "only the public Lab or an isolated loopback build is supported"
    report = {
        "observed_at": datetime.now(timezone.utc).isoformat(),
        "url": base,
        "scope": "Recorded static explorer only; no new inference or native vendor execution",
        "checks": [],
        "failures": [],
    }
    output.mkdir(parents=True, exist_ok=True)
    catalog = json.loads((expected / "catalog.json").read_text(encoding="utf-8"))
    errors, failed_requests, writes, outside = [], [], [], []

    def record(name, operation):
        try:
            detail = operation()
            report["checks"].append({"name": name, "status": "passed", "detail": detail})
        except Exception as error:
            report["failures"].append({"name": name, "error": type(error).__name__ + ": " + str(error)[:1200]})

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        context = browser.new_context(accept_downloads=True)
        page = context.new_page()
        page.set_default_timeout(10000)

        def boundary(route):
            request = route.request
            if request.method not in ("GET", "HEAD"):
                writes.append({"method": request.method, "url": request.url})
                route.abort()
            elif not request.url.startswith(base):
                outside.append(request.url)
                route.abort()
            else:
                route.continue_()

        context.route("**/*", boundary)
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.on("console", lambda message: errors.append({"message": message.text, "location": message.location}) if message.type == "error" and not (
            parsed.hostname == "127.0.0.1" and message.location.get("url") == base + "api/config" and "404" in message.text
        ) else None)
        page.on("requestfailed", lambda request: failed_requests.append(request.url))
        page.on("response", lambda response: failed_requests.append(
            {"url": response.url, "status": response.status}
        ) if response.status >= 400 and not (
            parsed.hostname == "127.0.0.1" and response.url == base + "api/config" and response.status == 404
        ) else None)

        def assets():
            hashes = {}
            for name in ("index.html", "style.css", "app.js", "gtm.js", "research.js", "release.js", "integrity.js", "analytics.js", "measurement.js", "assurance.js", "assurance.css", "catalog.json"):
                response = context.request.get(base + name)
                assert response.status == 200, name
                data = response.body()
                assert data == (expected / name).read_bytes(), "deployed bytes differ: " + name
                hashes[name] = hashlib.sha256(data).hexdigest()
            return hashes

        record("deployed_static_bytes", assets)
        for width, height in ((1440, 1000), (390, 844)):
            page.set_viewport_size({"width": width, "height": height})
            for case in catalog["scenarios"]:
                def inspect(case=case, width=width):
                    page.goto(base + "?case=" + case["id"], wait_until="networkidle")
                    page.get_by_role("heading", name=case["title"], exact=True).wait_for()
                    page.locator("#status").filter(has_text="Recorded evidence loaded").wait_for()
                    assert page.get_by_label("CHOOSE AN EVIDENCE CASE").input_value() == case["id"]
                    assert page.get_by_text("RECORDED EVIDENCE", exact=True).is_visible()
                    assert page.locator("#fresh").is_hidden()
                    assert page.locator("#limitations").inner_text().strip()
                    assert page.locator("#source-link").get_attribute("href") == (
                        "https://github.com/" + case["source"]["repository"] + "/tree/" + case["source"]["commit"]
                    )
                    page.get_by_role("button", name="Validate artifact integrity").click()
                    page.locator("#status").filter(has_text="Artifact integrity verified").wait_for()
                    assert page.evaluate("document.documentElement.scrollWidth <= innerWidth"), "horizontal page overflow"
                    for tab in ("Source records", "Evidence timeline", "Compare & verify", "Decision & outcome"):
                        page.get_by_role("tab", name=tab, exact=True).click()
                        assert page.locator("#panel").inner_text().strip()
                    result = {"case": case["id"], "width": width, "source": case["source"]}
                    if width == 1440:
                        with page.expect_download() as event:
                            page.get_by_role("link", name="Download reproduction ZIP").click()
                        target = output / (case["id"] + ".zip")
                        event.value.save_as(target)
                        result["zip"] = check_zip(target.read_bytes(), expected / "evidence" / case["id"])
                    return result

                record(f"case:{case['id']}:{width}", inspect)

        def navigation():
            page.goto(base + "?case=seller-application", wait_until="networkidle")
            page.get_by_role("heading", name="Reviewed discovery action", exact=True).wait_for()
            for label, case_id in (
                ("Recover uncertain execution", "control-recovery"),
                ("Reconcile the numbers", "revenue-bridge"),
                ("Connect CRM and warehouse", "connected-roundtrip"),
                ("Inspect qualified pipeline", "gtm-enterprise"),
                ("Assure the model release", "release-assurance"),
                ("Trace commitment to cash", "revenue-integrity"),
                ("Prove models and performance", "analytics-engineering"),
                ("Trust measurement claims", "measurement-integrity"),
                ("Assure estate changes", "estate-assurance"),
                ("Trust source publication", "reliability-operations"),
                ("Assure audience activation", "temporal-assurance"),
                ("Trust the seller action", "seller-application"),
            ):
                button = page.get_by_role("button", name=label)
                button.focus()
                page.keyboard.press("Enter")
                page.locator("#status").filter(has_text="Recorded evidence loaded").wait_for()
                page.wait_for_url("**/?case=" + case_id)
                page.get_by_role("heading", name=next(c["title"] for c in catalog["scenarios"] if c["id"] == case_id), exact=True).wait_for()
                assert page.get_by_label("CHOOSE AN EVIDENCE CASE").input_value() == case_id
            page.get_by_label("CHOOSE AN EVIDENCE CASE").select_option("seller-support-review")
            page.wait_for_url("**/?case=seller-support-review")
            page.get_by_role("heading", name="A passing draft with an unsupported claim", exact=True).wait_for()
            page.reload(wait_until="networkidle")
            page.get_by_role("heading", name="A passing draft with an unsupported claim", exact=True).wait_for()
            page.go_back(wait_until="networkidle")
            page.get_by_role("heading", name="Reviewed discovery action", exact=True).wait_for()
            page.go_forward(wait_until="networkidle")
            page.get_by_role("heading", name="A passing draft with an unsupported claim", exact=True).wait_for()
            page.get_by_role("tab", name="Decision & outcome").focus()
            for key, name in (("ArrowRight", "Source records"), ("End", "Compare & verify"), ("Home", "Decision & outcome")):
                page.keyboard.press(key)
                assert page.get_by_role("tab", name=name).get_attribute("aria-selected") == "true"
            page.reload(wait_until="networkidle")
            page.keyboard.press("Tab")
            assert page.get_by_role("link", name="Skip to investigation").evaluate("e => e === document.activeElement")
            page.keyboard.press("Enter")
            assert page.evaluate("document.activeElement.id") == "main", "skip link did not focus the investigation"
            return "Twelve keyboard-selectable investigations; share/reload/Back/Forward; tab keys; skip link"

        record("navigation_and_keyboard", navigation)

        def imports():
            page.goto(base + "?case=revenue-correction", wait_until="networkidle")
            page.get_by_role("heading", name="Late correction and equivalent rebuild", exact=True).wait_for()
            page.get_by_text("Validate a downloaded portable bundle", exact=True).click()
            page.get_by_label("Portable evidence JSON").set_input_files(expected / "evidence/seller-support-review/portable.json")
            page.locator("#status").filter(has_text="Artifact integrity verified").wait_for()
            page.go_back(wait_until="networkidle")
            page.get_by_role("heading", name="Late correction and equivalent rebuild", exact=True).wait_for()
            page.go_forward(wait_until="networkidle")
            page.get_by_role("heading", name="A passing draft with an unsupported claim", exact=True).wait_for()
            portable = json.loads((expected / "evidence/seller-support-review/portable.json").read_text(encoding="utf-8"))
            portable["artifacts"]["trace.json"] += " "
            tampered = output / "tampered.json"
            write_json(tampered, portable)
            page.get_by_label("Portable evidence JSON").set_input_files(tampered)
            page.locator("#status").filter(has_text="Verification refused").wait_for()
            assert "Artifact integrity mismatch" in page.locator("#status").inner_text()
            return "Pinned bundle accepted with one history entry; one-byte artifact mutation refused; no execution"

        record("portable_import", imports)
        # Public-source reachability is separate from the application's strict network boundary.
        if source_links:
            def sources():
                links = sorted({
                    "https://github.com/" + case["source"]["repository"] + "/tree/" + case["source"]["commit"]
                    for case in catalog["scenarios"]
                })
                source_context = playwright.request.new_context()
                try:
                    for link in links:
                        response = source_context.get(link, timeout=30000)
                        assert response.status == 200, f"source link returned {response.status}: {link}"
                finally:
                    source_context.dispose()
                return links
            record("original_source_links", sources)
        # A missing path is probed with GET only; never send a hosted execution request.
        def static_boundary():
            for path in ("api/config", "api/runs"):
                response = context.request.get(base + path)
                assert response.status == 404, "unexpected hosted API response: " + path
            assert not writes and not outside, "browser attempted writes or external requests"
            return "GET probes 404; no browser HTTP writes, vendor requests or fresh controls"
        record("static_only_boundary", static_boundary)
        record("browser_errors", lambda: _clean(errors, failed_requests))
        report["browser_errors"] = errors
        report["failed_resources"] = failed_requests
        report["attempted_writes"] = writes
        report["outside_requests"] = outside
        browser.close()
    report["status"] = "failed" if report["failures"] else "passed"
    write_json(output / "verification.json", report)
    return report


def _clean(errors, requests):
    assert not errors, "browser console/JavaScript errors: " + str(errors[:5])
    assert not requests, "failed browser resources: " + str(requests[:5])
    return "No console errors, uncaught exceptions or failed resources"
