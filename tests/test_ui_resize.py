from phantom import ui


class FakeStdin:
    def isatty(self):
        return True


class NoKeys:
    def kbhit(self):
        return False


def fake_sizes(monkeypatch, seq):
    """size() returns the values in `seq`, then keeps returning the last one."""
    it = iter(seq)
    state = {"last": seq[0]}

    def size():
        state["last"] = next(it, state["last"])
        return state["last"]
    monkeypatch.setattr(ui, "size", size)


def setup(monkeypatch):
    monkeypatch.setattr(ui.sys, "stdin", FakeStdin())
    monkeypatch.setattr(ui, "msvcrt", NoKeys())
    monkeypatch.setattr(ui, "RESIZE_SETTLE", 0.1)


def test_waits_until_size_is_stable(monkeypatch):
    setup(monkeypatch)
    # leaving full screen: several in-between sizes, then the final one
    fake_sizes(monkeypatch, [(200, 60), (180, 55), (150, 45), (120, 35), (100, 30)])
    assert ui.wait_for_stable_size(0.1) == (100, 30)


def test_resize_during_drawing_is_detected(monkeypatch):
    setup(monkeypatch)
    ui.drawn_size = (200, 60)               # screen was drawn for full screen
    fake_sizes(monkeypatch, [(100, 30)])    # window is already smaller at the prompt
    assert ui.choose() == ui.REDRAW


def test_no_redraw_without_resize(monkeypatch):
    setup(monkeypatch)
    ui.drawn_size = (100, 30)
    fake_sizes(monkeypatch, [(100, 30)])
    keys = list("1\r")

    class Keys:
        def kbhit(self):
            return bool(keys)

        def getwch(self):
            return keys.pop(0)
    monkeypatch.setattr(ui, "msvcrt", Keys())
    assert ui.choose() == "1"
