"""Import exact public Git blobs; never execute the GTM engine, a model or a vendor API."""

import argparse
import ast
import hashlib
import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from revenue_lab.bundle import ROOT, seal, write_json

REVISION = "6da3603a8e447dacfdbde25a8aab5c5fa3721328"
NATIVE = "c54503f00e65ad4195a74c0bacf2ce003add091c"
AI = "4b06935b23edee3045a58553ec9fcdf2fa056084"
CLEANUP = "36fd314015812f2114d5e96a0cbbaee24b17b2e4"
LANES = {
    "gtm-enterprise": [
        ("execution.json", "docs/evidence/enterprise-usd/demo.json", REVISION),
        ("scenario.json", "src/gtm/enterprise-scenario.json", REVISION),
        ("regression.json", "docs/evidence/enterprise-usd/verification.json", REVISION),
    ],
    "gtm-salesforce": [
        ("acceptance.json", "docs/evidence/salesforce-standard/acceptance.json", NATIVE),
        ("native-details.json", "docs/evidence/salesforce-standard/native-details.json", "62e48215a3609ba136f4ce581f98cc893e2378d9"),
        ("post-cleanup.json", "docs/evidence/salesforce-standard/post-cleanup.json", CLEANUP),
    ],
    "gtm-qwen": [
        ("evaluation.json", "docs/evidence/native-ai/ai-evaluation.json", AI),
        ("model-source.py", "src/gtm/advice.py", AI),
        ("policy-source.py", "scripts/evaluate_ai.py", AI),
        ("cases.json", "src/gtm/upgrade_cases.json", AI),
    ],
}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path, help="Existing GTM Git checkout; public committed blobs only")
    args = parser.parse_args()
    lock = json.loads((ROOT / "sources.lock.json").read_text())
    lock["sources"]["gtm"] = {"repository": "rlbsem/gtm-pipeline-orchestration", "commit": REVISION}
    lock["gtm_imports"] = {}
    imported = {}
    for scenario, entries in LANES.items():
        artifacts, originals = {}, {}
        for name, upstream_path, executed_revision in entries:
            read_revision = executed_revision if name in {"model-source.py", "policy-source.py", "cases.json"} else REVISION
            data = subprocess.check_output(["git", "show", f"{read_revision}:{upstream_path}"], cwd=args.source)
            artifacts[name] = data
            originals[name] = json.loads(data) if name.endswith(".json") else data.decode("utf-8")
        upstream = {"repository": lock["sources"]["gtm"]["repository"], "import_revision": REVISION,
                    "lane": scenario, "artifacts": [
                        {"file": name, "source_path": path, "recorded_source_revision": revision,
                         "sha256": hashlib.sha256(artifacts[name]).hexdigest(),
                         "source_url": f"https://github.com/rlbsem/gtm-pipeline-orchestration/blob/{revision if name in {'model-source.py', 'policy-source.py', 'cases.json'} else REVISION}/{path}"}
                        for name, path, revision in entries]}
        lock["gtm_imports"][scenario] = upstream
        artifacts["upstream.json"] = upstream
        artifacts["observation.json"] = {
            "derivation": "Offline import of exact public committed artifacts; no new system execution",
            "lane": scenario, "new_vendor_execution": False, "new_model_execution": False,
            "continuous_vendor_workflow": False,
        }
        if scenario == "gtm-enterprise":
            d = originals["execution.json"]
            timeline = [{"action": a["event"], "detail": a["at"] + " · local synthetic event", "body": a}
                        for a in d["audit"] if a["event"] in {"exact_approval", "dispatch_authorized", "receipt_recovered"}][:30]
        elif scenario == "gtm-salesforce":
            a = originals["acceptance.json"]
            timeline = [{"action": f'{r["method"]} · {r["resource"]} · HTTP {r["http"]}',
                         "detail": r["at"] + " · " + r["role"] + " · recorded request " + str(i + 1), "body": r}
                        for i, r in enumerate(a["requests"])]
        else:
            tree = ast.parse(originals["model-source.py"])
            prompt = next(ast.literal_eval(n.value) for n in ast.walk(tree) if isinstance(n, ast.Assign)
                          and any(isinstance(t, ast.Name) and t.id == "prompt" for t in n.targets))
            artifacts["instructions.json"] = {"system_prompt": prompt["content"],
                "derivation": "Exact literal extracted from recorded model source, not a new model request",
                "source": "model-source.py"}
            timeline = [{"action": r["case_id"], "detail": r["executed_at"] + " · recorded Qwen3 inference",
                         "body": r} for r in originals["evaluation.json"]["records"]]
        artifacts["timeline.json"] = timeline
        imported[scenario] = artifacts
    write_json(ROOT / "sources.lock.json", lock)
    # seal reads the module lock; update only this import process after the deliberate lock write.
    from revenue_lab.bundle import LOCK
    LOCK.update(lock)
    for scenario, artifacts in imported.items():
        destination = ROOT / "web/evidence" / scenario
        manifest = seal(destination, scenario, "gtm", artifacts, "recorded", [
            "Three separate execution sets: local synthetic enterprise pipeline, native Salesforce acceptance and Qwen3 evaluation. They are not one continuous live vendor workflow.",
            "Synthetic opportunity estimates are not revenue or evidence of causal lift. No prospect communications or new vendor/model calls occur in this Lab.",
            "Sanitized native response hashes are author-controlled evidence, not vendor signatures; organization and record identities remain hashed.",
        ])
        manifest["input_hashes"] = {a["path"]: a["sha256"] for a in manifest["artifacts"] if a["path"] not in {"observation.json", "timeline.json"}}
        manifest["reproduce"] = [f"python -m revenue_lab.cli verify web/evidence/{scenario}"]
        write_json(destination / "bundle.json", manifest)
    print("Imported three recorded GTM lanes at " + REVISION + "; no native or model execution")


if __name__ == "__main__":
    main()
