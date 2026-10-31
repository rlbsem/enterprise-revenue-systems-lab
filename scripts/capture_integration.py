"""Actual static Pages-path browser checks. No model, source engine or vendor calls."""
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

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from revenue_lab.bundle import ROOT, write_json
from revenue_lab.site import build
from capture_presentation import CONTRAST, Quiet

CASES={'economics-integration':['decision','cost','sensitivity','execution'],
       'warehouse-verification':['native','local','guard','boundary']}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,default=ROOT/'docs/evidence/integration-economics/browser.json')
    parser.add_argument('--images',type=Path,default=ROOT/'docs/images/integration-economics')
    args=parser.parse_args()
    if args.output.exists() or args.images.exists():
        raise FileExistsError('Use fresh paths; historical captures are immutable')
    build();args.images.mkdir(parents=True)
    axe=ROOT/'tests/assurance_vendor/axe.min.js'
    axe_sha=hashlib.sha256(axe.read_bytes()).hexdigest()
    assert axe_sha=='880970c081707360e64f34cea25ff91892f5bc95675b0776925b9709dd8a68bb'
    class Pages(Quiet):
        def translate_path(self,path):
            prefix='/enterprise-revenue-systems-lab/'
            return super().translate_path(path.removeprefix(prefix) if path.startswith(prefix) else '/not-found')
    server=ThreadingHTTPServer(('127.0.0.1',0),functools.partial(Pages,directory=str(ROOT/'dist')))
    thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
    base=f'http://127.0.0.1:{server.server_port}/enterprise-revenue-systems-lab/'
    errors,writes,outside,layouts,accessibility,images,catalog_checks,interactions=[],[],[],[],[],{},[],[]
    try:
        with sync_playwright() as pw:
            browser=pw.chromium.launch();page=browser.new_page(viewport={'width':1440,'height':1100},reduced_motion='reduce')
            page.on('pageerror',lambda e:errors.append(str(e)))
            page.on('request',lambda r:writes.append(r.url) if r.method!='GET' else None)
            page.on('request',lambda r:outside.append(r.url) if not r.url.startswith(base) else None)
            catalog=json.loads((ROOT/'web/catalog.json').read_bytes())['scenarios']
            # Every old route and both additions render, validate, and retain static downloads.
            for row in catalog:
                page.goto(base+'?case='+row['id']);page.get_by_role('button',name='Validate artifact integrity').click()
                page.locator('#status').filter(has_text='Artifact integrity verified').wait_for()
                assert page.locator('#panel').inner_text().strip()
                assert page.locator('#download').get_attribute('href')=='evidence/'+row['id']+'/reproduction.zip'
                assert page.locator('#fresh').is_hidden()
                for width in (1440,320):
                    page.set_viewport_size({'width':width,'height':1000})
                    for tab in ['Decision & outcome','Source records','Evidence timeline','Compare & verify']:
                        page.get_by_role('tab',name=tab,exact=True).click()
                        assert page.locator('#panel').inner_text().strip()
                        catalog_checks.append(dict(case=row['id'],width=width,tab=tab,overflow=page.evaluate('document.documentElement.scrollWidth>innerWidth')))
            for case,stages in CASES.items():
                page.goto(base+'?case='+case);page.locator('.release-investigation').wait_for()
                page.add_script_tag(content=axe.read_text(encoding='utf8'))
                for width in (1440,1024,768,390,320):
                    page.set_viewport_size({'width':width,'height':1100 if width>768 else 900})
                    for stage in stages:
                        page.locator('[data-evidence-stage="'+stage+'"]').click()
                        layouts.append(dict(case=case,width=width,stage=stage,overflow=page.evaluate('document.documentElement.scrollWidth>innerWidth'),contrast=page.evaluate(CONTRAST)))
                        if width in (1440,390):
                            result=page.evaluate("async()=>{const r=await axe.run(document,{runOnly:{type:'tag',values:['wcag2a','wcag2aa','wcag21aa']}});return {violations:r.violations,incomplete:r.incomplete.map(x=>({id:x.id,impact:x.impact})),passes:r.passes.length}}")
                            accessibility.append(dict(case=case,width=width,stage=stage,**result))
                for width in (320,390):
                    page.set_viewport_size({'width':width,'height':1000})
                    if case=='economics-integration':
                        page.locator('[data-evidence-stage="execution"]').click()
                        options=page.locator('#economics-trial option').evaluate_all('(options)=>options.map(o=>o.value)')
                        selector='#economics-trial'
                    else:
                        page.locator('[data-evidence-stage="guard"]').click()
                        options=page.locator('#warehouse-fault option').evaluate_all('(options)=>options.map(o=>o.value)')
                        selector='#warehouse-fault'
                    for value in options:
                        page.locator(selector).select_option(value)
                        interactions.append(dict(case=case,width=width,selection=value,overflow=page.evaluate('document.documentElement.scrollWidth>innerWidth'),contrast=page.evaluate(CONTRAST)))
                captures=[(1440,1260,stages[0],'desktop'),(1440,1260,stages[2],'detail'),(390,1000,stages[0],'mobile')]
                if case=='economics-integration':captures.append((1440,1260,'execution','http'))
                for width,height,stage,suffix in captures:
                    page.set_viewport_size({'width':width,'height':height});page.locator('[data-evidence-stage="'+stage+'"]').click()
                    page.evaluate("scrollTo(0,document.querySelector('.release-hero').getBoundingClientRect().top+scrollY-20)")
                    name=case+'-'+suffix+'.png';page.screenshot(path=str(args.images/name))
                    images[name]=dict(width=width,height=height,case=case,stage=stage,capture='Unedited actual static application viewport')
            version=browser.version;browser.close()
    finally:
        server.shutdown();server.server_close();thread.join()
    paths=['web/app.js','web/index.html','web/assurance.css','web/style.css','web/economics.js','web/warehouse.js','web/evidence-ui.js','web/catalog.json','sources.lock.json','scripts/capture_integration.py']
    record=dict(captured_at=datetime.now(timezone.utc).isoformat(),browser='Chromium '+version,
                served='Actual dist at GitHub Pages subpath; no public deployment',
                source_sha256={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in paths},
                image_sha256={n:hashlib.sha256((args.images/n).read_bytes()).hexdigest() for n in images},images=images,
                catalog_checks=catalog_checks,layouts=layouts,interaction_layouts=interactions,accessibility=accessibility,axe_sha256=axe_sha,
                page_errors=errors,http_writes=writes,nonlocal_requests=outside,new_source_execution=False,new_native_execution=False)
    write_json(args.output,record)
    assert not errors and not writes and not outside
    assert all(not r['overflow'] for r in catalog_checks)
    assert all(not r['overflow'] and not r['contrast']['failures'] for r in layouts)
    assert all(not r['overflow'] and not r['contrast']['failures'] for r in interactions)
    assert all(not r['violations'] for r in accessibility)
    print(json.dumps(dict(status='passed',catalog_states=len(catalog_checks),layouts=len(layouts),interaction_layouts=len(interactions),accessibility_states=len(accessibility),screenshots=len(images))))


if __name__=='__main__':main()
