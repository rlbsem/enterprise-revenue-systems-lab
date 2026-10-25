"""Read-only checks of the pinned, finite Revenue Integrity scenario. No source engine imports."""
import ast
import hashlib
from datetime import datetime

from .bundle import LOCK, digest
from .gtm_checks import require


def calculate(lifecycle):
    """Reconcile raw exported invoice, amendment, adjustment and allocation grains."""
    snap = lifecycle["source_snapshot"]
    period = snap["period"]
    records, heads = [], {}
    for export in snap["snapshots"]:
        require(export["complete_local_snapshot"] and digest(export["contents"]) == export["content_hash"], "incomplete financial export")
        source = export["service"]
        records += [{**r, "source": source} for r in export["contents"].get("records", [])]
        for e in export["contents"].get("source_events", []):
            if datetime.fromisoformat(e["observed_source_at"]) <= datetime.fromisoformat(period["known_at"]):
                k = (source, e["tenant"], e["entity"], e["logical_id"])
                if k not in heads or e["revision"] > heads[k][1]["revision"]:
                    heads[k] = (source, e)
    rows = []
    for inv in records:
        if inv["source"] != "stripe" or inv["kind"] != "invoice" or not period["start"] <= inv["invoice_date"] < period["end_exclusive"]:
            continue
        related = [r for r in records if r.get("invoice_id") == inv["id"]]
        lines = [r for r in related if r["kind"] == "invoice_line"]
        require(lines and sum(r["amount_cents"] for r in lines) == inv["amount_cents"], "invoice header/line mismatch")
        require(all((r["tenant"], r["entity"], r["canonical_account"]) == (inv["tenant"], inv["entity"], inv["canonical_account"]) for r in related), "financial relationship scope mismatch")
        adjustments = [(src, e) for src, e in heads.values() if e["invoice_id"] == inv["id"] and period["start"] <= e["effective_date"] < period["end_exclusive"]]
        amendment = sum(r["amount_cents"] for r in related if r["kind"] == "amendment_line" and datetime.fromisoformat(r["observed_source_at"]) <= datetime.fromisoformat(period["known_at"]))
        billing_adjust = sum(e["amount_cents"] * (-1 if e["kind"] == "credit" else 1) for src, e in adjustments if src == "stripe")
        erp_adjust = sum(e["amount_cents"] * (-1 if e["kind"] == "credit_posting" else 1) for src, e in adjustments if src == "netsuite")
        posts = [r for r in related if r["source"] == "netsuite" and r["kind"] in ("posting", "change_posting") and period["start"] <= r["posting_date"] < period["end_exclusive"] and datetime.fromisoformat(r.get("observed_source_at", "2025-01-01T00:00:00+00:00")) <= datetime.fromisoformat(period["known_at"])]
        allocations = [r for r in related if r["source"] == "stripe" and r["kind"] == "payment_allocation" and period["start"] <= r["payment_date"] < period["end_exclusive"]]
        for a in allocations:
            payment = next(r for r in records if r["source"] == "stripe" and r["kind"] == "payment" and r["id"] == a["payment_id"])
            require(a["amount_cents"] <= payment["amount_cents"], "allocation exceeds payment")
        sub = next(r for r in records if r["source"] == "stripe" and r["kind"] == "subscription" and r["id"] == inv["subscription_id"])
        contract = next(r for x in snap["snapshots"] if x["service"] == "salesforce" for r in x["contents"]["contracts"] if r["contract_id"] == sub["contract_id"] and (r["tenant"], r["entity"]) == (inv["tenant"], inv["entity"]))
        mappings = [r for r in snap["mappings"] if (r["tenant"], r["entity"], r["canonical_account"]) == (inv["tenant"], inv["entity"], inv["canonical_account"])]
        rows.append({"invoice_id": inv["id"], "entity": inv["entity"], "account": inv["canonical_account"], "contract": contract,
            "mappings": mappings, "subscription": sub, "invoice": inv, "invoice_lines": lines,
            "amendments": [r for r in related if r["kind"] == "amendment_line"], "adjustments": [e for _, e in adjustments],
            "postings": posts, "allocations": allocations, "initial_cents": inv["amount_cents"],
            "amendment_cents": amendment, "billing_adjustment_cents": billing_adjust,
            "billing_cents": inv["amount_cents"] + amendment + billing_adjust,
            "erp_cents": sum(r["amount_cents"] for r in posts) + erp_adjust,
            "cash_cents": sum(r["amount_cents"] for r in allocations)})
    totals = {k: sum(r[k] for r in rows) for k in ("billing_cents", "erp_cents", "cash_cents")}
    # Independent March 31 stock, not joined through invoice activity.
    arr = 0
    for sub in [r for r in records if r["source"] == "stripe" and r["kind"] == "subscription" and r["effective_start"] <= "2026-03-31" < r["effective_end"]]:
        item = next(r for r in records if r["kind"] == "subscription_item" and r["subscription_id"] == sub["id"])
        latest = {}
        for r in records:
            if r["kind"] == "subscription_change" and r["contract_id"] == sub["contract_id"]:
                e = r["change"]
                if datetime.fromisoformat(e["observed_source_at"]) <= datetime.fromisoformat(period["known_at"]) and (e["change_id"] not in latest or latest[e["change_id"]]["revision"] < e["revision"]):
                    latest[e["change_id"]] = e
        active = [e for e in latest.values() if e["effective_start"] <= "2026-03-31" < e["effective_end"]]
        basis = max(active, key=lambda e: (e["effective_start"], e["revision"])) if active else item
        arr += basis["unit_monthly_cents"] * basis["quantity"] * 12
    totals.update(arr_cents=arr, variance_cents=totals["billing_cents"] - totals["erp_cents"])
    return rows, totals


