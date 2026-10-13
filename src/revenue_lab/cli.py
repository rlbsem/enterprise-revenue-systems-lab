import argparse
import json
import os
import subprocess
import sys
import signal
from pathlib import Path
from uuid import uuid4

from .bundle import LOCK, ROOT, seal, verify, write_json


def source_path(key):
    return ROOT / ".cache/sources" / LOCK["sources"][key]["repository"].split("/")[1]


def assert_source(key):
    path = source_path(key)
    actual = subprocess.check_output(
        ["git", "-C", str(path), "rev-parse", "HEAD"], text=True
    ).strip()
    dirty = subprocess.check_output(
        ["git", "-C", str(path), "status", "--porcelain", "--untracked-files=normal"],
        text=True,
    ).strip()
    if actual != LOCK["sources"][key]["commit"] or dirty:
        raise ValueError("source revision mismatch or modified source tree")
    return path


def prepare(key, install=False):
    path = source_path(key)
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(
            [
                "git",
                "clone",
                "--no-checkout",
                "https://github.com/" + LOCK["sources"][key]["repository"] + ".git",
                str(path),
            ],
            check=True,
            timeout=180,
        )
        subprocess.run(
            [
                "git",
                "-C",
                str(path),
                "checkout",
                "--detach",
                LOCK["sources"][key]["commit"],
            ],
            check=True,
            timeout=60,
        )
    assert_source(key)
    if install:
        env = ROOT / ".cache/envs" / key
        python = env / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
        if not python.exists():
            subprocess.run(
                [sys.executable, "-m", "venv", str(env)], check=True, timeout=60
            )
        python = env / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
        subprocess.run(
            [
                str(python),
                "-m",
                "pip",
                "install",
                "--no-deps",
                "-r",
                str(path / "requirements.lock"),
            ],
            check=True,
            timeout=1800,
        )
    print(path)


def run(scenario, python=None, model_url=None):
    allowed = {
        "seller-stale",
        "seller-suppressed",
        "seller-delivery",
        "seller-live",
        "control-recovery",
        "revenue-correction",
    }
    if scenario not in allowed:
        raise ValueError("scenario is not approved for execution")
    key = scenario.split("-")[0]
    source = assert_source(key)
    workspace = ROOT / ".cache/runs" / (scenario + "-" + uuid4().hex)
    workspace.mkdir(parents=True)
    if scenario == "seller-live":
        from urllib.parse import urlparse

        parsed = urlparse(model_url or "")
        if (
            parsed.scheme != "http"
            or parsed.hostname not in ("127.0.0.1", "localhost")
            or parsed.username
            or parsed.password
        ):
            raise ValueError(
                "fresh inference requires an explicit local HTTP model endpoint"
            )
    command = [
        python
        or str(
            ROOT
            / ".cache/envs"
            / key
            / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
        ),
        "-m",
        "revenue_lab.worker",
        scenario,
        str(source),
        str(workspace),
    ]
    if model_url:
        command += [model_url]
    env = execution_environment(key, scenario)
    env["PYTHONPATH"] = os.pathsep.join([str(ROOT / "src"), str(source / "src")])
    try:
        result = bounded(command, env=env, timeout=900 if key == "revenue" else 120)
    except subprocess.TimeoutExpired:
        write_json(
            workspace / "failure.json", {"status": "timeout", "scenario": scenario}
        )
        raise RuntimeError("scenario timed out; no successful bundle produced")
    (workspace / "execution.log").write_text(
        result.stdout + result.stderr, encoding="utf-8"
    )
    if result.returncode:
        write_json(
            workspace / "failure.json",
            {"status": "failed", "returncode": result.returncode, "scenario": scenario},
        )
        raise RuntimeError("scenario failed; see " + str(workspace / "execution.log"))
    verified = verify(workspace / "bundle")
    write_json(workspace / "verification.json", verified)
    print(
        json.dumps(
            {"bundle": str(workspace / "bundle"), "verification": verified}, indent=2
        )
    )
    return workspace / "bundle"


def bounded(command, *, env, timeout):
    """Kill the owned process tree on timeout, including engine descendants."""
    options = (
        {
            "creationflags": subprocess.CREATE_NEW_PROCESS_GROUP
            | subprocess.CREATE_NO_WINDOW
        }
        if os.name == "nt"
        else {"start_new_session": True}
    )
    child = subprocess.Popen(
        command,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        **options,
    )
    try:
        stdout, stderr = child.communicate(timeout=timeout)
        return subprocess.CompletedProcess(command, child.returncode, stdout, stderr)
    except subprocess.TimeoutExpired:
        if os.name == "nt":
            subprocess.run(
                ["taskkill", "/PID", str(child.pid), "/T", "/F"],
                capture_output=True,
                timeout=10,
            )
        else:
            os.killpg(child.pid, signal.SIGKILL)
        child.communicate(timeout=10)
        raise


def execution_environment(source, scenario):
    """Pass process essentials and only the selected engine's explicit local authority."""
    essentials = {
        "PATH",
        "SYSTEMROOT",
        "WINDIR",
        "COMSPEC",
        "TEMP",
        "TMP",
        "HOME",
        "USERPROFILE",
        "LOCALAPPDATA",
        "APPDATA",
        "PATHEXT",
        "LANG",
        "LC_ALL",
        "PYTHONUTF8",
        "PYTHONIOENCODING",
    }
    env = {key: value for key, value in os.environ.items() if key.upper() in essentials}
    if source == "control" and os.environ.get("LAB_POSTGRES_ADMIN_DSN"):
        env["LAB_POSTGRES_ADMIN_DSN"] = os.environ["LAB_POSTGRES_ADMIN_DSN"]
    if scenario == "seller-live" and os.environ.get("SELLER_MODEL_KEY"):
        env["SELLER_MODEL_KEY"] = os.environ["SELLER_MODEL_KEY"]
    return env


def main():
    p = argparse.ArgumentParser(
        description="Pinned, bounded Enterprise Revenue Systems Lab"
    )
    sub = p.add_subparsers(dest="command", required=True)
    s = sub.add_parser("prepare")
    s.add_argument("source", choices=LOCK["sources"])
    s.add_argument("--install", action="store_true")
    s = sub.add_parser("recorded")
    s.add_argument("--source", choices=["seller"], default="seller")
    s = sub.add_parser("verify")
    s.add_argument("bundle", type=Path)
    s = sub.add_parser("run")
    s.add_argument("scenario")
    s.add_argument("--python")
    s.add_argument("--model-url")
    sub.add_parser("build")
    s = sub.add_parser("serve")
    s.add_argument("--port", type=int, default=8542)
    s.add_argument("--execute", action="store_true")
    s.add_argument("--model-url")
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
    elif args.command == "serve":
        from .server import serve

        serve(args.port, args.execute, args.model_url)
    else:
        from .site import build

        build()


if __name__ == "__main__":
    main()
