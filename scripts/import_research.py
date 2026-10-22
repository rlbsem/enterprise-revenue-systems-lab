"""Import only public committed research artifacts from the merged source revision."""
import argparse
import ast
import hashlib
import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from revenue_lab.bundle import ROOT, LOCK, seal, write_json
from revenue_lab.research_checks import queue

REVISION = "81d9381169456ca8893be0ddea483296ac77e12e"
FILES = {name: "docs/evidence/research/" + name for name in [
    "evaluation.json", "round1-evaluation.json", "round1-sources.json", "round2-evaluation.json",
    "round2-sources.json", "round3-evaluation.json", "round3-sources.json", "operator-proof.json",
    "reviewer-assessment.json", "public-jobs.json"]}
FILES.update({"scenario.json": "src/gtm/research-scenario.json", "research-source.py": "src/gtm/research.py",
              "browser-provenance.json": "docs/images/research/provenance.json", "browser-capture.py": "scripts/capture_research.py",
              "regression.json": "docs/evidence/research/local/verification.json"})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    args = parser.parse_args()
    data = {name: subprocess.check_output(["git", "show", f"{REVISION}:{path}"], cwd=args.source)
            for name, path in FILES.items()}
    pin = {"repository": "rlbsem/gtm-pipeline-orchestration", "commit": REVISION}
    upstream = {"repository": pin["repository"], "import_revision": REVISION, "lane": "gtm-research", "artifacts": [
        {"file": name, "source_path": path, "recorded_source_revision": "embedded per execution; import revision is not execution time",
         "sha256": hashlib.sha256(data[name]).hexdigest(),
         "source_url": f"https://github.com/{pin['repository']}/blob/{REVISION}/{path}"} for name, path in FILES.items()]}
    lock = json.loads((ROOT / "sources.lock.json").read_text(encoding="utf-8"))
    lock["sources"]["research"] = pin
    lock["gtm_imports"]["gtm-research"] = upstream
    write_json(ROOT / "sources.lock.json", lock)
    LOCK.update(lock)
    data["upstream.json"] = upstream
    data["queue.json"] = queue(json.loads(data["scenario.json"]), data["research-source.py"].decode("utf-8"))
    edited = next(ast.literal_eval(n.args[0]) for n in ast.walk(ast.parse(data["browser-capture.py"]))
                  if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and n.func.attr == "fill")
    data["browser-edit.json"] = {"derivation": "Exact fill literal in executed capture source; screenshot and interaction proof remain separately pinned",
                                 "opening": edited, "new_approval": False}
    data["observation.json"] = {"derivation": "Offline read-only projection; no new research, approval or vendor execution",
                                "new_vendor_execution": False, "new_model_execution": False, "continuous_vendor_workflow": False}
    data["timeline.json"] = [{"action": r["case_id"] + " · " + r["approach"], "detail": r["executed_at"] + " · recorded inference", "body": r}
                             for r in json.loads(data["evaluation.json"])["records"]]
    destination = ROOT / "web/evidence/gtm-research"
    manifest = seal(destination, "gtm-research", "research", data, "recorded", [
        "40 model evaluation responses and a separate fresh local operator run; not the native Salesforce execution or the 120-account pipeline scenario.",
        "Synthetic January 2026 study contexts; actual model execution in October 2026. Priority is deterministic fit/signal arithmetic, not buying intent.",
        "Exact citations do not establish semantic entailment. Qualitative assessment is an AI engineering review, not a blind human SDR study.",
        "Clay/provider enrichment is fixture-based; n8n is an unexecuted reference. No prospect communications, new approvals or CRM writes occur here.",
        "One real public job API archive is a separate read-only reference. API updated_at is not publication date; real company is not a synthetic CRM target."])
    manifest["input_hashes"] = {a["path"]: a["sha256"] for a in manifest["artifacts"] if a["path"] in FILES}
    manifest["reproduce"] = ["python scripts/import_research.py <gtm-git-checkout>", "python -m revenue_lab.cli verify web/evidence/gtm-research"]
    write_json(destination / "bundle.json", manifest)
    print(f"Imported {len(FILES)} exact public artifacts at {REVISION}; no vendor or model execution")


if __name__ == "__main__":
    main()
