"""Offline checks of pinned acquisition records; no privileged action or database writes."""
from datetime import datetime
import hashlib
from .bundle import ROOT, LOCK, canonical
from .gtm_checks import require
from .acquisition_oracle import calculate

def verify_original_bytes(path,up):
 for a in up["artifacts"]:
  require(hashlib.sha256((path/a["file"]).read_bytes()).hexdigest()==a["sha256"],"original acquisition bytes differ")

def sha(value):return hashlib.sha256(canonical(value).encode()).hexdigest()
def rows_equal(a,b):return sorted(map(canonical,a))==sorted(map(canonical,b))

def recalculate(data,version):
 snapshots={r["id"]:r for r in data["records"]["financial_snapshots"]};snap=snapshots[version]
 policies={r["version"]:r for r in data["records"]["financial_policies"]};policy=policies[snap["policy_version"]]
 require(sha(policy["body"])==policy["hash"],"financial policy hash differs")
 selected={}
 for event in data["source_events"]:
  b=event["body"];require(sha(b)==event["hash"],"financial source content differs")
  if event["status"]!="accepted" or datetime.fromisoformat(b["observed_at"])>datetime.fromisoformat(snap["cutoff"]):continue
  key=b["company"],b["kind"],b["source_id"]
  if key not in selected or b["revision"]>selected[key]["body"]["revision"]:selected[key]=event
 frozen=[r for r in data["records"]["financial_inputs"] if r["report_id"]==version]
 require(len(frozen)==len(selected) and {r["event_id"] for r in frozen}=={e["id"] for e in selected.values()},"frozen source coverage differs")
 events={e["id"]:e for e in selected.values()}
 require(all(r["body"]==events[r["event_id"]]["body"] and r["hash"]==events[r["event_id"]]["hash"] for r in frozen),"frozen source lineage differs")
 previous=recalculate(data,snap["previous_id"])["portfolio_totals"] if snap["previous_id"] else None
 return calculate(frozen,snap["control"],policy["body"],previous)

def project(files):
 def financial(d):
  return {"original":{k:sum(r[k] for r in d["original"]["results"]["portfolio_totals"]) for k in d["totals_before"]},"restated":{k:sum(r[k] for r in d["restated"]["results"]["portfolio_totals"]) for k in d["totals_after"]},"findings":d["original"]["results"]["reconciliation_variances"]}
 return {"currency":"USD","companies":files["demo.json"]["portfolio"]["companies"],"selected":financial(files["selected-period.json"]),"annual":financial(files["annual.json"]),"delivery":files["governance.json"]["D_E_delivery"]}

