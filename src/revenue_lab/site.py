"""Static packaging derives views from original artifacts; no independent business engine."""

import hashlib
import json
import shutil
import zipfile
from pathlib import Path
from .bundle import ROOT, verify, write_json

SCENARIOS = {
    "measurement-integrity": ("measurement", "First-Party Measurement — Conversion & Revenue Integrity",
        "Reconcile synthetic source contracts and payments against measured claims; inspect recorded browser controls, local GA4 models and separate native Google sample queries."),
    "analytics-engineering": ("analytics", "Analytics Engineering — Model Correctness & Performance",
        "Inspect 15 SQL/dbt models, six paired local benchmark runs, rejected selective rebuilds and separate historical native Snowflake fixture acceptance."),
    "revenue-integrity": (
        "integrity", "Revenue Integrity: From Sales Commitment to Collected Cash",
        "Trace the $1,500 discrepancy, authoritative records and a separately reviewed delivery recovery. Recorded local execution; synthetic USD.",
    ),
    "release-assurance": (
        "release", "AI Model Release Assurance",
        "Inspect rejected model evaluations, finite-suite acceptance, actual local promotion and controlled-fault rollback.",
    ),
    "gtm-research": (
        "gtm", "SDR account intelligence · sources to seller review",
        "Prioritize six synthetic accounts, compare 40 actual Qwen3 responses and inspect a separately recorded local seller decision.",
    ),
    "gtm-enterprise": (
        "gtm", "120 accounts · USD $3.46M synthetic pipeline",
        "Inspect account qualification, exact approvals and five source CRM outcomes across treatment and holdout.",
    ),
    "gtm-salesforce": (
        "gtm", "Native Salesforce · one guarded SDR Task",
        "A separate Developer Edition run: Account/Contact resolution, ownership, lost-ack recovery and duplicate rollback.",
    ),
    "gtm-qwen": (
        "gtm", "Recorded Qwen3 · advice and refusal",
        "A separate 16-response evaluation preserves exact quotations, policy observations and six citation failures.",
    ),
    "connected-roundtrip": (
        "connected",
        "Salesforce and Snowflake round trip",
        "A governed CRM review survives a lost acknowledgment and changes the next warehouse decision.",
    ),
    "seller-application": (
        "seller",
        "Reviewed discovery action",
        "A saved model response was edited, approved and delivered to a synthetic CRM.",
    ),
    "seller-support-review": (
        "seller",
        "A passing draft with an unsupported claim",
        "Exact citations pass. The draft still implies unverified support availability.",
    ),
    "seller-stale": (
        "seller",
        "Evidence changes before approval",
        "The original Workbench refuses approval after new account evidence arrives.",
    ),
    "seller-suppressed": (
        "seller",
        "Consent blocks the action",
        "A recorded response is replayed; commercial authority prevents an effect.",
    ),
    "seller-live": (
        "seller",
        "Recorded fresh local inference",
        "A real local model produced this response; the original engine recorded the synthetic effect.",
    ),
    "seller-delivery": (
        "seller",
        "Saved response, fresh approved delivery",
        "Recorded response replay with original-engine approval and a new local receiver effect.",
    ),
    "control-recovery": (
        "control",
        "Uncertain delivery and recovery",
        "Durable intent, lost acknowledgments and independently observed receiver effects.",
    ),
    "revenue-bridge": (
        "revenue",
        "Installed ARR and quarterly flows",
        "Different economic measures reconcile at their own grain and time boundary.",
    ),
    "revenue-correction": (
        "revenue",
        "Late correction and equivalent rebuild",
        "Original dbt builds are compared with independently exported model rows.",
    ),
}


def build():
    catalog = []
    for path in sorted((ROOT / "web/evidence").glob("*/bundle.json")):
        verification = verify(path.parent)
        manifest = json.loads(path.read_text())
        scenario = manifest["scenario"]
        investigation, title, summary = SCENARIOS[scenario]
        write_json(path.parent / "verification.json", verification)
        portable = {
            "manifest": manifest,
            "artifacts": {
                # Preserve original line endings inside portable JSON. Text-mode
                # reads would normalize a Windows source artifact before hashing.
                a["path"]: (path.parent / a["path"]).read_bytes().decode("utf-8")
                for a in manifest["artifacts"]
            },
        }
        write_json(path.parent / "portable.json", portable)
        members = {"bundle.json": path.read_bytes(), **{
            a["path"]: (path.parent / a["path"]).read_bytes() for a in manifest["artifacts"]},
            "REPRODUCE.txt": (
                "Clone https://github.com/rlbsem/enterprise-revenue-systems-lab\nInstall requirements.lock and set PYTHONPATH=src.\n"
                + "\n".join(manifest["reproduce"])
                + "\npython -m revenue_lab.cli verify <extracted-bundle>\nRecorded inference is not reproducible byte-for-byte by a new model run.\n"
            ).encode()}
        archive = path.parent / "reproduction.zip"
        if archive.is_symlink():
            raise ValueError("reproduction archive cannot be a symlink")
        unchanged = False
        if archive.exists():
            try:
                with zipfile.ZipFile(archive) as z:
                    unchanged = (len(z.namelist()) == len(members) and set(z.namelist()) == set(members)
                                 and all(z.read(name) == data for name, data in members.items()))
            except (zipfile.BadZipFile, OSError):
                pass
        # Preserve historical bytes when the content is identical. Repacking on
        # Linux would otherwise change Windows ZIP platform metadata and hashes.
        if not unchanged:
            with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as z:
                for name, data in members.items():
                    info = zipfile.ZipInfo(name, date_time=(2026, 1, 1, 0, 0, 0))
                    info.create_system = 3
                    info.external_attr = 0o100644 << 16
                    info.compress_type = zipfile.ZIP_DEFLATED
                    z.writestr(info, data)
        catalog.append(
            {
                "id": scenario,
                "investigation": investigation,
                "title": title,
                "summary": summary,
                "manifest_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                "verification_sha256": hashlib.sha256(
                    (path.parent / "verification.json").read_bytes()
                ).hexdigest(),
                "source": manifest["source"],
                "mode": manifest["mode"],
            }
        )
    write_json(ROOT / "web/catalog.json", {"version": 1, "scenarios": catalog})
    # Distribution is additive in an isolated build directory. No source or evidence deletion.
    shutil.copytree(ROOT / "web", ROOT / "dist", dirs_exist_ok=True)
    print(json.dumps({"scenarios": len(catalog), "output": str(ROOT / "dist")}))
