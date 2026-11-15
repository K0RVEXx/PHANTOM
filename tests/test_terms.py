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


def test_decline_is_remembered(monkeypatch, cfg):
    answers(monkeypatch, "no")
    app.accept_terms(cfg)
    assert cfg["terms_declined"] is True


def test_returning_user_changed_mind(monkeypatch, cfg):
    cfg["terms_declined"] = True
    answers(monkeypatch, "1", "yes")
    assert app.accept_terms(cfg) is True
    assert cfg["terms_declined"] is False
    assert cfg["terms_accepted"] == TERMS_VERSION


def test_returning_user_only_to_get_in_sees_terms_again(monkeypatch, cfg):
    cfg["terms_declined"] = True
    answers(monkeypatch, "2", "no")
    assert app.accept_terms(cfg) is False
    assert cfg["terms_declined"] is True


def test_returning_user_can_exit(monkeypatch, cfg):
    cfg["terms_declined"] = True
    answers(monkeypatch, "0")
    assert app.accept_terms(cfg) is False


def test_welcome_back_not_shown_to_new_users(monkeypatch, cfg):
    shown = []
    monkeypatch.setattr(app, "welcome_back", lambda: shown.append(1) or True)
    answers(monkeypatch, "yes")
    app.accept_terms(cfg)
    assert shown == []
