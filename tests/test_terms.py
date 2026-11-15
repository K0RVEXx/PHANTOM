from phantom import TERMS_VERSION, app, ui


def answers(monkeypatch, *replies):
    it = iter(replies)
    monkeypatch.setattr(ui, "choose", lambda *a, **k: next(it))
    monkeypatch.setattr(ui, "clear", lambda: None)
    monkeypatch.setattr(ui, "pause", lambda *a, **k: None)


def test_accept_saves_version(monkeypatch, cfg):
    answers(monkeypatch, "yes")
    assert app.accept_terms(cfg) is True
    assert cfg["terms_accepted"] == TERMS_VERSION


def test_decline_exits(monkeypatch, cfg):
    answers(monkeypatch, "no")
    assert app.accept_terms(cfg) is False
    assert cfg["terms_accepted"] == ""


def test_invalid_answer_asks_again(monkeypatch, cfg):
    answers(monkeypatch, "maybe", ui.REDRAW, "Y")
    assert app.accept_terms(cfg) is True


def test_not_asked_again_after_accepting(monkeypatch, cfg):
    cfg["terms_accepted"] = TERMS_VERSION
    monkeypatch.setattr(ui, "choose", lambda *a, **k: (_ for _ in ()).throw(AssertionError("asked")))
    assert app.accept_terms(cfg) is True


def test_asked_again_when_terms_change(monkeypatch, cfg):
    cfg["terms_accepted"] = "0"
    answers(monkeypatch, "yes")
    assert app.accept_terms(cfg) is True
    assert cfg["terms_accepted"] == TERMS_VERSION
