"""Independent relationships in selected recorded release evidence. Never runs a model."""
import hashlib
import json
from collections import Counter

from .bundle import LOCK
from .gtm_checks import require, source_digest

CONFIGS = [
    ("original-reference.json", "Original Qwen2.5 · reference", "withheld"),
    ("original-candidate.json", "Original Qwen2.5 · summary-first", "withheld"),
    ("first-reference.json", "First Qwen3 · reference", "blocked"),
    ("first-candidate.json", "First Qwen3 · candidate", "blocked"),
    ("bounded-reference.json", "Bounded Qwen3 · reference", "eligible"),
    ("bounded-candidate.json", "Bounded Qwen3 · candidate", "eligible"),
]


def project(files, upstream):
    """Derived display rows remain traceable to original results, not a new evaluation."""
    origins = {a["file"]: a for a in upstream["artifacts"]}
    comparisons = []
    for name, label, release in CONFIGS:
        summary = files[name]
        results = summary["results"]
        source = origins[name]["source_path"]
        rows, ordinal = [], Counter()
        for r in results:
            case = r.get("case_id", r["account"])
            # Upstream filenames use a per-case ordinal. The recorded sample
            # includes split offsets (2/3 and 6/7) and is not a file suffix.
            task = str(case) + "-" + str(ordinal[case])
            ordinal[case] += 1
            path = source.removesuffix("summary.json") + task + ".json"
            rows.append({"task": task, "account": r["account"], "split": r.get("split", "original suite"),
                         "passed": r["task_success"], "reason": r["reason"], "unsafe": r["unsafe_recommendations"],
                         "source_url": f"https://github.com/{upstream['repository']}/blob/{upstream['import_revision']}/{path}"})
        comparisons.append({"file": name, "label": label, "release": release,
                            "passed": sum(r["task_success"] for r in results), "tasks": len(results),
                            "unsafe": sum(r["unsafe_recommendations"] for r in results),
                            "unauthorized": sum(r["unauthorized_effects"] for r in results),
                            "duplicates": sum(r["duplicate_effects"] for r in results), "results": rows})
    return {"derivation": "Read-only aggregation of original result arrays; not a new model evaluation",
            "comparisons": comparisons}


def request_checks(records):
    for record in records:
        require(source_digest(record["request"]) == record["input_hash"], "model request hash mismatch")
        require(record["usage"]["completion_tokens"] > 0, "missing actual token observation")


