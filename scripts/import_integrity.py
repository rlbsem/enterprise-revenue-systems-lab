"""Import selected exact source bytes from the unmerged, pinned local-contract acceptance."""
import argparse
from datetime import datetime
import hashlib
import json
import subprocess
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from revenue_lab.bundle import ROOT, LOCK, seal, write_json
from revenue_lab.integrity_checks import project

REVISION = "e2993099acaaae188aac0d83ba840cecef1c0014"
REPOSITORY = "rlbsem/enterprise-revenue-integrity-platform"
BASE = "docs/evidence/internal-acceptance/run01/"
FILES = {"lifecycle.json": BASE + "lifecycle.json", "delivery.json": BASE + "demo.json", "software.json": BASE + "verification.json",
    "process-death.json": BASE + "process-death.json", "history-rehydration.json": BASE + "history-rehydration.json",
    "publication-process-death.json": BASE + "publication-process-death.json",
    "operator-browser.json": "docs/evidence/operator-console/run02/browser.json", "source-console.py": "src/integrity/console.py",
    "source-browser.cjs": "scripts/browser_acceptance.cjs"}

def main():
    p = argparse.ArgumentParser(description=__doc__); p.add_argument("source", type=Path); args = p.parse_args()
    data = {name: subprocess.check_output(["git", "-C", str(args.source), "show", f"{REVISION}:{path}"]) for name, path in FILES.items()}
    upstream = {"repository": REPOSITORY, "import_revision": REVISION, "source_pr": f"https://github.com/{REPOSITORY}/pull/1",
        "execution_revision_note": "Pinned unmerged implementation, not an independent architecture sign-off. Lifecycle and delivery run at 9f7ce81; operator capture at 369bd0b. Their original records retain source fingerprints. These are separate local executions.",
        "artifacts": [{"file": name, "source_path": path, "sha256": hashlib.sha256(data[name]).hexdigest(),
            "source_url": f"https://github.com/{REPOSITORY}/blob/{REVISION}/{path}"} for name, path in FILES.items()]}
    lock = json.loads((ROOT / "sources.lock.json").read_text(encoding="utf-8"))
    lock["sources"]["integrity"] = {"repository": REPOSITORY, "commit": REVISION}; lock["integrity_import"] = upstream
    write_json(ROOT / "sources.lock.json", lock); LOCK.update(lock)
    files = {name: json.loads(raw) if name.endswith(".json") else raw.decode() for name, raw in data.items()}
    projection = project(files)
    demo = files["delivery.json"]
    data.update({"upstream.json": upstream, "projection.json": projection,
        "observation.json": {"new_effects": False, "native_vendor_calls": False, "scope": "Read-only recorded local synthetic execution; no live operator API"},
        "timeline.json": [{"action": r["action"], "occurred": datetime.fromisoformat(r["recorded_at"]).timestamp(), "body": {**r, "evidence_set": "Separate foundation delivery run"}} for r in demo["persisted_state"]["control"]["audit"]]})
    dest = ROOT / "web/evidence/revenue-integrity"
    manifest = seal(dest, "revenue-integrity", "integrity", data, "recorded", [
        "Read-only recorded local contract services with synthetic USD data. No native Salesforce, Stripe, NetSuite or Snowflake execution; no production or commercial results.",
        "Lifecycle, foundation delivery, process-death and operator-browser runs are separate evidence sets. Pinned source PR is unmerged; this viewer is not an independent certification of the source platform.",
        "Post-recovery billing/ERP totals are archived browser observations. Cash/ARR use versioned fixture arithmetic corroborated by executed assertions. Full recovery approval/attempt rows were not archived at this revision.",
        "Only the recorded finite scenario is checked. This does not establish general financial correctness, strict cross-system revocation atomicity, production HA or universal exactly-once delivery."])
    manifest["input_hashes"] = {a["path"]: a["sha256"] for a in manifest["artifacts"] if a["path"] in FILES}
    manifest["reproduce"] = ["python scripts/import_integrity.py <pinned-revenue-integrity-git-checkout>", "python -m revenue_lab.cli verify web/evidence/revenue-integrity"]
    write_json(dest / "bundle.json", manifest)
    print(json.dumps({"original_artifacts": len(FILES), "source_revision": REVISION, "new_vendor_calls": False}))

if __name__ == "__main__": main()
