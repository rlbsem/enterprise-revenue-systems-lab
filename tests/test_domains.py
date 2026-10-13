import json
import shutil
import pytest
from revenue_lab.bundle import ROOT, verify
from test_bundles import resign


@pytest.mark.parametrize(
    "name",
    ["control-recovery", "revenue-correction", "revenue-bridge", "seller-delivery"],
)
def test_new_domain_bundles(name):
    assert verify(ROOT / "web/evidence" / name)["integrity"] == "verified"


@pytest.mark.parametrize("change", ["effect", "intent", "receipt", "uncertainty"])
def test_recovery_relationship_failures_with_valid_hashes(tmp_path, change):
    path = tmp_path / "bundle"
    shutil.copytree(ROOT / "web/evidence/control-recovery", path)
    name = (
        "receiver.json"
        if change in ("effect", "receipt")
        else "ledger.json"
        if change == "intent"
        else "stages.json"
    )
    data = json.loads((path / name).read_text())
    if change == "effect":
        data[0]["body"]["revision"] += 1
    elif change == "receipt":
        data[0]["receipt"] = "different-receipt"
    elif change == "intent":
        data["jobs"][0]["mutation"]["payload"]["owner"] = "wrong-owner"
    else:
        stage = next(s for s in data if s["job"]["status"] == "retry")
        stage["effects"] = []
    resign(path, name, data)
    with pytest.raises(ValueError):
        verify(path)


@pytest.mark.parametrize(
    "change", ["source", "metric", "equivalence", "correction", "dbt"]
)
def test_financial_relationship_failures_with_valid_hashes(tmp_path, change):
    path = tmp_path / "bundle"
    shutil.copytree(ROOT / "web/evidence/revenue-correction", path)
    name = {
        "source": "source-records.json",
        "metric": "observation.json",
        "equivalence": "models.json",
        "correction": "models.json",
        "dbt": "dbt-results.json",
    }[change]
    data = json.loads((path / name).read_text())
    if change == "source":
        data["booking_events"][0]["amount_cents"] = str(
            int(data["booking_events"][0]["amount_cents"]) + 100
        )
    elif change == "metric":
        data["measures"]["period_end_arr"] += 100
    elif change == "equivalence":
        data["full"]["daily"][0]["amount_cents"] += 1
    elif change == "correction":
        data["before"]["daily"] = data["incremental"]["daily"]
    else:
        data["full"][0]["status"] = "error"
    resign(path, name, data)
    with pytest.raises(ValueError):
        verify(path)
