import copy
import json
import shutil

import pytest
from revenue_lab.bundle import ROOT, verify
from test_bundles import resign


def test_connected_native_bundle():
    proof = verify(ROOT / "web/evidence/connected-roundtrip")
    assert proof["integrity"] == "verified"
    assert proof["checks"]["warehouse_transition"] == "clarify_need -> hold"
    assert proof["checks"]["independent_receiver_effects"] == 1


@pytest.mark.parametrize("change", [
    "extra_review", "old_review", "wrong_account", "missing_receipt",
    "second_post", "warehouse_hold", "source_hash", "cleanup", "claimed_cloud_rerun",
])
def test_connected_claims_reject_resigned_tampering(tmp_path, change):
    path = tmp_path / "connected"
    shutil.copytree(ROOT / "web/evidence/connected-roundtrip", path)
    name = "source-after.json" if change in {"extra_review", "old_review", "wrong_account"} else "observation.json"
    item = json.loads((path / name).read_text())
    if change == "extra_review":
        item["body"]["reviews"].append(copy.deepcopy(item["body"]["reviews"][0]))
    elif change == "old_review":
        item["body"]["reviews"][1]["review_status"] = "Pending"
    elif change == "wrong_account":
        item["body"]["reviews"][0]["account_source_ref"] = "wrong"
    elif change == "missing_receipt":
        item["delivery"]["readback_independent"] = False
    elif change == "second_post":
        item["delivery"]["post_requests"] = 2
    elif change == "warehouse_hold":
        item["feedback_decision"]["decision_action"] = "clarify_need"
    elif change == "source_hash":
        item["source_business_hash_after"] = "bad"
    elif change == "cleanup":
        item["cleanup"]["remaining_schemas"] = 1
    else:
        item["new_vendor_execution"] = True
    resign(path, name, item)
    with pytest.raises(ValueError):
        verify(path)
