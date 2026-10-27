"""Import a finite set of original Git blobs; never run source engines or vendor calls."""

import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from revenue_lab.bundle import ROOT, LOCK, seal, write_json
from revenue_lab.assurance_checks import project

SOURCES = {
    "estate-assurance": {
        "key":"estate", "repository":"rlbsem/martech-estate-impact",
        "revision":"11890321d8cd6c164da236cad7896d00b6e0938e",
        "files":{
            "record.json":"docs/evidence/change-assurance/run-03/estate-record.json",
            "regression.json":"docs/evidence/change-assurance/run-03/verification.json",
            "comparison.json":"docs/evidence/change-assurance/run-03/oracle-comparison.json",
            "catalog-source.json":"fixtures/change-assurance/catalog.json",
            "cmdb.csv":"fixtures/change-assurance/cmdb.csv",
            "owner-source.json":"fixtures/change-assurance/owner.json",
            "registry-source.json":"fixtures/change-assurance/registry.json",
            "execution-source.json":"fixtures/change-assurance/execution.json",
            "requirement-engine.py":"src/estate_impact/requirements.py",
            "governance-source.py":"src/estate_change/service.py",
            "governance.sql":"src/estate_change/schema.sql",
        },
    },
    "reliability-operations": {
        "key":"reliability", "repository":"rlbsem/martech-data-reliability",
        "revision":"225964aead1a3f697007605534613f5a813aaed9",
        "files":{
            "record.json":"docs/evidence/operations/run02/acceptance.json",
            "regression.json":"docs/evidence/operations/run02/verification.json",
            "crashes.json":"docs/evidence/operations/run02/original-recovery.json",
            "contracts-source.py":"src/marketing_reliability/contracts.py",
            "controller-source.py":"src/reliability_ops/controller.py",
            "publication.sql":"src/marketing_reliability/sql/campaign_daily.sql",
        },
    },
    "temporal-assurance": {
        "key":"temporal", "repository":"rlbsem/temporal-customer-audiences",
        "revision":"5488c4796b6789d4df470d77ac12f9ee4a0c18bc",
        "files":{
            "record.json":"docs/evidence/activation-assurance/run02/acceptance.json",
            "regression.json":"docs/evidence/activation-assurance/run02/verification.json",
            "temporal-proof.json":"docs/evidence/activation-assurance/run02/original-demo/temporal-proof.json",
            "ci-record.json":"docs/evidence/activation-assurance/ci-execution.json",
            "operating.sql":"src/audience_ops/operating.sql",
            "permission-source.py":"src/audience_ops/activation.py",
            "delivery-source.py":"src/audience_ops/worker.py",
        },
    },
}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("scenario", choices=SOURCES)
    parser.add_argument("source", type=Path, help="Existing source Git checkout; no files are modified")
    args = parser.parse_args()
    spec = SOURCES[args.scenario]
    dest = ROOT / "web/evidence" / args.scenario
    if dest.exists():
        raise ValueError("recorded import already exists; preserve it, use a deliberate new revision")
    raw = {name:subprocess.check_output(["git","-C",str(args.source),"show",spec["revision"]+":"+path])
           for name,path in spec["files"].items()}
    upstream = dict(repository=spec["repository"],import_revision=spec["revision"],
        execution_note="The import pins current main, not execution time. Original source hashes, execution revisions, clocks and native/local boundaries remain inside unmodified records.",
        artifacts=[dict(file=n,source_path=p,sha256=hashlib.sha256(raw[n]).hexdigest(),
                        source_url=f"https://github.com/{spec['repository']}/blob/{spec['revision']}/{p}")
                   for n,p in spec["files"].items()])
    lock = json.loads((ROOT/"sources.lock.json").read_bytes())
    lock["sources"][spec["key"]] = dict(repository=spec["repository"],commit=spec["revision"])
    lock.setdefault("assurance_imports",{})[args.scenario] = upstream
    write_json(ROOT/"sources.lock.json",lock)
    LOCK.update(lock)
    parsed = {n:json.loads(b) if n.endswith(".json") else b.decode("utf-8") for n,b in raw.items()}
    summary = project(args.scenario,parsed)
    observation = dict(scope="Read-only recorded evidence inspection",synthetic=True,
                       new_source_execution=False,new_native_external_execution=False,summary=summary)
    data = dict(raw)
    data.update({"upstream.json":upstream,"projection.json":summary,"observation.json":observation,
                 "timeline.json":[dict(action="Inspect pinned original execution",body=summary),
                                  dict(action="Distinguish captured state from current authority",body={"new_actions":0,"new_native_execution":False})]})
    manifest = seal(dest,args.scenario,spec["key"],data,"recorded",[
        "All companies, people, source feeds, financial values and destination effects are synthetic. No customer result, causal uplift, vendor certification or production reliability is established.",
        "Original records describe executed local software and independent synthetic source/receiver services. They are not native marketing-platform acceptance or a continuous workflow shared with other investigations.",
        "This browser replays records. Its offline checker reconstructs selected relationships, arithmetic and temporal answers; it does not rerun the source engines, authorize changes, contact a person or connect to a live database.",
        "Captured approvals, permissions, coverage and readiness describe the recorded clock only. Historical receipts and restatements never authorize a new present-day action."])
    manifest["input_hashes"] = {a["path"]:a["sha256"] for a in manifest["artifacts"] if a["path"] in spec["files"]}
    manifest["reproduce"] = [f"git clone https://github.com/{spec['repository']}",
        f"git -C {spec['repository'].split('/')[1]} checkout {spec['revision']}",
        f"python scripts/import_assurance.py {args.scenario} <source-git-checkout> # only in a fresh Lab checkout without this imported case",
        f"python -m revenue_lab.cli verify web/evidence/{args.scenario}"]
    write_json(dest/"bundle.json",manifest)
    print(json.dumps(dict(scenario=args.scenario,original_artifacts=len(raw),projection=summary)))


if __name__ == "__main__":
    main()
