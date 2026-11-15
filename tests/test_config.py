import json

from phantom import config


def test_defaults_and_autosave():
    c = config.Config()
    assert c["listen_port"] == 8888
    c["interval"] = 42
    with open(config.CONFIG_PATH, encoding="utf-8") as f:
        assert json.load(f)["interval"] == 42
    assert config.Config()["interval"] == 42


def test_bad_values_are_ignored():
    with open(config.CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump({"interval": "oops", "unknown": 1, "timeout": 5}, f)
    c = config.Config()
    assert c["interval"] == config.DEFAULTS["interval"]
    assert c["timeout"] == 5
    assert "unknown" not in c


def test_corrupt_file_falls_back_to_defaults():
    with open(config.CONFIG_PATH, "w", encoding="utf-8") as f:
        f.write("{not json")
    assert config.Config()["mode"] == config.DEFAULTS["mode"]
