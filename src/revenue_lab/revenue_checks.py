"""Selected source economics and exported analytical rows, verified independently."""

from collections import Counter
from decimal import Decimal
from .bundle import canonical


def checks(manifest, files):
    data, observation = files["models.json"], files["observation.json"]
    incremental, full = data["incremental"], data["full"]
    for key in incremental:
        if Counter(map(canonical, incremental[key])) != Counter(
            map(canonical, full[key])
        ):
            raise ValueError("exported incremental/full rowsets differ: " + key)
    if data["before"]["daily"] == incremental["daily"]:
        raise ValueError("correction evidence did not alter daily model rows")
    metrics = {
        r["metric_id"]: Decimal(r["value"])
        for r in full["metrics"]
        if r["region"] == "ALL"
    }
    for key in ("net_bookings", "net_invoiced", "cash_received", "period_end_arr"):
        if abs(metrics[key] - Decimal(str(observation["measures"][key]))) > Decimal(
            "0.000001"
        ):
            raise ValueError("displayed measure contradicts model output")
        if Decimal(files["source-controls.json"][key]["cents"]) / 100 != metrics[key]:
            raise ValueError("independent source control differs from metric")
    raw = files["source-records.json"]
    for row in full["bridge"]:
        expected = {}
        for table, field in [
            ("booking_events", "bookings"),
            ("invoice_lines", "invoiced"),
            ("payment_allocations", "cash"),
        ]:
            expected[field] = (
                sum(
                    int(r["amount_cents"])
                    for r in raw[table]
                    if r["account_id"] == row["account_id"]
                    and "2026-01-01" <= r["event_date"] <= "2026-03-31"
                )
                / 100
            )
            if abs(Decimal(str(expected[field])) - Decimal(str(row[field]))) > Decimal(
                "0.000001"
            ):
                raise ValueError(
                    "selected account bridge contradicts original source rows"
                )
        for key, value in [
            ("bookings_less_invoices", expected["bookings"] - expected["invoiced"]),
            ("invoices_less_cash", expected["invoiced"] - expected["cash"]),
        ]:
            if abs(Decimal(str(value)) - Decimal(str(row[key]))) > Decimal("0.000001"):
                raise ValueError("selected variance arithmetic is wrong")
    if metrics["period_end_arr"] <= metrics["net_bookings"]:
        raise ValueError(
            "installed-base scenario unexpectedly resembles a quarterly launch"
        )
    for stage in files["dbt-results.json"].values():
        if not stage or any(r["status"] not in ("success", "pass") for r in stage):
            raise ValueError("unsuccessful or incomplete dbt evidence")
    differences = files["equivalence.json"]["differences"]
    if len(differences) != 15 or any(any(pair) for pair in differences.values()):
        raise ValueError("full warehouse comparison reports a mismatch")
    return {
        "selected_account_source_totals_checked": len(full["bridge"]),
        "exported_incremental_full_rowsets_equal": True,
        "warehouse_comparison": "Recorded fresh SQL observations: zero differences in 15 models",
        "global_controls": "Fresh runner independently read all source CSVs; small bundle retains controls, not all enterprise rows",
        "arr_stock_distinct_from_quarterly_flows": True,
    }
