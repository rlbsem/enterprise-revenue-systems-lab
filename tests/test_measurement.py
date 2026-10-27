"""Finite evidence contracts, independent arithmetic and immutable history."""
import copy
import hashlib
import json
import re
import shutil
import pytest
from revenue_lab.bundle import ROOT, load_verified, verify, write_json, canonical
from revenue_lab.measurement_checks import measurement, project, MODELS

BUNDLE=ROOT/"web/evidence/measurement-integrity"
def files():return load_verified(BUNDLE)[1]

def test_measurement_independently_reconciles_source_financials():
 f=files();r=measurement(f)
 assert r["financial_findings"]==3 and r["source_facts"]==25
 assert project(f)["totals"]==f["demo.json"]["commercial"]
 assert sum(r["value_cents"] for r in f["ledger.json"]["source_facts"] if r["stage"]=="payment")==14350000
 assert sorted(r["delta_cents"] for r in f["projection.json"]["findings"])==[-24500000,-1300000,17150000]

@pytest.mark.parametrize("mutation",["display","source_money","reconciliation","event_hash","authority","receipt","independent","native_count","native_sql","native_job","parity","correction","anomaly","fresh_row","fresh_pin","fresh_input","fresh_anomaly","new_native"])
def test_measurement_rejects_changed_evidence_contract(mutation):
 f=copy.deepcopy(files())
 if mutation=="display":f["projection.json"]["totals"]["payment_cents"]+=1
 elif mutation=="source_money":f["ledger.json"]["source_facts"][1]["value_cents"]+=1
 elif mutation=="reconciliation":f["demo.json"]["final"]["models"]["mart_reconciliation"][0]["delta_cents"]=1
 elif mutation=="event_hash":f["ledger.json"]["events"][0]["hash"]="0"*64
 elif mutation=="authority":
  event=f["ledger.json"]["events"][0];event["payload"]["value_basis"]="payment";event["hash"]=hashlib.sha256(canonical(event["payload"]).encode()).hexdigest()
 elif mutation=="receipt":f["ledger.json"]["decisions"][0]["event_id"]="missing"
 elif mutation=="independent":f["demo.json"]["independent"]["models"]["fct_events"].pop()
 elif mutation=="native_count":f["native.json"]["findings"]["purchase_events"]=57
 elif mutation=="native_sql":f["sql/event_health.sql"]+="-- changed"
 elif mutation=="native_job":f["native.json"]["queries"]["event_health"]["job"]["state"]="RUNNING"
 elif mutation=="parity":f["local-warehouse.json"]["controls"]["incremental_equals_independent_full_refresh"]=False
 elif mutation=="correction":f["local-warehouse.json"]["controls"]["corrected_purchase_revenue_cents"]=12000
 elif mutation=="anomaly":f["local-warehouse.json"]["phases"][-1]["item_revenue_discrepancies"]=0
 elif mutation=="fresh_row":f["fixture-execution.json"]["models"]["fct_ga4_events"]["rows"].pop()
 elif mutation=="fresh_pin":f["fixture-execution.json"]["source_revision"]="0"*40
 elif mutation=="fresh_input":f["fixture-execution.json"]["source_input_sha256"].pop("ga4-verifier.py")
 elif mutation=="fresh_anomaly":f["fixture-execution.json"]["models"]["mart_ga4_purchase_quality"]["rows"][0]["revenue_finding"]=1
 elif mutation=="new_native":f["observation.json"]["new_native_execution"]=True
 with pytest.raises(ValueError):measurement(f)

def test_original_bytes_cannot_be_resealed_away(tmp_path):
 p=tmp_path/"bundle";shutil.copytree(BUNDLE,p)
 name="ledger.json";raw=(p/name).read_bytes()+b" ";(p/name).write_bytes(raw)
 m=json.loads((p/"bundle.json").read_bytes());a=next(a for a in m["artifacts"] if a["path"]==name);a.update(sha256=hashlib.sha256(raw).hexdigest(),bytes=len(raw));m["input_hashes"][name]=a["sha256"];write_json(p/"bundle.json",m)
 with pytest.raises(ValueError,match="original measurement bytes differ"):verify(p)

