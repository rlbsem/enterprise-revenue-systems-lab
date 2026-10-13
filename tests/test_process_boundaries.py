import os
import subprocess
import sys
import time
from pathlib import Path

import pytest
from revenue_lab.cli import bounded, execution_environment


def test_timeout_terminates_engine_descendants(tmp_path):
    marker, pidfile = tmp_path / "late-effect", tmp_path / "pid"
    grandchild = f"import time;from pathlib import Path;time.sleep(2);Path({str(marker)!r}).write_text('unbounded effect')"
    code = (
        "import subprocess,sys,time;from pathlib import Path;"
        f"p=subprocess.Popen([sys.executable,'-c',{grandchild!r}],"
        "creationflags=subprocess.CREATE_NO_WINDOW if sys.platform=='win32' else 0);"
        f"Path({str(pidfile)!r}).write_text(str(p.pid));time.sleep(20)"
    )
    with pytest.raises(subprocess.TimeoutExpired):
        bounded([sys.executable, "-c", code], env=dict(os.environ), timeout=1)
    assert int(pidfile.read_text()) > 0
    time.sleep(1.5)
    assert not marker.exists(), "timed-out descendant still produced an effect"


def test_scenario_receives_only_its_explicit_local_authority(monkeypatch):
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "must-not-inherit")
    monkeypatch.setenv("OPENAI_API_KEY", "must-not-inherit")
    monkeypatch.setenv("API_TOKENS", "must-not-inherit")
    monkeypatch.setenv("LAB_POSTGRES_ADMIN_DSN", "local-db-authority")
    monkeypatch.setenv("SELLER_MODEL_KEY", "local-model-authority")
    revenue = execution_environment("revenue", "revenue-correction")
    assert not any(
        k in revenue
        for k in [
            "AWS_SECRET_ACCESS_KEY",
            "OPENAI_API_KEY",
            "API_TOKENS",
            "LAB_POSTGRES_ADMIN_DSN",
            "SELLER_MODEL_KEY",
        ]
    )
    control = execution_environment("control", "control-recovery")
    assert (
        control["LAB_POSTGRES_ADMIN_DSN"] == "local-db-authority"
        and "SELLER_MODEL_KEY" not in control
    )
    replay = execution_environment("seller", "seller-stale")
    assert "SELLER_MODEL_KEY" not in replay
    assert (
        execution_environment("seller", "seller-live")["SELLER_MODEL_KEY"]
        == "local-model-authority"
    )
