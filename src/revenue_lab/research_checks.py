"""Offline projections and independent checks of pinned research records; no inference."""
import ast
import hashlib
import json
from datetime import datetime

from .gtm_checks import require, source_digest


def moment(value):
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def queue(scenario, source):
    """Mirror documented priority arithmetic, not the operational engine or an AI score."""
    weights = next(ast.literal_eval(n.value) for n in ast.parse(source).body
                   if isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "WEIGHTS" for t in n.targets))
    rows = []
    for case in scenario["cases"]:
        if case["id"] not in scenario["workspace_cases"]:
            continue
        seen, contributions = set(), []
        for s in sorted(case["sources"], key=lambda s: (-s["confidence"], s["source_id"])):
            key = (s["kind"], s["event_key"])
            age = max(0, (moment(case["as_of"]) - moment(s["published_at"] or s["observed_at"])).total_seconds()/86400)
            reason = ("account_mismatch" if s["account_domain"] != case["domain"] else "duplicate" if key in seen
                      else "expired" if moment(s["expires_at"]) <= moment(case["as_of"]) else
                      "undated_publication" if not s["published_at"] else "contributing")
            seen.add(key)
            points = round(weights.get(s["kind"], 0)*s["confidence"]*max(0, 1-age/90), 2) if reason == "contributing" else 0
            contributions.append({"source_id": s["source_id"], "kind": s["kind"], "confidence": s["confidence"],
                                  "age_days": round(age, 2), "reason": reason, "points": points})
        signal_points = min(60, sum(s["points"] for s in contributions))
        crm = case["crm"]
        blocks = list(crm.get("blocks", []))
        if any(s["reason"] == "account_mismatch" for s in contributions):
            blocks.append("source_account_mismatch")
        if not crm.get("owner"):
            blocks.append("unverified_owner")
        if not crm.get("consent"):
            blocks.append("no_contact_permission")
        if crm.get("open_opportunities", 0):
            blocks.append("existing_open_opportunity")
        if not case["synthetic"]:
            blocks.append("public_reference_read_only")
        if signal_points < 30:
            blocks.append("insufficient_corroborated_signals")
        # The upstream provider adapters are fixtures. CRM retains authority on conflicts.
        values, lineage, attempts, conflicts = {"employees": 240}, {}, [], []
        for provider in scenario["providers"]:
            require(provider["mode"] == "fixture", "native enrichment not executed")
            result = provider["records"].get(case["domain"], {})
            attempts.append({"provider": provider["name"], "status": "found" if result else "missing"})
            for field, value in result.items():
                if field in values and values[field] != value:
                    conflicts.append({"field": field, "kept": values[field], "rejected": value, "provider": provider["name"]})
                elif field not in values:
                    values[field] = value
                    lineage[field] = {"provider": provider["name"], "confidence": provider["confidence"]}
            if all(k in values for k in ("employees", "industry", "territory")):
                break
        rows.append({"case_id": case["id"], "name": case["name"], "domain": case["domain"],
                     "fit": case["fit"], "signal_points": round(signal_points, 2),
                     "priority": round(case["fit"]*.4+signal_points, 2), "contributions": contributions,
                     "owner": crm.get("owner"), "blocks": sorted(set(blocks)), "eligible": not blocks,
                     "enrichment": {"values": values, "lineage": lineage, "attempts": attempts, "conflicts": conflicts}})
    return sorted(rows, key=lambda r: (-r["priority"], r["case_id"]))


def check_record(r):
    require(r["inference"] == "executed" and r["advisory_only"], "research authority/execution mismatch")
    require(source_digest(r["context"]) == r["context_hash"] and source_digest(r["request"]) == r["request_hash"], "research request mismatch")
    require(json.loads(r["request"]["messages"][1]["content"]) == r["context"] and
            r["request"]["messages"][0]["content"] == r["prompt"], "research prompt mismatch")
    require(r["latency_seconds"] > 0 and r["usage"]["completion_tokens"] > 0, "missing inference observation")
    if r["parsed"] is not None:
        parsed = r["parsed"]
        require(r["error"] is None and json.loads(r["raw_response"]) == parsed, "research response mismatch")
        sources = {s["source_id"]: s for s in r["context"]["sources"]}
        require(parsed["action"] in {"review", "abstain"}, "research action mismatch")
        for fact in parsed["facts"]:
            require(fact["source_id"] in sources and len(fact["quote"]) >= 8 and
                    fact["quote"] in sources[fact["source_id"]]["text"], "research citation mismatch")
        for h in parsed["hypotheses"]:
            require(h["source_ids"] and all(k in sources for k in h["source_ids"]), "research hypothesis mismatch")
        require(not (parsed["action"] == "abstain" and parsed["opening"]), "abstention drafts outreach")
    else:
        require(bool(r["error"]), "discarded research failure")


