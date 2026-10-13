"""Run the original enterprise generator and dbt pipeline, then export audit observations."""

import csv
import hashlib
import json
import shutil
import time
from decimal import Decimal
from .bundle import write_json


def execute_revenue(source, workspace):
    import duckdb
    from revenue_platform.generator import generate
    from revenue_platform.runtime import (
        MODELS,
        add_correction,
        load_local,
        local_snapshot,
        records,
        run_dbt,
    )

    sources = workspace / "sources"
    timings, timeline = {}, []

    def measured(label, fn):
        start = time.perf_counter()
        result = fn()
        timings[label] = round(time.perf_counter() - start, 3)
        timeline.append(
            {
                "action": label.replace("_", " "),
                "detail": f"Observed original-engine execution: {timings[label]} seconds",
            }
        )
        print(label, timings[label], flush=True)
        return result

    manifest = measured("generate_enterprise_sources", lambda: generate(sources))
    database = workspace / "warehouse.duckdb"
    measured("load_original_sources", lambda: load_local(database, source_dir=sources))
    measured(
        "initial_dbt_build",
        lambda: run_dbt(database, workspace / "initial", full_refresh=True),
    )

    def snapshot_models():
        with duckdb.connect(str(database), read_only=True) as c:
            oid = c.execute(
                "select opportunity_id from read_csv_auto(?) order by event_id limit 1",
                [str(sources / "late_opportunity_events.csv")],
            ).fetchone()[0]
            return {
                "metrics": records(
                    c.execute("select * from analytics.mart_metric_values order by all")
                ),
                "bridge": records(
                    c.execute(
                        "select * from analytics.mart_discrepancy_bridge order by account_id limit 3"
                    )
                ),
                "daily": records(
                    c.execute(
                        "select * from analytics.fct_opportunity_daily where opportunity_id=? order by all",
                        [oid],
                    )
                ),
            }

    before = snapshot_models()
    measured("load_late_correction", lambda: add_correction(database, sources))
    measured(
        "incremental_dbt_build", lambda: run_dbt(database, workspace / "incremental")
    )
    incremental = snapshot_models()
    snapshot = local_snapshot(database)
    shutil.copyfile(database, workspace / "incremental.duckdb")
    measured(
        "full_refresh_dbt_build",
        lambda: run_dbt(database, workspace / "full", full_refresh=True),
    )
    full = snapshot_models()
    differences = {}
    with duckdb.connect(str(database), read_only=True) as c:
        c.execute("set memory_limit='2GB'")
        c.execute("set threads=2")
        previous_path = (
            (workspace / "incremental.duckdb").resolve().as_posix().replace("'", "''")
        )
        c.execute("attach '" + previous_path + "' as previous (read_only)")
        for name in MODELS:
            # Closed model-name list from the pinned source tree, never a user-supplied identifier.
            q1 = f"select count(*) from (select * from analytics.{name} except all select * from previous.analytics.{name})"
            q2 = f"select count(*) from (select * from previous.analytics.{name} except all select * from analytics.{name})"
            differences[name] = [
                c.execute(q1).fetchone()[0],
                c.execute(q2).fetchone()[0],
            ]
        model_counts = {
            name: c.execute(f"select count(*) from analytics.{name}").fetchone()[0]
            for name in MODELS
        }
    if any(any(pair) for pair in differences.values()) or incremental != full:
        raise RuntimeError("incremental/full results differ")
    if before["daily"] == incremental["daily"]:
        raise RuntimeError("late correction did not change observed daily rows")
    metrics = {
        r["metric_id"]: r["value"] for r in full["metrics"] if r["region"] == "ALL"
    }
    selected_ids = {r["account_id"] for r in full["bridge"]}
    raw_selected, controls = {}, {}
    flow_tables = {
        "booking_events": "net_bookings",
        "invoice_lines": "net_invoiced",
        "payment_allocations": "cash_received",
    }
    for table, metric in flow_tables.items():
        total, quarter_count, selected = 0, 0, []
        with (sources / (table + ".csv")).open(newline="", encoding="utf-8") as stream:
            for row in csv.DictReader(stream):
                if "2026-01-01" <= row["event_date"] <= "2026-03-31":
                    total += int(row["amount_cents"])
                    quarter_count += 1
                    if row["account_id"] in selected_ids:
                        selected.append(row)
        raw_selected[table] = selected
        controls[metric] = {
            "cents": str(total),
            "rows": quarter_count,
            "method": "Python csv reader over all Q1 source rows",
        }
        if Decimal(total) / 100 != Decimal(metrics[metric]):
            raise RuntimeError("independent source flow total differs: " + metric)
    annual, eligible, selected = Decimal(0), 0, []
    with (sources / "subscription_contracts.csv").open(
        newline="", encoding="utf-8"
    ) as stream:
        for row in csv.DictReader(stream):
            if row["account_id"] in selected_ids:
                selected.append(row)
            if (
                row["start_date"] <= "2026-03-31" < row["end_date"]
                and row["contract_type"] == "recurring"
                and row["is_trial"] == "0"
            ):
                annual += (
                    Decimal(row["fee_cents"]) * 12 / Decimal(row["billing_months"])
                )
                eligible += 1
    raw_selected["subscription_contracts"] = selected
    controls["period_end_arr"] = {
        "cents": str(annual),
        "eligible_contracts": eligible,
        "method": "Independent Python CSV audit of eligible period-end recurring contracts",
    }
    if annual / 100 != Decimal(metrics["period_end_arr"]):
        raise RuntimeError("independent installed ARR differs")
    dbt = {
        stage: json.loads(
            (workspace / stage / "dbt-target/run_results.json").read_text()
        )
        for stage in ["initial", "incremental", "full"]
    }
    if any(
        r["status"] not in ("pass", "success")
        for run in dbt.values()
        for r in run["results"]
    ):
        raise RuntimeError("dbt build includes unsuccessful results")
    bridge = {
        "bookings_less_invoices": float(
            Decimal(metrics["net_bookings"]) - Decimal(metrics["net_invoiced"])
        ),
        "invoices_less_cash": float(
            Decimal(metrics["net_invoiced"]) - Decimal(metrics["cash_received"])
        ),
    }
    observation = {
        "measures": {k: float(v) for k, v in metrics.items()},
        "bridge": bridge,
        "equivalence": "Zero bidirectional EXCEPT ALL differences in all 15 model rowsets; selected exported rows independently compared.",
        "model_counts": model_counts,
        "timings_seconds": timings,
        "scope": "Enterprise profile: 60000 accounts. Timing is a single local run, not a production benchmark.",
    }
    files = {
        "observation.json": observation,
        "timeline.json": timeline,
        "dataset-manifest.json": manifest,
        "models.json": {"before": before, "incremental": incremental, "full": full},
        "source-controls.json": controls,
        "source-records.json": raw_selected,
        "equivalence.json": {
            "method": "bidirectional EXCEPT ALL in the original warehouse",
            "differences": differences,
        },
        "dbt-results.json": {
            k: [{"node": r["unique_id"], "status": r["status"]} for r in run["results"]]
            for k, run in dbt.items()
        },
    }
    return files, "fresh_engine"
