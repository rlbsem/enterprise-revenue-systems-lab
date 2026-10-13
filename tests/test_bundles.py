import copy
import hashlib
import json
import shutil
from pathlib import Path

import pytest
from revenue_lab.bundle import ROOT, digest, verify, write_json
from revenue_lab.cli import run


@pytest.mark.parametrize("name", ["seller-application", "seller-support-review", "seller-stale", "seller-suppressed"])
def test_preserved_and_executed_evidence(name):
    assert verify(ROOT / "web/evidence" / name)["integrity"] == "verified"


@pytest.fixture
def bundle(tmp_path):
    target = tmp_path / "bundle"
    shutil.copytree(ROOT / "web/evidence/seller-application", target)
    return target


@pytest.mark.parametrize("change", ["tamper", "missing", "version", "stale", "duplicate", "traversal", "configuration", "incomplete"])
def test_invalid_bundle_refused(bundle, change):
    manifest = json.loads((bundle / "bundle.json").read_text())
    if change == "tamper":
        (bundle / "application.json").write_text("{}")
    elif change == "missing":
        (bundle / "application.json").unlink()
    elif change == "version":
        manifest["schema_version"] = "2.0"
    elif change == "stale":
        manifest["source"]["commit"] = "a" * 40
    elif change == "duplicate":
        manifest["artifacts"].append(manifest["artifacts"][0])
    elif change == "traversal":
        manifest["artifacts"][0]["path"] = "../secret.json"
    elif change == "configuration":
        manifest["configuration_hash"] = "b" * 64
    else:
        manifest["artifacts"] = manifest["artifacts"][:1]
    write_json(bundle / "bundle.json", manifest)
    with pytest.raises(Exception):
        verify(bundle)


def resign(bundle, name, value):
    write_json(bundle / name, value)
    manifest = json.loads((bundle / "bundle.json").read_text())
    a = next(a for a in manifest["artifacts"] if a["path"] == name)
    raw = (bundle / name).read_bytes()
    a.update(sha256=hashlib.sha256(raw).hexdigest(), bytes=len(raw))
    write_json(bundle / "bundle.json", manifest)


@pytest.mark.parametrize("change", ["receipt", "quote", "approval", "authority"])
def test_valid_hash_does_not_prove_business_relationship(bundle, change):
    app = json.loads((bundle / "application.json").read_text())
    action = app["actions"][0]
    if change == "receipt":
        receipt = json.loads(action["receipt"])
        receipt["payload_hash"] = "wrong"
        action["receipt"] = json.dumps(receipt)
    elif change == "quote":
        app["runs"][0]["proposal"]["claims"][0]["quote"] = "Invented commitment"
    elif change == "approval":
        app["audit"] = [a for a in app["audit"] if a["action"] != "proposal_approved"]
    else:
        payload = json.loads(action["payload"])
        payload["evidence_hash"] = "changed"
        action["payload"] = json.dumps(payload)
    resign(bundle, "application.json", app)
    with pytest.raises(ValueError):
        verify(bundle)


def test_runner_rejects_arbitrary_command():
    with pytest.raises(ValueError, match="not approved"):
        run("shell rm everything")


def test_review_does_not_claim_independent_usefulness():
    checks = verify(ROOT / "web/evidence/seller-support-review")["checks"]
    assert checks["quality"] == "unsupported_availability_statement_preserved"
    assert checks["independent_usefulness"] == "pending"