def project(files):
    rows, before = calculate(files["lifecycle.json"])
    browser = files["operator-browser.json"]
    # Read fixture constants without executing privileged source code.
    fn = next(n for n in ast.parse(files["source-console.py"]).body if isinstance(n, ast.FunctionDef) and n.name == "seed_recovery")
    definition = next(n.value for n in fn.body if isinstance(n, ast.Assign) and isinstance(n.value, ast.Dict))
    constants = {ast.literal_eval(k): ast.literal_eval(v) for k, v in zip(definition.keys, definition.values) if k is not None and isinstance(v, ast.Constant)}
    monthly = constants["unit_monthly_cents"] * constants["quantity"]
    after = {"billing_cents": int(browser["final"]["billing_cents"]), "erp_cents": int(browser["final"]["erp_cents"]),
        "cash_cents": before["cash_cents"], "arr_cents": before["arr_cents"] + monthly * 12}
    after["variance_cents"] = after["billing_cents"] - after["erp_cents"]
    return {"currency": "USD", "period": files["lifecycle.json"]["source_snapshot"]["period"],
        "before": before, "after": after, "lineage": sorted(rows, key=lambda r: r["entity"]),
        "recovery": {"event_id": constants["event_id"], "monthly_cents": monthly, "quarter_cents": monthly * 3,
            "basis": "Versioned fixture plus archived browser assertions; full recovery approval/attempt rows were not archived."},
        "derivation": "Lifecycle amounts recalculated from raw exports. Post-recovery billing/ERP are archived browser totals; cash/ARR use source fixture arithmetic corroborated by executed browser assertions."}


