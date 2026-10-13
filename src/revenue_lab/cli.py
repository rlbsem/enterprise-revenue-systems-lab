import argparse
import json
import os
import subprocess
import sys
from pathlib import Path
from uuid import uuid4

from .bundle import LOCK, ROOT, seal, verify, write_json


def source_path(key):
    return ROOT / ".cache/sources" / LOCK["sources"][key]["repository"].split("/")[1]


def assert_source(key):
    path = source_path(key)
    actual = subprocess.check_output(["git", "-C", str(path), "rev-parse", "HEAD"], text=True).strip()
    dirty = subprocess.check_output(["git", "-C", str(path), "status", "--porcelain", "--untracked-files=no"], text=True).strip()
    if actual != LOCK["sources"][key]["commit"] or dirty:
        raise ValueError("source revision mismatch or modified source tree")
    return path


def prepare(key, install=False):
    path = source_path(key)
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(["git", "clone", "--no-checkout", "https://github.com/" + LOCK["sources"][key]["repository"] + ".git", str(path)], check=True, timeout=180)
        subprocess.run(["git", "-C", str(path), "checkout", "--detach", LOCK["sources"][key]["commit"]], check=True, timeout=60)
    assert_source(key)
    if install:
        env = ROOT / ".cache/envs" / key
        subprocess.run([sys.executable, "-m", "venv", str(env)], check=True, timeout=60)
        python = env / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
        subprocess.run([str(python), "-m", "pip", "install", "-r", str(path / "requirements.lock")], check=True, timeout=600)
    print(path)


def run(scenario, python=None, model_url=None):
    allowed = {"seller-stale", "seller-suppressed", "seller-live", "control-recovery", "revenue-correction"}
    if scenario not in allowed:
        raise ValueError("scenario is not approved for execution")
    key = scenario.split("-")[0]
    source = assert_source(key)
    workspace = ROOT / ".cache/runs" / (scenario + "-" + uuid4().hex)
    workspace.mkdir(parents=True)
    if scenario == "seller-live":
        from urllib.parse import urlparse
        parsed = urlparse(model_url or "")
        if parsed.scheme != "http" or parsed.hostname not in ("127.0.0.1", "localhost") or parsed.username or parsed.password:
            raise ValueError("fresh inference requires an explicit local HTTP model endpoint")
    command = [python or str(ROOT / ".cache/envs" / key / ("Scripts/python.exe" if os.name == "nt" else "bin/python")),
               "-m", "revenue_lab.worker", scenario, str(source), str(workspace)]
    if model_url:
        command += [model_url]
    env = dict(os.environ, PYTHONPATH=os.pathsep.join([str(ROOT / "src"), str(source / "src")]))
    try:
        result = subprocess.run(command, env=env, capture_output=True, text=True, timeout=900 if key == "revenue" else 120)
    except subprocess.TimeoutExpired:
        write_json(workspace / "failure.json", {"status": "timeout", "scenario": scenario})
        raise RuntimeError("scenario timed out; no successful bundle produced")
    (workspace / "execution.log").write_text(result.stdout + result.stderr, encoding="utf-8")
    if result.returncode:
        write_json(workspace / "failure.json", {"status": "failed", "returncode": result.returncode, "scenario": scenario})
        raise RuntimeError("scenario failed; see " + str(workspace / "execution.log"))
    verified = verify(workspace / "bundle")
    write_json(workspace / "verification.json", verified)
    print(json.dumps({"bundle": str(workspace / "bundle"), "verification": verified}, indent=2))
    return workspace / "bundle"


def main():
    p = argparse.ArgumentParser(description="Pinned, bounded Enterprise Revenue Systems Lab")
    sub = p.add_subparsers(dest="command", required=True)
    s = sub.add_parser("prepare"); s.add_argument("source", choices=LOCK["sources"]); s.add_argument("--install", action="store_true")
    s = sub.add_parser("recorded"); s.add_argument("--source", choices=["seller", "control", "revenue"], default="seller")
    s = sub.add_parser("verify"); s.add_argument("bundle", type=Path)
    s = sub.add_parser("run"); s.add_argument("scenario"); s.add_argument("--python"); s.add_argument("--model-url")
    sub.add_parser("build")
    args = p.parse_args()
    if args.command == "prepare":
        prepare(args.source, args.install)
    elif args.command == "run":
        run(args.scenario, args.python, args.model_url)
    elif args.command == "verify":
        print(json.dumps(verify(args.bundle), indent=2))
    elif args.command == "recorded":
        source = assert_source(args.source)
        if args.source == "seller":
            from .seller_adapter import recorded
        else:
            from .recorded import recorded
        recorded(source, ROOT / "web/evidence")
    else:
        from .site import build
        build()


if __name__ == "__main__":
    main()
