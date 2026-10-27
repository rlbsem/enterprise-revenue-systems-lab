"""Transactional revisions and fail-closed decisions; no external change executor."""

from datetime import timedelta
import os
from pathlib import Path

from psycopg import sql
from psycopg.types.json import Jsonb

from estate_impact import db
from estate_impact.contracts import digest, timestamp
from estate_impact.impact import assess, scenario
from estate_impact.requirements import evaluate as evaluate_requirements
from estate_impact.snapshots import check_identity

from .evidence import references, validate_scope

KINDS = {
    "retirement",
    "replacement",
    "integration-removal",
    "capability-reassignment",
    "consolidation",
    "temporary-outage",
}


def migrate(root):
    db.migrate(root)
    with db.connect() as c:
        c.execute("SELECT pg_advisory_xact_lock(4187051)")
        schema = c.execute("SELECT current_schema()").fetchone()[0]
        ddl = (
            Path(__file__)
            .with_name("schema.sql")
            .read_text()
            .replace(
                "SET search_path=public,pg_temp",
                "SET search_path=" + sql.Identifier(schema).as_string(c) + ",pg_temp",
            )
        )
        c.execute(ddl)


def publish(prepared, snapshot, catalog, expected=None, fail=False):
    check_identity(snapshot)
    for item in prepared:
        db.store_artifact(item)
    db.publish(snapshot)
    # A staged immutable snapshot may survive interruption; authoritative pointer cannot.
    expires = min(
        [
            timestamp(snapshot["as_of"]) + timedelta(days=30),
            *[
                timestamp(a["collected_at"])
                + timedelta(days=30 if a["source"] == "execution" else 90)
                for a in snapshot["artifacts"]
            ],
            *[
                timestamp(m["reviewed_at"]) + timedelta(days=m["max_age_days"])
                for m in snapshot["manifests"]
            ],
        ]
    )
    with db.connect() as c:
        c.execute("SELECT pg_advisory_xact_lock(731992)")
        head = c.execute("SELECT snapshot_id FROM ca_head WHERE name='group' FOR UPDATE").fetchone()
        if head and head[0] == snapshot["id"]:
            return False
        if (head[0] if head else None) != expected:
            raise ValueError("evidence revision conflict")
        if head:
            previous = c.execute(
                "SELECT payload FROM estate_snapshot WHERE id=%s", head
            ).fetchone()[0]
            if timestamp(snapshot["as_of"]) < timestamp(previous["as_of"]):
                raise ValueError("evidence clock cannot move backward")
            old_sources = {a["source"]: a for a in previous["artifacts"]}
            new_sources = {a["source"]: a for a in snapshot["artifacts"]}
            if old_sources.keys() != new_sources.keys():
                raise ValueError("source coverage must remain explicit")
            for source, old in old_sources.items():
                new = new_sources[source]
                if new["revision"] < old["revision"] or (
                    new["revision"] == old["revision"] and new["id"] != old["id"]
                ):
                    raise ValueError("source revision rollback or content collision")
        c.execute(
            "INSERT INTO ca_catalog VALUES(%s,%s) ON CONFLICT DO NOTHING",
            (snapshot["id"], Jsonb(catalog)),
        )
        if fail:
            if fail == "process":
                os._exit(77)
            raise RuntimeError("injected interruption before authoritative publication")
        c.execute(
            "INSERT INTO ca_head VALUES('group',%s,%s) ON CONFLICT(name) DO UPDATE "
            "SET snapshot_id=excluded.snapshot_id,expires_at=excluded.expires_at",
            (snapshot["id"], expires),
        )
    return True


