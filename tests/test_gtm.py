"""Recorded GTM arithmetic, authority, provenance and browser boundaries."""

import json
import hashlib
import shutil

import pytest

from revenue_lab.bundle import ROOT, verify
from revenue_lab.gtm_checks import pipeline, salesforce, qwen
from test_bundles import resign


def artifacts(case):
    path = ROOT / "web/evidence" / case
    manifest = json.loads((path / "bundle.json").read_text())
    return {a["path"]: (json.loads((path / a["path"]).read_text(encoding="utf-8")) if a["path"].endswith(".json")
                         else (path / a["path"]).read_text(encoding="utf-8")) for a in manifest["artifacts"]}


@pytest.mark.parametrize("case", ["gtm-enterprise", "gtm-salesforce", "gtm-qwen"])
def test_gtm_bundles_verify_without_engine_or_vendor(case):
    report = verify(ROOT / "web/evidence" / case)
    assert report["integrity"] == "verified"
    assert report["checks"]["new_vendor_or_model_execution"] is False


@pytest.mark.parametrize("mutation", ["currency", "amount", "denominator", "approval", "leakage", "source", "scope"])
def test_gtm_pipeline_rejects_inconsistent_business_evidence(mutation):
    f = artifacts("gtm-enterprise")
    d = f["execution.json"]
    if mutation == "currency":
        d["scenario"]["currency"] = "CAD"
    elif mutation == "amount":
        d["measurement"]["arms"]["treatment"]["pipeline_cents"] += 1
    elif mutation == "denominator":
        d["measurement"]["arms"]["holdout"]["assigned"] -= 1
    elif mutation == "approval":
        d["audit"] = [a for a in d["audit"] if a["event"] != "exact_approval"]
    elif mutation == "leakage":
        d["measurement"]["leakage_accounts"] = ["holdout-account"]
    elif mutation == "source":
        d["source_records"][0]["payload_hash"] = "0" * 64
    else:
        d["scenario"]["scope_quotes"][0]["sites"] += 1
    with pytest.raises(ValueError):
        pipeline(f)


@pytest.mark.parametrize("mutation", ["relationship", "reader", "receipt", "grant", "cleanup"])
def test_native_gtm_relationships_and_permissions_are_not_a_success_flag(mutation):
    f = artifacts("gtm-salesforce")
    n = f["native-details.json"]
    if mutation == "relationship":
        n["relationships"]["task_contact_id_hash"] = "wrong"
    elif mutation == "reader":
        n["relationships"]["task_created_by_hash"] = n["relationships"]["independent_reader_hash"]
    elif mutation == "receipt":
        f["acceptance.json"]["receipt"]["task_count"] = 2
    elif mutation == "grant":
        n["effective_permissions"]["integration"]["Account"]["updateable"] = True
    else:
        f["post-cleanup.json"]["original_assignments_exactly_restored"] = False
    with pytest.raises(ValueError):
        salesforce(f)


@pytest.mark.parametrize("mutation", ["citation", "context", "authority", "failure_count", "instructions", "request"])
def test_qwen_exact_response_and_limitations_are_preserved(mutation):
    f = artifacts("gtm-qwen")
    d = f["evaluation.json"]
    r = d["records"][0]
    if mutation == "citation":
        parsed = json.loads(r["raw_response"])
        parsed["citations"][0]["quote"] = "An unsupported guarantee"
        r["parsed"] = parsed
        r["raw_response"] = json.dumps(parsed)
    elif mutation == "context":
        r["context"]["account"]["owner"] = "different-owner"
    elif mutation == "authority":
        r["advisory_only"] = False
    elif mutation == "instructions":
        f["instructions.json"]["system_prompt"] = "Invent a guarantee"
    elif mutation == "request":
        r["request_hash"] = "0" * 64
    else:
        d["exact_citation_checks_passed"] = 16
    with pytest.raises(ValueError):
        qwen(f)


@pytest.mark.parametrize("field", ["new_vendor_execution", "new_model_execution", "continuous_vendor_workflow"])
def test_gtm_lane_conflation_is_rejected_even_after_resigning(tmp_path, field):
    target = tmp_path / "bundle"
    shutil.copytree(ROOT / "web/evidence/gtm-enterprise", target)
    obs = json.loads((target / "observation.json").read_text())
    obs[field] = True
    resign(target, "observation.json", obs)
    with pytest.raises(ValueError, match="conflated"):
        verify(target)


def test_original_gtm_bytes_are_independently_pinned(tmp_path):
    target = tmp_path / "bundle"
    shutil.copytree(ROOT / "web/evidence/gtm-qwen", target)
    data = artifacts("gtm-qwen")["evaluation.json"]
    data["boundary"] = "changed evidence"
    resign(target, "evaluation.json", data)
    with pytest.raises(ValueError, match="upstream artifact bytes changed"):
        verify(target)


def test_original_four_investigations_and_screenshots_remain_byte_preserved():
    record = json.loads((ROOT / "docs/evidence/gtm-integration/preserved-files.json").read_text())
    assert len(record["sha256"]) > 100
    for path, expected in record["sha256"].items():
        assert hashlib.sha256((ROOT / path).read_bytes()).hexdigest() == expected, path


def test_gtm_screenshot_provenance_matches_actual_ui_and_images():
    record = json.loads((ROOT / "docs/evidence/gtm-integration/browser.json").read_text())
    for field, name in [("stylesheet_sha256", "style.css"), ("app_sha256", "app.js"),
                        ("gtm_sha256", "gtm.js"), ("html_sha256", "index.html"), ("catalog_sha256", "catalog.json")]:
        assert hashlib.sha256((ROOT / "web" / name).read_bytes()).hexdigest() == record[field]
    assert len(record["reviews"]) == 60 and len(record["images"]) == 6
    assert record["page_errors"] == []
    for review in record["reviews"]:
        assert not review["overflow"] and review["contrast"]["failures"] == []
    for name, detail in record["images"].items():
        assert hashlib.sha256((ROOT / "docs/images/gtm" / name).read_bytes()).hexdigest() == detail["sha256"]


@pytest.mark.parametrize("case", ["gtm-enterprise", "gtm-salesforce", "gtm-qwen"])
def test_utf8_portable_artifacts_preserve_original_bytes(case):
    path = ROOT / "web/evidence" / case
    portable = json.loads((path / "portable.json").read_text(encoding="utf-8"))
    for entry in portable["manifest"]["artifacts"]:
        assert portable["artifacts"][entry["path"]].encode("utf-8") == (path / entry["path"]).read_bytes()
