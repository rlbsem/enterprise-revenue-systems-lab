"""Portable evidence files, explicit provenance, and strict verification."""

import hashlib
import json
import platform
import re
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
LOCK = json.loads((ROOT / "sources.lock.json").read_text())


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def digest(value):
    return hashlib.sha256(canonical(value).encode()).hexdigest()


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def seal(path, scenario, source, artifacts, mode, limitations):
    path.mkdir(parents=True, exist_ok=True)
    entries = []
    for name, item in artifacts.items():
        data = (
            item
            if isinstance(item, bytes)
            else (json.dumps(item, indent=2, ensure_ascii=False) + "\n").encode()
        )
        target = path / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
        entries.append(
            {
                "path": name,
                "sha256": hashlib.sha256(data).hexdigest(),
                "bytes": len(data),
            }
        )
    manifest = {
        "schema_version": "1.0",
        "scenario": scenario,
        "source": LOCK["sources"][source],
        "mode": mode,
        "environment": "independent_synthetic_environment",
        "packaged_at": datetime.now(timezone.utc).isoformat(),
        "runtime": {
            "python": platform.python_version(),
            "platform": platform.platform(),
        },
        "artifacts": entries,
        "limitations": limitations,
        "input_hashes": {
            a["path"]: a["sha256"]
            for a in entries
            if a["path"]
            in (
                "recorded-input.json",
                "dataset-manifest.json",
                "source-records.json",
                "ledger.json",
                "trace.json",
                "application.json",
            )
        },
        "reproduce": [
            "python -m revenue_lab.cli prepare " + source + " --install",
            ("python -m revenue_lab.cli recorded --source seller")
            if mode == "recorded" and source == "seller"
            else "python -m revenue_lab.cli run "
            + ("revenue-correction" if scenario == "revenue-bridge" else scenario),
        ],
    }
    manifest["configuration_hash"] = digest(
        {"scenario": scenario, "source": manifest["source"], "mode": mode}
    )
    write_json(path / "bundle.json", manifest)
    return manifest


def load_verified(path):
    """Check integrity, contracts and source pin before domain verification."""
    from jsonschema import Draft202012Validator, FormatChecker

    manifest = json.loads((path / "bundle.json").read_text(encoding="utf-8"))
    schema = json.loads((ROOT / "schema/bundle-v1.json").read_text())
    Draft202012Validator(schema, format_checker=FormatChecker()).validate(manifest)
    scenario = manifest["scenario"]
    source_key = scenario.split("-")[0]
    if (
        source_key not in LOCK["sources"]
        or manifest["source"] != LOCK["sources"][source_key]
    ):
        raise ValueError("stale or unexpected source revision")
    if manifest["configuration_hash"] != digest(
        {"scenario": scenario, "source": manifest["source"], "mode": manifest["mode"]}
    ):
        raise ValueError("configuration mismatch")
    names = [a["path"] for a in manifest["artifacts"]]
    if len(names) != len(set(names)) or "observation.json" not in names:
        raise ValueError("duplicate or incomplete artifact set")
    found = {}
    for entry in manifest["artifacts"]:
        name = entry["path"]
        if not re.fullmatch(r"[a-zA-Z0-9_-]+(?:/[a-zA-Z0-9_-]+)*\.[a-zA-Z0-9]+", name):
            raise ValueError("unsafe artifact path")
        target = path / name
        if not target.resolve().is_relative_to(path.resolve()) or target.is_symlink():
            raise ValueError("artifact escapes bundle")
        raw = target.read_bytes()
        if (
            len(raw) != entry["bytes"]
            or hashlib.sha256(raw).hexdigest() != entry["sha256"]
        ):
            raise ValueError("artifact integrity mismatch: " + name)
        found[name] = json.loads(raw) if name.endswith(".json") else raw.decode("utf-8")
    hashes = {a["path"]: a["sha256"] for a in manifest["artifacts"]}
    if not manifest["input_hashes"] or any(
        hashes.get(name) != value for name, value in manifest["input_hashes"].items()
    ):
        raise ValueError("input evidence hashes do not match artifacts")
    return manifest, found


def citations(proposal, snapshot):
    documents = {d["id"]: d["text"] for d in snapshot["documents"]}
    claims = proposal["claims"]
    if not claims or any(
        c["source"] not in documents
        or not c["quote"]
        or c["quote"] not in documents[c["source"]]
        for c in claims
    ):
        raise ValueError("citation is not an exact source span")


