"""Portable links, catalog integrity, bundle semantics and package inventory checks."""

import hashlib
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from revenue_lab.bundle import ROOT, verify

catalog = json.loads((ROOT / "web/catalog.json").read_text())
checks = []
for item in catalog["scenarios"]:
    path = ROOT / "web/evidence" / item["id"]
    assert (
        hashlib.sha256((path / "bundle.json").read_bytes()).hexdigest()
        == item["manifest_sha256"]
    )
    assert (
        hashlib.sha256((path / "verification.json").read_bytes()).hexdigest()
        == item["verification_sha256"]
    )
    checks.append(verify(path))
    portable = json.loads((path / "portable.json").read_text())
    for artifact in portable["manifest"]["artifacts"]:
        assert (
            portable["artifacts"][artifact["path"]].encode()
            == (path / artifact["path"]).read_bytes()
        )
links = 0
for path in [ROOT / "README.md", *(ROOT / "docs").rglob("*.md")]:
    for target in re.findall(r"\]\(([^)]+)\)", path.read_text(encoding="utf-8")):
        if target.startswith(("https://", "http://", "#", "mailto:")):
            continue
        assert (path.parent / target.split("#")[0]).exists(), f"{path.name}: {target}"
        links += 1
print(
    json.dumps(
        {"bundles": len(checks), "local_markdown_links": links, "status": "passed"}
    )
)
manifest = ROOT / "package-manifest.json"
if manifest.exists():
    inventory = json.loads(manifest.read_text())["files"]
    import subprocess

    if (ROOT / ".git").exists():
        names = set(
            subprocess.check_output(
                ["git", "ls-files", "-co", "--exclude-standard"], cwd=ROOT, text=True
            ).splitlines()
        )
    else:
        ignored = {
            ".cache",
            ".venv",
            "dist",
            "__pycache__",
            ".pytest_cache",
            ".hypothesis",
            ".ruff_cache",
            "node_modules",
            "test-results",
        }
        names = {
            p.relative_to(ROOT).as_posix()
            for p in ROOT.rglob("*")
            if p.is_file()
            and not any(
                part in ignored or part.endswith(".egg-info")
                for part in p.relative_to(ROOT).parts
            )
        }
    names -= {"package-manifest.json"}
    assert names == set(inventory), "package file inventory differs"
    for name, entry in inventory.items():
        assert (
            hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == entry["sha256"]
        ), "package hash differs: " + name
    print(json.dumps({"package_inventory": len(inventory), "status": "passed"}))
