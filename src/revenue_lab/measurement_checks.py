"""Offline record verification, not a tracking collector or warehouse engine."""
import csv
import io
import hashlib
from collections import Counter, defaultdict
from .bundle import LOCK, canonical
from .gtm_checks import require
def verify_original_bytes(path, upstream):
 for a in upstream["artifacts"]:
  require(hashlib.sha256((path/a["file"]).read_bytes()).hexdigest()==a["sha256"],"original measurement bytes differ")

MODELS = ["fct_ga4_events", "fct_ga4_items", "mart_ga4_purchase_quality", "mart_ga4_sessions", "mart_ga4_daily"]

def warehouse_oracle(files):
 """Small independent CSV-to-rowset oracle; no SQL or imported source execution."""
 events={}
 for r in csv.DictReader(io.StringIO(files["ga4_pipeline/seeds/raw_ga4_events.csv"])):
  for k in ["arrival_batch","source_version","revenue_cents"]:r[k]=int(r[k])
  for k in ["transaction_id","user_pseudo_id","session_id"]:r[k]=r[k] or None
  old=events.get(r["event_key"])
  if r["arrival_batch"]<=2 and (old is None or (r["source_version"],r["arrival_batch"])>(old["source_version"],old["arrival_batch"])):events[r["event_key"]]=r
 items=[]
 for row in csv.DictReader(io.StringIO(files["ga4_pipeline/seeds/raw_ga4_items.csv"])):
  e=events.get(row["event_key"])
  if not e or int(row["source_version"])!=e["source_version"]:continue
  r={k:int(v) if k in ["source_version","item_index","price_cents","quantity"] else v for k,v in row.items()}
  r.update(extended_cents=r["price_cents"]*r["quantity"],event_date=e["event_date"]);items.append(r)
 purchases=[r for r in events.values() if r["event_name"]=="purchase"];transactions=Counter(r["transaction_id"] for r in purchases);quality=[]
 for e in purchases:
  subset=[r for r in items if r["event_key"]==e["event_key"]];total=sum(r["extended_cents"] for r in subset)
  quality.append({k:e[k] for k in ["event_key","event_date","arrival_batch","transaction_id","user_pseudo_id","session_id","revenue_cents"]}|dict(item_rows=len(subset),item_value_cents=total,revenue_variance_cents=e["revenue_cents"]-total,transaction_id_finding=int(not e["transaction_id"] or transactions[e["transaction_id"]]>1),identity_finding=int(not e["user_pseudo_id"] or not e["session_id"]),revenue_finding=int(not subset or abs(e["revenue_cents"]-total)>1)))
 groups=defaultdict(list)
 for e in events.values():
  if e["user_pseudo_id"] and e["session_id"]:groups[e["user_pseudo_id"],e["session_id"]].append(e)
 sessions=[dict(user_pseudo_id=k[0],session_id=k[1],first_event_date=min(e["event_date"] for e in v),last_event_date=max(e["event_date"] for e in v),event_count=len(v),purchase_events=sum(e["event_name"]=="purchase" for e in v)) for k,v in groups.items()]
 daily=[]
 for day in sorted({e["event_date"] for e in events.values()}):
  es=[e for e in events.values() if e["event_date"]==day];ps=[e for e in quality if e["event_date"]==day]
  daily.append(dict(event_date=day,event_count=len(es),purchase_events=len(ps),purchase_item_rows=sum(e["item_rows"] for e in ps),reported_revenue_cents=sum(e["revenue_cents"] for e in ps),item_value_cents=sum(e["item_value_cents"] for e in ps),transaction_id_findings=sum(e["transaction_id_finding"] for e in ps),revenue_findings=sum(e["revenue_finding"] for e in ps),identity_findings=sum(not e["user_pseudo_id"] or not e["session_id"] for e in es)))
 return dict(zip(MODELS,[list(events.values()),items,quality,sessions,daily]))

def project(files):
 ledger=files["ledger.json"];models=files["demo.json"]["final"]["models"]
 totals={"proposal_cents":sum(r["value_cents"] for r in ledger["source_facts"] if r["stage"]=="proposal"),
 "signed_contract_cents":sum(r["value_cents"] for r in ledger["source_facts"] if r["stage"]=="signed_contract"),
 "payment_cents":sum(r["value_cents"] for r in ledger["source_facts"] if r["stage"]=="payment")}
 for basis,label in [("contract","measured_contract_cents"),("payment","measured_payment_cents")]:
  totals[label]=sum(r["value_cents"] for r in models["fct_conversions"] if r["value_basis"]==basis)
 return {"currency":"USD","totals":totals,"projects":ledger["projects"],
 "findings":[r for r in models["mart_reconciliation"] if r["status"]!="matched"],
 "receipt_statuses":dict(Counter(r["status"] for r in ledger["decisions"])),
 "model_rows":{k:len(v) for k,v in models.items()},"warehouse_models":MODELS,
 "native":files["native.json"]["findings"]}

