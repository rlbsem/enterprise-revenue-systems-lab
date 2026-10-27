import hashlib
import json
import shutil

import pytest
from revenue_lab.bundle import ROOT, verify
from revenue_lab.integrity_checks import integrity, project
from test_bundles import resign

def records():
    p=ROOT/"web/evidence/revenue-integrity"
    return {a["path"]: json.loads((p/a["path"]).read_bytes()) if a["path"].endswith(".json") else (p/a["path"]).read_bytes().decode()
            for a in json.loads((p/"bundle.json").read_bytes())["artifacts"]}

def test_recorded_integrity_source_money_and_independent_receipts():
    r=verify(ROOT/"web/evidence/revenue-integrity")
    assert r["checks"]["raw_invoice_traces"]==2
    assert r["checks"]["verified_receiver_effects"]==4
    assert r["checks"]["unresolved_variance_cents"]==150000
    assert r["checks"]["recorded_browser_assertions"]==43
    assert r["checks"]["new_vendor_calls"] is False
    assert records()["projection.json"]==project(records())

@pytest.mark.parametrize("mutation",["money","arr","variance","receipt","record","assertion","new_effect","provenance","dbt","projection"])
def test_financial_evidence_rejects_false_or_incomplete_claims(mutation):
    f=records()
    if mutation=="money":f["lifecycle.json"]["source_snapshot"]["snapshots"][1]["contents"]["records"][0]["amount_cents"]=1
    elif mutation=="arr":f["projection.json"]["after"]["arr_cents"]+=1
    elif mutation=="variance":f["lifecycle.json"]["current_release"]["variance_bridge"]["entries"]=[]
    elif mutation=="receipt":f["delivery.json"]["persisted_state"]["stripe"]["effects"][0]["receipt"]["records_hash"]="0"*64
    elif mutation=="record":f["delivery.json"]["persisted_state"]["stripe"]["records"][1]["body"]["currency"]="CAD"
    elif mutation=="assertion":f["operator-browser.json"]["cases"].remove("original 1500 variance still open")
    elif mutation=="new_effect":f["observation.json"]["new_effects"]=True
    elif mutation=="provenance":f["upstream.json"]["import_revision"]="0"*40
    elif mutation=="dbt":f["lifecycle.json"]["incremental"]["results"][0]["status"]="fail"
    else:f["projection.json"]["recovery"]["basis"]="fictional live approval"
    with pytest.raises(ValueError):integrity(f)

def test_resealing_cannot_change_upstream_original_bytes(tmp_path):
    p=tmp_path/"bundle";shutil.copytree(ROOT/"web/evidence/revenue-integrity",p)
    d=json.loads((p/"software.json").read_bytes());d["test_count"]+=1
    resign(p,"software.json",d)
    with pytest.raises(ValueError,match="original integrity bytes differ"):verify(p)

def test_six_prior_investigations_remain_exact_and_routes_preserved():
    r=json.loads((ROOT/"docs/evidence/revenue-integrity/preserved-files.json").read_bytes())
    for name,h in r["sha256"].items():assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==h,name
    snap=json.loads((ROOT/"docs/evidence/revenue-integrity/prior-release-ui.json").read_bytes())
    before={x["id"]:x for x in json.loads(snap["files"]["web/catalog.json"])["scenarios"]}
    after={x["id"]:x for x in json.loads((ROOT/"web/catalog.json").read_bytes())["scenarios"]}
    assert set(after)-set(before)=={"revenue-integrity", "analytics-engineering"}
    assert all(after[k]==v for k,v in before.items())

def test_genuine_screenshot_provenance():
    r=json.loads((ROOT/"docs/evidence/revenue-integrity/browser.json").read_bytes())
    assert len(r["layouts"])==40 and len(r["accessibility"])==10
    assert r["http_writes"]==r["nonlocal_requests"]==r["page_errors"]==[]
    for x in r["layouts"]:assert not x["overflow"] and not x["contrast"]["failures"]
    for x in r["accessibility"]:assert not x["violations"]
    baseline=json.loads((ROOT/"docs/evidence/analytics-engineering/prior-ui.json").read_bytes())["files"]
    main=json.loads((ROOT/"docs/evidence/release-qa-eight/prior-ui-main.json").read_bytes())["files"]
    for n,h in r["source_sha256"].items():
        data=baseline[n].encode() if n in baseline else main[n].encode() if n in main else (ROOT/n).read_bytes()
        assert hashlib.sha256(data).hexdigest()==h,n
    for n,h in r["image_sha256"].items():assert hashlib.sha256((ROOT/"docs/images/revenue-integrity"/n).read_bytes()).hexdigest()==h

def test_public_investigation_has_no_live_operator_connection_or_credentials():
    import re
    code=(ROOT/"web/integrity.js").read_text(encoding="utf-8")
    assert not re.search(r"\b(fetch|XMLHttpRequest|WebSocket|sendBeacon)\b",code)
    for path in (ROOT/"web/evidence/revenue-integrity").glob("*.json"):
        text=path.read_bytes().decode()
        assert not re.search(r'"(?:control_dsn|password|access_token|api_secret|private_key)"\s*:',text)
        assert not re.search(r"postgres(?:ql)?://|-----BEGIN (?:RSA )?PRIVATE KEY|(?:AKIA|ASIA)[A-Z0-9]{16}",text)
