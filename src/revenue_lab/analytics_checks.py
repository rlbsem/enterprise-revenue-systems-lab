"""Finite recorded evidence checks, not a new warehouse benchmark or SQL engine."""
import csv
import hashlib
import io
from statistics import median

from .bundle import LOCK
from .gtm_checks import require


def project(files):
    lineage = files["lineage.json"]
    models = [{"name": k.split(".")[-1], "grain": v["description"], "parents": v["depends_on"],
               "sql": "sql/" + k.split(".")[-1] + ".sql"}
              for k, v in lineage.items() if v["resource_type"] == "model"]
    profiles = {}
    for profile in ["enterprise", "stress"]:
        pairs = [files[f"{profile}-pair-{i}.json"] for i in [1, 2, 3]]
        base = median(p["stages"]["baseline_incremental"]["seconds"] for p in pairs)
        candidate = median(p["stages"]["optimized_incremental"]["seconds"] for p in pairs)
        rows = {m["model"]: m["rows"] for m in pairs[0]["optimized_full_parity"]["models"]}
        profiles[profile] = {"accounts": pairs[0]["source_counts"]["account_attributes"],
            "opportunities": pairs[0]["total_opportunities"], "fact_rows": rows["fct_opportunity_daily"],
            "model_rows": rows, "baseline_median_seconds": base, "candidate_median_seconds": candidate,
            "wall_change_percent": (candidate / base - 1) * 100,
            "pairs": [{"repetition": p["repetition"], "baseline": p["stages"]["baseline_incremental"]["seconds"],
                       "candidate": p["stages"]["optimized_incremental"]["seconds"],
                       "baseline_noop": p["stages"]["baseline_noop"]["seconds"],
                       "candidate_noop": p["stages"]["optimized_noop"]["seconds"]} for p in pairs]}
    native = files["snowflake.json"]
    return {"models": models, "metrics": files["metrics.json"], "profiles": profiles,
        "fixture_sources": {n.split("/")[-1][:-4]: list(csv.DictReader(io.StringIO(v))) for n, v in files.items() if n.startswith("fixture/")},
        "software_tests": len(files["software.json"]),
        "native": {"started_at": native["started_at"], "finished_at": native["finished_at"],
                   "query_ids": len(native["query_ids"]), "models": len(native["model_comparison"]),
                   "denied_operations": native["denied_operations"], "consumption": native["consumption"]}}


