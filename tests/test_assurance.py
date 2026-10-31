"""Pinned original records, independent offline checks and immutable nine-case history."""

from copy import deepcopy
import hashlib
import json

import pytest

from revenue_lab.bundle import ROOT, LOCK, load_verified, verify
from revenue_lab.assurance_checks import project, exact

CASES = ["estate-assurance","reliability-operations","temporal-assurance"]


@pytest.mark.parametrize("case",CASES)
def test_original_bytes_and_offline_domain_relationships(case):
    manifest,files = load_verified(ROOT/"web/evidence"/case)
    result = verify(ROOT/"web/evidence"/case)
    assert manifest["mode"] == "recorded"
    assert files["observation.json"]["new_source_execution"] is False
    assert result["integrity"] == "verified"
    assert result["checks"]["native_external_execution"] is False
    assert exact(project(case,files),files["projection.json"])
    for a in LOCK["assurance_imports"][case]["artifacts"]:
        assert hashlib.sha256((ROOT/"web/evidence"/case/a["file"]).read_bytes()).hexdigest()==a["sha256"]


def test_original_nine_investigations_eighteen_cases_and_476_artifacts_unchanged():
    folder=ROOT/"docs/evidence/architecture-assurance"
    for name,h in json.loads((folder/"preserved-main.json").read_bytes())["sha256"].items():
        assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==h,name
    old=json.loads((folder/"prior-main-ui.json").read_bytes())["files"]
    before={r["id"]:r for r in json.loads(old["web/catalog.json"])["scenarios"]}
    after={r["id"]:r for r in json.loads((ROOT/"web/catalog.json").read_bytes())["scenarios"]}
    assert len(before)==18 and len(after)==23
    assert set(after)-set(before)==set(CASES)|{"economics-integration","warehouse-verification"}
    assert all(after[k]==v for k,v in before.items())
    assert len({v["investigation"] for v in after.values()})==13
    old_lock=json.loads(old["sources.lock.json"])
    assert all(LOCK[k]==v for k,v in old_lock.items() if k!="sources")
    assert all(LOCK["sources"][k]==v for k,v in old_lock["sources"].items())


@pytest.mark.parametrize("case",CASES)
def test_tampered_original_rejected_before_presentation(tmp_path,case):
    import shutil
    original=ROOT/"web/evidence"/case
    path=tmp_path/case
    shutil.copytree(original,path)
    (path/"record.json").write_bytes(b'{}')
    with pytest.raises(ValueError,match="artifact integrity mismatch"):
        verify(path)


@pytest.mark.parametrize("mutation",["scope_gate","unknown_owner","oracle","accepted_authority"])
def test_estate_false_clean_and_changed_comparisons_fail(mutation):
    _,f=load_verified(ROOT/"web/evidence/estate-assurance")
    f=deepcopy(f)
    record=f["record.json"]
    if mutation=="scope_gate":
        v=next(v for v in record["versions"] if v["id"]=="retirement")
        v["gates"]["ready"]=True
    elif mutation=="unknown_owner":
        record["snapshot"]["facts"]["ownership:atlas/workbench"]["state"]="SUPPORTED"
    elif mutation=="oracle":
        f["comparison.json"]["comparisons"][0]["independent"]["atlas/cycle-a"]="SUPPORTED"
    else:
        v=next(v for v in record["versions"] if v["state"]=="ACCEPTED")
        v["decisions"] = []
    with pytest.raises(ValueError):project("estate-assurance",f)


@pytest.mark.parametrize("mutation",["amount","raw_bytes","checkpoint","receipt_identity","lineage","row_accounting","wrong_candidate"])
def test_reliability_source_to_publication_negative_cases(mutation):
    _,f=load_verified(ROOT/"web/evidence/reliability-operations")
    f=deepcopy(f);r=f["record.json"];s=r["snapshot"]
    if mutation=="amount":s["warehouse"]["published"][0][3]+=1
    elif mutation=="raw_bytes":s["retained_remote_deliveries"][0]["exact_base64"]="e30="
    elif mutation=="checkpoint":s["journal"]["checkpoints"][0]["seq"]+=1
    elif mutation=="receipt_identity":
        a=r["independent_source_receipts"]["advertising"]["acknowledgments"][0]
        body=json.loads(a["body"]);body["seq"]=True;a["body"]=json.dumps(body)
    elif mutation=="lineage":s["candidates"][-1]["lineage"][0][-1]=2
    elif mutation=="row_accounting":s["warehouse"]["row_dispositions"]["quarantined"]-=1
    else:next(c for c in s["candidates"] if c["name"]=="Equal row count, wrong values")["run"]["status"]="published"
    with pytest.raises((ValueError,KeyError)):project("reliability-operations",f)


@pytest.mark.parametrize("mutation",["historical_decision","brand","permission","business_record","receipt","historical_action"])
def test_temporal_authority_and_recovery_negative_cases(mutation):
    _,f=load_verified(ROOT/"web/evidence/temporal-assurance")
    f=deepcopy(f);r=f["record.json"];o=r["snapshot"]["operating"];receiver=r["snapshot"]["receiver"]
    if mutation=="historical_decision":o["decisions"][0]["member"]=not o["decisions"][0]["member"]
    elif mutation=="brand":o["decisions"][0]["brand"]="nova"
    elif mutation=="permission":o["activation_eligibility"][0]["reason"]="eligible"
    elif mutation=="business_record":receiver["records"][0]["body"]["seq"]=True
    elif mutation=="receipt":receiver["effects"][0]["receipt"]["payload_hash"]="0"*64
    else:r["observations"]["history"]["new_http_actions_from_backfill"]=1
    with pytest.raises((ValueError,KeyError)):project("temporal-assurance",f)


def test_no_vendor_client_or_new_execution_allowlist():
    import re
    code=(ROOT/"web/assurance.js").read_text(encoding="utf-8")
    assert not re.search(r"\b(fetch|XMLHttpRequest|WebSocket|sendBeacon)\s*\(",code)
    from revenue_lab.server import ALLOWED
    assert not set(CASES)&set(ALLOWED)
    for case in CASES:
        for p in (ROOT/"web/evidence"/case).glob("*.json"):
            assert not re.search(r'"(?:access_token|password|api_secret|private_key)"\s*:',p.read_text(encoding="utf-8"))


def test_pages_build_contains_exact_static_files_only():
    from revenue_lab.site import build
    build()
    expected={p.relative_to(ROOT/"web"):p for p in (ROOT/"web").rglob("*") if p.is_file()}
    actual={p.relative_to(ROOT/"dist"):p for p in (ROOT/"dist").rglob("*") if p.is_file()}
    assert actual.keys()==expected.keys()
    for path, source in expected.items():
        assert actual[path].read_bytes()==source.read_bytes()
        assert not any(part in {".git",".local",".venv",".cache"} for part in path.parts)
    # Selected source SQL/Python contracts are evidence, not deployed execution servers.
    assert not (ROOT/"dist/src").exists() and not (ROOT/"dist/api").exists()
