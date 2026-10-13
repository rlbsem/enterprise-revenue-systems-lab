"""Executed local UI proof; requires prepared seller environment and opt-in Lab server."""

import argparse
import json
from pathlib import Path
from playwright.sync_api import sync_playwright

p = argparse.ArgumentParser()
p.add_argument("--url", default="http://127.0.0.1:8542")
p.add_argument("--output", type=Path, default=Path("docs/evidence/local-ui.json"))
a = p.parse_args()
checks = []
with sync_playwright() as playwright:
    browser = playwright.chromium.launch(headless=True)
    page = browser.new_page(viewport={"width": 1440, "height": 1000})
    for scenario in ["seller-stale", "seller-suppressed", "seller-delivery"]:
        page.goto(a.url + "/?case=" + scenario)
        page.get_by_text(
            "Reproduce this investigation · fresh local execution", exact=True
        ).click()
        page.get_by_role("button", name="Run approved local scenario").click()
        page.locator("#fresh-status").filter(
            has_text="Original engine executed successfully"
        ).wait_for(timeout=30000)
        assert page.get_by_text("FRESH LOCAL EXECUTION", exact=True).count() == 2
        assert "Artifact integrity verified" in page.locator("#status").inner_text()
        with page.expect_download() as event:
            page.get_by_role("link", name="Download fresh portable JSON").click()
        a.output.parent.mkdir(parents=True, exist_ok=True)
        saved = a.output.parent / (scenario + "-fresh.json")
        event.value.save_as(saved)
        bundle = json.loads(saved.read_text())
        assert bundle["manifest"]["mode"] == "fresh_replay"
        app = json.loads(bundle["artifacts"]["application.json"])
        assert all(
            r["configuration"]["mode"] == "recorded_response_replay"
            for r in app["runs"]
        )
        checks.append(
            {
                "scenario": scenario,
                "result": "fresh original engine executed",
                "new_inference": False,
            }
        )
    page.screenshot(path="docs/images/local-execution.png", full_page=True)
    browser.close()
a.output.write_text(
    json.dumps(
        {
            "checks": checks,
            "scope": "Real Chromium controls, original Workbench, isolated receivers; no fresh inference in these three replay tests",
        },
        indent=2,
    )
    + "\n"
)
print(json.dumps(checks))
