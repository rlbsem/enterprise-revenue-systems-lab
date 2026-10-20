"""Read-only checks of the published Lab against this exact checkout's web files."""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from revenue_lab.bundle import ROOT
from revenue_lab.smoke import PUBLIC_URL, check_site

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--expected", type=Path, default=ROOT / "web")
parser.add_argument("--output", type=Path, default=ROOT / ".cache/hosted")
args = parser.parse_args()
report = check_site(PUBLIC_URL, args.expected, args.output, source_links=True)
print(json.dumps({"status": report["status"], "checks": len(report["checks"]), "failures": report["failures"]}))
raise SystemExit(0 if report["status"] == "passed" else 1)