def integrity(files):
    upstream = files["upstream.json"]
    require(upstream == LOCK["integrity_import"], "integrity provenance mismatch")
    require(files["projection.json"] == project(files), "integrity display projection mismatch")
    p, life, browser, delivery = files["projection.json"], files["lifecycle.json"], files["operator-browser.json"], files["delivery.json"]
    require(p["before"] == dict(billing_cents=3900000, erp_cents=3750000, cash_cents=1650000, arr_cents=12000000, variance_cents=150000), "lifecycle financial scenario mismatch")
    require(p["after"] == dict(billing_cents=4560000, erp_cents=4410000, cash_cents=1650000, arr_cents=14640000, variance_cents=150000), "recovery financial scenario mismatch")
    require(int(browser["initial"]["billing_cents"]) == p["before"]["billing_cents"] and int(browser["initial"]["erp_cents"]) == p["before"]["erp_cents"], "operator baseline differs")
    required = ["rejection did not dispatch", "actual approved effect and dependent finance verified", "recovery budget persisted", "cash remains 16500", "rechecked ARR 146400", "original 1500 variance still open"]
    require(all(c in browser["cases"] for c in required) and not browser["errors"] and all(not a["violations"] for a in browser["accessibility"]), "archived operator assertions missing")
    for row in p["lineage"]:
        expected = next(r for r in life["current_release"]["rows"] if r["invoice_id"] == row["invoice_id"])
        require(all(row[k] == expected[v] for k, v in [("billing_cents", "billing_net_cents"), ("erp_cents", "erp_net_cents"), ("cash_cents", "allocated_cash_cents")]), "raw source and mart differ")
    bridge = life["current_release"]["variance_bridge"]["entries"]
    require(any(e["category"] == "unposted_adjustment_requires_review" and e["amount_cents"] == -p["before"]["variance_cents"] for e in bridge), "unresolved variance hidden")
    require(life["six_model_exact_equivalence"] and life["portability"]["snowflake_native_execution"] is False, "warehouse boundary mismatch")
    for name in ["incremental", "independent_full"]:
        gate = life[name]
        require(gate["models"] == 6 and gate["tests"] == 23 and all(r["status"] in ["pass", "success"] for r in gate["results"]), "source dbt gate failed")
    count = 0
    for destination in ("stripe", "netsuite"):
        for record in delivery["persisted_state"][destination]["records"]:
            body = record["body"]
            require(body["currency"] == "USD" and (body["tenant"], body["entity"], body["kind"], body["id"]) == (record["tenant"], record["entity"], record["kind"], record["id"]), "receiver record envelope mismatch")
    for intent in delivery["persisted_state"]["control"]["outbox"]:
        receiver = delivery["persisted_state"][intent["destination"]]
        effect = next(e for e in receiver["effects"] if e["effect_id"] == intent["effect_id"])
        proof = effect["receipt"]
        require(intent["status"] == "verified" and intent["proof"] == proof and proof["payload"] == intent["payload"] and digest(proof["payload"]) == intent["hash"] == effect["hash"] and digest(proof["records"]) == proof["records_hash"], "delivery receipt mismatch")
        for r in proof["records"]:
            require(next(x["body"] for x in receiver["records"] if (x["kind"], x["id"]) == (r["kind"], r["id"])) == r, "receiver record mismatch")
        count += 1
    require(delivery["lost_ack"]["remote_committed_before_recovery"] == 1 and delivery["lost_ack"]["recovered"], "lost acknowledgment not established")
    require(files["process-death.json"]["actual_subprocess_terminated"] and files["process-death.json"]["remote_effects_after_restart"] == 1, "process death recovery missing")
    require(files["history-rehydration.json"]["remote_posts"] == 0 and files["history-rehydration.json"]["safe_to_resume"], "history repair boundary mismatch")
    software = files["software.json"]
    require(software["test_count"] == 60 and all(software[k] == 0 for k in ["failures", "errors", "skipped"]), "software evidence failed")
    require(files["observation.json"]["new_effects"] is False, "viewer claims new actions")
    return {"raw_invoice_traces": len(p["lineage"]), "verified_receiver_effects": count, "unresolved_variance_cents": p["before"]["variance_cents"],
        "recorded_software_tests": software["test_count"], "recorded_browser_assertions": len(browser["cases"]),
        "dbt_models": 6, "dbt_tests_per_build": 23, "new_vendor_calls": False, "new_financial_effects": False}


def verify_original_bytes(path, upstream):
    for a in upstream["artifacts"]:
        require(hashlib.sha256((path / a["file"]).read_bytes()).hexdigest() == a["sha256"], "original integrity bytes differ")
