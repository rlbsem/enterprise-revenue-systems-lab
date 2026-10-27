"""Actual static acquisition interactions, read-only controls and download integrity."""
import json
from playwright.sync_api import sync_playwright
from revenue_lab.bundle import ROOT
from revenue_lab.smoke import check_zip
from test_browser import url

def test_acquisition_identity_admission_receipts_financial_versions_and_download(url,tmp_path):
 with sync_playwright() as p:
  browser=p.chromium.launch();page=browser.new_page(viewport={"width":1440,"height":1100});errors=[];writes=[]
  page.on("pageerror",lambda e:errors.append(str(e)));page.on("request",lambda r:writes.append(r.url) if r.method!="GET" else None)
  page.goto(url+"/?case=acquisition-governance");page.get_by_role("heading",name="Same customer number. Different legal identities.").wait_for()
  assert page.locator("[data-investigation]").count()==10
  page.get_by_role("button",name="Validate artifact integrity").click();page.locator("#status").filter(has_text="Artifact integrity verified").wait_for()
  for c in ["cedar","meridian","summit"]:page.get_by_label("Inspect an operating company").select_option(c)
  page.locator('[data-acquisition-stage="admission"]').focus();page.keyboard.press("Enter")
  page.get_by_role("heading",name="Readiness is a fresh computation, not a stored flag.",exact=True).wait_for()
  page.get_by_text("Mapping resnapshot: incomplete coverage refused, version 2 checked",exact=True).click()
  assert "reviewed_coverage_mismatch" in page.locator(".acquisition-investigation").inner_text()
  page.locator('[data-acquisition-stage="delivery"]').click()
  for v in ["receipt","recovery","authority","exhaustion"]:page.get_by_label("Inspect a recorded delivery control").select_option(v)
  page.locator('[data-acquisition-stage="finance"]').click()
  page.get_by_role("cell",name="$20,057,260.00",exact=True).wait_for()
  page.get_by_label("Choose a published version").select_option("original");page.get_by_role("cell",name="$20,012,260.00",exact=True).wait_for()
  page.get_by_label("Choose a separately executed financial scenario").select_option("selected");page.get_by_role("cell",name="$368,000.00",exact=True).wait_for()
  for n in ["fct_invoices","fct_allocations","intercompany_eliminations","reconciliation_variances","legal_entity_totals","portfolio_totals","restatement_bridge"]:
   page.get_by_label("Inspect a published financial rowset").select_option(n)
   summary=page.locator("summary").filter(has_text="published rows · "+n);summary.click();assert summary.locator("..").locator("pre").inner_text()
  page.locator('[data-acquisition-stage="history"]').click();assert "Original-cutoff replay equal" in page.locator(".acquisition-investigation").inner_text()
  page.locator('[data-acquisition-stage="proof"]').click();assert "62 passing tests" in page.locator(".acquisition-investigation").inner_text()
  page.get_by_text("fct_invoices.sql",exact=True).click()
  code=page.locator(".acquisition-investigation details[open] > pre").last
  assert code.get_attribute("tabindex")=="0"
  code.focus();page.keyboard.press("ArrowDown")
  with page.expect_download() as event:page.get_by_role("link",name="Download reproduction ZIP").click()
  target=tmp_path/"acquisition.zip";event.value.save_as(target);check_zip(target.read_bytes(),ROOT/"web/evidence/acquisition-governance")
  page.get_by_text("Validate a downloaded portable bundle",exact=True).click()
  with page.expect_download() as event:page.locator("#portable").click()
  target=tmp_path/"portable.json";event.value.save_as(target);assert "annual.json" in json.loads(target.read_bytes())["artifacts"]
  for tab in ["Source records","Evidence timeline","Compare & verify"]:
   page.get_by_role("tab",name=tab,exact=True).click();assert page.locator("#panel").inner_text().strip()
  page.get_by_role("tab",name="Decision & outcome",exact=True).click();page.set_viewport_size({"width":320,"height":844});assert not page.evaluate("document.documentElement.scrollWidth>innerWidth")
  page.locator('[data-acquisition-stage="finance"]').click()
  page.get_by_label("Choose a separately executed financial scenario").select_option("annual")
  page.get_by_label("Choose a published version").select_option("restated")
  bounds=page.get_by_role("cell",name="$20,057,260.00",exact=True).bounding_box()
  assert bounds["x"]>=0 and bounds["x"]+bounds["width"]<=320
  assert page.locator("#fresh").is_hidden() and not errors and not writes
  browser.close()

def test_acquisition_tampered_verification_refuses_render(url):
 with sync_playwright() as p:
  browser=p.chromium.launch();page=browser.new_page();page.route("**/acquisition-governance/verification.json",lambda r:r.fulfill(json={"integrity":"fabricated"}))
  page.goto(url+"/?case=acquisition-governance");page.locator("#status").filter(has_text="Verification record integrity mismatch").wait_for()
  assert page.locator(".acquisition-investigation").count()==0;browser.close()
