"""Independent checks for the recorded native Salesforce/Snowflake review loop.

These checks operate on the public sanitized snapshots. They do not make vendor calls.
"""

def verify_connected(manifest, files):
    before = files["source-before.json"]
    after = files["source-after.json"]
    intent = files["intent.json"]
    observed = files["observation.json"]

    if manifest["mode"] != "recorded" or manifest["source"]["repository"] != "rlbsem/customer-signal-activation":
        raise ValueError("native source provenance mismatch")
    if any(s.get("contract") != "salesforce-review-state/v1" for s in (before, after)):
        raise ValueError("unexpected CRM state contract")
    if before.get("organization_ref") != after.get("organization_ref"):
        raise ValueError("source environment changed")
    initial, final = before["body"], after["body"]
    if len(initial["accounts"]) != 1 or final["accounts"] != initial["accounts"]:
        raise ValueError("account ownership or identity changed")
    account = initial["accounts"][0]
    if not account["active"] or not account["synthetic"]:
        raise ValueError("source is not the approved synthetic active account")
    old = {r["source_ref"]: r for r in initial["reviews"]}
    new = {r["source_ref"]: r for r in final["reviews"]}
    if len(old) != 2 or len(new) != 3 or len(new) != len(final["reviews"]):
        raise ValueError("review cardinality or identity conflict")
    if any(new.get(k) != v for k, v in old.items()):
        raise ValueError("historical Salesforce reviews changed")
    added = [r for ref, r in new.items() if ref not in old]
    if len(added) != 1:
        raise ValueError("did not observe exactly one new CRM review")
    review = added[0]
    if (review["review_status"], review["proposed_action"], review["action_key"]) != (
        "Pending", "clarify_need", intent["id"]
    ):
        raise ValueError("new CRM review does not match the approved intent")
    if review["account_source_ref"] != account["source_ref"]:
        raise ValueError("CRM review maps to a different account")
    if (intent["state"], intent["payload"]["account"], intent["payload"]["brand"], intent["payload"]["owner"]) != (
        "approved", account["account_key"], account["brand"], account["owner_key"]
    ):
        raise ValueError("intent authority or mapping mismatch")
    if intent["payload"]["proposal"]["action"] != review["proposed_action"]:
        raise ValueError("approved payload and CRM review disagree")

    first, last = observed["initial_decision"], observed["feedback_decision"]
    for d, count, pending, action in ((first, 2, 0, "clarify_need"), (last, 3, 1, "hold")):
        if (
            d["account_source_ref"] != account["source_ref"]
            or d["owner_key"] != account["owner_key"]
            or d["review_count"] != count
            or d["pending_count"] != pending
            or d["decision_action"] != action
        ):
            raise ValueError("warehouse decision inconsistent with CRM snapshots")
    delivery = observed["delivery"]
    if (
        delivery.get("first_state") != "retry"
        or delivery.get("restarted_state") != "delivered"
        or delivery.get("repeated_state") != "delivered"
        or delivery.get("post_requests") != 1
        or delivery.get("independent_action_count") != 1
        or delivery.get("readback_exact_fields") != 13
        or not delivery.get("readback_independent")
        or not delivery.get("original_sources_unchanged")
        or not delivery.get("feedback_suppressed")
    ):
        raise ValueError("lost-ack recovery or independent readback evidence mismatch")
    if (delivery.get("action_key") != intent["id"] or
        observed["source_business_hash_before"] != before["business_hash"] or
        observed["source_business_hash_after"] != after["business_hash"]):
        raise ValueError("source and receiver evidence does not reconcile")
    if observed["native_counts"] != {"distinct_snowflake_query_ids": 126, "composite_salesforce_requests": 42}:
        raise ValueError("native execution counts changed")
    if observed.get("new_vendor_execution") is not False or observed.get("llm_inference") != "not_executed_deterministic_policy":
        raise ValueError("recorded evidence was misrepresented as a new execution")
    if observed["cleanup"] != {"warehouse": "SUSPENDED", "remaining_schemas": 0}:
        raise ValueError("final warehouse cleanup observation is missing")
    timeline = files["timeline.json"]
    if [e["action"] for e in timeline] != [
        "Original Salesforce state",
        "Initial Snowflake recommendation",
        "One approved synthetic CRM review",
        "Lost acknowledgment and receipt recovery",
        "Independent Salesforce readback",
        "Updated Snowflake decision",
        "Read-only cleanup confirmation",
    ]:
        raise ValueError("timeline stages changed")
    return {
        "native_source_snapshots": 2,
        "previous_reviews_unchanged": len(old),
        "new_pending_reviews": len(added),
        "independent_receiver_effects": 1,
        "duplicate_effects": 0,
        "warehouse_transition": "clarify_need -> hold",
        "cloud_cleanup": "SUSPENDED, no integration schemas",
        "scope": "Recorded native synthetic internal review, not new vendor execution or customer contact",
    }
