"""Genuine static browser controls, downloads, navigation and refusal."""
import pytest
from playwright.sync_api import sync_playwright
from revenue_lab.bundle import ROOT
from revenue_lab.smoke import check_zip
from test_browser import url


@pytest.mark.parametrize('case',['economics-integration','warehouse-verification'])
def test_new_cases_interactions_downloads_and_mobile(url,tmp_path,case):
    with sync_playwright() as p:
        browser=p.chromium.launch();page=browser.new_page(viewport={'width':1440,'height':1100})
        errors,writes=[],[]
        page.on('pageerror',lambda e:errors.append(str(e)))
        page.on('request',lambda r:writes.append(r.url) if r.method!='GET' else None)
        page.goto(url+'/?case='+case);page.locator('.release-investigation').wait_for()
        assert page.locator('[data-investigation]').count()==13
        page.get_by_role('button',name='Validate artifact integrity').click();page.locator('#status').filter(has_text='Artifact integrity verified').wait_for()
        if case=='economics-integration':
            page.get_by_label('Architecture',exact=True).select_option('resilient')
            page.locator('[data-evidence-stage="cost"]').click()
            page.get_by_label('Operating condition',exact=True).select_option('campaign-disruption')
            page.get_by_label('Inspect a workload',exact=True).select_option('web-events')
            assert '$' in page.locator('.release-detail').inner_text()
            page.locator('[data-evidence-stage="sensitivity"]').click();page.get_by_label('Sensitivity dimension').select_option('quota_percent')
            page.locator('[data-evidence-stage="execution"]').click();page.get_by_label('Inspect a recorded HTTP trial').select_option('revoked-permission')
            assert 'Rejected' in page.locator('.release-detail').inner_text()
        else:
            page.get_by_label('Inspect a native rowset').select_option('items')
            assert '4,828' in page.locator('.release-detail').inner_text()
            page.locator('[data-evidence-stage="local"]').click();assert 'ev06' in page.locator('.release-detail').inner_text()
            page.locator('[data-evidence-stage="guard"]').click();page.get_by_label('Inspect a regression fault').select_option('12')
            assert 'extra_future_event' in page.locator('.release-detail').inner_text()
            page.locator('[data-evidence-stage="boundary"]').click();assert 'MERGE' in page.locator('.release-detail').inner_text()
        with page.expect_download() as download:page.get_by_role('link',name='Download reproduction ZIP').click()
        target=tmp_path/'bundle.zip';download.value.save_as(target);check_zip(target.read_bytes(),ROOT/'web/evidence'/case)
        for tab in ['Source records','Evidence timeline','Compare & verify']:
            page.get_by_role('tab',name=tab,exact=True).click();assert page.locator('#panel').inner_text().strip()
        page.get_by_role('tab',name='Decision & outcome',exact=True).click()
        # Linux falls back to Arial/Liberation Sans; Segoe UI hid a 1px metric-grid overflow locally.
        page.add_style_tag(content='body { font-family: Arial, sans-serif !important; }')
        page.set_viewport_size({'width':320,'height':900})
        assert not page.evaluate('document.documentElement.scrollWidth>innerWidth')
        assert page.locator('#fresh').is_hidden() and not errors and not writes
        browser.close()


@pytest.mark.parametrize('case',['economics-integration','warehouse-verification'])
def test_new_cases_tampered_verification_refused(url,case):
    with sync_playwright() as p:
        browser=p.chromium.launch();page=browser.new_page()
        page.route('**/'+case+'/verification.json',lambda r:r.fulfill(json={'integrity':'fabricated'}))
        page.goto(url+'/?case='+case);page.locator('#status').filter(has_text='Verification record integrity mismatch').wait_for()
        assert page.locator('.release-investigation').count()==0
        browser.close()
