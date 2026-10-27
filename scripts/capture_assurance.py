"""Exercise the actual static Pages build; capture recorded evidence, never run vendors."""
import argparse
import functools
import hashlib
import json
import sys
import threading
from datetime import datetime, timezone
from http.server import ThreadingHTTPServer
from pathlib import Path

from playwright.sync_api import sync_playwright

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from revenue_lab.bundle import ROOT, write_json
from revenue_lab.site import build
from capture_presentation import CONTRAST, Quiet

AXE_HASH = "880970c081707360e64f34cea25ff91892f5bc95675b0776925b9709dd8a68bb"
CASES = {
    "estate": ("estate-assurance", ["impact", "review", "evidence", "proof"], "review"),
    "reliability": ("reliability-operations", ["publication", "candidates", "sources", "recovery"], "candidates"),
    "temporal": ("temporal-assurance", ["time", "permissions", "delivery", "destination"], "delivery"),
}
SOURCES = ["web/app.js", "web/assurance.js", "web/assurance.css", "web/style.css",
           "web/index.html", "web/catalog.json", "sources.lock.json", "scripts/capture_assurance.py"]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def interactions(page, kind):
    """Exercise source-backed choices, including negative and recovery records."""
    checks = []
    def stage(name):
        page.locator(f'[data-assurance-stage="{name}"]').click()
    if kind == "estate":
        page.get_by_label("Operating company", exact=True).select_option("boreal")
        assert "boreal/" in page.locator("#assurance-platform").input_value()
        checks.append("company-scoped platform choices")
        page.get_by_label("Operating company", exact=True).select_option("atlas")
        page.get_by_label("Follow a business requirement", exact=True).select_option(index=0)
        page.get_by_role("button", name="Inspect input evidence", exact=True).first.click()
        assert page.locator(".assurance-selected-record").inner_text().strip()
        checks.append("interactive requirement inputs and source witness")
        stage("review")
        for value in ["replacement:1", "replacement:2"]:
            page.get_by_label("Recorded proposal revision", exact=True).select_option(value)
            assert "BLOCKED" in page.locator(".assurance-investigation").inner_text() or "STALE" in page.locator(".assurance-investigation").inner_text()
        checks.append("replacement revisions retain readiness failures")
        stage("evidence")
        assert "UNKNOWN" in page.locator(".assurance-investigation").inner_text()
        page.locator(".assurance-investigation details summary").first.click()
        checks.append("conflicting claims remain inspectable")
    elif kind == "reliability":
        assert "$410.00" in page.locator(".metrics").inner_text() if page.locator(".metrics").count() else "$410.00" in page.inner_text("body")
        stage("candidates")
        page.get_by_label("Recorded reporting candidate", exact=True).select_option("9")
        assert "wrong value" in page.locator(".assurance-investigation").inner_text().lower()
        assert page.locator(".assurance-investigation tbody tr").count() >= 6
        checks.append("equal-count wrong-value publication refusal")
        for value in ["2", "3", "4", "5", "7", "8", "13"]:
            page.get_by_label("Recorded reporting candidate", exact=True).select_option(value)
            assert page.locator(".assurance-investigation tbody tr").count() > 0
        checks.append("outage coverage schema race and full-rebuild candidates")
        stage("sources")
        for source in ["advertising", "website", "crm"]:
            page.get_by_label("Independently persisted source", exact=True).select_option(source)
            page.get_by_role("button", name="Inspect recorded acknowledgment", exact=True).click()
            page.get_by_text("Source acknowledgment", exact=True).click()
            assert "ack_id" in page.locator(".assurance-selected-record").inner_text()
        checks.append("independently stored acknowledgments for all three sources")
    else:
        page.get_by_label("Operating brand", exact=True).select_option("nova")
        assert page.locator("#assurance-person option").count() == 1
        page.get_by_label("Operating brand", exact=True).select_option("atlas")
        assert page.locator("#assurance-person option").count() == 9
        checks.append("same local person identity remains brand scoped")
        assert "restat" in page.locator(".assurance-investigation").inner_text().lower()
        stage("permissions")
        assert "trial_help" in page.locator(".assurance-investigation").inner_text()
        checks.append("two-time history and separate permission evidence")
        stage("delivery")
        page.get_by_role("button", name="Inspect independent receipt and business record", exact=True).click()
        page.get_by_text("Exact receipt and independently stored record", exact=True).click()
        assert "record_hash" in page.locator(".assurance-selected-record").inner_text()
        assert "committed_ack_lost" in page.locator(".assurance-investigation").inner_text()
        checks.append("lost acknowledgment and independent business-record receipt")
        stage("destination")
        assert "unobserved" in page.locator(".assurance-investigation").inner_text().lower()
        checks.append("missing destination state is not called synchronized")
    return checks


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "docs/evidence/architecture-assurance/browser.json")
    parser.add_argument("--images", type=Path, default=ROOT / "docs/images/architecture-assurance")
    args = parser.parse_args()
    build()
    print("Static build verified", flush=True)
    args.images.mkdir(parents=True, exist_ok=True)
    axe = ROOT / "tests/assurance_vendor/axe.min.js"
    assert sha(axe) == AXE_HASH

    class Pages(Quiet):
        def translate_path(self, path):
            prefix = "/enterprise-revenue-systems-lab/"
            return super().translate_path(path.removeprefix(prefix) if path.startswith(prefix) else "/not-found")

    server = ThreadingHTTPServer(("127.0.0.1", 0), functools.partial(Pages, directory=str(ROOT / "dist")))
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base = f"http://127.0.0.1:{server.server_port}/enterprise-revenue-systems-lab/"
    errors, outside, writes, layouts, accessibility, images, exercised = [], [], [], [], [], {}, {}
    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch()
            page = browser.new_page(viewport={"width": 1440, "height": 1100}, device_scale_factor=1, reduced_motion="reduce")
            page.on("pageerror", lambda e: errors.append(str(e)))
            page.on("request", lambda r: outside.append(r.url) if not r.url.startswith(base) else None)
            page.on("request", lambda r: writes.append(r.url) if r.method != "GET" else None)
            for kind, (case, stages, feature) in CASES.items():
                print("Reviewing " + case, flush=True)
                page.goto(base + "?case=" + case)
                page.locator(".assurance-investigation").wait_for()
                page.get_by_role("button", name="Validate artifact integrity").click()
                page.locator("#status").filter(has_text="Artifact integrity verified").wait_for()
                exercised[kind] = interactions(page, kind)
                print("Interactions passed: " + case, flush=True)
                page.add_script_tag(content=axe.read_text(encoding="utf-8"))
                for width in [1440, 1024, 768, 390, 320]:
                    print(case + " viewport " + str(width), flush=True)
                    page.set_viewport_size({"width": width, "height": 1100 if width > 768 else 900})
                    for stage in stages:
                        page.locator(f'[data-assurance-stage="{stage}"]').click()
                        layouts.append({"case": case, "width": width, "state": stage,
                                        "overflow": page.evaluate("document.documentElement.scrollWidth>innerWidth"), "contrast": page.evaluate(CONTRAST)})
                        if width in [1440, 390]:
                            result = page.evaluate("""async()=>{const r=await axe.run(document,{runOnly:{type:'tag',values:['wcag2a','wcag2aa','wcag21aa']}});return {violations:r.violations,incomplete:r.incomplete.map(x=>({id:x.id,impact:x.impact})),passes:r.passes.length}}""")
                            accessibility.append({"case": case, "width": width, "state": stage, **result})
                            if stage == {"estate":"evidence", "reliability":"sources", "temporal":"delivery"}[kind]:
                                if kind == "reliability":
                                    page.get_by_role("button", name="Inspect recorded acknowledgment", exact=True).click()
                                if kind == "temporal":
                                    page.get_by_role("button", name="Inspect independent receipt and business record", exact=True).click()
                                page.locator(".assurance-investigation details").first.evaluate("e=>e.open=true")
                                layouts.append({"case":case,"width":width,"state":stage+":expanded", "overflow":page.evaluate("document.documentElement.scrollWidth>innerWidth"),"contrast":page.evaluate(CONTRAST)})
                                expanded = page.evaluate("""async()=>{const r=await axe.run(document,{runOnly:{type:'tag',values:['wcag2a','wcag2aa','wcag21aa']}});return {violations:r.violations,incomplete:r.incomplete.map(x=>({id:x.id,impact:x.impact})),passes:r.passes.length}}""")
                                accessibility.append({"case":case,"width":width,"state":stage+":expanded",**expanded})
                    for tab in ["Source records", "Evidence timeline", "Compare & verify"]:
                        page.get_by_role("tab", name=tab, exact=True).click()
                        layouts.append({"case": case, "width": width, "tab": tab,
                                        "overflow": page.evaluate("document.documentElement.scrollWidth>innerWidth"), "contrast": page.evaluate(CONTRAST)})
                    page.get_by_role("tab", name="Decision & outcome", exact=True).click()
                for suffix, stage, width, height in [("desktop", stages[0], 1440, 1250), ("proof", feature, 1440, 1250), ("mobile", feature, 390, 1050)]:
                    page.set_viewport_size({"width": width, "height": height})
                    page.locator(f'[data-assurance-stage="{stage}"]').click()
                    if kind == "reliability" and stage == "candidates":
                        page.locator("#assurance-candidate").select_option("9")
                    target = ".assurance-investigation .release-stages" if width < 768 else ".assurance-investigation"
                    page.evaluate("selector=>scrollTo(0,document.querySelector(selector).getBoundingClientRect().top+scrollY-18)", target)
                    name = kind + "-" + suffix + ".png"
                    page.screenshot(path=str(args.images / name))
                    images[name] = {"width": width, "height": height, "case": case, "stage": stage,
                                    "capture": "Actual viewport of static dist; recorded synthetic evidence, no compositing"}
            browser_version = browser.version
            browser.close()
    finally:
        server.shutdown()
        server.server_close()
        thread.join()
    report = {"captured_at": datetime.now(timezone.utc).isoformat(), "browser": "Chromium " + browser_version,
              "served": "Actual dist at /enterprise-revenue-systems-lab/; not a public deployment",
              "source_sha256": {name: sha(ROOT / name) for name in SOURCES},
              "image_sha256": {name: sha(args.images / name) for name in images}, "images": images,
              "layouts": layouts, "accessibility": accessibility, "interactions": exercised,
              "axe_version": "4.10.3", "axe_sha256": AXE_HASH, "page_errors": errors,
              "nonlocal_requests": outside, "http_writes": writes, "new_source_engine_execution": False,
              "new_model_execution": False, "new_vendor_execution": False}
    write_json(args.output, report)
    assert not errors and not outside and not writes
    assert all(not r["overflow"] and not r["contrast"]["failures"] for r in layouts), "layout/contrast failure"
    assert all(not r["violations"] for r in accessibility), "automated accessibility failure"
    assert all(not r["incomplete"] for r in accessibility), "unresolved automated accessibility review"
    print(json.dumps({"layouts": len(layouts), "accessibility_states": len(accessibility), "screenshots": len(images), "status": "passed"}))


if __name__ == "__main__":
    main()
