"""Import selected original Git blobs; never execute or modify the source platform."""
import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from revenue_lab.bundle import ROOT, LOCK, seal, write_json
from revenue_lab.analytics_checks import project

REVISION = "4cc1480d63f1095584db2ddcde72ed5626eb7ea7"
REPOSITORY = "rlbsem/revenue-metrics-platform"
FILES = {
    "lineage.json": "docs/evidence/dbt-lineage.json",
    "metrics.json": "metrics/catalog.json",
    "summary.json": "docs/evidence/performance/summary.json",
    "protocol.json": "docs/evidence/performance/protocol.json",
    "software.json": "docs/evidence/performance/current-test-results.json",
    "fixture-cases.json": "docs/evidence/fixture/modeling-cases.json",
    "fixture-publication.json": "docs/evidence/performance/current-fixture-publication/64fe92180afe05e3c2a0f324cf5221b505cc1b08a0e1f0586969518964657a8f.json",
    "snowflake.json": "docs/evidence/snowflake/fixture/verification.json",
    "snowflake-notes.json": "docs/evidence/snowflake/fixture/execution-notes.json",
}
for profile in ["enterprise", "stress"]:
    for name in ["pair-1", "pair-2", "pair-3", "execution-protocol", "generation"]:
        FILES[f"{profile}-{name}.json"] = f"docs/evidence/performance/{profile}/{name}.json"
for name in ["initial_full_build", "corrected_incremental_build", "independent_corrected_full_build"]:
    FILES[f"snowflake-{name}.json"] = f"docs/evidence/snowflake/fixture/{name}-results.json"


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("source", type=Path)
    args = p.parse_args()
    names = subprocess.check_output(["git", "-C", str(args.source), "ls-tree", "-r", "--name-only", REVISION, "dbt/models", "data"]).decode().splitlines()
    paths = dict(FILES)
    paths.update({"sql/" + Path(n).name: n for n in names if n.endswith(".sql")})
    paths.update({"fixture/" + Path(n).name: n for n in names if n.startswith("data/") and n.endswith(".csv")})
    data = {name: subprocess.check_output(["git", "-C", str(args.source), "show", f"{REVISION}:{path}"]) for name, path in paths.items()}
    upstream = {"repository": REPOSITORY, "import_revision": REVISION,
        "execution_revision_note": "Import revision pins bytes, not a new run. Enterprise benchmark executed d26b430; stress b13a011. Their full revisions and conditions remain in execution-protocol records. Historical Snowflake fixture predates the USD unit correction. Current SQL and fixture publication are separately versioned source records.",
        "artifacts": [{"file": name, "source_path": path, "sha256": hashlib.sha256(data[name]).hexdigest(),
            "source_url": f"https://github.com/{REPOSITORY}/blob/{REVISION}/{path}"} for name, path in paths.items()]}
    lock = json.loads((ROOT / "sources.lock.json").read_bytes())
    lock["sources"]["analytics"] = {"repository": REPOSITORY, "commit": REVISION}
    lock["analytics_import"] = upstream
    write_json(ROOT / "sources.lock.json", lock)
    LOCK.update(lock)
    parsed = {n: json.loads(raw) if n.endswith(".json") else raw.decode() for n, raw in data.items()}
    projection = project(parsed)
    data.update({"fixture-execution.json": (ROOT / "docs/evidence/analytics-engineering/fixture-execution.json").read_bytes(),
        "upstream.json": upstream, "projection.json": projection,
        "observation.json": {"new_warehouse_execution": False, "new_benchmarks": False, "scope": "Offline recorded evidence inspection; synthetic data"},
        "timeline.json": [{"action": "Local enterprise paired benchmark", "body": projection["profiles"]["enterprise"]},
                          {"action": "Local stress paired benchmark", "body": projection["profiles"]["stress"]},
                          {"action": "Separate historical native Snowflake fixture", "body": projection["native"]}]})
    dest = ROOT / "web/evidence/analytics-engineering"
    m = seal(dest, "analytics-engineering", "analytics", data, "recorded", [
        "Recorded synthetic local DuckDB/dbt benchmarks and historical native Snowflake fixture are separate executions. No new warehouse/model/cloud calls occur.",
        "Three filesystem-warm paired observations per scale on one Windows host, one dbt/DuckDB thread and 2GB engine setting; not cold-cache, production capacity, cost savings or a process memory cap.",
        "Complete typed-export equality was recorded upstream. Compact downloads contain original comparison records, SQL, the small fixture and selected publication rows, not 37 million fact rows; offline checks do not repeat those warehouse comparisons.",
        "Snowflake acceptance predates the USD unit correction. It does not validate the current USD-specific revision, selective candidate or large-scale Snowflake performance; billed consumption remains unavailable."])
    m["input_hashes"] = {a["path"]: a["sha256"] for a in m["artifacts"] if a["path"] in paths}
    m["reproduce"] = ["python scripts/import_analytics.py <pinned-revenue-metrics-git-checkout>", "python -m revenue_lab.cli verify web/evidence/analytics-engineering"]
    write_json(dest / "bundle.json", m)
    print(json.dumps({"original_artifacts": len(paths), "source_revision": REVISION}))


if __name__ == "__main__":
    main()
