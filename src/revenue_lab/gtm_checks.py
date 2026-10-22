"""Offline checks of three separate, pinned GTM execution records. No vendor SDKs."""

import hashlib
import json
import ast
from collections import Counter

from .bundle import LOCK


def source_digest(value):
    # The source engine canonicalizes non-ASCII text with ensure_ascii=True.
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()).hexdigest()


def require(condition, message):
    if not condition:
        raise ValueError(message)


def pipeline(files):
    d, spec = files["execution.json"], files["scenario.json"]
    regression = files["regression.json"]
    require(regression["tests"]["tests"] == 163 and not any(regression["tests"][k] for k in ("failures", "errors", "skipped"))
            and regression["independent_demo_runs"] == 4, "original regression evidence mismatch")
    require(d["fresh_inference"] == d["native_vendors"] == "not_executed", "local pipeline is not native execution")
    require(d["scenario"]["currency"] == d["measurement"]["currency"] == spec["currency"] == "USD", "pipeline currency mismatch")
    require(d["scenario"]["specification_sha256"] == source_digest(spec), "scenario specification mismatch")
    accounts = {a["id"]: a for a in d["account_records"]}
    cohorts = {a["account_id"]: a for a in d["measurement"]["accounts"]}
    require(len(accounts) == len(cohorts) == spec["population"] == 120, "account denominator mismatch")
    sources = {s["source_key"]: s for s in d["source_records"]}
    feedback = {f["source_key"]: f for f in d["feedback"]}
    values, counts, meetings, seen = Counter(), Counter(), Counter(), set()
    for key, source in sources.items():
        r = json.loads(source["payload"])
        require(source_digest(r) == source["payload_hash"], "source payload mismatch")
        if r["kind"] != "outcome" or source["disposition"] != "accepted":
            continue
        data, cohort = r["data"], cohorts[source["account_id"]]
        require(data["currency"] == "USD" and cohort["currency"] == "USD", "source currency mismatch")
        f = feedback[key]
        require(f["amount_cents"] == data["amount_cents"] and f["business_id"] == data["business_id"], "feedback/source mismatch")
        require(f["account_id"] == source["account_id"] and f["origin"] == data["origin"], "feedback identity mismatch")
        in_window = (cohort["window_end"] <= d["measurement"]["as_of"] and
                     cohort["assigned_at"] <= r["observed_at"] < cohort["window_end"] and
                     source["received_at"] <= d["measurement"]["as_of"] and
                     data["created_at"] >= cohort["assigned_at"])
        if not in_window:
            continue
        identity = (source["account_id"], data["kind"], data["business_id"])
        require(identity not in seen, "duplicate admitted business identity")
        seen.add(identity)
        if data["kind"] == "meeting_qualified":
            meetings[cohort["arm"]] += 1
        if data["kind"] == "opportunity_accepted":
            require(r["source"] == "crm", "opportunity is not CRM sourced")
            values[cohort["arm"]] += data["amount_cents"]
            counts[cohort["arm"]] += 1
    for arm, measured in d["measurement"]["arms"].items():
        rows = [c for c in cohorts.values() if c["arm"] == arm]
        require(len(rows) == measured["assigned"] == measured["mature_accounts"], "assigned denominator changed")
        require(measured["pipeline_cents"] == values[arm] == sum(c["pipeline_cents"] for c in rows), "pipeline source-to-mart mismatch")
        require(measured["accepted_opportunities"] == counts[arm] and measured["qualified_meetings"] == meetings[arm], "outcome count mismatch")
    quotes = d["scenario"]["scope_quotes"]
    require(sum(q["sites"] * q["annual_site_value_cents"] for q in quotes) == sum(values.values()) == 346000000, "scope economics mismatch")
    require(sum(counts.values()) == len(quotes) == 5, "opportunity grain mismatch")
    require(d["financial_audit"]["pipeline_cents"] == sum(values.values()) and d["financial_audit"]["currency"] == "USD", "financial audit mismatch")
    for action in d["actions"]:
        payload = json.loads(action["payload"])
        require(source_digest(payload) == action["payload_hash"], "action content mismatch")
        approvals = [a for a in d["audit"] if a["event"] == "exact_approval" and a["subject"] == action["action_key"]]
        require(any(json.loads(a["detail"])["payload_hash"] == action["payload_hash"] for a in approvals), "missing exact approval")
        if action["status"] == "delivered":
            receipt = json.loads(action["receipt"])
            require(receipt["payload_hash"] == action["payload_hash"], "receipt content mismatch")
    require(d["reconciliation"]["safe_to_resume"] and not d["reconciliation"]["discrepancies"], "local reconciliation discrepancy")
    require(not d["measurement"]["leakage_accounts"], "holdout exposure leakage")
    return {"accounts": len(accounts), "opportunities": sum(counts.values()), "currency": "USD",
            "original_regression_tests": regression["tests"]["tests"], "original_independent_demos": regression["independent_demo_runs"],
            "pipeline_cents": sum(values.values()), "pipeline_by_arm_cents": dict(values),
            "method": "Source CRM outcomes, scope multiplication, full account denominator, SQL rows and approvals checked offline",
            "causal_or_commercial_lift": "not_established"}


