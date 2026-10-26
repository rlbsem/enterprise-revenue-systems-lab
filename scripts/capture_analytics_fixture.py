"""Run only the small pinned local fixture and record typed model display subsets.

Use the source platform's locked environment, not the Lab's minimal dependencies.
No network/vendor credentials or large benchmark is invoked.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--source", type=Path, required=True)
    p.add_argument("--workspace", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    a = p.parse_args()
    root = Path(__file__).resolve().parents[1]
    up = json.loads((root / "web/evidence/analytics-engineering/upstream.json").read_bytes())
    hashes = {}
    for artifact in up["artifacts"]:
        if artifact["source_path"].startswith(("dbt/models/", "data/")):
            digest = hashlib.sha256((a.source / artifact["source_path"]).read_bytes()).hexdigest()
            assert digest == artifact["sha256"], artifact["source_path"]
            hashes[artifact["file"]] = digest
    assert not a.workspace.exists() and not a.output.exists(), "use fresh owned output paths"
    env = {**os.environ, "PYTHONPATH": str((a.source / "src").resolve()), "DBT_SEND_ANONYMOUS_USAGE_STATS": "false"}
    subprocess.run([sys.executable, "-m", "revenue_platform.cli", "demo", "--profile", "fixture", "--workspace", str(a.workspace.resolve())], cwd=a.source, env=env, check=True)
    import duckdb
    sys.path.insert(0, str(a.source / "src"))
    from revenue_platform.runtime import MODELS, records
    with duckdb.connect(str(a.workspace / "warehouse.duckdb"), read_only=True) as c:
        models = {name: {"rows": c.execute(f'SELECT count(*) FROM analytics."{name}"').fetchone()[0],
                         "columns": [[r[0], r[1]] for r in c.execute(f'DESCRIBE analytics."{name}"').fetchall()],
                         "sample": records(c.execute(f'SELECT * FROM analytics."{name}" ORDER BY ALL LIMIT 4'))} for name in MODELS}
    runs = list(a.workspace.rglob("run_results.json"))
    result = json.loads(runs[0].read_bytes())
    nodes = [{"node": r["unique_id"], "status": r["status"]} for r in result["results"]]
    assert sum(n["node"].startswith("model.") for n in nodes) == 15
    assert sum(n["node"].startswith("test.") for n in nodes) == 30
    assert all(n["status"] in ["success", "pass"] for n in nodes)
    record = {"executed_at": datetime.now(timezone.utc).isoformat(), "source_revision": up["import_revision"],
        "source_input_sha256": hashes, "lane": "fresh_local_small_fixture_duckdb_dbt", "late_batch_loaded": True,
        "independent_fixture_expectations_passed": True, "models": models, "build_results": nodes,
        "display_limit_per_model": 4, "new_native_execution": False, "new_large_benchmark": False,
        "note": "Actual local model rows; first four ordered typed rows per model. Not the historical Snowflake run or the 60K/180K benchmark. The source demo validates independent fixture expectations before publication."}
    a.output.parent.mkdir(parents=True, exist_ok=True)
    a.output.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({"models": len(models), "tests": 30, "status": "passed"}))


if __name__ == "__main__":
    main()
