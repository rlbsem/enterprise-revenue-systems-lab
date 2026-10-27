"""Actual static dist browser acceptance and screenshots; no model, cloud or vendor calls."""
import argparse
import functools
import hashlib
import json
import sys
import threading
import urllib.request
from datetime import datetime, timezone
from http.server import ThreadingHTTPServer
from pathlib import Path

from playwright.sync_api import sync_playwright

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from revenue_lab.bundle import ROOT, write_json
from revenue_lab.site import build
from capture_presentation import CONTRAST, Quiet

AXE_HASH="880970c081707360e64f34cea25ff91892f5bc95675b0776925b9709dd8a68bb"
STAGES=["models","metrics","quality","performance","native"]


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output",type=Path,default=ROOT/"docs/evidence/analytics-engineering/browser.json")
    parser.add_argument("--images",type=Path,default=ROOT/"docs/images/analytics-engineering")
    args=parser.parse_args();build();args.images.mkdir(parents=True,exist_ok=True)
    axe=ROOT/".cache/research-axe.min.js"
    if not axe.exists():
        with urllib.request.urlopen("https://cdnjs.cloudflare.com/ajax/libs/axe-core/4.10.3/axe.min.js",timeout=40) as response:axe.write_bytes(response.read())
    assert hashlib.sha256(axe.read_bytes()).hexdigest()==AXE_HASH

    class Pages(Quiet):
        def translate_path(self,path):
            prefix="/enterprise-revenue-systems-lab/"
            return super().translate_path(path.removeprefix(prefix) if path.startswith(prefix) else "/not-found")

    server=ThreadingHTTPServer(("127.0.0.1",0),functools.partial(Pages,directory=str(ROOT/"dist")))
    thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
    base=f"http://127.0.0.1:{server.server_port}/enterprise-revenue-systems-lab/"
    errors,outside,writes,layouts,accessibility,images=[],[],[],[],[],{}
    try:
        with sync_playwright() as pw:
            browser=pw.chromium.launch();page=browser.new_page(viewport={"width":1440,"height":1100},device_scale_factor=1,reduced_motion="reduce")
            page.on("pageerror",lambda e:errors.append(str(e)))
            page.on("request",lambda r:outside.append(r.url) if not r.url.startswith(base) else None)
            page.on("request",lambda r:writes.append(r.url) if r.method!="GET" else None)
            page.goto(base+"?case=analytics-engineering")
            page.get_by_role("heading",name="What is one row supposed to mean?").wait_for()
            page.get_by_role("button",name="Validate artifact integrity").click()
            page.locator("#status").filter(has_text="Artifact integrity verified").wait_for()
            page.add_script_tag(content=axe.read_text(encoding="utf-8"))
            for width in [1440,1024,768,390,320]:
                page.set_viewport_size({"width":width,"height":1100 if width>768 else 844})
                for stage in STAGES:
                    page.locator(f'[data-analytics-stage="{stage}"]').click()
                    layouts.append({"width":width,"state":stage,"overflow":page.evaluate("document.documentElement.scrollWidth>innerWidth"),"contrast":page.evaluate(CONTRAST)})
                    if width in [1440,390]:
                        result=page.evaluate("async()=>{const r=await axe.run(document,{runOnly:{type:'tag',values:['wcag2a','wcag2aa','wcag21aa']}});return {violations:r.violations,incomplete:r.incomplete.map(x=>({id:x.id,impact:x.impact})),passes:r.passes.length}}")
                        accessibility.append({"width":width,"state":stage,**result})
                for tab in ["Source records","Evidence timeline","Compare & verify"]:
                    page.get_by_role("tab",name=tab,exact=True).click()
                    layouts.append({"width":width,"tab":tab,"overflow":page.evaluate("document.documentElement.scrollWidth>innerWidth"),"contrast":page.evaluate(CONTRAST)})
                page.get_by_role("tab",name="Decision & outcome",exact=True).click()
            page.set_viewport_size({"width":1440,"height":1260});page.locator('[data-analytics-stage="models"]').click()
            page.evaluate("scrollTo(0,document.querySelector('.release-hero').getBoundingClientRect().top+scrollY-20)")
            page.screenshot(path=str(args.images/"analytics-engineering-desktop.png"));images["analytics-engineering-desktop.png"]={"width":1440,"height":1260,"capture":"actual viewport; recorded model grain, lineage and source fixture"}
            page.locator('[data-analytics-stage="performance"]').click()
            page.evaluate("scrollTo(0,document.querySelector('.release-stages').getBoundingClientRect().top+scrollY-25)")
            page.screenshot(path=str(args.images/"analytics-engineering-performance.png"));images["analytics-engineering-performance.png"]={"width":1440,"height":1260,"capture":"actual viewport; actual paired local measurements and rejected optimization"}
            page.set_viewport_size({"width":390,"height":1000})
            page.evaluate("scrollTo(0,document.querySelector('.release-stages').getBoundingClientRect().top+scrollY-15)")
            page.screenshot(path=str(args.images/"analytics-engineering-mobile.png"));images["analytics-engineering-mobile.png"]={"width":390,"height":1000,"capture":"actual mobile viewport; selectable analytics investigation and stress measurements"}
            browser_version=browser.version;browser.close()
    finally:
        server.shutdown();server.server_close();thread.join()
    report={"captured_at":datetime.now(timezone.utc).isoformat(),"browser":"Chromium "+browser_version,
            "served":"actual dist at /enterprise-revenue-systems-lab/; not a public deployment", "case":"analytics-engineering",
            "source_revision":"4cc1480d63f1095584db2ddcde72ed5626eb7ea7",
            "source_sha256":{name:hashlib.sha256((ROOT/name).read_bytes()).hexdigest() for name in ["web/app.js","web/analytics.js","web/style.css","web/index.html","web/catalog.json","sources.lock.json","scripts/capture_analytics.py"]},
            "image_sha256":{name:hashlib.sha256((args.images/name).read_bytes()).hexdigest() for name in images},"images":images,
            "layouts":layouts,"accessibility":accessibility,"axe_version":"4.10.3","axe_sha256":AXE_HASH,
            "page_errors":errors,"nonlocal_requests":outside,"http_writes":writes,"new_model_execution":False,"new_warehouse_execution":False}
    write_json(args.output,report)
    assert not errors and not outside and not writes
    assert all(not r["overflow"] and not r["contrast"]["failures"] for r in layouts), "layout/contrast failure"
    assert all(not r["violations"] for r in accessibility), "automated accessibility failure"
    print(json.dumps({"layout_checks":len(layouts),"accessibility_states":len(accessibility),"screenshots":len(images),"status":"passed"}))


if __name__=="__main__":main()