def release(files):
    upstream = files["upstream.json"]
    require(upstream == LOCK["release_import"], "release provenance differs from source lock")
    for a in upstream["artifacts"]:
        expected = f"https://github.com/{upstream['repository']}/blob/{upstream['import_revision']}/{a['source_path']}"
        require(a["source_url"] == expected and a["file"] in files, "release source link mismatch")
    require(files["projection.json"] == project(files, upstream), "release projection differs from original results")
    for name, _, _ in CONFIGS:
        d = files[name]
        require(d["mode"] == "live" and d["task_successes"] == sum(r["task_success"] for r in d["results"]), "live aggregate mismatch")
        ids = [(r.get("case_id", r["account"]), r["sample"]) for r in d["results"]]
        require(len(ids) == len(set(ids)), "duplicate evaluation task")
        if name.startswith("bounded"):
            require(all(r["task_success"] and all(r["oracle_checks"].values()) for r in d["results"]), "bounded oracle failure")
            require(not any(r[k] for r in d["results"] for k in ["unsafe_recommendations", "unauthorized_effects", "duplicate_effects"]), "bounded unsafe result")
    first, gate, life = files["first-gate.json"], files["bounded-gate.json"], files["lifecycle.json"]
    require(first["decision"] == "blocked" and first["reasons"] and files["first-release.json"]["decision"] == "withheld", "rejected run hidden")
    fail = files["first-failure.json"]
    require(not fail["evaluation"]["task_success"] and any(i["finish_reason"] == "length" and not i["response_text"] for i in fail["inference"]), "failed inference missing")
    require(files["original-failure.json"]["evaluation"]["unsafe_recommendations"] > 0, "original unsafe recommendation hidden")
    require(gate["decision"] == "eligible" and not gate["reasons"] and life["gate"]["decision"] == "eligible", "release gate mismatch")
    require(life["decision"] == "promoted_then_rolled_back", "release transition missing")
    require([h["event"] for h in life["history"]] == ["registered", "registered", "baseline_activated", "gate", "shadow", "canary_started", "canary", "promoted", "rollback"], "release event ordering mismatch")
    require(files["timeline.json"] == [{"action": h["event"], "occurred": h["at"], "body": h} for h in life["history"]], "timeline differs")
    configs = {files[n]["configuration"]["version"]: files[n]["configuration"] for n in ["bounded-reference.json", "bounded-candidate.json"]}
    require(files["seal.json"]["configurations"] == list(configs.values()), "configuration seal mismatch")
    for c in configs.values():
        require(source_digest({k:v for k,v in c.items() if k != "fingerprint"}) == c["fingerprint"], "configuration fingerprint mismatch")
    require(life["shadow"]["external_effects"] == life["canary"]["external_effects"] == 0, "shadow/canary wrote effects")
    require(life["shadow"]["pairs"] and life["canary"]["pairs"], "paired shadow/canary missing")
    decisions = 0
    for name in ["routed_canary", "promoted_run", "injected_context_fault", "rollback_run"]:
        run = life[name]
        config = configs[run["route"]["version"]]
        for t in run["trace"]:
            if t["kind"] != "model_decision":
                continue
            decisions += 1
            provider = t["detail"]["provider"]
            require(provider["mode"] == "live_local_llm" and provider["configuration_fingerprint"] == config["fingerprint"], "routed version fingerprint mismatch")
            matches = [i for i in life["inference"][config["version"]] if i["input_hash"] == provider["input_hash"]]
            require(matches, "routed decision has no recorded inference")
            for m in matches:
                require(m["request"]["reasoning_budget_tokens"] == config["decoding"]["reasoning_cap"], "routed reasoning cap mismatch")
    for records in life["inference"].values():
        request_checks(records)
    request_checks(fail["inference"])
    promoted = life["promoted_run"]
    receipts = [t["detail"]["receipt"] for t in promoted["trace"] if t["kind"] == "verified_receipt"]
    require(receipts and receipts == life["independent_effects"], "independent receipt content mismatch")
    for r in receipts:
        require(source_digest(r["effect"]) == r["hash"], "receipt payload hash mismatch")
    require(promoted["status"] == "completed" and promoted["route"]["version"] == life["history"][-2]["detail"]["active"], "promoted routing mismatch")
    require(life["routed_canary"]["status"] == "shadowed" and life["routed_canary"]["route"]["canary_selected"], "canary route mismatch")
    fault = life["injected_context_fault"]
    require(fault["status"] == "escalated" and any(t["kind"] == "guardrail" and t["detail"]["reason"] == "ungrounded_claim" for t in fault["trace"]), "controlled fault not detected")
    require(not any(t["kind"] in ["dispatch", "verified_receipt"] for t in fault["trace"]), "fault caused effect")
    rollback = life["history"][-1]["detail"]
    require(not rollback["external_effects_undone"] and life["rollback_run"]["route"]["version"] == rollback["to"] != rollback["from"], "rollback routing mismatch")
    require(life["rollback_run"]["status"] == "completed", "post-rollback run incomplete")
    controls, software = files["controls.json"], files["software.json"]
    require(controls["passed"] and all(controls["checks"].values()), "permission/replay control failed")
    require(software["tests"] > 0 and not any(software[k] for k in ["failures", "errors", "skipped"]), "software tests did not pass")
    require(files["observation.json"]["new_model_execution"] is False and files["observation.json"]["new_effects"] is False, "viewer misstates execution")
    return {"source_artifacts": len(upstream["artifacts"]), "recorded_model_tasks": sum(len(files[n]["results"]) for n,_,_ in CONFIGS),
            "routed_decisions_checked": decisions, "exact_independent_receipts": len(receipts),
            "permission_replay_checks": len(controls["checks"]), "source_software_tests": software["tests"],
            "new_inference": False, "domain_checks": "aggregate/oracle consistency, source hashes, request hashes, routed configurations and receipt content"}


def verify_original_bytes(path, upstream):
    for a in upstream["artifacts"]:
        require(hashlib.sha256((path / a["file"]).read_bytes()).hexdigest() == a["sha256"], "original release bytes differ")
