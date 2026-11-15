from phantom import app, ui, winshell


def setup(monkeypatch, exists=False, answer="y"):
    calls = []
    monkeypatch.setattr(winshell, "SUPPORTED", True)
    monkeypatch.setattr(winshell, "shortcut_exists", lambda: exists)
    monkeypatch.setattr(winshell, "create_shortcut", lambda: calls.append("create"))
    monkeypatch.setattr(ui, "clear", lambda: None)
    monkeypatch.setattr(ui, "ask", lambda *a, **k: answer)
    monkeypatch.setattr(app.time, "sleep", lambda s: None)
    return calls


def test_offer_creates_shortcut_and_is_asked_once(monkeypatch, cfg):
    calls = setup(monkeypatch, answer="y")
    app.offer_shortcut(cfg)
    assert calls == ["create"] and cfg["shortcut_asked"] is True
    app.offer_shortcut(cfg)
    assert calls == ["create"]


def test_offer_declined(monkeypatch, cfg):
    calls = setup(monkeypatch, answer="n")
    app.offer_shortcut(cfg)
    assert calls == [] and cfg["shortcut_asked"] is True


def test_not_offered_when_shortcut_exists(monkeypatch, cfg):
    calls = setup(monkeypatch, exists=True)
    app.offer_shortcut(cfg)
    assert calls == [] and cfg["shortcut_asked"] is False


def test_icon_file_is_valid():
    import struct
    data = open(winshell.ICON_PATH, "rb").read()
    reserved, kind, count = struct.unpack("<HHH", data[:6])
    assert (reserved, kind) == (0, 1) and count >= 4      # ICO header with several sizes
    widths = {data[6 + 16 * i] or 256 for i in range(count)}
    assert {16, 32, 256} <= widths
