"""Offline checks of pinned records, not live governance, source services or activation."""

import base64
from collections import Counter, defaultdict
import hashlib
import json

from .bundle import LOCK, canonical, digest
from .gtm_checks import require

SCENARIOS = {"estate-assurance": "estate", "reliability-operations": "reliability", "temporal-assurance": "temporal"}


def exact(a, b):
    """JSON types matter: True, 1 and 1.0 must not alias in receipts or decisions."""
    return canonical(a) == canonical(b)


def estate_digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()).hexdigest()


def original_bytes(path, scenario, upstream):
    require(exact(upstream, LOCK["assurance_imports"][scenario]), "unexpected assurance provenance")
    source = LOCK["sources"][SCENARIOS[scenario]]
    require(upstream["repository"] == source["repository"] and upstream["import_revision"] == source["commit"], "source pin mismatch")
    for a in upstream["artifacts"]:
        require(a["source_url"] == f"https://github.com/{source['repository']}/blob/{source['commit']}/{a['source_path']}", "unpinned source URL")
        require(hashlib.sha256((path / a["file"]).read_bytes()).hexdigest() == a["sha256"], "original assurance bytes differ")


def estate(files):
    record = files["record.json"]
    snapshot = record["snapshot"]
    require(record["synthetic"] is True and record["read_only"] is True, "estate execution boundary")
    require(snapshot["id"] == estate_digest({k:v for k,v in snapshot.items() if k != "id"}), "snapshot identity")
    versions = {(v["id"],v["revision"]):v for v in record["versions"]}
    require(len(versions) == len(record["versions"]), "duplicate proposal version")
    for v in versions.values():
        a, p = v["assessment"], v["proposal"]
        require(a["id"] == estate_digest({k:x for k,x in a.items() if k != "id"}), "assessment identity")
        require(a["proposal_hash"] == estate_digest(p) and exact(a["proposal"],p), "proposal binding")
        require(p["base_snapshot"] == a["snapshot_id"] == snapshot["id"], "historical snapshot binding")
        require(all(type(x) is bool for x in v["gates"]["checks"].values()), "gate types")
        require(v["gates"]["ready"] is all(v["gates"]["checks"].values()), "false clean readiness")
        if v["state"] == "ACCEPTED":
            require(v["gates"]["ready"] is True and any(d["decision"] == "ACCEPT" and d["authority_current"] is True for d in v["decisions"]), "acceptance without recorded authority")
        actual = a["requirements"]
        require(sorted(a["failed_requirements"]) == sorted(k for k,x in actual.items() if x["state"] == "UNSUPPORTED"), "failed requirement list")
        require(sorted(a["unknown_requirements"]) == sorted(k for k,x in actual.items() if x["state"] == "UNKNOWN"), "unknown requirement list")
    comparisons = files["comparison.json"]["comparisons"]
    for c in comparisons:
        require(exact(c["actual"], c["independent"]), "independent estate comparison")
        if c["proposal"] != "baseline":
            v = versions[c["proposal"],c["revision"]]
            require(exact(c["actual"], {k.removeprefix("req:"):state for k,state in v["node_states"].items() if k.startswith("req:")}), "comparison does not describe target graph")
            require(all(c["actual"][k] == x["state"] for k,x in v["assessment"]["requirements"].items()), "comparison does not describe scoped assessment")
    count = sum(len(c["actual"]) for c in comparisons)
    require(count == files["comparison.json"]["requirements_compared"], "comparison count")
    require(snapshot["facts"]["ownership:atlas/workbench"]["state"] == "UNKNOWN", "preserved owner dispute")
    return {"companies":len(record["catalog"]["companies"]), "systems":sum(f["kind"] == "system" for f in snapshot["facts"].values()),
            "requirements":sum(f["kind"] == "requirement" for f in snapshot["facts"].values()),
            "proposal_revisions":len(versions), "independent_requirement_outcomes":count,
            "change_classes":sorted({v["proposal"]["change_kind"] for v in versions.values()}),
            "capture_clock":snapshot["as_of"], "native_external_execution":False}


