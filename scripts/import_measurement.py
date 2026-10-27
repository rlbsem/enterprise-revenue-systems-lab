"""Import exact source blobs. No tracking, warehouse, or vendor execution."""
import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from revenue_lab.bundle import ROOT, LOCK, seal, write_json
from revenue_lab.measurement_checks import project
REVISION = "88a197c761cfd167c19e3d23039948ffe6bb7f2b"
REPOSITORY = "rlbsem/first-party-measurement-assurance"
FILES = {
 "demo.json":"docs/evidence/demo.json", "ledger.json":"docs/evidence/source-ledger.json",
 "browser.json":"docs/evidence/browser.json", "software.json":"docs/evidence/verification.json",
 "native.json":"docs/evidence/google-bigquery/acceptance.json",
 "job-statistics.json":"docs/evidence/google-bigquery/job-statistics-results.json",
 "local-warehouse.json":"docs/evidence/ga4-warehouse/local-acceptance.json",
 "event-contract.json":"contracts/event-v2.json", "data-layer-contract.json":"contracts/data-layer-v1.json",
 "sql/event_health.sql":"bigquery/event_health.sql", "sql/purchase_grain.sql":"bigquery/purchase_grain.sql",
 "sql/job-statistics.sql":"docs/evidence/google-bigquery/job-statistics.sql",
 "ga4-verifier.py":"scripts/verify_ga4_pipeline.py",
}
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument("source",type=Path);args=p.parse_args()
 paths=dict(FILES)
 names=subprocess.check_output(["git","-C",str(args.source),"ls-tree","-r","--name-only",REVISION,"dbt/models","ga4_pipeline"]).decode().splitlines()
 for n in names:
  if n.endswith((".sql",".csv",".yml")): paths[n]=n
 data={name:subprocess.check_output(["git","-C",str(args.source),"show",REVISION+":"+path]) for name,path in paths.items()}
 up={"repository":REPOSITORY,"import_revision":REVISION,"execution_note":"Source revision pins original bytes, not a new execution. Evermere local conversion, historical Google sample queries and local synthetic GA4 warehouse acceptance are separate records.","artifacts":[{"file":n,"source_path":p,"sha256":hashlib.sha256(data[n]).hexdigest(),"source_url":f"https://github.com/{REPOSITORY}/blob/{REVISION}/{p}"} for n,p in paths.items()]}
 lock=json.loads((ROOT/"sources.lock.json").read_bytes());lock["sources"]["measurement"]={"repository":REPOSITORY,"commit":REVISION};lock["measurement_import"]=up;write_json(ROOT/"sources.lock.json",lock);LOCK.update(lock)
 parsed={n:json.loads(b) if n.endswith(".json") else b.decode() for n,b in data.items()}
 projection=project(parsed)
 data.update({"fixture-execution.json":(ROOT/"docs/evidence/measurement-integrity/fixture-execution.json").read_bytes(),"upstream.json":up,"projection.json":projection,"observation.json":{"scope":"Read-only offline recorded evidence inspection","new_native_execution":False,"new_source_execution":True},"timeline.json":[{"action":"Local synthetic conversion reconciliation","body":projection["totals"]},{"action":"Separate native Google sample queries","body":projection["native"]},{"action":"Separate local GA4 warehouse acceptance","body":parsed["local-warehouse.json"]}]})
 dest=ROOT/"web/evidence/measurement-integrity"
 m=seal(dest,"measurement-integrity","measurement",data,"recorded",[
 "Evermere Design + Build is synthetic. Proposal, contract and payment amounts have different grains and must not be added into revenue. Measured conversion values are claims, not money received.",
 "Historical native BigQuery queried Google's public obfuscated ecommerce sample, not Evermere or a production GA4 export. Repeated transaction IDs do not prove ingestion duplicates. Findings remain unresolved.",
 "Local synthetic GA4 warehouse acceptance used DuckDB/dbt, not native dbt-bigquery. Five-model parity is a recorded result; this explorer verifies records without reexecuting SQL.",
 "No new model inference, tracking or native warehouse execution. The small pinned GA4 fixture was separately reexecuted locally. Measurement Protocol debug, a published GTM container, production ingestion and production deployment were not executed."])
 m["input_hashes"]={a["path"]:a["sha256"] for a in m["artifacts"] if a["path"] in paths}
 m["reproduce"]=["python scripts/import_measurement.py <pinned-measurement-git-checkout>","python -m revenue_lab.cli verify web/evidence/measurement-integrity"]
 write_json(dest/"bundle.json",m);print(json.dumps({"original_artifacts":len(paths),"source_revision":REVISION}))
if __name__=="__main__":main()
