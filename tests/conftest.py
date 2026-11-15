import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(__file__)), "app"))

from phantom import config, logger  # noqa: E402
from phantom.proxy import Proxy  # noqa: E402


@pytest.fixture(autouse=True)
def isolated_files(tmp_path, monkeypatch):
    """Never touch the user's real config or log files."""
    monkeypatch.setattr(config, "CONFIG_PATH", str(tmp_path / "config.json"))
    monkeypatch.setattr(logger, "LOG_DIR", str(tmp_path / "logs"))
    monkeypatch.setattr(logger, "LOG_PATH", str(tmp_path / "logs" / "phantom.log"))


@pytest.fixture
def cfg():
    return dict(config.DEFAULTS)


def make_proxy(host, latency=None, status="ONLINE", port=8080):
    p = Proxy("http", host, port)
    p.status = status
    p.latency = latency
    return p
