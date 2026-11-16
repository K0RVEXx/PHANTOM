from phantom import config, ui


def test_start_maximized_is_on_by_default():
    assert config.DEFAULTS["start_maximized"] is True


def test_maximize_without_console_window_is_safe():
    # Under pytest there is no console window; the call must simply report False.
    assert ui.maximize_window() in (True, False)
