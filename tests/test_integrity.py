import os
import shutil

import pytest

from phantom import app, integrity, ui


def test_manifest_is_up_to_date():
    """If this fails, run:  python tools/update_integrity.py"""
    assert integrity.check()["status"] == "ok"


@pytest.fixture
def copy(tmp_path, monkeypatch):
    """A private copy of the app folder, so files can be changed safely."""
    dst = tmp_path / "app"
    shutil.copytree(integrity.BASE_DIR, dst, ignore=shutil.ignore_patterns("__pycache__", "logs", "*.json", "assets"))
    shutil.copy(integrity.MANIFEST, dst / "integrity.json")
    monkeypatch.setattr(integrity, "BASE_DIR", str(dst))
    monkeypatch.setattr(integrity, "MANIFEST", str(dst / "integrity.json"))
    return dst


def test_unchanged_copy_is_ok(copy):
    assert integrity.check()["status"] == "ok"


def test_line_endings_do_not_count_as_change(copy):
    f = copy / integrity.PACKAGE / "ui.py"
    f.write_bytes(f.read_bytes().replace(b"\r\n", b"\n").replace(b"\n", b"\r\n"))
    assert integrity.check()["status"] == "ok"


def test_changed_added_and_missing_files(copy):
    (copy / integrity.PACKAGE / "ui.py").write_text("# changed\n", encoding="utf-8")
    (copy / integrity.PACKAGE / "extra.py").write_text("x = 1\n", encoding="utf-8")
    os.remove(copy / integrity.PACKAGE / "logger.py")
    r = integrity.check()
    assert r["status"] == "modified"
    assert r["changed"] == [f"{integrity.PACKAGE}/ui.py"]
    assert r["added"] == [f"{integrity.PACKAGE}/extra.py"]
    assert r["missing"] == [f"{integrity.PACKAGE}/logger.py"]


def test_missing_manifest_is_silent(copy):
    os.remove(copy / "integrity.json")
    assert integrity.check()["status"] == "no-manifest"


def test_notice_shown_once_after_acknowledge(copy, cfg, monkeypatch):
    (copy / integrity.PACKAGE / "ui.py").write_text("# changed\n", encoding="utf-8")
    shown = []
    monkeypatch.setattr(ui, "clear", lambda: shown.append(1))
    monkeypatch.setattr(ui, "choose", lambda *a, **k: "1")
    app.integrity_notice(cfg)
    assert shown and cfg["integrity_ack"]
    shown.clear()
    app.integrity_notice(cfg)
    assert not shown                          # same changes -> not shown again
    (copy / integrity.PACKAGE / "ui.py").write_text("# changed again\n", encoding="utf-8")
    app.integrity_notice(cfg)
    assert shown                              # new changes -> shown again


def test_no_notice_for_original_copy(copy, cfg, monkeypatch):
    monkeypatch.setattr(ui, "clear", lambda: pytest.fail("notice shown for an unmodified copy"))
    app.integrity_notice(cfg)
