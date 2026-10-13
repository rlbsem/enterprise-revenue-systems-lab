"""Isolated child execution; only the runner supplies these arguments."""
import sys
from pathlib import Path
from .bundle import seal

if __name__ == "__main__":
    scenario, source, workspace = sys.argv[1], Path(sys.argv[2]), Path(sys.argv[3])
    if scenario.startswith("seller-"):
        from .seller_adapter import execute
        files, mode = execute(scenario, source, workspace, sys.argv[4] if len(sys.argv) > 4 else None)
    else:
        from .execution import execute
        files, mode = execute(scenario, source, workspace)
    files["execution.json"] = {"scenario": scenario, "interpreter": sys.version,
                               "scope": "original engine in isolated workspace"}
    seal(workspace / "bundle", scenario, scenario.split("-")[0], files, mode,
         ["Local synthetic execution, not production deployment.",
          "Recorded-response replay is not new inference; model availability is explicit."])