def affected(snapshot, proposal):
    """Conservative reverse reachability, including every conflicting candidate path."""
    changed = set()
    for action in proposal["actions"]:
        if "system" in action:
            changed.add(action["system"])
        elif "integration" in action:
            changed.add(action["integration"])
        elif "key" in action:
            changed.add(action["key"].split(":", 1)[1])
        elif "claim" in action:
            changed.add(action["claim"]["subject"])
    target, _, _ = scenario(snapshot, proposal)
    all_facts = list(snapshot["facts"].values()) + list(target.values())
    while True:
        previous = set(changed)
        for f in all_facts:
            for v in [f["value"]] if f["value"] else f["candidates"]:
                if changed.intersection(references(f["kind"], v)):
                    changed.add(f["subject"])
        if previous == changed:
            break
    requirements = {f["subject"] for f in all_facts if f["kind"] == "requirement"}
    return changed, sorted(changed & requirements)


def evaluate(snapshot, catalog, proposal):
    if proposal.get("change_kind") not in KINDS or not proposal.get("title", "").strip():
        raise ValueError("versioned change kind and title required")
    if not proposal.get("actions"):
        raise ValueError("empty change cannot be reviewed")
    for s in proposal["systems"]:
        if f"system:{s}" not in snapshot["facts"]:
            raise ValueError("unknown scoped system")
    target, _, _ = scenario(snapshot, proposal)
    for f in target.values():
        for value in [f["value"]] if f["value"] else f["candidates"]:
            validate_scope(dict(f, value=value), catalog)
    changed, impacted = affected(snapshot, proposal)
    companies = sorted(
        {
            s.split("/", 1)[0]
            for s in changed | set(proposal["systems"]) | set(proposal["requirements"])
        }
    )
    if sorted(set(proposal["companies"])) != companies:
        raise ValueError("proposal omits affected company scope")
    result = assess(snapshot, proposal)
    owners = [
        s
        for s in proposal["systems"]
        if snapshot["facts"].get(f"ownership:{s}", {}).get("state") != "SUPPORTED"
    ]
    missing = sorted(set(impacted) - set(proposal["requirements"]))
    checks = {
        "modeled_requirements": result["disposition"]
        == "NO_IDENTIFIED_BLOCKERS_WITHIN_REVIEWED_SCOPE",
        "complete_impact_scope": not missing,
        "accountable_owners": not owners,
        "sequencing": not any(
            result["sequence"][k]
            for k in ["blocked", "missing_prerequisites", "invalid_completed", "missing_acceptance"]
        ),
    }
    touched_systems = set()
    for action in proposal["actions"]:
        if "system" in action:
            touched_systems.add(action["system"])
        keys = (
            [action["key"]]
            if "key" in action
            else ["integration:" + action["integration"]]
            if "integration" in action
            else [action["claim"]["key"]]
            if "claim" in action
            else []
        )
        for key in keys:
            for facts in [snapshot["facts"], target]:
                f = facts.get(key)
                if f and f["kind"] in {"dependency", "integration"}:
                    for v in [f["value"]] if f["value"] else f["candidates"]:
                        touched_systems.update(
                            r
                            for r in references(f["kind"], v)
                            if f"system:{r}" in snapshot["facts"]
                        )
    omitted_systems = sorted(touched_systems - set(proposal["systems"]))
    checks["complete_system_scope"] = not omitted_systems
    gates = dict(
        ready=all(checks.values()),
        checks=checks,
        omitted_requirements=missing,
        omitted_systems=omitted_systems,
        unresolved_owners=owners,
        impacted_requirements=impacted,
        boundary="Readiness within declared synthetic architecture; never cutover authority",
    )
    return result, gates, companies


