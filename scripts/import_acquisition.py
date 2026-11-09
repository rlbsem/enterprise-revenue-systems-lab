"""Import exact source blobs. No tracking, warehouse, or vendor execution."""
import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from revenue_lab.bundle import ROOT, LOCK, seal, write_json
from revenue_lab.acquisition_checks import project
REVISION = "3a1d6d7de9447a101f8f8414c50ace9f2171ebc3"
REPOSITORY = "rlbsem/enterprise-acquisition-onboarding"
FILES = {'demo.json': 'docs/evidence/pass5/run01/demo.json', 'governance.json': 'docs/evidence/pass5/run01/pass2.json', 'selected-period.json': 'docs/evidence/pass5/run01/pass3.json', 'annual.json': 'docs/evidence/annual/run01/financial.json', 'annual-execution.json': 'docs/evidence/annual/run01/annual.json', 'browser.json': 'docs/evidence/pass5/run01/pass4.json', 'software.json': 'docs/evidence/pass5/run01/verification.json', 'independent-financial.json': 'docs/evidence/pass5/run01/independent-financial.json', 'historical-authority.json': 'docs/evidence/pass5/run01/historical-authority.json', 'identity-negative.json': 'docs/evidence/pass5/run01/identity-negative.json', 'publication-negative.json': 'docs/evidence/pass5/run01/payment-and-publication-negative.json', 'exhaustion.json': 'docs/evidence/pass5/run01/exhaustion.json', 'process-death.json': 'docs/evidence/pass5/run01/process-death.json', 'financial-oracle.py': 'src/onboarding/financial_oracle.py', 'mapping-fixtures.py': 'src/onboarding/fixtures.py', 'admission-contract.md': 'docs/admission-contract.md', 'governed-execution.md': 'docs/governed-execution.md', 'financial-reporting.md': 'docs/financial-reporting.md', 'pass5-findings.md': 'docs/evidence/pass5/findings.md', 'authorization-admission.json': 'docs/evidence/pass5/run01/authorization-admission.json', 'authorization-business.json': 'docs/evidence/pass5/run01/authorization-business.json', 'authorization-mapping.json': 'docs/evidence/pass5/run01/authorization-mapping.json', 'authorization-source_revision.json': 'docs/evidence/pass5/run01/authorization-source_revision.json'}
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument("source",type=Path);args=p.parse_args()
 paths=dict(FILES)
 names=subprocess.check_output(["git","-C",str(args.source),"ls-tree","-r","--name-only",REVISION,"warehouse"]).decode().splitlines()
 for n in names:
  if n.endswith((".sql",".yml")): paths[n]=n
 data={name:subprocess.check_output(["git","-C",str(args.source),"show",REVISION+":"+path]) for name,path in paths.items()}
 up={"repository":REPOSITORY,"import_revision":REVISION,"execution_note":"Source revision pins original bytes, not a new execution. Selected-period financial publications, governed delivery, annual publications and adversarial review retain their distinct execution provenance.","artifacts":[{"file":n,"source_path":p,"sha256":hashlib.sha256(data[n]).hexdigest(),"source_url":f"https://github.com/{REPOSITORY}/blob/{REVISION}/{p}"} for n,p in paths.items()]}
 lock=json.loads((ROOT/"sources.lock.json").read_bytes());lock["sources"]["acquisition"]={"repository":REPOSITORY,"commit":REVISION};lock["acquisition_import"]=up;write_json(ROOT/"sources.lock.json",lock);LOCK.update(lock)
 parsed={n:json.loads(b) if n.endswith(".json") else b.decode() for n,b in data.items()}
 projection=project(parsed)
 data.update({"source-regression.json":(ROOT/"docs/evidence/acquisition-governance/source-regression.json").read_bytes(),"upstream.json":up,"projection.json":projection,"observation.json":{"scope":"Fresh offline recalculation of original records; no new vendor or financial writes","new_native_execution":False},"timeline.json":[{"action":"Separate selected-period publications","body":projection["selected"]},{"action":"Separate annual publications","body":projection["annual"]},{"action":"Recorded governed handoff","body":parsed["governance.json"]["D_E_delivery"]}]})
 dest=ROOT/"web/evidence/acquisition-governance"
 m=seal(dest,"acquisition-governance","acquisition",data,"recorded",[
 "Three fictional operating companies and synthetic USD only; no 50-company deployment, recognized revenue, statutory accounting or commercial outcomes.",
 "Selected-period and annual scenarios are separate executed records. Admission today is not historical publication inclusion. Source import revision is not either execution revision.",
 "Recorded local PostgreSQL, HTTP, dbt and browser acceptance; no native vendor connection or production deployment. Frozen receipts do not authorize a new action or prove universal exactly-once execution.",
 "Pass 5 is a recorded independent AI-led adversarial assessment, not independent human security certification. This static explorer performs no privileged actions."])
 m["input_hashes"]={a["path"]:a["sha256"] for a in m["artifacts"] if a["path"] in paths}
 m["reproduce"]=["python scripts/import_acquisition.py <pinned-measurement-git-checkout>","python -m revenue_lab.cli verify web/evidence/acquisition-governance"]
 write_json(dest/"bundle.json",m);print(json.dumps({"original_artifacts":len(paths),"source_revision":REVISION}))
if __name__=="__main__":main()
