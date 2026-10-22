"""Real Chromium proof against dist under a GitHub Pages-style prefix; no vendor calls."""
import argparse
import functools
import hashlib
import json
import sys
import threading
import urllib.request
from datetime import datetime, timezone
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from playwright.sync_api import sync_playwright

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from revenue_lab.bundle import ROOT, write_json
from revenue_lab.site import build
from capture_presentation import CONTRAST, Quiet

AXE_HASH = "880970c081707360e64f34cea25ff91892f5bc95675b0776925b9709dd8a68bb"


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output",type=Path,default=ROOT/"docs/evidence/research-case/browser.json")
    parser.add_argument("--images",type=Path,default=ROOT/"docs/images/research")
    args=parser.parse_args()
    build()
    args.images.mkdir(parents=True,exist_ok=True)
    axe=ROOT/".cache/research-axe.min.js"
    if not axe.exists():
        axe.parent.mkdir(exist_ok=True)
        with urllib.request.urlopen("https://cdnjs.cloudflare.com/ajax/libs/axe-core/4.10.3/axe.min.js",timeout=45) as response:
            axe.write_bytes(response.read())
    assert hashlib.sha256(axe.read_bytes()).hexdigest()==AXE_HASH
    # The host serves only static dist, mounted under the same project prefix as Pages.
    class Pages(Quiet):
        def translate_path(self,path):
            prefix="/enterprise-revenue-systems-lab/"
            return super().translate_path(path.removeprefix(prefix) if path.startswith(prefix) else "/not-found")
    server=ThreadingHTTPServer(("127.0.0.1",0),functools.partial(Pages,directory=str(ROOT/"dist")))
    thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
    base=f"http://127.0.0.1:{server.server_port}/enterprise-revenue-systems-lab/"
    errors,external,layouts,accessibility,images=[],[],[],{},{}
    try:
        with sync_playwright() as pw:
            browser=pw.chromium.launch()
            page=browser.new_page(viewport={"width":1440,"height":1050},device_scale_factor=1,reduced_motion="reduce")
            page.on("pageerror",lambda e:errors.append(str(e)))
            page.on("request",lambda r:external.append(r.url) if not r.url.startswith(base) else None)
            page.goto(base+"?case=gtm-research")
            page.get_by_label("Research context").wait_for()
            page.get_by_role("button",name="Validate artifact integrity").click()
            page.locator("#status").filter(has_text="Artifact integrity verified").wait_for()
            for width in [1440,1024,768,390,320]:
                page.set_viewport_size({"width":width,"height":1050 if width>768 else 844})
                for tab in ["Decision & outcome","Source records","Evidence timeline","Compare & verify"]:
                    page.get_by_role("tab",name=tab,exact=True).click()
                    layouts.append({"width":width,"tab":tab,"overflow":page.evaluate("document.documentElement.scrollWidth>innerWidth"),"contrast":page.evaluate(CONTRAST)})
                page.get_by_role("tab",name="Decision & outcome",exact=True).click()
            # Full document automated a11y plus rendered contrast; incomplete rules remain reported.
            page.add_script_tag(content=axe.read_text(encoding="utf-8"))
            for width in [1440,390]:
                page.set_viewport_size({"width":width,"height":1050 if width==1440 else 844})
                result=page.evaluate("async()=>{const r=await axe.run(document,{runOnly:{type:'tag',values:['wcag2a','wcag2aa','wcag21aa']}});return {violations:r.violations,incomplete:r.incomplete.map(x=>({id:x.id,impact:x.impact})),passes:r.passes.map(x=>x.id)}}")
                accessibility[str(width)]=result
            page.set_viewport_size({"width":1440,"height":1320})
            page.locator(".research-hero").scroll_into_view_if_needed();page.evaluate("window.scrollTo(0,document.querySelector('.research-hero').getBoundingClientRect().top+scrollY-20)")
            page.screenshot(path=str(args.images/"sdr-intelligence-desktop.png"))
            images["sdr-intelligence-desktop.png"]={"width":1440,"height":1320,"capture":"actual viewport crop; hero, queue and selected account"}
            page.locator("#research-saved-review").screenshot(path=str(args.images/"recorded-seller-review.png"))
            images["recorded-seller-review.png"]={"capture":"actual saved-review section; no compositing"}
            page.set_viewport_size({"width":390,"height":844})
            page.locator(".research-controls").scroll_into_view_if_needed();page.evaluate("window.scrollTo(0,document.querySelector('.research-controls').getBoundingClientRect().top+scrollY-12)")
            page.screenshot(path=str(args.images/"sdr-intelligence-mobile.png"))
            images["sdr-intelligence-mobile.png"]={"width":390,"height":844,"capture":"actual viewport crop; selected account controls"}
            browser_version=browser.version;browser.close()
    finally:
        server.shutdown();server.server_close();thread.join()
    report={"captured_at":datetime.now(timezone.utc).isoformat(),"browser":"Chromium "+browser_version,"case":"gtm-research",
            "served":"actual dist build under /enterprise-revenue-systems-lab/; not public deployment",
            "source_sha256":{name:hashlib.sha256((ROOT/name).read_bytes()).hexdigest() for name in ["web/app.js","web/gtm.js","web/research.js","web/style.css","web/index.html","web/catalog.json","sources.lock.json","scripts/capture_research.py"]},
            "image_sha256":{name:hashlib.sha256((args.images/name).read_bytes()).hexdigest() for name in images},
            "images":images,"layouts":layouts,"accessibility":accessibility,"axe_version":"4.10.3","axe_sha256":AXE_HASH,
            "page_errors":errors,"nonlocal_requests":external,"new_model_vendor_or_approval_execution":False}
    write_json(args.output,report)
    assert not errors and not external
    assert all(not r["overflow"] and not r["contrast"]["failures"] for r in layouts), "layout/contrast failures; inspect report"
    assert all(not r["violations"] for r in accessibility.values()), "automated accessibility violations; inspect report"
    print(json.dumps({"layouts":len(layouts),"images":len(images),"axe_violations":sum(len(r["violations"]) for r in accessibility.values()),"status":"passed"}))


if __name__=="__main__":
    main()
