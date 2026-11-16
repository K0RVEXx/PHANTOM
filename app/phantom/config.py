"""Persistent configuration (auto-saved to phantom_config.json)."""
import json
import os

from . import BASE_DIR

CONFIG_PATH = os.path.join(BASE_DIR, "phantom_config.json")

DEFAULTS = {
    "start_maximized": True,  # open the console window maximized
    "interval": 60,          # seconds between automatic rotations, 0 = manual only
    "timeout": 8,            # connection timeout in seconds
    "auto_failover": True,   # switch proxy automatically after a failed connection
    "mode": "fastest",       # fastest | random | sequential
    "fast_pool": 3,          # fastest mode: rotate among the N fastest proxies
    "health_interval": 180,  # s - background re-check of latency, 0 = off
    "sticky": True,          # keep each website on the same proxy for a while
    "sticky_minutes": 10,    # how long a website stays on its proxy
    "avoid_repeat": True,    # avoid recently used proxies in random mode
    "max_retries": 5,        # proxies tried per client connection
    "max_latency": 2500,     # ms - only proxies at most this slow are rotated (if any)
    "hedge_ms": 1500,        # ms - start a parallel backup attempt if no answer by then
    "listen_port": 8888,     # local proxy port (127.0.0.1 only)
    "last_list": "",
    "default_protocol": "http",
    "sysproxy_backup": {},
    "terms_accepted": "",    # version of the terms of use the user accepted
    "terms_declined": False, # user declined last time -> asked why they came back
    "shortcut_asked": False, # desktop shortcut offer was shown once
    "integrity_ack": "",     # modified-copy notice acknowledged for this exact state   # original Windows proxy values while PHANTOM controls them
}


class Config(dict):
    def __init__(self):
        super().__init__(DEFAULTS)
        try:
            with open(CONFIG_PATH, encoding="utf-8") as f:
                data = json.load(f)
            for k, v in data.items():
                if k in DEFAULTS and isinstance(v, type(DEFAULTS[k])):
                    super().__setitem__(k, v)
        except (OSError, ValueError):
            pass
        self.save()

    def __setitem__(self, key, value):
        super().__setitem__(key, value)
        self.save()

    def save(self):
        try:
            with open(CONFIG_PATH, "w", encoding="utf-8") as f:
                json.dump(dict(self), f, indent=2)
        except OSError:
            pass