def measurement(files):
 require(files["upstream.json"]==LOCK["measurement_import"],"measurement provenance mismatch")
 p=project(files);require(p==files["projection.json"],"measurement display projection mismatch")
 require(p["totals"]==files["demo.json"]["commercial"],"commercial totals differ from source facts")
 require(p["totals"]==dict(proposal_cents=92000000,signed_contract_cents=43500000,payment_cents=14350000,measured_contract_cents=19000000,measured_payment_cents=30200000),"fixture economics changed")
 facts={r["source_ref"]:r for r in files["ledger.json"]["source_facts"]}
 conversions={r["source_ref"]:r for r in files["demo.json"]["final"]["models"]["fct_conversions"]}
 expected=[]
 stages={"inquiry":"generate_lead","qualified":"qualify_lead","working":"working_lead","signed_contract":"close_convert_lead","payment":"purchase","disqualified":"disqualify_lead"}
 for f in facts.values():
  if f["stage"] not in stages or not f["measurement_eligible"]:continue
  actual=conversions.get(f["source_ref"]);delta=(actual["value_cents"] if actual else 0)-f["value_cents"]
  expected.append((f["source_ref"],f["value_cents"],actual["value_cents"] if actual else None,delta,"missing" if not actual else "matched" if delta==0 else "value_mismatch"))
 recon=files["demo.json"]["final"]["models"]["mart_reconciliation"]
 require(sorted(expected)==sorted((r["source_ref"],r["expected_cents"],r["measured_cents"],r["delta_cents"],r["status"]) for r in recon),"source-to-conversion reconciliation differs")
 require(sorted(r["delta_cents"] for r in p["findings"])==[-24500000,-1300000,17150000],"unresolved findings hidden")
 demo=files["demo.json"]
 require(demo["equivalence"] is True and demo["final"]["models"]==demo["independent"]["models"],"recorded independent rowsets differ")
 ledger=files["ledger.json"];events={r["event_id"]:r for r in ledger["events"]}
 require(len(events)==len(ledger["events"])==19 and len(ledger["decisions"])==29,"fixture grain changed")
 for event in events.values():
  require(hashlib.sha256(canonical(event["payload"]).encode()).hexdigest()==event["hash"],"event content hash mismatch")
  require(event["payload"]["origin"]=="offline" or event["payload"]["value_basis"]=="unvalued","browser claimed monetary authority")
 for decision in ledger["decisions"]:
  if decision["detail"]=="see_admitted_event":require(decision["event_id"] in events,"receipt has no admitted identity")
 require(len({r["receipt"] for r in ledger["decisions"]})==29,"receipt identity duplicated")
 browser=files["browser.json"];software=files["software.json"]
 require(browser["status"]==software["status"]=="passed" and len(browser["checks"])==16,"recorded browser checks incomplete")
 require(software["python_tests"]==dict(tests=85,failures=0,errors=0,skipped=0) and software["dbt_models_each"]==9 and software["dbt_tests_each"]==21 and software["independent_model_equivalence"],"recorded software gates differ")
 native=files["native.json"]
 require(native["status"]=="executed" and p["native"]["purchase_events"]==14 and p["native"]["purchase_item_rows"]==57 and p["native"]["distinct_transaction_ids"]==13 and p["native"]["item_revenue_disagreements"]==2,"native observations changed")
 health=next(r for r in native["queries"]["event_health"]["rows"] if r["event_name"]=="purchase")
 grain=native["queries"]["purchase_grain"]["rows"][0]
 require(health["event_count"]==grain["purchase_events"]==14 and health["item_rows"]==57 and grain["distinct_transaction_ids"]==13 and grain["item_revenue_disagreements"]==2,"native query/findings disagree")
 for name,q in native["queries"].items():
  sql=files["sql/"+name+".sql"].replace("\r\n","\n")
  require(hashlib.sha256(sql.encode()).hexdigest()==q["source_sha256"],"native source SQL hash mismatch")
  require(hashlib.sha256(sql.replace("\n","\r\n").encode()).hexdigest()==q["executed_sql_sha256"],"native executed SQL hash mismatch")
  require(q["job"]["completed_without_error"] and q["job"]["state"]=="DONE" and q["job"]["job_id"],"native job incomplete")
 stats={r["job_id"]:r for r in files["job-statistics.json"]}
 require(set(stats)=={q["job"]["job_id"] for q in native["queries"].values()},"native metadata job set differs")
 for q in native["queries"].values():
  row=stats[q["job"]["job_id"]]
  require(row["sql_sha256"]==q["executed_sql_sha256"] and row["completed_without_error"]=="true","native independent metadata mismatch")
  for key in ["total_bytes_processed","total_bytes_billed","total_slot_ms"]:
   require(int(row[key])==q["job"][key],"native resource metadata mismatch")
 require(hashlib.sha256(files["sql/job-statistics.sql"].encode()).hexdigest()==native["metadata_capture"]["sql_sha256"],"metadata query hash mismatch")
 for name in ["baseline","final","independent"]:
  nodes=demo[name]["dbt_results"]
  require(sum(n["node"].startswith("model.") for n in nodes)==9 and sum(n["node"].startswith("test.") for n in nodes)==21 and all(n["status"] in ["success","pass"] for n in nodes),"conversion build gates failed")
 warehouse=files["local-warehouse.json"]
 require(warehouse["status"]=="passed_local_synthetic" and warehouse["controls"]["compared_models"]==MODELS,"local warehouse model coverage differs")
 require(warehouse["controls"]["incremental_equals_independent_full_refresh"] and warehouse["controls"]["same_batch_replay_unchanged"] and warehouse["controls"]["old_item_revision_removed"] and warehouse["controls"]["late_historical_event_present"],"local parity/correction failed")
 require(warehouse["controls"]["corrected_purchase_revenue_cents"]==13000 and warehouse["controls"]["corrected_purchase_source_version"]==2,"correction changed")
 require(warehouse["phases"][-1]["item_revenue_discrepancies"]==1 and warehouse["phases"][-1]["duplicate_transaction_event_rows"]==2,"warehouse anomalies hidden")
 require(not files["observation.json"]["new_native_execution"] and files["observation.json"]["new_source_execution"],"new execution claimed")
 local=files["fixture-execution.json"]
 require(local["lane"]=="fresh_local_synthetic_ga4_duckdb_dbt" and local["source_revision"]==files["upstream.json"]["import_revision"] and not local["new_native_execution"],"fresh local fixture provenance differs")
 inputs={a["file"]:a["sha256"] for a in files["upstream.json"]["artifacts"] if a["file"].startswith("ga4_pipeline/") or a["file"]=="ga4-verifier.py"}
 require(local["source_input_sha256"]==inputs,"fresh local fixture input hashes differ")
 require(set(local["models"])==set(MODELS)==set(local["independent_full_rowsets"]),"fresh model coverage differs")
 oracle=warehouse_oracle(files)
 for name,m in local["models"].items():
  require(sorted(map(canonical,m["rows"]))==sorted(map(canonical,oracle[name])),"fresh rowset differs from independent CSV oracle")
  require(m["rows"]==local["independent_full_rowsets"][name] and all(set(r)=={c[0] for c in m["columns"]} for r in m["rows"]),"fresh rowset/column comparison failed")
 report=local["report"]
 require(report["status"]=="passed" and report["native_bigquery"]=="not_executed" and report["rowset_comparison"]["incremental_equals_full_refresh"] and report["rowset_comparison"]["same_batch_replay_unchanged"],"fresh local gates failed")
 require([len(local["models"][n]["rows"]) for n in MODELS]==[10,8,7,6,5],"fresh fixture counts differ")
 ev={r["event_key"]:r for r in local["models"]["fct_ga4_events"]["rows"]}
 require(ev["ev03"]["source_version"]==2 and ev["ev03"]["revenue_cents"]==13000 and ev["ev06"]["event_date"]=="2026-09-26","fresh correction or late event lost")
 quality=local["models"]["mart_ga4_purchase_quality"]["rows"]
 require(sum(r["revenue_finding"] for r in quality)==1 and sum(r["transaction_id_finding"] for r in quality)==2,"fresh anomalies hidden")
 return {"source_facts":len(facts),"fixture_attempts":29,"distinct_events":19,"financial_findings":3,"conversion_models":9,"local_warehouse_models":5,"native_purchase_events":14,"native_item_rows":57,"native_transaction_ids":13,"native_unresolved_variances":2,"recorded_browser_checks":16,"recorded_software_tests":85}
