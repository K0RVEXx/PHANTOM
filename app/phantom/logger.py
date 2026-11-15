"""Activity log. Never receives credentials (callers use Proxy.label())."""
import datetime
import os
import threading

from . import BASE_DIR

LOG_DIR = os.path.join(BASE_DIR, "logs")
LOG_PATH = os.path.join(LOG_DIR, "phantom.log")

_lock = threading.Lock()


def _write(level, msg):
    ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"{ts} [{level}] {msg}\n"
    with _lock:
        try:
            os.makedirs(LOG_DIR, exist_ok=True)
            with open(LOG_PATH, "a", encoding="utf-8") as f:
                f.write(line)
        except OSError:
            pass


def info(msg):
    _write("INFO", msg)


def warn(msg):
    _write("WARN", msg)


def error(msg):
    _write("ERROR", msg)


def tail(n=40):
    try:
        with open(LOG_PATH, encoding="utf-8") as f:
            return f.readlines()[-n:]
    except OSError:
        return []


def clear():
    with _lock:
        try:
            open(LOG_PATH, "w").close()
        except OSError:
            pass