def research(files):
    combined = files["evaluation.json"]
    records = []
    for entry in combined["rounds"]:
        report, snapshots = files[entry["evaluation"]], files[entry["sources"]]
        for name, expected in report["source_sha256"].items():
            require(hashlib.sha256(snapshots[name].encode()).hexdigest() == expected, "research executed source mismatch")
        cases = json.loads(snapshots["src/gtm/research-scenario.json"])["cases"]
        for r in report["records"]:
            case = next(c for c in cases if c["id"] == r["case_id"])
            require(r["context"] == {k: v for k, v in case.items() if k != "rubric"}, "research round context mismatch")
            require(r["source_sha256"] == report["source_sha256"], "research revision mismatch")
            check_record(r)
            brief, rubric = r["parsed"], case["rubric"]
            assessment = dict.fromkeys(["schema", "expected_action", "opening_relevant", "banned_phrases_absent"], False)
            if brief:
                opening = brief["opening"].lower()
                assessment = {"schema": True, "expected_action": brief["action"] == rubric["expected_action"],
                              "opening_relevant": not opening if brief["action"] == "abstain" else any(w in opening for w in rubric["must_mention"]),
                              "banned_phrases_absent": not any(w in opening for w in rubric["forbidden_claims"])}
            require(assessment == r["contract_assessment"], "research rubric mismatch")
        for approach, stats in report["comparisons"].items():
            subset = [r for r in report["records"] if r["approach"] == approach]
            require(stats["responses"] == len(subset) and stats["contract_passes"] == sum(all(r["contract_assessment"].values()) for r in subset), "research comparison mismatch")
        records.extend(report["records"])
    require(records == combined["records"] and len(records) == 40, "research response count mismatch")
    qualitative = files["reviewer-assessment.json"]
    require(qualitative["evaluation_hash"] == source_digest(combined) and
            [r["run_hash"] for r in qualitative["records"]] == [source_digest(r) for r in records] and
            qualitative["blind_human_sdr_study"] is False, "research qualitative lineage mismatch")
    scenario, source = files["scenario.json"], files["research-source.py"]
    require(files["queue.json"] == queue(scenario, source), "research queue projection mismatch")
    require(json.loads(files["round3-sources.json"]["src/gtm/research-scenario.json"]) == scenario, "research current scenario mismatch")
    op = files["operator-proof.json"]
    check_record(op["record"])
    require(op["run_hash"] == source_digest(op["record"]) == op["review"]["run_hash"], "operator run mismatch")
    review = op["review"]
    require(review["review_hash"] == source_digest({k: v for k, v in review.items() if k != "review_hash"}), "operator approval content mismatch")
    require(review["context_hash"] == op["record"]["context_hash"] and not review["crm_write_authorized"] and
            review["scope"] == "local_internal_review_only" and op["native_writes"] == "not_executed" and op["prospect_communications"] == "not_executed",
            "operator authority mismatch")
    require(op["repeat_review_identical"] and op["primary_120_account_state_unchanged"] and op["current_sources_verified"], "operator recovery observation mismatch")
    for name, checksum in op["source_sha256"].items():
        require(hashlib.sha256(op["source_snapshots"][name].encode()).hexdigest() == checksum, "operator source mismatch")
    jobs = files["public-jobs.json"]
    require(jobs["http_status"] == 200 and jobs["published_at"] is None and len(jobs["records"]) == 3, "public jobs boundary mismatch")
    regression = files["regression.json"]
    browser = files["browser-provenance.json"]
    require(hashlib.sha256(files["browser-capture.py"].encode()).hexdigest() == browser["source_sha256"]["scripts/capture_research.py"], "recorded browser source mismatch")
    edited = next(ast.literal_eval(n.args[0]) for n in ast.walk(ast.parse(files["browser-capture.py"]))
                  if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and n.func.attr == "fill")
    require(files["browser-edit.json"]["opening"] == edited and not files["browser-edit.json"]["new_approval"] and
            "edit_opening" in browser["browser_interactions"] and "approve_exact_local_review" in browser["browser_interactions"] and
            not browser["page_errors"], "recorded editable opening mismatch")
    require(regression["tests"] == {"tests": 237, "failures": 0, "errors": 0, "skipped": 0} and regression["independent_demo_runs"] == 4, "source regression mismatch")
    return {"recorded_responses": 40, "prompt_approaches": len({r["approach"] for r in records}),
            "queue_accounts": len(files["queue.json"]), "recorded_local_reviews": 1,
            "source_regression_tests": 237, "new_vendor_or_model_execution": False,
            "semantic_entailment": "not_established_by_exact_citations", "native_research_delivery": "not_executed"}