def reliability(files):
    r = files["record.json"]
    require(r["synthetic"] is True and r["native_marketing_vendor_calls"] == 0, "reliability execution boundary")
    snapshot = r["snapshot"]
    warehouse = snapshot["warehouse"]
    raw = {}
    for d in snapshot["retained_remote_deliveries"]:
        data = base64.b64decode(d["exact_base64"], validate=True)
        require(hashlib.sha256(data).hexdigest() == d["sha256"], "retained source bytes")
        require((d["service"],d["seq"]) not in raw, "duplicate source position")
        raw[d["service"],d["seq"]] = (d, json.loads(data))
    positions = {(d["service"], d["seq"]): d for d in snapshot["journal"]["deliveries"]}
    require(set(raw) == set(positions), "unaccounted source positions")
    for service, source in r["independent_source_receipts"].items():
        for ack in source["acknowledgments"]:
            receipt = json.loads(ack["body"])
            position = positions[service,ack["seq"]]
            require(type(receipt["seq"]) is int and receipt["seq"] == ack["seq"], "receipt sequence type")
            require(receipt["service"] == service and receipt["sha256"] == position["sha"], "receipt identity")
            # The upstream ack ID is a durable receiver identity; its exact original
            # content is also bound by the controller's checkpoint audit below.
            require(isinstance(receipt["ack_id"], str) and len(receipt["ack_id"]) == 64, "missing acknowledgment identity")
    audits = snapshot["journal"]["audit"]
    acks = {(service,a["seq"]):json.loads(a["body"]) for service,s in r["independent_source_receipts"].items() for a in s["acknowledgments"]}
    for audit in audits:
        if audit["operation"] == "checkpoint_committed":
            body = json.loads(audit["body"])
            require(exact(body["receipt"], acks[body["receipt"]["service"],body["receipt"]["seq"]]), "checkpoint independent readback differs")
    for checkpoint in snapshot["journal"]["checkpoints"]:
        require(set(range(1,checkpoint["seq"]+1)) <= {seq for service,seq in acks if service == checkpoint["service"]}, "checkpoint skipped unacknowledged position")
    by_hash = {d["sha256"]:body for d,body in raw.values()}
    quarantined = {(row[0],row[1]) for row in warehouse["quarantine"]}
    versions, dispositions = {}, Counter()
    accepted = [d for d,body in raw.values() if d.get("warehouse_receipt",{}).get("status") == "accepted"]
    for delivery in accepted:
        body = by_hash[delivery["sha256"]]
        require(body["source"] in {"campaigns","paid_media","web","crm"}, "unknown accepted source")
        for line,row in enumerate(body["rows"],1):
            if (delivery["sha256"],line) in quarantined:
                dispositions["quarantined"] += 1
                continue
            key = (body["source"],row["id"],row["revision"])
            normalized = dict(row)
            if body["source"] == "paid_media" and row["op"] == "upsert":
                require(body["schema_version"] in [1,2] and (body["schema_version"] == 1 or row["currency"] == "USD"), "source currency contract")
                normalized.setdefault("currency", "USD")  # documented v1 unit, never FX conversion
            if key in versions:
                require(exact(versions[key],normalized), "conflicting admitted revision")
                dispositions["duplicate"] += 1
            else:
                versions[key] = normalized
                dispositions["admitted"] += 1
    latest = {}
    for (source,key,rev),row in versions.items():
        if (source,key) not in latest or latest[source,key]["revision"] < rev:
            latest[source,key] = row
    final = next(c for c in snapshot["candidates"] if c["run"]["id"] == warehouse["active_run"])
    lineage = final["lineage"]
    require(len(lineage) == len(latest), "latest-source grain")
    for source,key,rev,op,day,campaign,hash_value,line in lineage:
        body = by_hash[hash_value]
        source_row = body["rows"][line-1]
        require(body["source"] == source and (source,key,rev) in versions, "raw lineage identity")
        require(source_row["id"] == key and source_row["revision"] == rev and source_row["op"] == op, "raw lineage row")
        require(source_row.get("day") == day and source_row.get("campaign_id") == campaign, "raw lineage business coordinates")
        require(latest[source,key]["revision"] == rev, "lineage not latest revision")
    labels = {key:row["name"] for (s,key),row in latest.items() if s == "campaigns" and row["op"] != "delete"}
    groups = defaultdict(lambda:[0,0,0,0,0])
    metric_keys = ["cost_cents","impressions","clicks","conversions","revenue_cents"]
    for (source,_),row in latest.items():
        if source == "campaigns" or row["op"] == "delete":
            continue
        require(row["campaign_id"] in labels, "unresolved final reference")
        values = groups[row["day"],row["campaign_id"]]
        for i,k in enumerate(metric_keys):
            value = row.get(k,0)
            require(type(value) is int, "metric type")
            values[i] += value
    table = [[day,campaign,labels[campaign],*values] for (day,campaign),values in sorted(groups.items())]
    require(exact(table, warehouse["published"]) and exact(table,final["raw_oracle"]["expected"]), "raw-source financial reconciliation")
    require(dict(dispositions) == warehouse["row_dispositions"], "row disposition accounting")
    require(sum(dispositions.values()) == warehouse["accepted_delivery_rows"], "accepted source accounting")
    require(len(versions) == warehouse["admitted_versions"] and len(latest) == warehouse["current_live_records"] + warehouse["current_tombstones"], "source revision accounting")
    wrong = next(c for c in snapshot["candidates"] if c["name"] == "Equal row count, wrong values")
    require(len(wrong["table"]) == len(wrong["raw_oracle"]["expected"]) and wrong["raw_oracle"]["differences"] and wrong["run"]["status"] != "published", "wrong-value candidate erased or published")
    require(any(a["operation"] == "publication_blocked" for a in audits), "failed publication not retained")
    return dict(sources=len(r["independent_source_receipts"]),source_positions=len(raw),row_accounting=dict(dispositions),
                latest_records=len(latest),superseded=len(versions)-len(latest), rows=len(table),active_run=warehouse["active_run"],
                totals=dict(zip(metric_keys,[sum(row[i+3] for row in table) for i in range(5)])),
                raw_source_rows_reconciled=len(lineage),candidates=len(snapshot["candidates"]),native_external_execution=False)


