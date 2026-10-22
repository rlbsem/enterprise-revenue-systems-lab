"""Pinned lineage, negative domain checks and historical preservation for the SDR case."""
import hashlib
import json
import shutil
import zipfile

import pytest

from revenue_lab.bundle import ROOT, verify
from revenue_lab.research_checks import research
from test_gtm import artifacts
from test_bundles import resign


def test_research_bundle_is_separate_and_reproducible_offline(tmp_path):
    path = ROOT / "web/evidence/gtm-research"
    report = verify(path)
    assert report["checks"]["recorded_responses"] == 40
    assert report["checks"]["source_regression_tests"] == 237
    assert report["checks"]["new_vendor_or_model_execution"] is False
    manifest = json.loads((path / "bundle.json").read_text(encoding="utf-8"))
    assert manifest["source"]["commit"] == "81d9381169456ca8893be0ddea483296ac77e12e"
    portable = json.loads((path / "portable.json").read_text(encoding="utf-8"))
    with zipfile.ZipFile(path / "reproduction.zip") as archive:
        assert archive.testzip() is None
        for a in manifest["artifacts"]:
            assert archive.read(a["path"]) == portable["artifacts"][a["path"]].encode() == (path / a["path"]).read_bytes()
        archive.extractall(tmp_path)
    assert verify(tmp_path) == report


@pytest.mark.parametrize("mutation", ["response", "prompt", "citation", "context", "qualitative", "round", "queue", "enrichment", "source", "review", "authority", "operator", "jobs", "regression"])
def test_research_rejects_broken_lineage_and_fabricated_authority(mutation):
    f = artifacts("gtm-research")
    if mutation == "response":
        f["evaluation.json"]["records"].pop()
    elif mutation == "prompt":
        f["round3-evaluation.json"]["records"][0]["prompt"] = "Invent intent"
    elif mutation == "citation":
        r = next(r for r in f["round3-evaluation.json"]["records"] if r["parsed"] and r["parsed"]["facts"])
        r["parsed"]["facts"][0]["quote"] = "not in the source"
    elif mutation == "context":
        f["round1-evaluation.json"]["records"][0]["context"]["crm"]["owner"] = "unknown"
    elif mutation == "qualitative":
        f["reviewer-assessment.json"]["records"].reverse()
    elif mutation == "round":
        f["round3-evaluation.json"]["comparisons"]["evidence-first-v3"]["contract_passes"] = 10
    elif mutation == "queue":
        f["queue.json"][0]["priority"] += 1
    elif mutation == "enrichment":
        f["queue.json"][0]["enrichment"]["values"]["employees"] = 999
    elif mutation == "source":
        f["round3-sources.json"]["src/gtm/research.py"] += "\n# changed"
    elif mutation == "review":
        f["operator-proof.json"]["review"]["opening"] = "A new historical approval"
    elif mutation == "authority":
        f["operator-proof.json"]["review"]["crm_write_authorized"] = True
    elif mutation == "operator":
        f["operator-proof.json"]["record"]["request_hash"] = "0" * 64
    elif mutation == "jobs":
        f["public-jobs.json"]["published_at"] = "2026-01-21"
    else:
        f["regression.json"]["tests"]["tests"] = 999
    with pytest.raises(ValueError):
        research(f)


def test_research_original_bytes_are_pinned_independently_of_bundle_hashes(tmp_path):
    shutil.copytree(ROOT / "web/evidence/gtm-research", tmp_path / "bundle")
    f = artifacts("gtm-research")
    f["evaluation.json"]["limits"] = "changed"
    resign(tmp_path / "bundle", "evaluation.json", f["evaluation.json"])
    with pytest.raises(ValueError, match="upstream artifact bytes changed"):
        verify(tmp_path / "bundle")


def test_prior_lab_evidence_and_images_remain_byte_exact():
    record = json.loads((ROOT / "docs/evidence/research-case/preserved-files.json").read_text(encoding="utf-8"))
    for name, checksum in record["sha256"].items():
        assert hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == checksum, name


def test_current_research_capture_and_ui_provenance():
    record = json.loads((ROOT / "docs/evidence/research-case/browser.json").read_text(encoding="utf-8"))
    for name, checksum in record["source_sha256"].items():
        assert hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == checksum
    for name, checksum in record["image_sha256"].items():
        assert hashlib.sha256((ROOT / "docs/images/research" / name).read_bytes()).hexdigest() == checksum
    assert not record["page_errors"] and not record["nonlocal_requests"]
    assert all(not r["overflow"] and not r["contrast"]["failures"] for r in record["layouts"])
    assert all(not r["violations"] for r in record["accessibility"].values())


def test_static_build_preserves_valid_foreign_zip_metadata_and_repairs_bad_content(tmp_path, monkeypatch):
    from revenue_lab.site import build
    shutil.copytree(ROOT / "web", tmp_path / "web")
    archive = tmp_path / "web/evidence/control-recovery/reproduction.zip"
    with zipfile.ZipFile(archive) as z:
        members = {name: z.read(name) for name in z.namelist()}
    # Simulate an archive originating on a different platform, with distinct metadata.
    with zipfile.ZipFile(archive, "w") as z:
        z.comment = b"same verified contents, foreign packaging metadata"
        for name, data in members.items():
            z.writestr(name, data)
    before = archive.read_bytes()
    monkeypatch.setattr("revenue_lab.site.ROOT", tmp_path)
    build()
    assert archive.read_bytes() == before
    with zipfile.ZipFile(archive, "w") as z:
        for name, data in members.items():
            z.writestr(name, b"corrupt" if name == "bundle.json" else data)
    build()
    with zipfile.ZipFile(archive) as z:
        assert {name: z.read(name) for name in z.namelist()} == members