def salesforce(files):
    a, details, cleanup = files["acceptance.json"], files["native-details.json"], files["post-cleanup.json"]
    require(a["status"] == "passed" and all(a["checks"].values()), "native check missing or failed")
    require(a["authenticated_requests"] == len(a["requests"]) == 140, "native request count mismatch")
    require(details["derived_from_acceptance_sha256"] == source_digest(a), "native derivation mismatch")
    rel = details["relationships"]
    require(rel["account_id_hash"] == rel["contact_account_id_hash"] == rel["task_account_id_hash"], "Account/Contact/Task association mismatch")
    require(rel["contact_id_hash"] == rel["task_contact_id_hash"], "Task Contact mismatch")
    require(rel["account_owner_hash"] == rel["contact_owner_hash"] == rel["task_owner_hash"] == rel["independent_reader_hash"], "owner/readback mismatch")
    require(rel["task_created_by_hash"] != rel["independent_reader_hash"], "readback is not independent")
    for obj in ("Account", "Contact"):
        permission = details["effective_permissions"]["integration"][obj]
        require(permission["queryable"] and not any(permission[k] for k in ("createable", "updateable", "deletable")), "protected object write grant")
    reviewer = details["effective_permissions"]["reviewer"]["Task"]
    require(reviewer["queryable"] and not any(reviewer[k] for k in ("createable", "updateable", "deletable")), "reviewer Task write grant")
    require(a["receipt"]["task_count"] == 1 and a["receipt"]["exact_content"], "native receipt lacks single exact effect")
    for rejection in details["rejected_operations"]:
        require(rejection["response_sha256"] == a["requests"][rejection["request_index"]]["response_sha256"], "rejection response mismatch")
    require(details["apex_deployment"]["tests_completed"] == 3 and details["apex_deployment"]["tests_failed"] == 0, "Apex result mismatch")
    require(cleanup["read_only"] and cleanup["authenticated_requests"] == len(cleanup["requests"]) == 20 and
            all(r["method"] == "GET" for r in cleanup["requests"]), "cleanup is not read-only verification")
    require(cleanup["original_assignments_exactly_restored"] and cleanup["completed_task_content_and_relationships_unchanged"] and
            a["cleanup"]["temporary_assignments_removed"] == 4, "permission restoration missing")
    return {"native_requests": 140, "read_only_cleanup_requests": 20, "exact_task_effects": 1,
            "independent_relationships": "consistent", "Apex_tests": 3,
            "scope": "Recorded native synthetic Account/Contact/Task only; not the enterprise pipeline cohort"}


def qwen(files):
    d = files["evaluation.json"]
    require(source_digest(files["cases.json"]) == d["cases_sha256"], "model case configuration mismatch")
    tree = ast.parse(files["model-source.py"])
    prompt = next(ast.literal_eval(n.value) for n in ast.walk(tree) if isinstance(n, ast.Assign)
                  and any(isinstance(t, ast.Name) and t.id == "prompt" for t in n.targets))
    require(prompt["content"] == files["instructions.json"]["system_prompt"], "model instructions mismatch")
    for name, path in [("model-source.py", "src/gtm/advice.py"), ("policy-source.py", "scripts/evaluate_ai.py")]:
        require(hashlib.sha256(files[name].encode()).hexdigest() == d["source_sha256"][path], "recorded model source mismatch")
    require(d["inferences_executed"] == len(d["records"]) == 16, "inference count mismatch")
    exact = 0
    for r in d["records"]:
        require(r["inference"] == "executed" and r["advisory_only"], "model execution/authority boundary mismatch")
        require(r["context_hash"] == source_digest(r["context"]), "model context mismatch")
        request = {"model": r["model"], "messages": [prompt, {"role": "user", "content": json.dumps(r["context"])}],
                   "temperature": r["temperature"], "seed": r["seed"], "max_tokens": 900, "response_format": {"type": "json_object"}}
        require(source_digest(request) == r["request_hash"], "recorded model request mismatch")
        if r["validation_error"] is None:
            parsed = json.loads(r["raw_response"])
            require(parsed == r["parsed"], "parsed model text mismatch")
            documents = {s["source_key"]: s["content"] for s in r["context"]["evidence"]}
            require(parsed["citations"] and all(c["source_key"] in documents and c["quote"] and c["quote"] in documents[c["source_key"]] for c in parsed["citations"]), "model citation is not an exact span")
            exact += 1
    require(d["exact_citation_checks_passed"] == exact == 10, "citation result count mismatch")
    return {"actual_responses": len(d["records"]), "exact_citation_passes": exact,
            "preserved_failures": len(d["records"]) - exact, "semantic_support": "not_independently_evaluated",
            "scope": "Recorded Qwen3 advisory evaluation with its own local policy observations; not native Salesforce execution"}


def verify_gtm(manifest, files):
    upstream, obs = files["upstream.json"], files["observation.json"]
    require(upstream == LOCK["gtm_imports"][manifest["scenario"]], "unexpected upstream provenance")
    require(obs["new_vendor_execution"] is False and obs["new_model_execution"] is False and
            obs["continuous_vendor_workflow"] is False, "execution lanes were conflated")
    for item in upstream["artifacts"]:
        # Original bytes are checked by load_verified; pin their hashes to the import lock too.
        entry = next(a for a in manifest["artifacts"] if a["path"] == item["file"])
        require(entry["sha256"] == item["sha256"], "upstream artifact bytes changed")
    check = {"gtm-enterprise": pipeline, "gtm-salesforce": salesforce, "gtm-qwen": qwen}[manifest["scenario"]]
    return {**check(files), "upstream_files": len(upstream["artifacts"]), "new_vendor_or_model_execution": False}
