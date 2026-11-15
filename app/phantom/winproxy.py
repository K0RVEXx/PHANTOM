"""Windows system proxy (per-user, HKCU - no admin rights needed).

Only used when the user explicitly enables it from the menu. The original
values are backed up and restored on disable, on exit, and on the next
start if PHANTOM was closed unexpectedly.
"""
import os

SUPPORTED = os.name == "nt"
KEY = r"Software\Microsoft\Windows\CurrentVersion\Internet Settings"
NAMES = ("ProxyEnable", "ProxyServer", "ProxyOverride")

if SUPPORTED:
    import ctypes
    import winreg


def _refresh():
    # INTERNET_OPTION_SETTINGS_CHANGED (39) + INTERNET_OPTION_REFRESH (37)
    inet = ctypes.windll.wininet
    inet.InternetSetOptionW(None, 39, None, 0)
    inet.InternetSetOptionW(None, 37, None, 0)


def snapshot():
    """Current values as {name: [value, type] or None} (JSON serializable)."""
    out = {}
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, KEY) as k:
        for name in NAMES:
            try:
                val, typ = winreg.QueryValueEx(k, name)
                out[name] = [val, typ]
            except FileNotFoundError:
                out[name] = None
    return out


def is_pointing_to(port):
    s = snapshot()
    return bool(s["ProxyEnable"] and s["ProxyEnable"][0] == 1 and s["ProxyServer"]
                and s["ProxyServer"][0] == f"127.0.0.1:{port}")


def enable(port):
    """Point Windows at 127.0.0.1:port. Returns the backup of the old values."""
    backup = snapshot()
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, KEY, 0, winreg.KEY_SET_VALUE) as k:
        winreg.SetValueEx(k, "ProxyServer", 0, winreg.REG_SZ, f"127.0.0.1:{port}")
        winreg.SetValueEx(k, "ProxyOverride", 0, winreg.REG_SZ, "<local>;localhost;127.0.0.1")
        winreg.SetValueEx(k, "ProxyEnable", 0, winreg.REG_DWORD, 1)
    _refresh()
    return backup


def restore(backup):
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, KEY, 0, winreg.KEY_SET_VALUE) as k:
        for name in NAMES:
            item = backup.get(name)
            if item is None:
                try:
                    winreg.DeleteValue(k, name)
                except FileNotFoundError:
                    pass
            else:
                winreg.SetValueEx(k, name, 0, item[1], item[0])
    _refresh()
