"""Clean source and static distributions with independently checked inventories."""

import hashlib
import json
import subprocess
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from revenue_lab.bundle import write_json
from revenue_lab.site import build


def files():
    names = subprocess.check_output(
        ["git", "ls-files", "-co", "--exclude-standard"], cwd=ROOT, text=True
    ).splitlines()
    return [
        ROOT / name for name in sorted(set(names)) if name != "package-manifest.json"
    ]


def package():
    build()
    selected = files()
    inventory = {
        p.relative_to(ROOT).as_posix(): {
            "sha256": hashlib.sha256(p.read_bytes()).hexdigest(),
            "bytes": p.stat().st_size,
        }
        for p in selected
    }
    write_json(
        ROOT / "package-manifest.json",
        {
            "version": 1,
            "scope": "all delivered source files; manifest excludes itself to avoid recursion",
            "files": inventory,
        },
    )
    output = ROOT.parent / "outputs/enterprise-revenue-systems-lab"
    output.mkdir(parents=True, exist_ok=True)

    def archive(target, members):
        with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED) as z:
            for name, p in members:
                info = zipfile.ZipInfo(name, date_time=(2026, 1, 1, 0, 0, 0))
                info.compress_type = zipfile.ZIP_DEFLATED
                z.writestr(info, p.read_bytes())
        with zipfile.ZipFile(target) as z:
            if z.testzip():
                raise RuntimeError("archive corruption")
            for name, p in members:
                if (
                    hashlib.sha256(z.read(name)).digest()
                    != hashlib.sha256(p.read_bytes()).digest()
                ):
                    raise RuntimeError("archive inventory mismatch: " + name)

    source = output / "Richard_Butts_Enterprise_Revenue_Systems_Lab.zip"
    static = output / "Enterprise_Revenue_Systems_Lab_Static.zip"
    archive(
        source,
        [
            (ROOT.name + "/" + p.relative_to(ROOT).as_posix(), p)
            for p in [*selected, ROOT / "package-manifest.json"]
        ],
    )
    archive(
        static,
        [
            (p.relative_to(ROOT / "web").as_posix(), p)
            for p in sorted((ROOT / "web").rglob("*"))
            if p.is_file()
        ],
    )
    write_json(
        output / "delivery-verification.json",
        {
            "source_zip": {
                "path": source.name,
                "sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
            },
            "static_zip": {
                "path": static.name,
                "sha256": hashlib.sha256(static.read_bytes()).hexdigest(),
            },
            "source_inventory_files": len(inventory),
            "zip_bytes_match_source": True,
        },
    )
    print(
        json.dumps(
            {"source": str(source), "static": str(static), "files": len(inventory)}
        )
    )


if __name__ == "__main__":
    package()
