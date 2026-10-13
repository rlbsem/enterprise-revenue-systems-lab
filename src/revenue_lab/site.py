"""Static packaging derives views from original artifacts; no independent business engine."""
import hashlib
import json
import shutil
import zipfile
from pathlib import Path
from .bundle import ROOT, verify, write_json

SCENARIOS = {
    "seller-application": ("seller", "Reviewed discovery action", "A saved model response was edited, approved and delivered to a synthetic CRM."),
    "seller-support-review": ("seller", "A passing draft with an unsupported claim", "Exact citations pass. The draft still implies unverified support availability."),
    "seller-stale": ("seller", "Evidence changes before approval", "The original Workbench refuses approval after new account evidence arrives."),
    "seller-suppressed": ("seller", "Consent blocks the action", "A recorded response is replayed; commercial authority prevents an effect."),
    "seller-live": ("seller", "Fresh local inference", "Actual configured local model inference and original-engine execution."),
    "control-recovery": ("control", "Uncertain delivery and recovery", "Durable intent, lost acknowledgments and independently observed receiver effects."),
    "revenue-bridge": ("revenue", "Installed ARR and quarterly flows", "Different economic measures reconcile at their own grain and time boundary."),
    "revenue-correction": ("revenue", "Late correction and equivalent rebuild", "Original dbt builds are compared with independently exported model rows."),
}


def build():
    catalog = []
    for path in sorted((ROOT / "web/evidence").glob("*/bundle.json")):
        verification = verify(path.parent)
        manifest = json.loads(path.read_text())
        scenario = manifest["scenario"]
        investigation, title, summary = SCENARIOS[scenario]
        write_json(path.parent / "verification.json", verification)
        portable = {"manifest": manifest, "artifacts": {a["path"]: (path.parent / a["path"]).read_text(encoding="utf-8") for a in manifest["artifacts"]}}
        write_json(path.parent / "portable.json", portable)
        with zipfile.ZipFile(path.parent / "reproduction.zip", "w", zipfile.ZIP_DEFLATED) as z:
            z.write(path, "bundle.json")
            for a in manifest["artifacts"]:
                z.write(path.parent / a["path"], a["path"])
            z.writestr("REPRODUCE.txt", "Clone https://github.com/rlbsem/enterprise-revenue-systems-lab\nInstall requirements.lock and set PYTHONPATH=src.\n" + "\n".join(manifest["reproduce"]) + "\npython -m revenue_lab.cli verify <extracted-bundle>\nRecorded inference is not reproducible byte-for-byte by a new model run.\n")
        catalog.append({"id": scenario, "investigation": investigation, "title": title, "summary": summary,
                        "manifest_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                        "source": manifest["source"], "mode": manifest["mode"]})
    write_json(ROOT / "web/catalog.json", {"version": 1, "scenarios": catalog})
    # Distribution is additive in an isolated build directory. No source or evidence deletion.
    shutil.copytree(ROOT / "web", ROOT / "dist", dirs_exist_ok=True)
    print(json.dumps({"scenarios": len(catalog), "output": str(ROOT / "dist")}))
