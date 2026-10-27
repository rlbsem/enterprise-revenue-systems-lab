"""Release integration: current presentation, immutable records and all eight cases."""
import hashlib
import json
import re

import pytest
from revenue_lab.bundle import ROOT, verify

QA = ROOT / "docs/evidence/release-qa-eight"


def test_historical_main_and_typography_artifacts_are_byte_exact():
    before = json.loads((QA / "preserved-files.json").read_bytes())
    for name, checksum in before["sha256"].items():
        assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest() == checksum, name


def test_current_main_contracts_survive_typography_reconciliation():
    baseline = json.loads((QA/"prior-ui-main.json").read_bytes())["files"]
    before = {r["id"]: r for r in json.loads(baseline["web/catalog.json"])["scenarios"]}
    after = {r["id"]: r for r in json.loads((ROOT/"web/catalog.json").read_bytes())["scenarios"]}
    assert set(before) == set(after) and len(after) == 17
    assert len({r["investigation"] for r in after.values()}) == 8
    for key, record in before.items():
        expected = dict(record)
        if key == "revenue-integrity":
            expected["title"] = "Revenue Integrity: From Sales Commitment to Collected Cash"
        assert after[key] == expected, key
    assert json.loads((ROOT/"sources.lock.json").read_bytes()) == json.loads(baseline["sources.lock.json"])
    result = verify(ROOT/"web/evidence/analytics-engineering")["checks"]
    assert result["models"] == 15 and result["paired_repetitions"] == 6 and result["native_query_ids"] == 461


@pytest.mark.parametrize("name", ["presentation", "research", "release", "integrity", "analytics"])
def test_fresh_eight_case_captures_bind_current_source_and_images(name):
    r = json.loads((QA/(name + ".json")).read_bytes())
    folder = ROOT/"docs/images/release-qa-eight"/name
    if name == "presentation":
        assert len(r["reviews"]) == 340 and not r["page_errors"]
        assert r["recorded_cases"] == json.loads((ROOT/"web/catalog.json").read_bytes())["scenarios"]
        for field, path in {"app_sha256":"web/app.js", "stylesheet_sha256":"web/style.css", "html_sha256":"web/index.html", "gtm_sha256":"web/gtm.js", "catalog_sha256":"web/catalog.json"}.items():
            assert hashlib.sha256((ROOT/path).read_bytes()).hexdigest() == r[field]
        assert all(not v["overflow"] and not v["contrast"]["failures"] for v in r["reviews"])
        for file, meta in r["images"].items():
            assert hashlib.sha256((folder/file).read_bytes()).hexdigest() == meta["sha256"]
    else:
        assert not r["page_errors"]
        assert all(not v["overflow"] and not v["contrast"]["failures"] for v in r["layouts"])
        states = r["accessibility"].values() if isinstance(r["accessibility"], dict) else r["accessibility"]
        assert all(not v["violations"] for v in states)
        for file, checksum in r["source_sha256"].items():
            assert hashlib.sha256((ROOT/file).read_bytes()).hexdigest() == checksum, file
        for file, checksum in r["image_sha256"].items():
            assert hashlib.sha256((folder/file).read_bytes()).hexdigest() == checksum, file


def test_readme_images_use_fresh_release_captures_without_losing_routes():
    text = (ROOT/"README.md").read_text(encoding="utf-8")
    images = re.findall(r'<img src="([^"]+)"', text)
    assert images and all(p.startswith("docs/images/release-qa-eight/") for p in images)
    assert all((ROOT/p).is_file() for p in images)
    assert "## Eight investigations" in text
    html = (ROOT/"web/index.html").read_text(encoding="utf-8")
    assert "Eight investigations. Independent evidence." in html
    assert not re.search(r"(?:Six|Seven|six|seven) investigations", html)
    assert not re.search(r"PR #11[^\n]*(?:unmerged|requires.*merge)", text)
