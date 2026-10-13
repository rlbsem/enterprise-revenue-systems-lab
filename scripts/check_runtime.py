import importlib.metadata
import json
import sys
from pathlib import Path
from packaging.requirements import Requirement

differences = []
checked = 0
for line in Path(sys.argv[1]).read_text(encoding="utf-8-sig").splitlines():
    if not line.strip() or line.startswith("#"):
        continue
    req = Requirement(line)
    if req.marker and not req.marker.evaluate():
        continue
    checked += 1
    try:
        actual = importlib.metadata.version(req.name)
    except importlib.metadata.PackageNotFoundError:
        actual = "missing"
    if actual == "missing" or not req.specifier.contains(actual):
        differences.append(
            {"package": req.name, "expected": str(req.specifier), "actual": actual}
        )
print(json.dumps({"checked": checked, "differences": differences}))
sys.exit(bool(differences))
