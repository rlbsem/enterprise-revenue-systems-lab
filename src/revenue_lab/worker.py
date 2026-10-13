"""Isolated child execution; only the runner supplies these arguments."""

import sys
import hashlib
import importlib.metadata
from datetime import datetime, timezone
from pathlib import Path
from .bundle import seal

if __name__ == "__main__":
    scenario, source, workspace = sys.argv[1], Path(sys.argv[2]), Path(sys.argv[3])
    if scenario not in {
        "seller-stale",
        "seller-suppressed",
        "seller-delivery",
        "seller-live",
        "control-recovery",
        "revenue-correction",
    }:
        raise ValueError("worker scenario is not approved")
    started = datetime.now(timezone.utc).isoformat()
    # Each source owns a complete pinned lock. Refuse execution with different dependencies.
    from packaging.requirements import Requirement

    differences = []
    for line in (
        (source / "requirements.lock").read_text(encoding="utf-8-sig").splitlines()
    ):
        if not line.strip() or line.startswith("#"):
            continue
        requirement = Requirement(line)
        if requirement.marker and not requirement.marker.evaluate():
            continue
        try:
            version = importlib.metadata.version(requirement.name)
        except importlib.metadata.PackageNotFoundError:
            version = "missing"
        if version == "missing" or not requirement.specifier.contains(version):
            differences.append(requirement.name)
    if differences:
        raise RuntimeError(
            "Pinned source dependencies differ: " + ",".join(differences)
        )
    if scenario.startswith("seller-"):
        from .seller_adapter import execute

        files, mode = execute(
            scenario, source, workspace, sys.argv[4] if len(sys.argv) > 4 else None
        )
    else:
        from .execution import execute

        files, mode = execute(scenario, source, workspace)
    files["execution.json"] = {
        "scenario": scenario,
        "interpreter": sys.version,
        "started_at": started,
        "finished_at": datetime.now(timezone.utc).isoformat(),
        "dependency_lock_sha256": hashlib.sha256(
            (source / "requirements.lock").read_bytes()
        ).hexdigest(),
        "dependencies": {
            d.metadata["Name"]: d.version for d in importlib.metadata.distributions()
        },
        "scope": "original engine in isolated workspace",
    }
    limitation = (
        "Fresh actual local inference; automatic scenario approval is not independent human review."
        if mode == "fresh_inference"
        else "Saved response replay; no new inference was performed."
        if mode == "fresh_replay"
        else "Original engine execution. Exported observations support bounded checks, not production guarantees."
    )
    seal(
        workspace / "bundle",
        scenario,
        scenario.split("-")[0],
        files,
        mode,
        ["Local synthetic execution, not production deployment.", limitation],
    )