def test_all_eight_prior_investigations_and_artifacts_are_unchanged():
 baseline=json.loads((ROOT/"docs/evidence/measurement-integrity/prior-ui.json").read_bytes())["files"]
 before=json.loads(baseline["web/catalog.json"])["scenarios"];after=json.loads((ROOT/"web/catalog.json").read_bytes())["scenarios"]
 assert all(r in after for r in before) and len(after)==len(before)+1
 old=json.loads(baseline["sources.lock.json"]);now=json.loads((ROOT/"sources.lock.json").read_bytes())
 assert all(now[k]==v for k,v in old.items() if k!="sources")
 assert all(now["sources"][k]==v for k,v in old["sources"].items())
 for n,h in json.loads((ROOT/"docs/evidence/measurement-integrity/preserved-files.json").read_bytes())["sha256"].items():
  assert hashlib.sha256((ROOT/n).read_bytes()).hexdigest()==h,n

def test_five_fresh_rowsets_match_independent_full_and_preserve_findings():
 f=files();local=f["fixture-execution.json"]
 assert set(local["models"])==set(MODELS)
 assert all(local["models"][n]["rows"]==local["independent_full_rowsets"][n] for n in MODELS)
 assert local["report"]["rowset_comparison"]["same_batch_replay_unchanged"]
 assert not local["new_native_execution"]

def test_measurement_static_surface_and_public_artifacts_have_no_secrets():
 code=(ROOT/"web/measurement.js").read_text(encoding="utf8")
 assert not re.search(r"\b(fetch|XMLHttpRequest|WebSocket|sendBeacon)\b",code)
 for p in BUNDLE.rglob("*"):
  if not p.is_file() or p.suffix==".zip":continue
  text=p.read_bytes().decode()
  assert not re.search(r'"(?:password|access_token|private_key|api_secret)"\s*:',text)
  assert not re.search(r"-----BEGIN (?:RSA )?PRIVATE KEY|(?:AKIA|ASIA)[A-Z0-9]{16}",text)

def test_measurement_screenshot_provenance():
 r=json.loads((ROOT/"docs/evidence/measurement-integrity/browser.json").read_bytes())
 assert len(r["layouts"])==40 and len(r["accessibility"])==10
 assert not r["http_writes"] and not r["nonlocal_requests"] and not r["page_errors"]
 assert all(not x["overflow"] and not x["contrast"]["failures"] for x in r["layouts"])
 assert all(not x["violations"] for x in r["accessibility"])
 for n,h in r["source_sha256"].items():assert hashlib.sha256((ROOT/n).read_bytes()).hexdigest()==h,n
 for n,h in r["image_sha256"].items():assert hashlib.sha256((ROOT/"docs/images/measurement-integrity"/n).read_bytes()).hexdigest()==h,n


def test_fresh_rowsets_are_checked_against_csv_even_if_both_records_change():
 f=copy.deepcopy(files());local=f["fixture-execution.json"]
 local["models"]["fct_ga4_events"]["rows"][0]["revenue_cents"]=999
 local["independent_full_rowsets"]["fct_ga4_events"][0]["revenue_cents"]=999
 with pytest.raises(ValueError,match="independent CSV oracle"):measurement(f)


def test_local_runner_refuses_to_reuse_workspace(tmp_path):
 import subprocess
 import sys
 p=subprocess.run([sys.executable,str(ROOT/"scripts/execute_measurement_fixture.py"),"--workspace",str(tmp_path)],capture_output=True,text=True)
 assert p.returncode!=0 and "FileExistsError" in p.stderr
 assert not list(tmp_path.iterdir())