def temporal_rows(inbox, pub):
    """Independent finite interpretation of the retained source records, without SQL."""
    rules, clock = pub["body"]["rules"], pub["clock"]
    rows, covers, people = {}, [], set()
    for batch in inbox:
        if batch["brand"] != pub["brand"] or batch["seq"] > pub["known"]:
            continue
        if batch["kind"] == "coverage":
            covers.append(batch["body"])
            continue
        for row in batch["body"]:
            people.add(row["person_id"])
            key = row["source"],row["fact_id"]
            if key not in rows or row["revision"] > rows[key]["revision"]:
                rows[key] = row
    active = [r for r in rows.values() if not r["retracted"]]
    coverage = max(covers,key=lambda r:r["revision"]) if covers else None
    covered = bool(coverage and not coverage["retracted"] and coverage["covered_after"] <= clock-rules["quiet_window"] and coverage["covered_through"] >= clock)
    answer = {}
    for person in people:
        profiles = [r for r in active if r["person_id"] == person and r["source"] == "profile" and r["effective_at"] <= clock]
        last = max((r["effective_at"] for r in profiles),default=None)
        trial = {r["value"] for r in profiles if r["effective_at"] == last} == {"trial"}
        events = [r for r in active if r["person_id"] == person and r["source"] == "activity" and r["value"] == "qualified" and r["effective_at"] <= clock]
        engaged = sum(r["effective_at"] > clock-rules["engaged_window"] for r in events)
        quiet = sum(r["effective_at"] > clock-rules["quiet_window"] for r in events)
        answer[person,"engaged_trial"] = dict(member=trial and engaged >= rules["minimum_events"],covered=True)
        answer[person,"quiet_trial"] = dict(member=trial and quiet == 0,covered=covered)
    return answer


