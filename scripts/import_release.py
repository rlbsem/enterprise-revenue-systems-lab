"""Import a small, exact-byte subset of the merged public release record. No inference."""
import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from revenue_lab.bundle import ROOT, LOCK, seal, write_json
from revenue_lab.release_checks import project

REVISION = "84b7bbaa92b08d3238aa321ada52b4881a62b4c2"
REPOSITORY = "rlbsem/enterprise-agent-runtime-evaluation"
BASE = "docs/evidence/live-release/"
FILES = {
    "original-reference.json": "docs/evidence/live-reference/summary.json",
    "original-candidate.json": "docs/evidence/live-candidate/summary.json",
    "original-failure.json": "docs/evidence/live-reference/adoption-0.json",
    "first-reference.json": BASE + "qwen3-v1/qwen3-14b-reference-v1/summary.json",
    "first-candidate.json": BASE + "qwen3-v1/qwen3-14b-authority-facts-v4/summary.json",
    "first-gate.json": BASE + "qwen3-v1/gate.json",
    "first-release.json": BASE + "qwen3-v1/release.json",
    "first-failure.json": BASE + "qwen3-v1/qwen3-14b-authority-facts-v4/injected-source-priority-0.json",
    "bounded-reference.json": BASE + "qwen3-bounded-v2/qwen3-14b-reasoning1024-reference/summary.json",
    "bounded-candidate.json": BASE + "qwen3-bounded-v2/qwen3-14b-reasoning768-candidate/summary.json",
    "bounded-gate.json": BASE + "qwen3-bounded-v2/gate.json",
    "lifecycle.json": BASE + "qwen3-bounded-v2/lifecycle.json",
    "controls.json": BASE + "qwen3-bounded-v2/controls.json",
    "seal.json": BASE + "qwen3-bounded-v2/seal.json",
    "software.json": BASE + "software/verification.json",
}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path, help="Git checkout or bare repository containing the merged revision")
    args = parser.parse_args()
    data = {name: subprocess.check_output(["git", "-C", str(args.source), "show", f"{REVISION}:{path}"])
            for name, path in FILES.items()}
    pin = {"repository": REPOSITORY, "commit": REVISION}
    upstream = {"repository": REPOSITORY, "import_revision": REVISION,
                "execution_revision_note": "Import merge is not execution time; each original seal/configuration retains its executed source hashes.",
                "artifacts": [{"file": name, "source_path": path, "sha256": hashlib.sha256(data[name]).hexdigest(),
                               "source_url": f"https://github.com/{REPOSITORY}/blob/{REVISION}/{path}"}
                              for name, path in FILES.items()]}
    lock = json.loads((ROOT / "sources.lock.json").read_text(encoding="utf-8"))
    lock["sources"]["release"] = pin
    lock["release_import"] = upstream
    write_json(ROOT / "sources.lock.json", lock)
    LOCK.update(lock)
    files = {name: json.loads(raw) for name, raw in data.items()}
    projection = project(files, upstream)
    # Validate every generated task link against actual committed task content,
    # without duplicating those 192 raw task files in the Lab.
    for comparison in projection["comparisons"]:
        for row, result in zip(comparison["results"], files[comparison["file"]]["results"], strict=True):
            path = row["source_url"].split(f"/blob/{REVISION}/", 1)[1]
            raw = subprocess.check_output(["git", "-C", str(args.source), "show", f"{REVISION}:{path}"])
            if json.loads(raw)["evaluation"] != result:
                raise ValueError("task link does not match recorded evaluation: " + path)
    data.update({"upstream.json": upstream, "projection.json": projection,
                 "observation.json": {"new_model_execution": False, "new_effects": False,
                                      "scope": "Recorded local inference; synthetic effects; no production deployment"},
                 "timeline.json": [{"action": item["event"], "occurred": item["at"], "body": item}
                                   for item in files["lifecycle.json"]["history"]]})
    destination = ROOT / "web/evidence/release-assurance"
    manifest = seal(destination, "release-assurance", "release", data, "recorded", [
        "Actual recorded Qwen2.5/Qwen3 inference and local synthetic HTTP/SQLite effects; this static Lab makes no model or vendor calls.",
        "Finite synthetic acceptance cases, including six fresh holdouts in the bounded run; not production reliability, general model accuracy or commercial outcomes.",
        "Controlled adapter-input corruption triggered rollback; it is not an observed natural model regression. Rollback changes routing and does not undo prior effects.",
        "Escalation approval came from the trusted evaluation harness, not an independent human reviewer. Software test counts are separate from model tasks.",
        "Selected exact-byte source records, aggregate result checks and routed receipt checks are packaged. Complete per-task raw inference and source snapshots remain at the pinned upstream revision."])
    manifest["input_hashes"] = {a["path"]: a["sha256"] for a in manifest["artifacts"] if a["path"] in FILES}
    manifest["reproduce"] = ["python scripts/import_release.py <agent-runtime-git-checkout>",
                             "python -m revenue_lab.cli verify web/evidence/release-assurance"]
    write_json(destination / "bundle.json", manifest)
    print(json.dumps({"exact_source_artifacts": len(FILES), "source_revision": REVISION, "new_inference": False}))


if __name__ == "__main__":
    main()
