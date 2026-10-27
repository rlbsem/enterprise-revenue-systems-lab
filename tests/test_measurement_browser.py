"""Real read-only browser interactions and integrity refusal."""
import json
from playwright.sync_api import sync_playwright
from revenue_lab.bundle import ROOT
from revenue_lab.smoke import check_zip
from test_browser import url

def test_measurement_project_receipt_sql_models_downloads_and_mobile(url,tmp_path):
 with sync_playwright() as p:
  browser=p.chromium.launch();page=browser.new_page(viewport={"width":1440,"height":1100});errors=[];writes=[]
  page.on("pageerror",lambda e:errors.append(str(e)))
  page.on("request",lambda r:writes.append(r.url) if r.method!="GET" else None)
  page.goto(url+"/?case=measurement-integrity");page.get_by_role("heading",name="Which number should the business trust?").wait_for()
  assert page.locator("[data-investigation]").count()==12
  page.get_by_role("button",name="Validate artifact integrity").click();page.locator("#status").filter(has_text="Artifact integrity verified").wait_for()
  page.get_by_label("Choose a synthetic project").select_option("SYN-P01");page.get_by_text("Missing $13,000 conversion",exact=True).wait_for()
  page.get_by_label("Choose a synthetic project").select_option("SYN-P03");page.get_by_text("Deposit overstated by $171,500",exact=True).wait_for()
  page.locator('[data-measurement-stage="journey"]').focus();page.keyboard.press("Enter")
  page.get_by_label("Filter recorded collection status").select_option("duplicate_event")
  assert page.locator(".measurement-investigation tbody tr").count()==1
  page.locator(".measurement-investigation details summary").first.click()
  assert "admitted_content" in page.locator(".measurement-investigation details").first.inner_text()
  page.locator('[data-measurement-stage="warehouse"]').click()
  for model in ["fct_ga4_events","fct_ga4_items","mart_ga4_purchase_quality","mart_ga4_sessions","mart_ga4_daily"]:
   page.get_by_label("Inspect a governed GA4 model").select_option(model)
   summary=page.locator("summary").filter(has_text="executed rows · "+model);summary.click()
   assert 'event_' in summary.locator("..").inner_text()
  page.locator('[data-measurement-stage="native"]').click()
  assert "57" in page.locator(".measurement-investigation").inner_text()
  assert "job_EgSHl_of2fLqQeIIjpuktW4Bk8AM" in page.locator(".measurement-investigation").inner_text()
  for a in page.locator(".measurement-investigation a").all():
   assert "/88a197c761cfd167c19e3d23039948ffe6bb7f2b/" in a.get_attribute("href")
  with page.expect_download() as event:page.get_by_role("link",name="Download reproduction ZIP").click()
  target=tmp_path/"measurement.zip";event.value.save_as(target);check_zip(target.read_bytes(),ROOT/"web/evidence/measurement-integrity")
  page.get_by_text("Validate a downloaded portable bundle",exact=True).click()
  with page.expect_download() as event:page.locator("#portable").click()
  target=tmp_path/"portable.json";event.value.save_as(target);portable=json.loads(target.read_bytes());assert "ledger.json" in portable["artifacts"]
  for tab in ["Source records","Evidence timeline","Compare & verify"]:
   page.get_by_role("tab",name=tab,exact=True).click();assert page.locator("#panel").inner_text().strip()
  page.set_viewport_size({"width":390,"height":844});page.get_by_role("tab",name="Decision & outcome",exact=True).click()
  assert not page.evaluate("document.documentElement.scrollWidth>innerWidth")
  assert page.locator("#fresh").is_hidden() and not errors and not writes
  browser.close()

def test_measurement_tampered_record_refuses_render(url):
 with sync_playwright() as p:
  browser=p.chromium.launch();page=browser.new_page()
  page.route("**/measurement-integrity/verification.json",lambda r:r.fulfill(json={"integrity":"fabricated"}))
  page.goto(url+"/?case=measurement-integrity");page.locator("#status").filter(has_text="Verification record integrity mismatch").wait_for()
  assert page.locator(".measurement-investigation").count()==0
  browser.close()