def analytics(files):
    require(files["upstream.json"] == LOCK["analytics_import"], "analytics provenance mismatch")
    expected = project(files)
    require(files["projection.json"] == expected, "analytics display projection mismatch")
    names = {m["name"] for m in expected["models"]}
    require(len(names) == 15 and len({m["metric_id"] for m in expected["metrics"]}) == 6, "model/metric contract incomplete")
    local = files["fixture-execution.json"]
    require(local["source_revision"] == files["upstream.json"]["import_revision"] and local["lane"] == "fresh_local_small_fixture_duckdb_dbt", "local fixture provenance differs")
    require(local["independent_fixture_expectations_passed"] and local["late_batch_loaded"] and not local["new_native_execution"] and not local["new_large_benchmark"], "local fixture boundary differs")
    source_hashes = {a["file"]: a["sha256"] for a in files["upstream.json"]["artifacts"] if a["file"].startswith(("sql/", "fixture/"))}
    require(local["source_input_sha256"] == source_hashes, "local fixture source bytes differ")
    require(set(local["models"]) == names, "local modeled row set missing")
    for m in local["models"].values():
        require(len(m["sample"]) == min(m["rows"], local["display_limit_per_model"]) and all(set(row) == {c[0] for c in m["columns"]} for row in m["sample"]), "local model sample contract differs")
    nodes = local["build_results"]
    require(sum(n["node"].startswith("model.") for n in nodes) == 15 and sum(n["node"].startswith("test.") for n in nodes) == 30 and all(n["status"] in ["success", "pass"] for n in nodes), "local fixture build gates failed")
    for m in expected["models"]:
        require(m["sql"] in files and files[m["sql"]].strip(), "missing model SQL")
        require(all(p.startswith("source.") or p.split(".")[-1] in names for p in m["parents"]), "lineage reference missing")
    for profile in ["enterprise", "stress"]:
        display = expected["profiles"][profile]
        summary = files["summary.json"]["profiles"][profile]
        require(abs(summary["baseline_incremental_median_seconds"] - display["baseline_median_seconds"]) < 1e-8 and
                abs(summary["candidate_incremental_median_seconds"] - display["candidate_median_seconds"]) < 1e-8 and
                abs(summary["candidate_wall_change_percent"] - display["wall_change_percent"]) < 1e-8, "benchmark summary differs from raw measurements")
        require(not summary["predeclared_threshold_met"] and display["wall_change_percent"] > 0, "rejected optimization hidden")
        protocol = files[f"{profile}-execution-protocol.json"]
        require(protocol["duckdb_threads"] == protocol["dbt_threads"] == 1 and protocol["memory_limit"] == "2GB", "benchmark conditions differ")
        for i in [1, 2, 3]:
            p = files[f"{profile}-pair-{i}.json"]
            require(p["repetition"] == i and p["profile"] == profile and p["consumer_payload_equal"], "benchmark pair mismatch")
            for key in ["baseline_optimized_parity", "optimized_full_parity", "noop_parity"]:
                compared = p[key]["models"]
                require(len(compared) == 15 and {m["model"] for m in compared} == names, "incomplete full-model comparison")
                require(all(m["exact_multiset_equal"] and m["differences"] == 0 and m["rows"] >= 0 for m in compared), "model rowset differs")
            for key in ["baseline_incremental", "optimized_incremental", "independent_full"]:
                nodes = p["stages"][key]["result"]["nodes"]
                tests = [n for n in nodes if n["node"].startswith("test.")]
                require(len(tests) == 30 and all(n["status"] in ["success", "pass"] for n in nodes), "recorded dbt gates failed")
    require(files["summary.json"]["candidate_promoted"] is False and files["summary.json"]["default_changed"] is False, "candidate incorrectly promoted")
    require(all(t["status"] == "passed" for t in files["software.json"]) and len({t["test"] for t in files["software.json"]}) == expected["software_tests"], "recorded software suite incomplete")
    native = files["snowflake.json"]
    require(native["executed_cloud"] and native["acceptance_passed"] and native["status"] == "passed", "native acceptance missing")
    require(len(native["model_comparison"]) == 15 and all(m["exact_multiset_equal"] and m["column_contract_equal"] and m["full_only_groups"] == m["incremental_only_groups"] == 0 for m in native["model_comparison"]), "native parity failed")
    require(all(d["denied"] for d in native["denied_operations"]) and len(native["denied_operations"]) == 4 and all(native["publication_safety"].values()), "native permission/publication safety failed")
    for name in ["initial_full_build", "corrected_incremental_build", "independent_corrected_full_build"]:
        nodes = files[f"snowflake-{name}.json"]
        require(sum(n["node"].startswith("model.") for n in nodes) == 15 and sum(n["node"].startswith("test.") for n in nodes) == 30 and all(n["status"] in ["success", "pass"] for n in nodes), "native build gate failed")
        require(all(n["query_id"] in native["query_ids"] for n in nodes), "native query lineage missing")
    require(not files["observation.json"]["new_warehouse_execution"] and not files["observation.json"]["new_benchmarks"], "viewer claims new execution")
    return {"models": 15, "metrics": 6, "paired_repetitions": 6, "complete_model_comparisons": 270,
            "recorded_software_tests": expected["software_tests"], "native_models_per_build": 15, "native_tests_per_build": 30,
            "native_query_ids": expected["native"]["query_ids"], "new_warehouse_execution": False}


def verify_original_bytes(path, upstream):
    for a in upstream["artifacts"]:
        require(hashlib.sha256((path / a["file"]).read_bytes()).hexdigest() == a["sha256"], "original analytics bytes differ")