def temporal(files):
    r = files["record.json"]
    require(r["synthetic"] is True and r["native_vendor_calls"] == 0, "temporal execution boundary")
    o, receiver = r["snapshot"]["operating"],r["snapshot"]["receiver"]
    count = 0
    publications = {p["id"]:p for p in o["publications"]}
    require(len(publications) == len(o["publications"]), "publication identity")
    for pub in publications.values():
        expected = temporal_rows(o["inbox"],pub)
        rows = [x for x in o["decisions"] if x["publication"] == pub["id"]]
        actual = {(x["person"],x["segment"]):dict(member=x["member"],covered=x["covered"]) for x in rows}
        require(len(actual) == len(rows) and set(actual) == set(expected), "temporal row grain")
        require(all(exact(actual[k],expected[k]) for k in expected), "raw-source temporal decision mismatch")
        require(all(x["brand"] == pub["brand"] for x in rows), "cross-brand decision leak")
        count += len(rows)
    grants = {}
    for row in o["permissions"]:
        if row["channel"] == "email" and row["purpose"] == "trial_help":
            key = row["brand"],row["person"]
            if key not in grants or row["revision"] > grants[key]["revision"]:
                grants[key] = row
    eligible = []
    for brand in o["brands"]:
        current = [row for row in o["activation_eligibility"] if row["brand"] == brand["brand"]]
        require(len(current) == 2 * sum(s["brand"] == brand["brand"] for s in o["subjects"]), "eligibility person-audience grain")
        for row in current:
            pub = publications[row["publication"]]
            require(pub["brand"] == row["brand"], "cross-brand active pointer")
            source = temporal_rows(o["inbox"],pub)[row["person"],row["segment"]]
            grant = grants.get((row["brand"],row["person"]))
            allowed = bool(source["member"] and source["covered"] and grant and grant["allowed"] and not grant["suppressed"] and grant["valid_from"] <= brand["clock"] < grant["expires"] and pub["clock"] == brand["clock"] and pub["known"] == sum(b["brand"] == row["brand"] for b in o["inbox"]))
            require(allowed == (row["reason"] == "eligible"), "current permission mismatch")
            if allowed: eligible.append([row["brand"],row["person"],row["segment"]])
    effects, records = {e["id"]:e for e in receiver["effects"]},{x["id"]:x for x in receiver["records"]}
    require(len(effects) == len(receiver["effects"]) == len(records), "duplicate independent effect")
    for intent in o["intents"]:
        require(intent["hash"] == digest(intent["payload"]), "frozen intent payload hash")
        if intent["state"] != "confirmed":continue
        effect = effects[intent["id"]]
        record = records[intent["id"]]
        require(exact(effect["payload"],intent["payload"]) and exact(effect["receipt"],intent["receipt"]), "receipt recovery identity")
        require(record["hash"] == digest(record["body"]) == intent["receipt"]["record_hash"] and exact(record["body"],intent["receipt"]["record"]), "independent business record")
    require(r["observations"]["history"]["new_http_actions_from_backfill"] == 0, "historical restatement emitted action")
    return dict(brands=len(o["brands"]),publications=len(publications),historical_decisions=count,
                eligibility_rows=len(o["activation_eligibility"]),eligible=eligible,effects=len(effects),
                intents=len(o["intents"]),observed_requests=len(receiver["requests"]),
                lost_acknowledgments=sum(x["result"] == "committed_ack_lost" for x in receiver["requests"]),
                native_external_execution=False)


def project(scenario, files):
    result = {"estate-assurance":estate,"reliability-operations":reliability,"temporal-assurance":temporal}[scenario](files)
    result["boundary"] = "Offline reconstruction of selected original records; no new source-engine, vendor or model execution."
    return result


def verify_assurance(path, scenario, files):
    original_bytes(path,scenario,files["upstream.json"])
    require(files["regression.json"]["status"] == "passed", "upstream execution did not pass")
    for check in files["record.json"].get("checks", []):
        require(check["passed"] is True and exact(check["expected"],check["observed"]), "upstream assertion did not pass")
    for group in files["regression.json"]["suites"].values():
        require(not any(group[k] for k in ["failures","errors","skipped"]), "upstream regression did not pass")
    calculated = project(scenario,files)
    require(exact(calculated,files["projection.json"]), "derived assurance projection differs")
    return calculated