def submit(pid, expected_revision, proposal, fail=False):
    """Trusted operator publication; CAS prevents concurrent revisions overwriting each other."""
    with db.connect() as c:
        h = c.execute("SELECT snapshot_id FROM ca_head WHERE name='group' FOR SHARE").fetchone()
        if not h or h[0] != proposal["base_snapshot"]:
            raise ValueError("proposal evidence is not current")
        snapshot = c.execute("SELECT payload FROM estate_snapshot WHERE id=%s", h).fetchone()[0]
        catalog = c.execute("SELECT payload FROM ca_catalog WHERE snapshot_id=%s", h).fetchone()[0]
        result, gates, companies = evaluate(snapshot, catalog, proposal)
        c.execute("SELECT pg_advisory_xact_lock(hashtext(%s))", ("proposal:" + pid,))
        row = c.execute(
            "SELECT revision FROM ca_proposal WHERE id=%s FOR UPDATE", (pid,)
        ).fetchone()
        if (row[0] if row else 0) != expected_revision:
            raise ValueError("proposal revision conflict")
        rev = expected_revision + 1
        c.execute(
            "INSERT INTO ca_proposal VALUES(%s,%s) ON CONFLICT(id) DO UPDATE SET revision=excluded.revision",
            (pid, rev),
        )
        c.execute(
            "INSERT INTO ca_version VALUES(%s,%s,%s,%s,%s,%s,%s)",
            (pid, rev, h[0], Jsonb(proposal), Jsonb(result), Jsonb(gates), companies),
        )
        if fail:
            if fail == "process":
                os._exit(77)
            raise RuntimeError("injected interruption before proposal publication")
    return rev, result["id"], gates


def decide(pid, revision, decision, reason):
    with db.connect() as c:
        return c.execute(
            "SELECT ca_decide(%s,%s,%s,%s)", (pid, revision, decision, reason)
        ).fetchone()[0]


def view():
    """Reads only persisted artifacts; pending approvals are never presented as acceptance."""
    with db.connect() as c:
        c.execute("SET TRANSACTION READ ONLY")
        h = c.execute(
            "SELECT snapshot_id,expires_at > now() FROM ca_head WHERE name='group'"
        ).fetchone()
        if not h:
            raise ValueError("no published estate")
        snapshot = c.execute("SELECT payload FROM estate_snapshot WHERE id=%s", (h[0],)).fetchone()[
            0
        ]
        check_identity(snapshot)
        catalog = c.execute(
            "SELECT payload FROM ca_catalog WHERE snapshot_id=%s", (h[0],)
        ).fetchone()[0]
        versions = []
        for pid, rev, sid, p, a, gates, latest in c.execute(
            "SELECT v.proposal_id,v.revision,v.snapshot_id,v.payload,v.assessment,v.gates,p.revision "
            "FROM ca_version v JOIN ca_proposal p ON p.id=v.proposal_id ORDER BY v.proposal_id,v.revision"
        ):
            if digest({k: v for k, v in a.items() if k != "id"}) != a["id"]:
                raise ValueError("assessment content hash mismatch")
            decisions = [
                dict(
                    principal=r[0],
                    decision=r[1],
                    reason=r[2],
                    recorded_at=r[3].isoformat(),
                    authority_current=bool(r[4]),
                )
                for r in c.execute(
                    "SELECT d.principal,d.decision,d.reason,d.recorded_at,"
                    "r.enabled AND %s <@ r.companies FROM ca_decision d "
                    "LEFT JOIN ca_reviewer r ON r.principal=d.principal "
                    "WHERE proposal_id=%s AND revision=%s ORDER BY id",
                    (p["companies"], pid, rev),
                )
            ]
            stale = sid != h[0] or rev != latest or not h[1]
            stale = stale or any(not d["authority_current"] for d in decisions)
            state = (
                "STALE"
                if stale
                else "BLOCKED"
                if not gates["ready"]
                else "REJECTED"
                if any(d["decision"] == "REJECT" for d in decisions)
                else "ACCEPTED"
                if decisions
                else "AWAITING_REVIEW"
            )
            bound = c.execute("SELECT payload FROM estate_snapshot WHERE id=%s", (sid,)).fetchone()[
                0
            ]
            node_states = evaluate_requirements(scenario(bound, p)[0])["states"]
            versions.append(
                dict(
                    id=pid,
                    revision=rev,
                    proposal=p,
                    assessment=a,
                    gates=gates,
                    node_states=node_states,
                    decisions=decisions,
                    state=state,
                )
            )
    return dict(
        format="change-console/v1",
        synthetic=True,
        snapshot=snapshot,
        catalog=catalog,
        versions=versions,
        evidence_current=h[1],
        read_only=True,
    )
