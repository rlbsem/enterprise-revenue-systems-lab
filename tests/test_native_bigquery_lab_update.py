"""Guard the additive native BigQuery Lab stage without rewriting old evidence."""
from pathlib import Path
import json
import re

ROOT = Path(__file__).resolve().parents[1]
SOURCE = "8259a65a6a9ceb3ccb08827733ab6a703c2de99d"
PLAN = "137a97bfc54a05f9cfab55eec22ed3ec3c31f21b8b135c7ff8a3fb99ca795d0f"


def test_native_dbt_addendum_is_distinct_from_historical_bundle():
    original = json.loads((ROOT / "web/evidence/warehouse-verification/bundle.json").read_text())
    original_projection = json.loads(
        (ROOT / "web/evidence/warehouse-verification/projection.json").read_text()
    )
    code = (ROOT / "web/native-bigquery.js").read_text()
    assert original["source"]["commit"] == "a1438e3eef101e23d61f0fd7889272098e50f9f6"
    assert original_projection["native_dbt_build"] is False
    assert original_projection["native_incremental_merge"] is False
    assert SOURCE in code and PLAN in code
    assert "d59a1ff0-0672-4543-88cc-806a61990676" in code
    assert "f9581672-4e00-486f-909c-ae14e8636b72" in code
    assert 'affectedRows: 6' in code and 'affectedRows: 0' in code
    assert 'terminalJobs: 178' in code
    assert 'productionGA4Export: false' in code
    assert 'actualBillingClearanceVerified: false' in code
    assert 'three datasets' in (ROOT / "docs/integration-economics.md").read_text()


def test_warehouse_extension_is_read_only_and_existing_navigation_is_preserved():
    code = (ROOT / "web/warehouse.js").read_text()
    addendum = (ROOT / "web/native-bigquery.js").read_text()
    app = (ROOT / "web/app.js").read_text()
    assert "['native-dbt','01 · Native BigQuery MERGE']" in code
    for stage in ("native", "local", "guard", "boundary"):
        assert "[data-evidence-stage=\"" + stage + "\"]" not in code  # stage controls use IDs
        assert "'" + stage + "'" in code
    assert "warehouse-verification" in app
    assert "Historical October bundle only" in app
    for source in (code, addendum):
        assert not re.search(r"\\b(fetch|XMLHttpRequest|WebSocket|sendBeacon|innerHTML)\\b", source)
    catalog = json.loads((ROOT / "web/catalog.json").read_text())
    assert len(catalog["scenarios"]) == 23
    assert len({e["investigation"] for e in catalog["scenarios"]}) == 13
    entry = next(e for e in catalog["scenarios"] if e["id"] == "warehouse-verification")
    assert entry["source"]["commit"] == "a1438e3eef101e23d61f0fd7889272098e50f9f6"
    assert "native dbt MERGE" in entry["title"]
