import json
import threading
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer

import pytest
from revenue_lab.server import handler


@pytest.fixture
def local():
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler(execute=True))
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    url = f"http://127.0.0.1:{server.server_port}"
    config = json.load(urllib.request.urlopen(url + "/api/config"))
    yield url, config
    server.shutdown()
    server.server_close()
    thread.join()


@pytest.mark.parametrize("change", ["origin", "token", "scenario", "extra", "host"])
def test_local_execution_rejects_unapproved_requests(local, change):
    url, config = local
    headers = {
        "Content-Type": "application/json",
        "Origin": url,
        "X-Lab-Token": config["token"],
    }
    body = {"scenario": "seller-stale"}
    if change == "origin":
        headers["Origin"] = "https://hostile.example"
    if change == "token":
        headers["X-Lab-Token"] = "invalid"
    if change == "scenario":
        body["scenario"] = "arbitrary-command"
    if change == "extra":
        body["python"] = "attacker-interpreter"
    if change == "host":
        headers["Host"] = "hostile.example"
    request = urllib.request.Request(
        url + "/api/runs", data=json.dumps(body).encode(), headers=headers
    )
    with pytest.raises(urllib.error.HTTPError) as error:
        urllib.request.urlopen(request)
    assert error.value.code in (403, 422)


def test_fresh_inference_unavailability_is_explicit(local):
    _, config = local
    assert config["fresh_inference"].startswith("unavailable")


def test_static_mode_disables_execution():
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler())
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        value = json.load(
            urllib.request.urlopen(f"http://127.0.0.1:{server.server_port}/api/config")
        )
        assert value["execution_enabled"] is False and value["token"] is None
    finally:
        server.shutdown()
        server.server_close()
        thread.join()
