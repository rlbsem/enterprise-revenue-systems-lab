import hashlib
import json
import shutil

import pytest
from revenue_lab.bundle import ROOT, verify
from revenue_lab.analytics_checks import analytics, project
from test_bundles import resign


def records():
    p = ROOT / "web/evidence/analytics-engineering"
    return {a["path"]: json.loads((p/a["path"]).read_bytes()) if a["path"].endswith(".json") else (p/a["path"]).read_bytes().decode()
            for a in json.loads((p/"bundle.json").read_bytes())["artifacts"]}


def test_actual_recorded_benchmarks_models_and_native_boundaries():
    r = verify(ROOT / "web/evidence/analytics-engineering")
    assert r["checks"]["paired_repetitions"] == 6
    assert r["checks"]["native_query_ids"] == 461
    f = records()
    assert f["projection.json"] == project(f)
    assert f["projection.json"]["profiles"]["stress"]["fact_rows"] == 37375442
    assert f["projection.json"]["profiles"]["enterprise"]["accounts"] == 60000
    assert f["projection.json"]["profiles"]["stress"]["accounts"] == 180000
    assert f["summary.json"]["candidate_promoted"] is False


@pytest.mark.parametrize("mutation", ["timing", "summary", "rowset", "model_missing", "test_failed", "native_failed", "native_denial", "native_query", "provenance", "projection", "promoted", "new_run", "local_native", "local_hash", "local_model", "local_gate"])
def test_evidence_cannot_be_relabelled_or_incomplete(mutation):
    f = records()
    if mutation == "timing": f["stress-pair-1.json"]["stages"]["optimized_incremental"]["seconds"] = 0.01
    elif mutation == "summary": f["summary.json"]["profiles"]["stress"]["candidate_wall_change_percent"] = -90
    elif mutation == "rowset": f["enterprise-pair-2.json"]["optimized_full_parity"]["models"][0]["differences"] = 1
    elif mutation == "model_missing": f["stress-pair-3.json"]["baseline_optimized_parity"]["models"].pop()
    elif mutation == "test_failed": f["software.json"][0]["status"] = "failed"
    elif mutation == "native_failed": f["snowflake.json"]["acceptance_passed"] = False
    elif mutation == "native_denial": f["snowflake.json"]["denied_operations"][0]["denied"] = False
    elif mutation == "native_query": f["snowflake-corrected_incremental_build.json"][0]["query_id"] = "invented"
    elif mutation == "provenance": f["upstream.json"]["import_revision"] = "0" * 40
    elif mutation == "projection": f["projection.json"]["profiles"]["stress"]["fact_rows"] += 1
    elif mutation == "promoted": f["summary.json"]["candidate_promoted"] = True
    elif mutation == "local_native": f["fixture-execution.json"]["new_native_execution"] = True
    elif mutation == "local_hash": f["fixture-execution.json"]["source_input_sha256"]["sql/dim_account.sql"] = "0" * 64
    elif mutation == "local_model": del f["fixture-execution.json"]["models"]["dim_account"]
    elif mutation == "local_gate": f["fixture-execution.json"]["build_results"][0]["status"] = "failed"
    else: f["observation.json"]["new_warehouse_execution"] = True
    with pytest.raises(ValueError): analytics(f)


def test_resealing_does_not_allow_changes_to_original_sql(tmp_path):
    p = tmp_path / "bundle"
    shutil.copytree(ROOT / "web/evidence/analytics-engineering", p)
    resign(p, "sql/mart_pipeline.sql", "select 1")
    with pytest.raises(ValueError): verify(p)


def test_git_index_preserves_imported_original_bytes():
    import subprocess
    up = records()["upstream.json"]
    for a in up["artifacts"]:
        path = "web/evidence/analytics-engineering/" + a["file"]
        blob = subprocess.check_output(["git", "show", ":" + path], cwd=ROOT)
        assert hashlib.sha256(blob).hexdigest() == a["sha256"], path


def test_shared_capture_registry_covers_every_investigation():
    import runpy
    registry = runpy.run_path(str(ROOT/"scripts/capture_presentation.py"))["CASES"]
    cases = json.loads((ROOT/"web/catalog.json").read_bytes())["scenarios"]
    assert set(registry) == {c["investigation"] for c in cases}
    assert all(any(c["id"] == scenario and c["investigation"] == key for c in cases) for key, scenario in registry.items())


def test_seven_prior_investigations_and_evidence_are_preserved():
    f = json.loads((ROOT / "docs/evidence/analytics-engineering/preserved-files.json").read_bytes())
    for name, checksum in f["sha256"].items():
        assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest() == checksum, name
    snapshot = json.loads((ROOT / "docs/evidence/analytics-engineering/prior-ui.json").read_bytes())
    before = {r["id"]: r for r in json.loads(snapshot["files"]["web/catalog.json"])["scenarios"]}
    after = {r["id"]: r for r in json.loads((ROOT/"web/catalog.json").read_bytes())["scenarios"]}
    assert set(after) - set(before) == {"analytics-engineering"}
    for k, v in before.items():
        expected = dict(v)
        if k == "revenue-integrity":
            expected["title"] = "Revenue Integrity: From Sales Commitment to Collected Cash"
        assert after[k] == expected
    old = json.loads(snapshot["files"]["sources.lock.json"])
    current = json.loads((ROOT/"sources.lock.json").read_bytes())
    assert all(current["sources"][k] == v for k, v in old["sources"].items())


def test_public_analytics_has_no_live_warehouse_or_private_material():
    import re
    code = (ROOT/"web/analytics.js").read_text(encoding="utf-8")
    assert not re.search(r"\b(fetch|XMLHttpRequest|WebSocket|sendBeacon)\b", code)
    for p in (ROOT/"web/evidence/analytics-engineering").rglob("*"):
        if not p.is_file() or p.suffix == ".zip": continue
        data = p.read_text(encoding="utf-8")
        assert not re.search(r'"(?:password|access_token|private_key|api_secret)"\s*:', data)
        assert not re.search(r"-----BEGIN (?:RSA )?PRIVATE KEY|(?:AKIA|ASIA)[A-Z0-9]{16}", data)


def test_genuine_rendered_screenshots_and_static_accessibility():
    r = json.loads((ROOT/"docs/evidence/analytics-engineering/browser.json").read_bytes())
    assert len(r["layouts"]) == 40 and len(r["accessibility"]) == 10
    assert not r["http_writes"] and not r["page_errors"] and not r["nonlocal_requests"]
    assert all(not x["overflow"] and not x["contrast"]["failures"] for x in r["layouts"])
    assert all(not x["violations"] for x in r["accessibility"])
    baseline = json.loads((ROOT/"docs/evidence/release-qa-eight/prior-ui-main.json").read_bytes())["files"]
    for name, checksum in r["source_sha256"].items():
        data = baseline[name].encode() if name in baseline else (ROOT/name).read_bytes()
        assert hashlib.sha256(data).hexdigest() == checksum, name
    for name, checksum in r["image_sha256"].items():
        assert hashlib.sha256((ROOT/"docs/images/analytics-engineering"/name).read_bytes()).hexdigest() == checksum, name
