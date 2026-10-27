"""Run pinned small synthetic GA4 fixture in a disposable export, never in the source checkout.
Requires the source's DuckDB/dbt dependencies; no cloud credentials or network queries.
"""
import argparse
import hashlib
import importlib.util
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"src"))
from revenue_lab.bundle import ROOT, write_json, verify

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument("--workspace",type=Path,required=True);args=p.parse_args()
 bundle=ROOT/"web/evidence/measurement-integrity"
 verify(bundle)
 up=json.loads((bundle/"upstream.json").read_bytes())
 workspace=args.workspace.resolve();workspace.mkdir(parents=True,exist_ok=False)
 inputs={a["file"]:a for a in up["artifacts"] if a["file"].startswith("ga4_pipeline/") or a["file"]=="ga4-verifier.py"}
 # Materialize only exact pinned inputs into a new disposable workspace.
 for name,a in inputs.items():
  target=workspace/("scripts/verify_ga4_pipeline.py" if name=="ga4-verifier.py" else name)
  raw=(bundle/name).read_bytes()
  if hashlib.sha256(raw).hexdigest()!=a["sha256"]:raise ValueError("bundle differs from pinned source: "+name)
  target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(raw)
 report=workspace/".local/lab-fixture.json"
 subprocess.run([sys.executable,str(workspace/"scripts/verify_ga4_pipeline.py"),"--output",str(report)],check=True,env=dict(os.environ,DBT_SEND_ANONYMOUS_USAGE_STATS="false"),timeout=300)
 r=json.loads(report.read_bytes());run=workspace/".local"/("ga4-verification-"+r["run_id"])
 spec=importlib.util.spec_from_file_location("original_ga4_verifier",workspace/"scripts/verify_ga4_pipeline.py");module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
 incremental=module.sql_rows(run/"incremental.duckdb");independent=module.sql_rows(run/"full.duckdb")
 if incremental!=independent:raise AssertionError("independent five-model comparison failed")
 import duckdb
 rows={}
 with duckdb.connect(str(run/"incremental.duckdb"),read_only=True) as db:
  for name,values in incremental.items():
   db.execute("select * from "+name);rows[name]={"columns":[[c[0],str(c[1])] for c in db.description],"rows":values}
 result={"executed_at":datetime.now(timezone.utc).isoformat(),"lane":"fresh_local_synthetic_ga4_duckdb_dbt","source_revision":up["import_revision"],"source_input_sha256":{n:a["sha256"] for n,a in inputs.items()},"new_native_execution":False,"report":r,"models":rows,"independent_full_rowsets":independent,"dependencies":{"duckdb":duckdb.__version__}}
 # Dates become ISO text in the portable JSON; exact typed comparison happened above.
 result=json.loads(json.dumps(result,default=str));write_json(ROOT/"docs/evidence/measurement-integrity/fixture-execution.json",result)
 print(json.dumps({"models":len(rows),"rows":{n:len(v["rows"]) for n,v in rows.items()},"independent_equal":True}))
if __name__=="__main__":main()
