"""Pinned acquisition evidence, integer financial truth and preservation gates."""
import copy
import hashlib
import json
import re
import shutil
import pytest
from revenue_lab.bundle import ROOT, load_verified, verify, write_json
from revenue_lab.acquisition_checks import acquisition, recalculate

BUNDLE=ROOT/"web/evidence/acquisition-governance"
def files():return load_verified(BUNDLE)[1]

def test_both_separate_financial_scenarios_recompute_every_published_rowset():
 f=files();r=acquisition(f)
 assert r["oracle_rowsets_compared"]==28 and r["receiver_effects"]==1
 for name in ["selected-period.json","annual.json"]:
  for version in ["original","restated"]:
   actual=recalculate(f[name],version)
   assert len(actual)==7
 assert f["projection.json"]["annual"]["original"]["consolidated_invoice_minor"]==2001226000
 assert f["projection.json"]["annual"]["restated"]["consolidated_invoice_minor"]==2005726000
 assert f["projection.json"]["annual"]["restated"]["allocated_cash_minor"]==1560958560

@pytest.mark.parametrize("mutation",["display","entity","identity","source","frozen","cutoff","policy","row","total","finding","blocked","dbt","compare","admission","coverage","intent","receipt","receiver","authority","exhaustion","software","browser","fresh","native"])
def test_rejects_corrupt_or_misrepresented_acquisition_evidence(mutation):
 f=copy.deepcopy(files());d=f["annual.json"];g=f["governance.json"]
 if mutation=="display":f["projection.json"]["annual"]["restated"]["consolidated_invoice_minor"]+=1
 elif mutation=="entity":f["demo.json"]["portfolio"]["companies"][1]["legal_entity"]=f["demo.json"]["portfolio"]["companies"][0]["legal_entity"]
 elif mutation=="identity":f["demo.json"]["portfolio"]["companies"][1]["source_records"][0]["canonical"]="merged"
 elif mutation=="source":d["source_events"][0]["body"]["amount_minor"]+=1
 elif mutation=="frozen":d["records"]["financial_inputs"].pop(0)
 elif mutation=="cutoff":d["records"]["financial_snapshots"][0]["cutoff"]="2000-01-01T00:00:00+00:00"
 elif mutation=="policy":d["records"]["financial_policies"][0]["hash"]="0"*64
 elif mutation=="row":d["original"]["results"]["fct_invoices"][0]["net_minor"]+=1
 elif mutation=="total":d["totals_before"]["allocated_cash_minor"]+=1
 elif mutation=="finding":d["original"]["results"]["reconciliation_variances"].pop()
 elif mutation=="blocked":d["blocked_candidate"]["published"]=True
 elif mutation=="dbt":d["original"]["dbt"]["return_code"]=1
 elif mutation=="compare":d["original"]["comparisons"][0]["row_differences"]=1
 elif mutation=="admission":g["C_resnapshot"]["final_gate"]["passed"]=False
 elif mutation=="coverage":g["C_resnapshot"]["incomplete_rejected"]["detail"]="ignored"
 elif mutation=="intent":g["control"]["outbound"][0]["payload"]["legal_entity"]="other"
 elif mutation=="receipt":g["receiver"]["effects"][0]["receipt"]["payload_hash"]="0"*64
 elif mutation=="receiver":g["receiver"]["records"][0]["body"]["company"]="other"
 elif mutation=="authority":f["historical-authority.json"]["new_plan_status"]=200
 elif mutation=="exhaustion":f["exhaustion.json"]["observed"]["attempts"]=4
 elif mutation=="software":f["software.json"]["cases"][0]["outcome"]="failed"
 elif mutation=="browser":f["browser.json"]["checks"][0]["passed"]=False
 elif mutation=="fresh":f["source-regression.json"]["native_vendor_calls"]=1
 elif mutation=="native":f["observation.json"]["new_native_execution"]=True
 with pytest.raises((ValueError,KeyError)):acquisition(f)

def test_resealed_original_bytes_still_refused(tmp_path):
 p=tmp_path/"bundle";shutil.copytree(BUNDLE,p);name="annual.json";raw=(p/name).read_bytes()+b" "
 (p/name).write_bytes(raw);m=json.loads((p/"bundle.json").read_bytes());a=next(a for a in m["artifacts"] if a["path"]==name);a.update(bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest());m["input_hashes"][name]=a["sha256"];write_json(p/"bundle.json",m)
 with pytest.raises(ValueError,match="original acquisition bytes differ"):verify(p)

def test_all_nine_prior_investigations_and_historical_bytes_are_preserved():
 snap=json.loads((ROOT/"docs/evidence/acquisition-governance/prior-ui.json").read_bytes())["files"]
 before=json.loads(snap["web/catalog.json"])["scenarios"];after=json.loads((ROOT/"web/catalog.json").read_bytes())["scenarios"]
 assert all(r in after for r in before) and len(after)==len(before)+1
 assert {r["id"] for r in after}-{r["id"] for r in before}=={"acquisition-governance"}
 old=json.loads(snap["sources.lock.json"]);current=json.loads((ROOT/"sources.lock.json").read_bytes())
 assert all(current[k]==v for k,v in old.items() if k!="sources")
 assert all(current["sources"][k]==v for k,v in old["sources"].items())
 hashes=json.loads((ROOT/"docs/evidence/acquisition-governance/preserved-files.json").read_bytes())["sha256"]
 for n,h in hashes.items():assert hashlib.sha256((ROOT/n).read_bytes()).hexdigest()==h,n

def test_acquisition_static_interface_and_records_do_not_expose_secrets():
 code=(ROOT/"web/acquisition.js").read_text(encoding="utf8")
 assert not re.search(r"\b(fetch|XMLHttpRequest|WebSocket|sendBeacon)\b",code)
 for p in BUNDLE.rglob("*"):
  if not p.is_file() or p.suffix==".zip":continue
  text=p.read_bytes().decode()
  assert not re.search(r'"(?:password|access_token|private_key|api_secret|dsn)"\s*:',text)
  assert not re.search(r"-----BEGIN (?:RSA )?PRIVATE KEY|(?:AKIA|ASIA)[A-Z0-9]{16}",text)

def test_acquisition_genuine_screenshots_and_accessibility_provenance():
 r=json.loads((ROOT/"docs/evidence/acquisition-governance/browser.json").read_bytes())
 assert len(r["layouts"])==45 and len(r["accessibility"])==12
 assert not r["http_writes"] and not r["nonlocal_requests"] and not r["page_errors"]
 assert all(not x["overflow"] and not x["contrast"]["failures"] for x in r["layouts"])
 assert all(not x["violations"] for x in r["accessibility"])
 for n,h in r["source_sha256"].items():assert hashlib.sha256((ROOT/n).read_bytes()).hexdigest()==h,n
 for n,h in r["image_sha256"].items():assert hashlib.sha256((ROOT/"docs/images/acquisition-governance"/n).read_bytes()).hexdigest()==h,n