def verify_seller(manifest, files):
    observation = files["observation.json"]
    if manifest["scenario"] == "seller-support-review":
        trace = files["trace.json"]
        citations(trace["raw_proposal"], trace["input_snapshot"])
        if "Our support team is available" not in trace["raw_proposal"]["draft"]:
            raise ValueError("review finding is not attached to original language")
        if "not the support team's" not in files["review.md"]:
            raise ValueError("missing explicit source-support finding")
        return {
            "exact_citations": len(trace["raw_proposal"]["claims"]),
            "quality": "unsupported_availability_statement_preserved",
            "independent_usefulness": "pending",
        }
    application = files["application.json"]
    runs = {r["id"]: r for r in application["runs"]}
    for run in runs.values():
        if run["status"] == "review_required":
            citations(run["proposal"], run["snapshot"])
    for action in application["actions"]:
        payload = (
            json.loads(action["payload"])
            if isinstance(action["payload"], str)
            else action["payload"]
        )
        run = runs[action["run_id"]]
        if (
            digest(payload) != action["id"]
            or payload["evidence_hash"] != run["snapshot"]["state_hash"]
        ):
            raise ValueError("approved payload does not match its evidence")
        citations(payload["proposal"], run["snapshot"])
        approvals = [
            a
            for a in application["audit"]
            if a["action"] == "proposal_approved" and a["subject"] == action["id"]
        ]
        if not approvals or any(
            json.loads(a["body"])["payload_hash"] != action["id"] for a in approvals
        ):
            raise ValueError("missing bound approval")
        if action["state"] == "delivered":
            receipt = (
                json.loads(action["receipt"])
                if isinstance(action["receipt"], str)
                else action["receipt"]
            )
            if receipt["id"] != action["id"] or receipt["payload_hash"] != digest(
                payload
            ):
                raise ValueError("receipt does not match approved content")
    scenario = manifest["scenario"]
    if scenario in ("seller-stale", "seller-suppressed"):
        expected = (
            "evidence_changed_regenerate"
            if scenario == "seller-stale"
            else "commercial_policy_blocks_action"
        )
        if (
            observation["refusal"] != expected
            or application["actions"]
            or observation["receiver_rows"]
        ):
            raise ValueError("refused action created an effect or wrong refusal")
        if (
            scenario == "seller-stale"
            and observation["current_snapshot"]["state_hash"]
            == next(iter(runs.values()))["snapshot"]["state_hash"]
        ):
            raise ValueError("stale scenario did not change evidence")
        if (
            scenario == "seller-suppressed"
            and observation["current_snapshot"]["decision"]["consent"] is not False
        ):
            raise ValueError("suppressed scenario lacks consent refusal")
    if manifest["mode"] == "fresh_replay":
        if any(
            r["configuration"]["mode"] != "recorded_response_replay"
            for r in runs.values()
        ):
            raise ValueError("replay presented as fresh inference")
    if "receiver.json" in files and application["actions"]:
        effects = {r["id"]: r for r in files["receiver.json"]}
        for action in application["actions"]:
            if action["state"] == "delivered":
                effect = effects.get(action["id"])
                if not effect or digest(effect["body"]) != action["id"]:
                    raise ValueError("fresh delivery lacks independent receiver effect")
    return {
        "runs_checked": len(runs),
        "approved_payloads_checked": len(application["actions"]),
        "quality": "structural_checks_only",
        "independent_usefulness": "pending",
    }


def verify(path):
    manifest, files = load_verified(Path(path))
    source = manifest["scenario"].split("-")[0]
    if source == "gtm":
        from .gtm_checks import verify_gtm

        checks = verify_gtm(manifest, files)
    elif source == "connected":
        from .connected_checks import verify_connected

        checks = verify_connected(manifest, files)
    elif source == "seller":
        checks = verify_seller(manifest, files)
    else:
        from .domain_checks import verify_control, verify_revenue

        checks = (verify_control if source == "control" else verify_revenue)(
            manifest, files
        )
    return {
        "scenario": manifest["scenario"],
        "integrity": "verified",
        "checks": checks,
        "limitations": manifest["limitations"],
    }
