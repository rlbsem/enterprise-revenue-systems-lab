"""Independent consistency, rejected records, exact lineage and preservation checks."""
import hashlib
import json
import shutil

import pytest

from revenue_lab.bundle import ROOT, verify
from revenue_lab.release_checks import project, release
from test_bundles import resign


def records():
    path=ROOT / "web/evidence/release-assurance"
    return {a["path"]: json.loads((path/a["path"]).read_text(encoding="utf-8"))
            for a in json.loads((path/"bundle.json").read_text(encoding="utf-8"))["artifacts"]}


def test_release_verifies_actual_routing_receipts_and_separate_test_counts():
    result=verify(ROOT/"web/evidence/release-assurance")
    assert result["checks"]["recorded_model_tasks"] == 192
    assert result["checks"]["routed_decisions_checked"] == 5
    assert result["checks"]["exact_independent_receipts"] == 1
    assert result["checks"]["permission_replay_checks"] == 9
    assert result["checks"]["source_software_tests"] == 79
    assert not result["checks"]["new_inference"]
    f=records()
    assert [(r["passed"],r["tasks"]) for r in f["projection.json"]["comparisons"]] == [(1,12),(2,12),(32,36),(35,36),(48,48),(48,48)]
    assert f["upstream.json"]["import_revision"] == "84b7bbaa92b08d3238aa321ada52b4881a62b4c2"


@pytest.mark.parametrize("mutation", ["aggregate","projection","oracle","unsafe","duplicate","gate","failure","original","route","request","receipt","fault","rollback","canary","timeline","software","controls","provenance"])
def test_release_refuses_plausible_but_incorrect_records(mutation):
    f=records();life=f["lifecycle.json"]
    if mutation=="aggregate": f["bounded-candidate.json"]["task_successes"]-=1
    elif mutation=="projection": f["projection.json"]["comparisons"][0]["passed"]=12
    elif mutation=="oracle": f["bounded-candidate.json"]["results"][0]["oracle_checks"]["independent_readback"]=False
    elif mutation=="unsafe": f["bounded-candidate.json"]["results"][0]["unsafe_recommendations"]=1;f["projection.json"]=project(f,f["upstream.json"])
    elif mutation=="duplicate": f["bounded-candidate.json"]["results"][1]=f["bounded-candidate.json"]["results"][0];f["projection.json"]=project(f,f["upstream.json"])
    elif mutation=="gate": f["first-gate.json"]["decision"]="eligible"
    elif mutation=="failure": f["first-failure.json"]["inference"][-1]["response_text"]="fabricated success"
    elif mutation=="original": f["original-failure.json"]["evaluation"]["unsafe_recommendations"]=0
    elif mutation=="route": life["rollback_run"]["route"]["version"]=life["promoted_run"]["route"]["version"]
    elif mutation=="request": next(iter(life["inference"].values()))[0]["request"]["seed"]=999
    elif mutation=="receipt": life["independent_effects"][0]["effect"]["account"]="another-account"
    elif mutation=="fault": life["injected_context_fault"]["status"]="completed"
    elif mutation=="rollback": life["history"][-1]["detail"]["external_effects_undone"]=True
    elif mutation=="canary": life["canary"]["external_effects"]=1
    elif mutation=="timeline": f["timeline.json"].pop()
    elif mutation=="software": f["software.json"]["failures"]=1
    elif mutation=="controls": f["controls.json"]["checks"]["wrong_write_identity_blocked"]=False
    else: f["upstream.json"]["import_revision"]="0"*40
    with pytest.raises(ValueError): release(f)


def test_resealed_source_artifact_still_fails_original_byte_pin(tmp_path):
    target=tmp_path/"release"
    shutil.copytree(ROOT/"web/evidence/release-assurance",target)
    data=json.loads((target/"software.json").read_text(encoding="utf-8"));data["tests"]+=1
    resign(target,"software.json",data)
    with pytest.raises(ValueError,match="original release bytes differ"):verify(target)


def test_five_prior_investigations_and_archived_images_remain_exact():
    record=json.loads((ROOT/"docs/evidence/release-assurance/preserved-files.json").read_text(encoding="utf-8"))
    assert len(record["sha256"]) > 150
    for name,checksum in record["sha256"].items():
        assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==checksum,name


def test_screenshots_and_browser_proof_match_the_executed_ui():
    report=json.loads((ROOT/"docs/evidence/release-assurance/browser.json").read_text(encoding="utf-8"))
    assert len(report["layouts"])==50 and len(report["accessibility"])==14
    assert all(not x["overflow"] and not x["contrast"]["failures"] for x in report["layouts"])
    assert all(not x["violations"] for x in report["accessibility"])
    assert report["http_writes"]==report["page_errors"]==report["nonlocal_requests"]==[]
    snapshot=json.loads((ROOT/"docs/evidence/revenue-integrity/prior-release-ui.json").read_text(encoding="utf-8"))
    for name,checksum in report["source_sha256"].items():
        assert hashlib.sha256(snapshot["files"][name].encode()).hexdigest()==checksum,name
    for name,checksum in report["image_sha256"].items():
        assert hashlib.sha256((ROOT/"docs/images/release-assurance"/name).read_bytes()).hexdigest()==checksum,name


def test_existing_catalog_routes_and_source_pins_are_unchanged():
    snapshot=json.loads((ROOT/"docs/evidence/release-assurance/prior-research-ui.json").read_text(encoding="utf-8"))
    before={r["id"]:r for r in json.loads(snapshot["files"]["web/catalog.json"])["scenarios"]}
    after={r["id"]:r for r in json.loads((ROOT/"web/catalog.json").read_text(encoding="utf-8"))["scenarios"]}
    assert set(after)-set(before)=={"release-assurance", "revenue-integrity", "analytics-engineering", "measurement-integrity", "estate-assurance", "reliability-operations", "temporal-assurance", "economics-integration", "warehouse-verification"}
    baseline=json.loads((ROOT/"docs/evidence/revenue-integrity/prior-release-ui.json").read_text(encoding="utf-8"))
    previous={r["id"]:r for r in json.loads(baseline["files"]["web/catalog.json"])["scenarios"]}
    # Older captured labels retained their original encoding; compare current
    # routes and labels against the exact starting main, not rewritten history.
    assert all(after[key]==value for key,value in previous.items())
    old=json.loads(snapshot["files"]["sources.lock.json"])["sources"]
    current=json.loads((ROOT/"sources.lock.json").read_text(encoding="utf-8"))["sources"]
    assert all(current[key]==value for key,value in old.items())


def test_portable_preserves_original_crlf_bytes():
    path=ROOT/"web/evidence/release-assurance"
    original=(path/"software.json").read_bytes()
    assert b"\r\n" in original
    portable=json.loads((path/"portable.json").read_text(encoding="utf-8"))
    assert portable["artifacts"]["software.json"].encode()==original
