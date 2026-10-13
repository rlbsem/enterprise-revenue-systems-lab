"""Loopback-only preview and opt-in bounded execution; never deployed with the static site."""
import functools
import hashlib
import json
import os
import secrets
import subprocess
import sys
import threading
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from uuid import uuid4
from .bundle import ROOT, verify

ALLOWED = {"seller-stale", "seller-suppressed", "seller-delivery", "control-recovery", "revenue-correction"}


def handler(execute=False, model_url=None):
    token, runs, lock = secrets.token_urlsafe(32), {}, threading.Lock()

    class Handler(SimpleHTTPRequestHandler):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, directory=str(ROOT / "web"), **kwargs)

        def log_message(self, *_):
            pass

        def permitted_host(self):
            return self.headers.get("Host") in (f"127.0.0.1:{self.server.server_port}", f"localhost:{self.server.server_port}")

        def send_json(self, status, value):
            data = json.dumps(value).encode()
            self.send_response(status); self.send_header("Content-Type", "application/json")
            self.send_header("Cache-Control", "no-store"); self.send_header("Content-Length", str(len(data)))
            self.end_headers(); self.wfile.write(data)

        def end_headers(self):
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Content-Security-Policy", "default-src 'self'; script-src 'self'; style-src 'self'; object-src 'none'; frame-ancestors 'none'; base-uri 'none'")
            super().end_headers()

        def do_GET(self):
            if not self.permitted_host():
                return self.send_json(403, {"error": "unexpected_host"})
            if self.path == "/api/config":
                return self.send_json(200, {"execution_enabled": execute, "token": token if execute else None,
                    "allowed": sorted(ALLOWED), "fresh_inference": "configured" if model_url else "unavailable: no local model endpoint configured"})
            if self.path.startswith("/api/runs/"):
                key = self.path.removeprefix("/api/runs/")
                return self.send_json(200 if key in runs else 404, runs.get(key, {"error": "unknown_run"}))
            if self.path.startswith("/api/"):
                return self.send_json(404, {"error": "unknown_endpoint"})
            # Static files are limited to the web directory. Hidden paths are not served.
            if any(p.startswith(".") for p in self.path.split("/") if p):
                return self.send_json(403, {"error": "hidden_path"})
            return super().do_GET()

        def do_POST(self):
            own_origins = {f"http://127.0.0.1:{self.server.server_port}", f"http://localhost:{self.server.server_port}"}
            if not execute or not self.permitted_host() or self.headers.get("Origin") not in own_origins or not secrets.compare_digest(self.headers.get("X-Lab-Token", ""), token):
                return self.send_json(403, {"error": "local_execution_authority_required"})
            if self.path != "/api/runs":
                return self.send_json(404, {"error": "unknown_endpoint"})
            try:
                length = int(self.headers.get("Content-Length", 0))
                if not 0 < length <= 1024:
                    raise ValueError()
                body = json.loads(self.rfile.read(length))
                if set(body) != {"scenario"} or body["scenario"] not in ALLOWED:
                    raise ValueError()
            except (ValueError, TypeError):
                return self.send_json(422, {"error": "unapproved_scenario_or_contract"})
            if not lock.acquire(blocking=False):
                return self.send_json(409, {"error": "one_execution_at_a_time"})
            if len(runs) >= 20:
                lock.release()
                return self.send_json(429, {"error": "session_execution_budget_exhausted"})
            key = uuid4().hex
            scenario = body["scenario"]
            runs[key] = {"state": "running", "scenario": scenario}

            def work():
                try:
                    env = dict(os.environ, PYTHONPATH=str(ROOT / "src"))
                    command = [sys.executable, "-m", "revenue_lab.cli", "run", scenario]
                    result = subprocess.run(command, env=env, capture_output=True, text=True, timeout=930)
                    if result.returncode:
                        runs[key] = {"state": "failed", "scenario": scenario,
                                     "error": "Original-engine execution failed. Inspect the local .cache/runs logs; no successful evidence was fabricated."}
                        return
                    report = json.loads(result.stdout)
                    from pathlib import Path
                    path = Path(report["bundle"])
                    if not path.resolve().is_relative_to((ROOT / ".cache/runs").resolve()):
                        raise ValueError("unexpected result path")
                    verification = verify(path)
                    manifest_text = (path / "bundle.json").read_text(encoding="utf-8")
                    manifest = json.loads(manifest_text)
                    runs[key] = {"state": "succeeded", "scenario": scenario, "verification": verification,
                                 "manifest_text": manifest_text, "manifest": manifest,
                                 "manifest_sha256": hashlib.sha256(manifest_text.encode()).hexdigest(),
                                 "artifacts": {a["path"]: (path / a["path"]).read_text(encoding="utf-8") for a in manifest["artifacts"]}}
                except (Exception, subprocess.TimeoutExpired):
                    runs[key] = {"state": "failed", "scenario": scenario, "error": "Bounded execution failed or timed out; inspect local logs."}
                finally:
                    lock.release()
            threading.Thread(target=work, daemon=True).start()
            self.send_json(202, {"id": key, **runs[key]})

    return Handler


def serve(port=8542, execute=False, model_url=None):
    server = ThreadingHTTPServer(("127.0.0.1", port), handler(execute, model_url))
    print(f"Lab: http://127.0.0.1:{server.server_port}/ · local execution {'enabled' if execute else 'disabled'}", flush=True)
    try:
        server.serve_forever()
    finally:
        server.server_close()
