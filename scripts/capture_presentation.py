"""Review/capture the static explorer using existing recorded evidence only."""

import argparse
import functools
import hashlib
import json
import threading
import zipfile
from datetime import datetime, timezone
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
CASES = {
    "release": "release-assurance",
    "seller": "seller-application",
    "control": "control-recovery",
    "revenue": "revenue-correction",
    "connected": "connected-roundtrip",
    "gtm": "gtm-enterprise",
}
TABS = ["Decision & outcome", "Source records", "Evidence timeline", "Compare & verify"]

# Rendered text on solid backgrounds; not a complete accessibility audit.
CONTRAST = """() => {
  const rgba = s => (s.match(/[\\d.]+/g) || []).map(Number);
  const over = (a,b) => { const t = a[3] ?? 1; return [0,1,2].map(i=>a[i]*t+b[i]*(1-t)); };
  const lum = c => c.map(x=>x/255).map(x=>x<=.04045?x/12.92:((x+.055)/1.055)**2.4)
    .reduce((s,x,i)=>s+x*[.2126,.7152,.0722][i],0);
  const failures=[], walker=document.createTreeWalker(document.body,NodeFilter.SHOW_TEXT);
  let node, checked=0, minimum=100;
  while(node=walker.nextNode()) {
    if(!/[a-z0-9]/i.test(node.textContent)) continue;
    const e=node.parentElement, s=getComputedStyle(e), r=e.getBoundingClientRect();
    if(!r.width||!r.height||s.visibility==='hidden'||s.display==='none'||e.closest('script,style,option')) continue;
    const parents=[]; for(let p=e;p;p=p.parentElement) parents.unshift(p);
    let bg=[255,255,255]; for(const p of parents) bg=over(rgba(getComputedStyle(p).backgroundColor),bg);
    const fg=over(rgba(s.color),bg), a=lum(fg), b=lum(bg), ratio=(Math.max(a,b)+.05)/(Math.min(a,b)+.05);
    const size=parseFloat(s.fontSize), large=size>=24||(size>=18.66&&parseInt(s.fontWeight)>=700);
    const threshold=large?3:4.5; checked++; minimum=Math.min(minimum,ratio);
    if(ratio+.001<threshold) failures.push({text:node.textContent.trim().slice(0,100),selector:e.id||e.className||e.tagName,ratio:+ratio.toFixed(3),threshold});
  }
  return {checked,minimum_ratio:+minimum.toFixed(3),failures};
}"""