def acquisition(files):
 require(files["upstream.json"]==LOCK["acquisition_import"],"acquisition provenance mismatch")
 p=project(files);require(p==files["projection.json"],"acquisition projection mismatch")
 require((ROOT/"src/revenue_lab/acquisition_oracle.py").read_bytes()==files["financial-oracle.py"].encode(),"pinned independent oracle implementation differs")
 companies=p["companies"];require({r["id"] for r in companies}=={"cedar","meridian","summit"},"company scope differs")
 require(len({r["legal_entity"] for r in companies})==3,"legal entities collapsed")
 accounts=[]
 for c in companies:
  identities={r["canonical"] for r in c["source_records"]};require(len(identities)==1,"within-company mapping differs")
  accounts.append(next(iter(identities)))
  require(all(r["source_id"]=="100" for r in c["source_records"]),"local identifier example differs")
 require(len(set(accounts))==3,"same local IDs merged across entities")
 require({c["id"] for c in companies if c["included"]}=={"cedar","meridian"},"initial admission boundary differs")
 for lane,key,expected in [("selected","selected-period.json",(36800000,38800000,23000000,500000,800000)),("annual","annual.json",(2001226000,2005726000,1560958560,2500000,4000000))]:
  d=files[key];require(d["synthetic"] and d["currency"]=="USD" and d["native_vendor_calls"]==0,"financial execution boundary differs")
  for version,label in [("original","totals_before"),("restated","totals_after")]:
   computed=recalculate(d,version);observed=d[version]
   require(set(computed)==set(observed["results"]),"financial model set differs")
   require(all(rows_equal(rows,observed["results"][name]) for name,rows in computed.items()),"financial source-to-model oracle differs")
   require(p[lane][version]==d[label] and all(type(v) is int for v in d[label].values()),"financial integer totals differ")
   nodes=observed["dbt"]["results"]
   require(observed["dbt"]["return_code"]==0 and len(nodes)==18 and sum(n["id"].startswith("model.") for n in nodes)==9 and all(n["status"] in ["success","pass"] for n in nodes),"dbt publication gates differ")
   require(len(observed["comparisons"])==7 and all(r["row_differences"]==0 and r["exact_content_match"] and r["sha256"]==r["observed_sha256"] for r in observed["comparisons"]),"recorded oracle comparison differs")
  require(p[lane]["original"]["consolidated_invoice_minor"]==expected[0] and p[lane]["restated"]["consolidated_invoice_minor"]==expected[1] and p[lane]["original"]["allocated_cash_minor"]==p[lane]["restated"]["allocated_cash_minor"]==expected[2],"scenario totals changed")
  require({(r["code"],r["amount_minor"]) for r in p[lane]["findings"]}=={("erp_posting_difference",expected[3]),("intercompany_unresolved",expected[4])},"financial findings hidden")
  require(d["original_report_unchanged"] and d["original_cutoff_replay_equal"] and recalculate(d,"original-cutoff-replay")==recalculate(d,"original"),"historical cutoff changed")
  require(not d["blocked_candidate"]["published"] and d["blocked_candidate"]["dbt"]["return_code"]!=0 and any(n["status"]=="fail" for n in d["blocked_candidate"]["dbt"]["results"]),"invalid candidate published")
 annual=files["annual.json"]
 require(len(annual["periods"])==12 and annual["rejected_held_crm_bookings"]==12,"annual scenario scope differs")
 for version in ["original","restated"]:
  invoices=annual[version]["results"]["fct_invoices"]
  require(not any(r["company"]=="summit" or (r["company"]=="meridian" and r["period"]=="2026-01-01") for r in invoices),"reporting exclusions bypassed")
 g=files["governance.json"]
 require(not g["A_identity"]["before_passed"] and g["A_identity"]["after_passed"] and g["C_resnapshot"]["final_gate"]["passed"] and g["C_resnapshot"]["final_gate"]["mapping_version"]==2,"reviewed admission progression differs")
 require(g["C_resnapshot"]["incomplete_rejected"]["detail"]=="reviewed_coverage_mismatch","coverage rejection hidden")
 require(g["D_E_delivery"]["uncertain"]=="uncertain" and g["D_E_delivery"]["recovered"]=="confirmed" and g["D_E_delivery"]["final_effects"]==1 and g["D_E_delivery"]["duplicate_plan"],"receipt recovery differs")
 require(len(g["receiver"]["effects"])==len(g["receiver"]["records"])==len(g["control"]["outbound"])==1,"receiver effect duplicated")
 e=g["receiver"]["effects"][0];o=g["control"]["outbound"][0];receipt=e["receipt"];record=g["receiver"]["records"][0]
 require(o["payload"]==e["payload"]==receipt["payload"] and o["hash"]==e["hash"]==receipt["payload_hash"]==sha(e["payload"]),"frozen intent receipt differs")
 require(record["body"]==receipt["record"] and receipt["record_hash"]==sha(record["body"]),"independent receiver record differs")
 for name in ["authorization-admission.json","authorization-business.json","authorization-mapping.json","authorization-source_revision.json","exhaustion.json"]:
  d=files[name];require(d["expected"]==d["observed"],"authorization or exhaustion check differs")
 require(files["exhaustion.json"]["observed"]==dict(state="exhausted",attempts=3,effects=0),"retry bound changed")
 h=files["historical-authority.json"];require(h["historical_readback"]=="confirmed" and h["new_plan_status"]==409 and h["current_admission"]=="held","historical receipt authorizes new intent")
 require(files["process-death.json"]["actual_process_terminated"] and files["process-death.json"]["confirmed_after_restart"],"process termination test missing")
 s=files["software.json"];require(s["tests"]==len(s["cases"])==62 and all(t["outcome"]=="passed" for t in s["cases"]) and s["failures"]==s["errors"]==0,"recorded regression gates differ")
 b=files["browser.json"];require(len(b["checks"])==53 and all(t["passed"] and t["expected"]==t["observed"] for t in b["checks"]),"recorded browser checks differ")
 require(files["independent-financial.json"]["differences"]==0 and files["independent-financial.json"]["one_cent_publication_mutation_detected"],"adversarial financial check differs")
 fresh=files["source-regression.json"]
 require(fresh["source_revision"]==files["upstream.json"]["import_revision"] and fresh["tests"]==len(fresh["cases"])==83 and fresh["failures"]==fresh["errors"]==fresh["skipped"]==0 and all(t["status"]=="passed" for t in fresh["cases"]) and fresh["native_vendor_calls"]==0 and not fresh["cloud_resources"],"fresh source regression differs")
 require(not files["observation.json"]["new_native_execution"],"new native execution claimed")
 return {"companies":3,"local_id":100,"separate_financial_scenarios":2,"models_per_build":9,"oracle_rowsets_compared":28,"recorded_software_tests":62,"recorded_browser_checks":53,"receiver_effects":1,"new_native_execution":False}
