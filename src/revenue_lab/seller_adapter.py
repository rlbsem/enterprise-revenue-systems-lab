"""Actual original Workbench execution with explicit recorded response replay."""
import copy
import json
import sqlite3
from pathlib import Path

from .bundle import ROOT, digest, seal


def recorded(source, output):
    evidence = source / "docs/evidence/seller"
    application = json.loads((evidence / "application.json").read_text())
    limitations = ["Synthetic accounts and HTTP CRM, not client deployment.",
                   "Saved actual Qwen3-14B inference; no new inference in this explorer.",
                   "Independent blinded usefulness review remains pending."]
    seal(output / "seller-application", "seller-application", "seller", {
        "application.json": (evidence / "application.json").read_bytes(),
        "operations.json": (evidence / "operations.json").read_bytes(),
        "runtime.json": (evidence / "runtime.json").read_bytes(),
        "observation.json": {"runs": len(application["runs"]), "actions": len(application["actions"]),
                             "scope": application["execution_scope"]},
    }, "recorded", limitations)
    files = {"trace.json": (evidence / "traces/grounded_workflow-regression-008-42.json").read_bytes(),
             "simple.json": (evidence / "traces/simple_llm-regression-008-42.json").read_bytes(),
             "template.json": (evidence / "traces/template-regression-008-42.json").read_bytes(),
             "review.md": (source / "docs/seller-review-notes.md").read_bytes(),
             "observation.json": {"finding": "Unsupported support availability", "review_type": "targeted_non_blinded_QA"}}
    seal(output / "seller-support-review", "seller-support-review", "seller", files, "recorded", limitations)


def execute(scenario, source, workspace, model_url=None):
    from signals.fixtures import AS_OF
    from signals.harness import serve
    from signals.seller import Model, Workbench, task_destination
    from signals.seller_fixtures import seed_workbench
    from signals.store import Refused, Store
    evidence = json.loads((source / "docs/evidence/seller/application.json").read_text())
    account = "account-0004" if scenario == "seller-suppressed" else "account-0012"
    original = next(r for r in evidence["runs"] if r["snapshot"]["account"] == account)

    class Replay:
        config = {"mode": "recorded_response_replay", "model": "saved-qwen3-14b-response",
                  "record_hash": digest(original)}

        def generate(self, snapshot):
            if snapshot != original["snapshot"]:
                raise Refused("recorded_response_input_mismatch")
            return copy.deepcopy(original["raw_proposal"]), {"mode": "recorded_response_replay",
                    "original_inference": original["inference"], "record_hash": digest(original)}

    model = Model(model_url, "qwen3-14b") if model_url else Replay()
    bench = Workbench(Store(workspace / "seller.sqlite"), model, AS_OF)
    seed_workbench(bench)
    run = bench.generate("cedar", account, "lab_scenario")
    if run["status"] != "review_required":
        raise RuntimeError("original engine generation unavailable: " + run.get("error", "unknown"))
    refusal, receipt = None, None
    if scenario == "seller-stale":
        bench.document({"id": "new-note", "brand": "cedar", "account": account, "revision": 1,
                        "title": "Changed requirements", "kind": "call_note",
                        "occurred_at": "2026-03-31T12:00:00Z", "text": "The requirements changed."}, "lab_scenario")
    with serve(task_destination(workspace / "receiver.sqlite", "ephemeral-local-test-token")) as url:
        try:
            action = bench.approve(run["id"], run["proposal"], digest(run), "lab_scenario")
            receipt = bench.deliver(action["id"], url, "ephemeral-local-test-token", "lab_scenario")
        except Refused as exc:
            refusal = str(exc)
    with sqlite3.connect(workspace / "receiver.sqlite") as con:
        receiver = [{"id": r[0], "body": json.loads(r[1]), "receipt": json.loads(r[2])}
                    for r in con.execute("SELECT id,body,receipt FROM seller_tasks")]
    return {"application.json": bench.overview(), "recorded-input.json": original,
            "receiver.json": receiver, "observation.json": {"refusal": refusal, "receipt": receipt,
              "receiver_rows": len(receiver), "current_snapshot": bench.context("cedar", account)}}, (
            "fresh_inference" if model_url else "fresh_replay")
