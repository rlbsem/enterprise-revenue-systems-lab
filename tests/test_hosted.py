import functools
import io
import json
import shutil
import threading
import zipfile
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

import pytest

from revenue_lab.bundle import ROOT
from revenue_lab.smoke import check_site, check_zip


@pytest.mark.parametrize("mutation", ["artifact", "manifest", "extra", "duplicate", "missing"])
def test_downloaded_archive_refuses_content_or_inventory_mutation(mutation):
    expected = ROOT / "web/evidence/seller-application"
    with zipfile.ZipFile(expected / "reproduction.zip") as original:
        contents = {name: original.read(name) for name in original.namelist()}
    if mutation == "artifact":
        contents["application.json"] += b" "
    elif mutation == "manifest":
        contents["bundle.json"] += b" "
    elif mutation == "extra":
        contents["../escape.txt"] = b"unexpected"
    elif mutation == "missing":
        del contents["application.json"]
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        for name, data in contents.items():
            archive.writestr(name, data)
        if mutation == "duplicate":
            with pytest.warns(UserWarning, match="Duplicate name"):
                archive.writestr("application.json", contents["application.json"])
    with pytest.raises(AssertionError):
        check_zip(buffer.getvalue(), expected)


def test_pages_shaped_build_passes_the_same_read_only_smoke_checks(tmp_path, monkeypatch):
    from revenue_lab.site import build

    workspace = tmp_path / "build"
    shutil.copytree(ROOT / "web", workspace / "web")
    monkeypatch.setattr("revenue_lab.site.ROOT", workspace)
    build()
    shutil.copytree(workspace / "dist", tmp_path / "enterprise-revenue-systems-lab")

    class Quiet(SimpleHTTPRequestHandler):
        def log_message(self, *_):
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), functools.partial(Quiet, directory=str(tmp_path)))
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        report = check_site(
            f"http://127.0.0.1:{server.server_port}/enterprise-revenue-systems-lab/",
            workspace / "web", tmp_path / "smoke",
        )
        assert report["status"] == "passed", json.dumps(report["failures"], indent=2)
        assert len([check for check in report["checks"] if check["name"].startswith("case:")]) == 26
        assert report["attempted_writes"] == report["outside_requests"] == []
    finally:
        server.shutdown()
        server.server_close()
        thread.join()


def test_smoke_refuses_other_hosts_before_opening_a_browser(tmp_path):
    with pytest.raises(AssertionError, match="public Lab"):
        check_site("https://unapproved.example/", ROOT / "web", tmp_path)
