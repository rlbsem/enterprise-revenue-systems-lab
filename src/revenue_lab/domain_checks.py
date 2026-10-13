"""Independent arithmetic and ledger checks. No source-engine imports."""

from decimal import Decimal
from .bundle import digest


def verify_control(manifest, files):
    ledger, receiver, stages = (
        files["ledger.json"],
        files["receiver.json"],
        files["stages.json"],
    )
    effects = {r["key"]: r for r in receiver}
    jobs = ledger["jobs"]
    if len(receiver) != len(effects) or len(jobs) != 2 or len(receiver) != 2:
        raise ValueError("missing or duplicate receiver effects")
    proposals = {p["id"]: p for p in ledger["proposals"]}
    for job in jobs:
        effect = effects[job["id"]]
        if (
            job["status"] != "succeeded"
            or job["reason"] != "reconciled_committed_effect"
            or job["attempts"] != 2
        ):
            raise ValueError("recovery did not reconcile a committed effect")
        if job["mutation"] != effect["body"] or effect["hash"] != digest(
            effect["body"]
        ):
            raise ValueError("receiver effect does not match durable intent")
        if job["remote_result"]["receipt"] != effect["receipt"]:
            raise ValueError("receiver receipt mismatch")
        if (
            proposals[job["id"]]["body"]["expected_revision"]
            != effect["body"]["revision"]
        ):
            raise ValueError("effect lacks expected commercial authority")
        dispatches = [
            a
            for a in ledger["audit"]
            if a["subject"] == job["id"] and a["kind"] == "dispatch_authorized"
        ]
        if not dispatches or any(
            a["detail"]["mutation_hash"] != effect["hash"] for a in dispatches
        ):
            raise ValueError("missing authorized dispatch evidence")
    uncertain = [s for s in stages if s["job"]["status"] in ("retry", "leased")]
    if len(uncertain) != 2 or any(
        not s["job"]["uncertain"] or len(s["effects"]) != 1 for s in uncertain
    ):
        raise ValueError("uncertain states do not show already committed effects")
    summary = files["observation.json"]["summary"]
    expected = {
        "attempts": sum(j["attempts"] for j in jobs),
        "unique_effects": len(effects),
        "duplicate_effects": 0,
    }
    if any(summary[k] != v for k, v in expected.items()) or summary["replay_claimed"]:
        raise ValueError("summary contradicts receiver or job observations")
    return {
        "bound_intents": len(jobs),
        "independent_receiver_effects": len(receiver),
        "uncertain_states_observed": len(uncertain),
        "duplicates": 0,
        "scope": "Synthetic receiver contract, not arbitrary vendor exactly-once guarantee",
    }


def verify_revenue(manifest, files):
    from .revenue_checks import checks

    return checks(manifest, files)