class Quiet(SimpleHTTPRequestHandler):
    def log_message(self, *_):
        pass


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--investigation", choices=CASES, help="Capture only one investigation; default reviews all")
    parser.add_argument("--images", type=Path, default=ROOT / ".cache/visual-review")
    parser.add_argument(
        "--evidence", type=Path, default=ROOT / ".cache/visual-review/capture.json"
    )
    args = parser.parse_args()
    # Generate only the new recorded case archive. Existing source-bound ZIPs
    # must not be rebuilt by a visual review.
    bundle_dir = ROOT / "web/evidence/connected-roundtrip"
    bundle = json.loads((bundle_dir / "bundle.json").read_text(encoding="utf-8"))
    with zipfile.ZipFile(bundle_dir / "reproduction.zip", "w", zipfile.ZIP_DEFLATED) as z:
        def member(name, data):
            info = zipfile.ZipInfo(name, date_time=(2026, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            z.writestr(info, data)

        member("bundle.json", (bundle_dir / "bundle.json").read_bytes())
        for item in bundle["artifacts"]:
            member(item["path"], (bundle_dir / item["path"]).read_bytes())
        member(
            "REPRODUCE.txt",
            (
                "Clone https://github.com/rlbsem/enterprise-revenue-systems-lab\\n"
                "Install requirements.lock and set PYTHONPATH=src.\\n"
                + "\\n".join(bundle["reproduce"])
                + "\\npython -m revenue_lab.cli verify <extracted-bundle>\\n"
                "Recorded vendor execution is verified offline; no new vendor calls.\\n"
            ).encode(),
        )
    args.images.mkdir(parents=True, exist_ok=True)
    args.evidence.parent.mkdir(parents=True, exist_ok=True)
    server = ThreadingHTTPServer(
        ("127.0.0.1", 0), functools.partial(Quiet, directory=str(ROOT / "web"))
    )
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    url = f"http://127.0.0.1:{server.server_port}/"
    catalog = json.loads((ROOT / "web/catalog.json").read_text(encoding="utf-8"))
    if args.investigation:
        catalog["scenarios"] = [c for c in catalog["scenarios"] if c["investigation"] == args.investigation]
    errors, requests, reviews, images = [], [], [], {}
    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=True)
            browser_version = browser.version
            context = browser.new_context(
                viewport={"width": 1440, "height": 1000},
                device_scale_factor=1,
                locale="en-CA",
                reduced_motion="reduce",
            )
            page = context.new_page()
            page.on("pageerror", lambda error: errors.append(str(error)))
            page.on(
                "request",
                lambda request: requests.append((request.method, request.url)),
            )
            for width, height in [
                (1440, 1000),
                (1280, 900),
                (768, 1024),
                (390, 844),
                (320, 740),
            ]:
                page.set_viewport_size({"width": width, "height": height})
                for case in catalog["scenarios"]:
                    investigation, scenario = case["investigation"], case["id"]
                    page.goto(url + "?case=" + scenario)
                    page.get_by_role(
                        "heading", name=case["title"], exact=True
                    ).wait_for()
                    page.get_by_role(
                        "button", name="Validate artifact integrity"
                    ).click()
                    page.locator("#status").filter(
                        has_text="Artifact integrity verified"
                    ).wait_for()
                    for tab in TABS:
                        page.get_by_role("tab", name=tab, exact=True).click()
                        assert page.locator("#panel").inner_text().strip()
                        reviews.append(
                            {
                                "case": scenario,
                                "width": width,
                                "view": tab,
                                "overflow": page.evaluate(
                                    "document.documentElement.scrollWidth > innerWidth"
                                ),
                                "contrast": page.evaluate(CONTRAST),
                            }
                        )
                    page.get_by_role("tab", name=TABS[0], exact=True).click()
                    page.evaluate("scrollTo(0,0)")
                    if width in (1440, 390) and (scenario == CASES[investigation] or investigation == "gtm"):
                        suffix = "overview" if width == 1440 else "mobile"
                        image_name = scenario if investigation == "gtm" else investigation
                        image = args.images / f"{image_name}-{suffix}.png"
                        if width == 390:
                            image = args.images / "visual-refresh" / image.name
                        image.parent.mkdir(parents=True, exist_ok=True)
                        page.screenshot(path=str(image), full_page=True)
                        images[image.relative_to(args.images).as_posix()] = {
                            "sha256": digest(image),
                            "case": scenario,
                            "viewport": {"width": width, "height": height},
                            "full_page": True,
                        }
                        if width == 390:
                            preview = (
                                ROOT
                                / ".cache/visual-review"
                                / f"{investigation}-mobile-viewport.png"
                            )
                            preview.parent.mkdir(parents=True, exist_ok=True)
                            page.screenshot(path=str(preview))
                            page.locator(".case").scroll_into_view_if_needed()
                            page.screenshot(
                                path=str(
                                    preview.with_name(
                                        f"{investigation}-mobile-panel.png"
                                    )
                                )
                            )
                    page.get_by_role("tab", name=TABS[0], exact=True).focus()
                    page.keyboard.press("ArrowRight")
                    assert (
                        page.get_by_role("tab", name=TABS[1], exact=True).get_attribute(
                            "aria-selected"
                        )
                        == "true"
                    )
                    assert (
                        page.evaluate(
                            "getComputedStyle(document.activeElement).outlineStyle"
                        )
                        != "none"
                    )
                    expected_label = (
                        "Verify this recorded release offline"
                        if investigation == "release" else
                        "Verify these separate records offline"
                        if investigation == "gtm" else
                        "Verify this native record offline"
                        if investigation == "connected"
                        else "Reproduce this investigation · fresh local execution"
                    )
                    page.get_by_text(expected_label, exact=True).click()
                    assert page.locator("#fresh").is_hidden()
                    assert page.locator("#commands").inner_text().strip()
                    if width == 1440:
                        with page.expect_download() as event:
                            page.get_by_role(
                                "link", name="Download reproduction ZIP"
                            ).click()
                        saved = ROOT / ".cache/visual-review" / f"{scenario}.zip"
                        saved.parent.mkdir(parents=True, exist_ok=True)
                        event.value.save_as(saved)
                        assert digest(saved) == digest(
                            ROOT / "web/evidence" / scenario / "reproduction.zip"
                        )
                        with zipfile.ZipFile(saved) as archive:
                            assert archive.testzip() is None
            # A real invalid import exercises the existing visible refusal state.
            page.set_viewport_size({"width": 390, "height": 844})
            page.get_by_text(
                "Validate a downloaded portable bundle", exact=True
            ).click()
            page.get_by_label("Portable evidence JSON").set_input_files(
                {
                    "name": "invalid.json",
                    "mimeType": "application/json",
                    "buffer": b"{}",
                }
            )
            page.locator("#status.error").filter(has_text="Import refused").wait_for()
            refusal = {
                "text": page.locator("#status").inner_text(),
                "contrast": page.evaluate(CONTRAST),
            }
            assert page.request.get(url + "api/config").status == 404
            browser.close()
    finally:
        server.shutdown()
        server.server_close()
        thread.join()
    assert not errors
    assert all(
        method == "GET" and address.startswith(url) for method, address in requests
    )
    record = {
        "captured_utc": datetime.now(timezone.utc).isoformat(),
        "scope": "Actual static HTML/CSS/JS; existing recorded synthetic bundles only. No new inference, engine run or external system call.",
        "browser": "Chromium",
        "browser_version": browser_version,
        "stylesheet_sha256": digest(ROOT / "web/style.css"),
        "app_sha256": digest(ROOT / "web/app.js"),
        "gtm_sha256": digest(ROOT / "web/gtm.js"),
        "html_sha256": digest(ROOT / "web/index.html"),
        "catalog_sha256": digest(ROOT / "web/catalog.json"),
        "images": images,
        "reviews": reviews,
        "recorded_cases": catalog["scenarios"],
        "historical_images": {
            p.relative_to(ROOT).as_posix(): digest(p)
            for p in sorted((ROOT / "docs/images/archive").glob("pre-navy-*.png"))
        },
        "refusal_state": refusal,
        "page_errors": errors,
        "network": "GET requests to loopback static server only",
        "interactions": [
            "case loading",
            "all four evidence tabs",
            "artifact validation",
            "keyboard tab navigation and visible focus",
            "exact-byte reproduction ZIP download",
            "reproduction commands with execution hidden",
            "invalid import refusal",
        ],
        "contrast_scope": "Computed text/solid-background checks; not a complete WCAG audit",
    }
    args.evidence.write_text(
        json.dumps(record, indent=2) + "\n", encoding="utf-8", newline="\n"
    )
    print(
        json.dumps(
            {
                "views": len(reviews),
                "overflow_failures": sum(r["overflow"] for r in reviews),
                "contrast_failures": sum(
                    len(r["contrast"]["failures"]) for r in reviews
                ),
                "images": list(images),
                "page_errors": errors,
            }
        )
    )
    assert not any(r["overflow"] or r["contrast"]["failures"] for r in reviews)
    assert not refusal["contrast"]["failures"]


if __name__ == "__main__":
    main()
