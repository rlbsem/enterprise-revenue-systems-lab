"""Bounded scenarios invoke original modules; the Lab only orchestrates and observes."""

import json
import os
import re
import secrets
import socket
import subprocess
import sys
import threading
import time
from contextlib import contextmanager
from pathlib import Path
from uuid import uuid4


def plain(value):
    return json.loads(json.dumps(value, default=str))


@contextmanager
def http_service(app):
    import uvicorn

    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    config = uvicorn.Config(app, log_level="error", access_log=False)
    server = uvicorn.Server(config)
    thread = threading.Thread(
        target=server.run, kwargs={"sockets": [sock]}, daemon=True
    )
    thread.start()
    try:
        for _ in range(200):
            if server.started:
                break
            if not thread.is_alive():
                raise RuntimeError("receiver server exited")
            time.sleep(0.01)
        else:
            raise RuntimeError("receiver server did not start")
        yield "http://127.0.0.1:" + str(sock.getsockname()[1])
    finally:
        server.should_exit = True
        thread.join(timeout=5)
        sock.close()


def control(source, workspace):
    import psycopg
    from psycopg import sql
    from psycopg.conninfo import conninfo_to_dict, make_conninfo

    admin = os.environ.get("LAB_POSTGRES_ADMIN_DSN")
    info = conninfo_to_dict(admin or "")
    if (
        info.get("host") not in ("127.0.0.1", "localhost")
        or info.get("user") != "lab_admin"
    ):
        raise RuntimeError(
            "Configure a dedicated local PostgreSQL cluster with user lab_admin"
        )
    database = "lab_" + uuid4().hex
    with psycopg.connect(admin, autocommit=True) as c:
        c.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(database)))
    dsn = make_conninfo(admin, dbname=database)
    tokens = {
        r: secrets.token_urlsafe(24)
        for r in [
            "crm",
            "consent",
            "privacy",
            "scoring",
            "agent",
            "approver",
            "operator",
        ]
    }
    os.environ.update(
        CONTROL_ADMIN_DSN=dsn,
        APP_DB_PASSWORD="local-app-only",
        REMOTE_DB_PASSWORD="local-remote-only",
        CONTROL_DSN=make_conninfo(dsn, user="control_app", password="local-app-only"),
        REMOTE_DSN=make_conninfo(
            dsn, user="synthetic_remote", password="local-remote-only"
        ),
        API_TOKENS=json.dumps(tokens),
        EXECUTOR_TOKEN=secrets.token_urlsafe(24),
        INJECTOR_TOKEN=secrets.token_urlsafe(24),
        REMOTE_TIMEOUT="0.2",
    )
    try:
        subprocess.run(
            [sys.executable, "-m", "controlplane", "bootstrap-local"],
            check=True,
            timeout=30,
        )
        from fastapi.testclient import TestClient
        import httpx
        from controlplane import api, db, mock, worker

        stages, timeline = [], []

        def rows(table, remote=False):
            with db.connect(os.environ["REMOTE_DSN"] if remote else dsn) as c:
                return plain(
                    c.execute("SELECT * FROM " + table + " ORDER BY 1").fetchall()
                )

        def observe(pid, label):
            with db.connect(dsn) as c:
                state = plain(
                    c.execute("SELECT * FROM cp.jobs WHERE id=%s", (pid,)).fetchone()
                )
            effects = [r for r in rows("remote.effects", True) if r["key"] == pid]
            stages.append({"label": label, "job": state, "effects": effects})
            timeline.append(
                {
                    "action": label,
                    "detail": "Original worker state and separate receiver ledger",
                    "body": stages[-1],
                }
            )
            return state

        def due(pid):
            with db.connect(dsn) as c:
                c.execute(
                    "UPDATE cp.jobs SET available_at=clock_timestamp()-interval '1 second',lease_until=clock_timestamp()-interval '1 second' WHERE id=%s",
                    (pid,),
                )

        with http_service(mock.app) as downstream, TestClient(api.app) as client:
            os.environ["DOWNSTREAM_URL"] = downstream

            def post(route, body, role):
                result = client.post(
                    route,
                    json=body,
                    headers={"Authorization": "Bearer " + tokens[role]},
                )
                result.raise_for_status()
                return result.json()

            for index, failure in enumerate(
                ["lost_acknowledgment", "process_interruption"]
            ):
                cid = post(
                    "/events",
                    {
                        "event_id": f"lab-{index}-1",
                        "subject": f"lab-{index}",
                        "sequence": 1,
                        "attributes": {
                            "email": f"lab-{index}@example.test",
                            "lifecycle": "Opportunity",
                            "owner": "lab-owner",
                        },
                    },
                    "crm",
                )["customer_id"]
                command = {
                    "request_id": str(uuid4()),
                    "customer_id": cid,
                    "expected_revision": 1,
                    "action": "sync_profile",
                    "rationale": "Lab controlled recovery investigation",
                }
                proposal = post("/proposals", command, "agent")
                pid = proposal["id"]
                if post("/proposals", command, "agent")["id"] != pid:
                    raise RuntimeError("duplicate proposal changed identity")
                response = httpx.post(
                    downstream + "/failure-plans",
                    json={"key": pid, "modes": ["timeout_after"]},
                    headers={"Authorization": "Bearer " + os.environ["INJECTOR_TOKEN"]},
                    trust_env=False,
                )
                response.raise_for_status()
                observe(pid, failure + ": durable proposal admitted")
                if failure == "lost_acknowledgment":
                    worker.once()
                    first = observe(
                        pid, failure + ": receiver committed, worker timed out"
                    )
                    if first["status"] != "retry" or not first["uncertain"]:
                        raise RuntimeError(
                            "lost acknowledgment did not exercise uncertainty"
                        )
                else:
                    child_env = {
                        k: v
                        for k, v in os.environ.items()
                        if k
                        not in (
                            "LAB_POSTGRES_ADMIN_DSN",
                            "CONTROL_ADMIN_DSN",
                            "REMOTE_DSN",
                            "API_TOKENS",
                            "INJECTOR_TOKEN",
                            "APP_DB_PASSWORD",
                            "REMOTE_DB_PASSWORD",
                        )
                    }
                    child_env["REMOTE_TIMEOUT"] = "5"
                    child = subprocess.Popen(
                        [sys.executable, "-m", "controlplane", "worker", "--once"],
                        env=child_env,
                        creationflags=subprocess.CREATE_NO_WINDOW
                        if os.name == "nt"
                        else 0,
                    )
                    try:
                        for _ in range(200):
                            if any(
                                r["key"] == pid for r in rows("remote.effects", True)
                            ):
                                break
                            if child.poll() is not None:
                                raise RuntimeError(
                                    "worker exited before observed remote commit"
                                )
                            time.sleep(0.01)
                        else:
                            raise RuntimeError("worker never reached remote commit")
                        child.kill()
                        code = child.wait(timeout=5)
                        timeline.append(
                            {
                                "action": "Worker process killed after receiver commit",
                                "body": {"exit_code": code},
                            }
                        )
                    finally:
                        if child.poll() is None:
                            child.kill()
                            child.wait(timeout=5)
                    first = observe(pid, failure + ": worker interrupted while leased")
                    if first["status"] != "leased":
                        raise RuntimeError(
                            "interrupted worker did not leave leased job"
                        )
                due(pid)
                worker.once()
                final = observe(
                    pid, failure + ": original worker reconciled existing receipt"
                )
                if (
                    final["status"] != "succeeded"
                    or final["reason"] != "reconciled_committed_effect"
                ):
                    raise RuntimeError("original engine recovery failed")
            replay_claimed = worker.once()
            ledger = {
                t: rows("cp." + t) for t in ["jobs", "proposals", "audit", "customers"]
            }
            receiver = rows("remote.effects", True)
        summary = {
            "attempts": sum(j["attempts"] for j in ledger["jobs"]),
            "unique_effects": len(receiver),
            "duplicate_effects": len(receiver) - len({r["key"] for r in receiver}),
            "lost_acknowledgments": 1,
            "interrupted_workers": 1,
            "replay_claimed": replay_claimed,
        }
        return {
            "ledger.json": ledger,
            "receiver.json": receiver,
            "stages.json": stages,
            "timeline.json": timeline,
            "observation.json": {
                "summary": summary,
                "scope": "Fresh original PostgreSQL engine; real worker killed; synthetic HTTP receiver",
            },
        }, "fresh_engine"
    finally:
        # Drop only the unique database created above on the dedicated lab cluster.
        if not re.fullmatch(r"lab_[a-f0-9]{32}", database):
            raise RuntimeError("unexpected owned database name")
        with psycopg.connect(admin, autocommit=True) as c:
            c.execute(
                sql.SQL("DROP DATABASE {} WITH (FORCE)").format(
                    sql.Identifier(database)
                )
            )


def execute(scenario, source, workspace):
    if scenario == "control-recovery":
        return control(source, workspace)
    if scenario == "revenue-correction":
        from .revenue_adapter import execute_revenue

        return execute_revenue(source, workspace)
    raise ValueError("unknown approved execution scenario")
