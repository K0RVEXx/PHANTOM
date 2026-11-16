"""PHANTOM menus."""
import atexit
import datetime
import os
import sys
import time

from . import AUTHOR, AUTHOR_URL, PROXY_DIR, NAME, SCHOOL, SLOGAN, TERMS_VERSION, VERSION, logger, ui, winproxy, winshell
from .config import Config
from .engine import Engine
from .proxy import PROTOCOLS, check, check_many, load_file
from .ui import B, C, G, GR, R, W, X, Y

print = ui.print  # noqa: A001 - every line is centered


def fmt_time(ts):
    return datetime.datetime.fromtimestamp(ts).strftime("%H:%M:%S") if ts else "-"


class App:
    def __init__(self):
        self.cfg = Config()
        self.pool = []
        self.engine = Engine(self.cfg, self.pool)
        self.page = 0
        # Leftover from an unexpected close: give the user their settings back.
        if self.cfg["sysproxy_backup"]:
            self.sysproxy_off("restored after unexpected shutdown")

    # ------------------------------------------------------------ helpers
    def counts(self):
        on = sum(p.status == "ONLINE" for p in self.pool)
        off = sum(p.status == "OFFLINE" for p in self.pool)
        return on, off, len(self.pool) - on - off

    @property
    def sysproxy_on(self):
        return bool(self.cfg["sysproxy_backup"])

    def status_word(self):
        if self.engine.running:
            return "ROTATING" if self.engine.current else "ERROR"
        return "READY"

    def run_checks(self, proxies):
        print()
        ui.info(f"Checking {len(proxies)} proxies (HTTPS tunnel test)...")
        start = time.time()
        check_many(proxies, self.cfg["timeout"],
                   lambda i, n, p: ui.progress(i, n, p.status))
        on = sum(p.status == "ONLINE" for p in proxies)
        best = sorted((p for p in proxies if p.status == "ONLINE"), key=lambda p: p.latency)[:5]
        print()
        ui.ok(f"Finished in {time.time() - start:.1f}s - {on}/{len(proxies)} online")
        for p in best:
            print(f"        {ui.tag('ONLINE', 10)} {W}{p.label():<30}{X} "
                  f"{C}{p.latency:>5}ms{X}  {GR}{p.geo[:18]}{X}")
        if on > 5:
            print(f"        {GR}... full list in menu [3] Proxy Pool{X}")
        logger.info(f"Proxy test: {on}/{len(proxies)} online, {len(proxies) - on} offline")

    # ------------------------------------------------------------ system proxy
    def sysproxy_enable(self):
        if not winproxy.SUPPORTED:
            ui.err("Only available on Windows.")
            return
        if not self.engine.running:
            ui.err("Start rotation first - otherwise Windows would have no internet.")
            return
        print()
        ui.warn("ALL apps using Windows proxy settings (Chrome, Edge...)")
        ui.warn("will go through untrusted free proxies. Do not log in anywhere.")
        if not ui.ask("Enable Windows system proxy? (y/n)", "n").lower().startswith("y"):
            ui.info("Cancelled - Windows settings unchanged.")
            return
        try:
            self.cfg["sysproxy_backup"] = winproxy.enable(self.cfg["listen_port"])
        except OSError as ex:
            ui.err(f"Could not change Windows proxy: {ex}")
            return
        logger.info(f"Windows system proxy ENABLED -> 127.0.0.1:{self.cfg['listen_port']}")
        ui.ok("Windows now uses PHANTOM. It is restored when you stop or exit.")

    def sysproxy_off(self, reason="disabled by user"):
        if not self.sysproxy_on or not winproxy.SUPPORTED:
            return
        try:
            winproxy.restore(self.cfg["sysproxy_backup"])
            self.cfg["sysproxy_backup"] = {}
            logger.info(f"Windows system proxy restored ({reason})")
        except OSError as ex:
            logger.error(f"Could not restore Windows proxy: {ex}")

    # ------------------------------------------------------------ main menu
    def main_menu(self):
        while True:
            ui.banner()
            on, _, _ = self.counts()
            ui.box_top()
            ui.box_row(f"{C}{B}{NAME} v{VERSION[:3]}{X}", center_text=True)
            ui.box_mid()
            items = ["Start Proxy Rotation", "Load Proxy List", "Proxy Pool",
                     "Connection Status", "Test Current Proxy", "Rotation Settings",
                     "Activity Logs", "About PHANTOM"]
            if self.engine.running:
                items[0] = "Rotation Control"
            for i, name in enumerate(items, 1):
                ui.box_row(f"  {C}[{i}]{X} {G}{name}{X}")
            ui.box_row(f"  {C}[0]{X} {G}Exit{X}")
            ui.box_mid()
            ui.box_row(f"  {GR}STATUS:{X} {ui.tag(self.status_word())}")
            ui.box_row(f"  {GR}PROXY POOL:{X} {G}{len(self.pool)} LOADED{X} {GR}({on} online){X}")
            rot = f"{Y}ENABLED{X}" if self.engine.running else f"{GR}DISABLED{X}"
            ui.box_row(f"  {GR}ROTATION:{X} {rot}")
            ui.box_row(f"  {GR}WINDOWS PROXY:{X} {ui.tag('ON' if self.sysproxy_on else 'OFF')}")
            ui.box_bot()
            choice = ui.choose()
            actions = {"1": self.rotation_menu, "2": self.load_menu, "3": self.pool_menu,
                       "4": self.status_menu, "5": self.test_current, "6": self.settings_menu,
                       "7": self.logs_menu, "8": self.about}
            if choice == "0":
                return
            if choice in actions:
                actions[choice]()

    # ------------------------------------------------------------ [1]
    def rotation_menu(self):
        while True:
            ui.title("Proxy Rotation")
            e = self.engine
            ui.kv("Engine", ui.tag("ROTATING" if e.running else "STOPPED"))
            ui.kv("Local endpoint", f"127.0.0.1:{self.cfg['listen_port']}")
            ui.kv("Active proxy", e.current.label() if e.current else "-")
            ui.kv("Mode", f"{self.cfg['mode']} / every {self.cfg['interval']}s"
                  if self.cfg["interval"] else f"{self.cfg['mode']} / manual only")
            ui.kv("Windows system proxy", ui.tag("ON" if self.sysproxy_on else "OFF"))
            ui.sep()
            ui.opt(1, "Stop rotation" if e.running else "Start rotation")
            ui.opt(2, "Rotate now (manual switch)")
            ui.opt(3, "Live monitor")
            ui.opt(4, "Disable Windows system proxy" if self.sysproxy_on
                   else "Enable Windows system proxy", f" {GR}(optional){X}")
            ui.opt(0, "Back")
            print()
            c = ui.choose()
            if c in ("0", ""):
                return
            if c == "1":
                if e.running:
                    self.sysproxy_off("rotation stopped")
                    e.stop()
                    ui.ok("Rotation stopped. Local endpoint closed.")
                    time.sleep(1)
                else:
                    self.start_engine()
            elif c == "2":
                if not e.running:
                    ui.err("Rotation is not running.")
                    ui.pause()
                    continue
                p = e.rotate("manual")
                ui.ok(f"Switched to {p.label()}") if p else ui.err("No usable proxy in pool.")
                time.sleep(1)
            elif c == "3":
                self.live_monitor()
            elif c == "4":
                if self.sysproxy_on:
                    self.sysproxy_off()
                    ui.ok("Windows proxy settings restored to original.")
                else:
                    self.sysproxy_enable()
                ui.pause()

    def start_engine(self):
        if not self.pool:
            ui.err("Proxy pool is empty. Load a proxy list first (menu 2).")
            ui.pause()
            return
        if not self.engine._candidates():
            ui.err("No usable proxies (all OFFLINE). Load or re-check a list.")
            ui.pause()
            return
        try:
            self.engine.start()
        except OSError as ex:
            ui.err(f"Cannot open 127.0.0.1:{self.cfg['listen_port']} - {ex.strerror or ex}")
            ui.info("Port is busy. Change it in Rotation Settings.")
            ui.pause()
            return
        print()
        ui.ok(f"Rotation started - local proxy at 127.0.0.1:{self.cfg['listen_port']}")
        ui.info("Use option [4] to route Windows through it, or set it per app.")
        ui.pause()

    def live_monitor(self):
        e = self.engine
        try:
            while True:
                ui.title("Live Monitor")
                cur = e.current
                ui.kv("Engine", ui.tag("ROTATING" if e.running else "STOPPED"))
                ui.kv("Active proxy", cur.label() if cur else "-")
                ui.kv("Proxy status", ui.tag(cur.status) if cur else "-")
                ui.kv("Location", cur.geo if cur else "-")
                nr = e.next_rotation
                ui.kv("Next rotation", f"in {max(0, int(nr - time.time()))}s" if nr else "manual")
                ui.kv("Connections / Rotations", f"{e.connections} / {e.rotations}")
                ui.kv("Failures", e.failures)
                ui.sep()
                for line in logger.tail(ui.avail_rows(11)):
                    print(f"    {GR}{line.rstrip()[11:][:LINE_W]}{X}")
                ui.sep()
                print(f"    {GR}Press Ctrl+C to return...{X}", end="")
                time.sleep(1)
        except KeyboardInterrupt:
            pass

    # ------------------------------------------------------------ [2]
    def load_menu(self):
        ui.title("Load Proxy List")
        os.makedirs(PROXY_DIR, exist_ok=True)
        files = sorted(f for f in os.listdir(PROXY_DIR) if f.lower().endswith(".txt"))[:9]
        for i, f in enumerate(files, 1):
            ui.opt(i, f)
        if files:
            print()
        default = self.cfg["last_list"] or (files[0] if files else "")
        raw = ui.ask("File number or path", default).strip('"')
        if not raw:
            return
        path = files[int(raw) - 1] if raw.isdigit() and 0 < int(raw) <= len(files) else raw
        if not os.path.isabs(path):
            path = os.path.join(PROXY_DIR, path)
        if not os.path.isfile(path):
            ui.err("File not found.")
            ui.pause()
            return
        proto = ui.ask(f"Protocol for lines without prefix ({'/'.join(PROTOCOLS)})",
                       self.cfg["default_protocol"]).lower()
        if proto not in PROTOCOLS:
            ui.err("Unknown protocol.")
            ui.pause()
            return
        self.cfg["default_protocol"] = proto
        try:
            proxies, invalid = load_file(path, proto)
        except OSError as ex:
            ui.err(f"Cannot read file: {ex}")
            ui.pause()
            return
        if not proxies:
            ui.err("No valid proxies found.")
            ui.info("Formats: IP:PORT  IP:PORT:USER:PASS  USER:PASS@IP:PORT")
            ui.pause()
            return
        mode = "r"
        if self.pool:
            mode = ui.ask("[R]eplace pool or [A]ppend?", "R").lower()[:1]
        if mode == "a":
            keys = {p.key for p in self.pool}
            proxies = [p for p in proxies if p.key not in keys]
            self.pool.extend(proxies)
        else:
            with self.engine.lock:
                self.pool[:] = proxies
                self.engine.current = None
        self.cfg["last_list"] = os.path.relpath(path, PROXY_DIR) if path.startswith(PROXY_DIR) else path
        ui.ok(f"Loaded {len(proxies)} proxies from {os.path.basename(path)}"
              + (f" ({invalid} invalid skipped)" if invalid else ""))
        logger.info(f"Proxy list loaded: {os.path.basename(path)} - {len(proxies)} valid, {invalid} invalid")
        if self.engine.running and self.engine.current is None:
            self.engine.rotate("pool reloaded")
        if proxies and ui.ask("Check availability now? (y/n)", "y").lower().startswith("y"):
            self.run_checks(proxies)
        ui.pause()

    # ------------------------------------------------------------ [3]
    def pool_menu(self):
        self.page = 0
        while True:
            ui.title("Proxy Pool")
            if not self.pool:
                ui.info("Pool is empty. Load a list with menu [2].")
                ui.pause()
                return
            on, off, un = self.counts()
            per_page = ui.avail_rows(7)
            order = {"ONLINE": 0, "UNTESTED": 1, "OFFLINE": 2}
            shown = sorted(self.pool, key=lambda p: (order[p.status], p.latency or 99999))
            pages = max(1, -(-len(shown) // per_page))
            self.page = min(self.page, pages - 1)
            print(f"    {G}{len(self.pool)} total{X}  {ui.tag('ONLINE')} {on}  "
                  f"{ui.tag('OFFLINE')} {off}  {ui.tag('UNTESTED')} {un}   "
                  f"{GR}page {self.page + 1}/{pages}{X}")
            print(f"    {GR}{'#':>3} {'STATUS':<10} {'PROXY':<30} {'PING':>6}  LOCATION{X}")
            start = self.page * per_page
            for i, p in enumerate(shown[start:start + per_page], start + 1):
                mark = f"{C}►{X}" if p is self.engine.current else " "
                lat = f"{p.latency}ms" if p.latency else "-"
                print(f"   {mark}{GR}{i:>3}{X} {ui.tag(p.status, 10)} {W}{p.label()[:30]:<30}{X} "
                      f"{C}{lat:>6}{X}  {GR}{p.geo[:14]}{X}")
            ui.sep()
            print(f"    {C}[N]{X}{G}ext{X} {C}[P]{X}{G}rev{X}  {C}[1]{X} {G}Re-check{X}  "
                  f"{C}[2]{X} {G}Remove offline{X}  {C}[3]{X} {G}Export{X}  {C}[0]{X} {G}Back{X}")
            c = ui.choose().lower()
            if c in ("0", ""):
                return
            if c == "n":
                self.page = (self.page + 1) % pages
            elif c == "p":
                self.page = (self.page - 1) % pages
            elif c == "1":
                self.run_checks(list(self.pool))
                ui.pause()
            elif c == "2":
                with self.engine.lock:
                    before = len(self.pool)
                    self.pool[:] = [p for p in self.pool if p.status != "OFFLINE"]
                    if self.engine.current not in self.pool:
                        self.engine.current = None
                        if self.engine.running:
                            self.engine.rotate("pool cleaned")
                removed = before - len(self.pool)
                logger.info(f"Removed {removed} offline proxies from pool")
                ui.ok(f"Removed {removed} offline proxies.")
                time.sleep(1)
            elif c == "3":
                path = os.path.join(PROXY_DIR, "phantom_online.txt")
                online = [p for p in self.pool if p.status == "ONLINE"]
                with open(path, "w", encoding="utf-8") as f:
                    for p in online:
                        f.write(f"{p.protocol}://{p.host}:{p.port}\n")
                logger.info(f"Exported {len(online)} online proxies (without credentials)")
                ui.ok(f"Exported {len(online)} proxies to phantom_online.txt")
                ui.pause()

    # ------------------------------------------------------------ [4]
    def status_menu(self):
        ui.title("Connection Status")
        e, p = self.engine, self.engine.current
        if e.running and p and p.status == "ONLINE":
            state = "CONNECTED"
        elif e.running and p:
            state = "ROTATING"
        elif e.running:
            state = "ERROR"
        else:
            state = "OFFLINE"
        ui.kv("Connection", ui.tag(state))
        ui.kv("Local endpoint", f"127.0.0.1:{self.cfg['listen_port']}" if e.running else "-")
        ui.kv("Windows system proxy", ui.tag("ON" if self.sysproxy_on else "OFF"))
        ui.kv("Current proxy", p.label() if p else "-")
        ui.kv("Proxy type", p.protocol.upper() if p else "-")
        ui.kv("External IP", (p.exit_ip or "unknown (run test [5])") if p else "-")
        ui.kv("Country / Region", p.geo if p else "-")
        ui.kv("Latency", f"{p.latency} ms" if p and p.latency else "-")
        ui.kv("Last successful check", fmt_time(p.last_check) if p and p.status == "ONLINE" else "-")
        nr = e.next_rotation
        ui.kv("Next rotation", f"{fmt_time(nr)} (in {max(0, int(nr - time.time()))}s)"
              if nr else ("manual" if e.running else "-"))
        ui.sep()
        ui.kv("Uptime", str(datetime.timedelta(seconds=int(time.time() - e.started_at)))
              if e.running else "-")
        ui.kv("Connections / Rotations", f"{e.connections} / {e.rotations}")
        ui.kv("Failures", e.failures)
        ui.kv("Sticky sites", f"{e.sticky_count()} active ({self.cfg['sticky_minutes']} min)"
              if self.cfg["sticky"] else "off")
        if e.last_error:
            ui.kv("Last error", f"{R}{e.last_error[:40]}{X}")
        if ui.wait():
            return self.status_menu()

    # ------------------------------------------------------------ [5]
    def test_current(self):
        ui.title("Test Current Proxy")
        p = self.engine.current
        if not p:
            ui.err("No active proxy. Start rotation first (menu 1).")
            ui.pause()
            return
        ui.info(f"Testing {p.label()} ...")
        check(p, self.cfg["timeout"])
        print()
        ui.kv("Result", ui.tag(p.status))
        if p.status == "ONLINE":
            ui.kv("External IP", p.exit_ip)
            ui.kv("Country / Region", p.geo)
            ui.kv("Latency", f"{p.latency} ms")
            logger.info(f"Current proxy test OK: {p.label()} ({p.latency}ms)")
        else:
            logger.error(f"Current proxy test FAILED: {p.label()}")
            if self.engine.running and self.cfg["auto_failover"]:
                n = self.engine.rotate("failover after test")
                ui.info(f"Auto-failover switched to {n.label()}" if n else "No usable proxy left.")
        ui.pause()

    # ------------------------------------------------------------ [6]
    def settings_menu(self):
        while True:
            ui.title("Rotation Settings")
            s = self.cfg
            onoff = lambda v: ui.tag("ON" if v else "OFF")
            ui.opt(1, "Rotation interval   ", f"{W}{s['interval']}s{X} {GR}(0 = manual){X}")
            ui.opt(2, "Connection timeout  ", f"{W}{s['timeout']}s{X}")
            ui.opt(3, "Auto failover       ", onoff(s["auto_failover"]))
            ui.opt(4, "Rotation mode       ", f"{W}{s['mode']}{X}")
            ui.opt(5, "Avoid reuse         ", onoff(s["avoid_repeat"]))
            ui.opt(6, "Max retries         ", f"{W}{s['max_retries']}{X}")
            ui.opt(7, "Local port          ", f"{W}{s['listen_port']}{X} {GR}(next start){X}")
            ui.opt(8, "Max latency         ", f"{W}{s['max_latency']}ms{X} {GR}(slower ones skipped){X}")
            ui.opt(9, "Backup after        ", f"{W}{s['hedge_ms']}ms{X} {GR}(parallel failover){X}")
            ui.opt("F", "Fastest pool size   ", f"{W}{s['fast_pool']}{X} {GR}(fastest mode){X}")
            ui.opt("H", "Health check every  ", f"{W}{s['health_interval']}s{X} {GR}(0 = off){X}")
            ui.opt("S", "Sticky sites        ", onoff(s["sticky"]) + f" {GR}same proxy per website{X}")
            ui.opt("T", "Sticky time         ", f"{W}{s['sticky_minutes']} min{X}")
            if winshell.SUPPORTED:
                ui.opt("D", "Desktop shortcut    ",
                       ui.tag("ON" if winshell.shortcut_exists() else "OFF") + f" {GR}PHANTOM icon{X}")
            ui.opt(0, "Back")
            print(f"\n      {GR}Settings are saved automatically.{X}")
            c = ui.choose()
            if c in ("0", ""):
                return
            try:
                if c == "1":
                    v = int(ui.ask("Interval in seconds", s["interval"]))
                    if v < 0:
                        raise ValueError
                    s["interval"] = v
                    with self.engine.lock:
                        self.engine.next_rotation = time.time() + v if v and self.engine.running else None
                elif c == "2":
                    v = int(ui.ask("Timeout in seconds (1-60)", s["timeout"]))
                    if not 1 <= v <= 60:
                        raise ValueError
                    s["timeout"] = v
                elif c == "3":
                    s["auto_failover"] = not s["auto_failover"]
                elif c == "4":
                    modes = ["fastest", "random", "sequential"]
                    s["mode"] = modes[(modes.index(s["mode"]) + 1) % 3 if s["mode"] in modes else 0]
                elif c == "5":
                    s["avoid_repeat"] = not s["avoid_repeat"]
                elif c == "6":
                    v = int(ui.ask("Max retries (1-20)", s["max_retries"]))
                    if not 1 <= v <= 20:
                        raise ValueError
                    s["max_retries"] = v
                elif c == "7":
                    if self.sysproxy_on:
                        ui.err("Disable Windows system proxy before changing the port.")
                        time.sleep(1.5)
                        continue
                    v = int(ui.ask("Port (1024-65535)", s["listen_port"]))
                    if not 1024 <= v <= 65535:
                        raise ValueError
                    s["listen_port"] = v
                elif c == "8":
                    v = int(ui.ask("Max latency in ms (200-20000)", s["max_latency"]))
                    if not 200 <= v <= 20000:
                        raise ValueError
                    s["max_latency"] = v
                elif c == "9":
                    v = int(ui.ask("Backup attempt after ms (200-10000)", s["hedge_ms"]))
                    if not 200 <= v <= 10000:
                        raise ValueError
                    s["hedge_ms"] = v
                elif c.lower() == "f":
                    v = int(ui.ask("Rotate among the N fastest (1-20)", s["fast_pool"]))
                    if not 1 <= v <= 20:
                        raise ValueError
                    s["fast_pool"] = v
                elif c.lower() == "s":
                    s["sticky"] = not s["sticky"]
                    if not s["sticky"]:
                        self.engine._sticky.clear()
                elif c.lower() == "d" and winshell.SUPPORTED:
                    toggle_shortcut()
                    time.sleep(1.5)
                elif c.lower() == "t":
                    v = int(ui.ask("Minutes a website keeps its proxy (1-120)", s["sticky_minutes"]))
                    if not 1 <= v <= 120:
                        raise ValueError
                    s["sticky_minutes"] = v
                elif c.lower() == "h":
                    v = int(ui.ask("Health check interval in s (0 or 30-3600)", s["health_interval"]))
                    if v != 0 and not 30 <= v <= 3600:
                        raise ValueError
                    s["health_interval"] = v
                else:
                    continue
                logger.info(f"Settings changed (option {c})")
            except ValueError:
                ui.err("Invalid value.")
                time.sleep(1.2)

    # ------------------------------------------------------------ [7]
    def logs_menu(self):
        while True:
            ui.title("Activity Logs")
            lines = logger.tail(ui.avail_rows(5))
            if not lines:
                ui.info("No log entries yet.")
            for line in lines:
                color = R if "[ERROR]" in line else Y if "[WARN]" in line else G
                print(f"  {GR}{line[5:19]}{X} {color}{line[20:].rstrip()[:LINE_W - 12]}{X}")
            ui.sep()
            print(f"    {C}[1]{X} {G}Refresh{X}   {C}[2]{X} {G}Clear logs{X}   {C}[0]{X} {G}Back{X}"
                  f"      {GR}full log: logs/phantom.log{X}")
            c = ui.choose()
            if c == "2":
                logger.clear()
                logger.info("Logs cleared")
            elif c not in ("1", ui.REDRAW):
                return

    # ------------------------------------------------------------ [8]
    def about(self):
        ui.title("About PHANTOM")
        ui.kv("Name", NAME)
        ui.kv("Made by", f"{C}{AUTHOR}{X}  {GR}{AUTHOR_URL}{X}")
        ui.kv("School", SCHOOL)
        ui.kv("Version", f"{VERSION}  (Python {sys.version.split()[0]})")
        ui.kv("License", f"{C}PolyForm Internal Use + personal use{X}")
        ui.sep()
        print("  " + ui.center(f"{C}{B}You may use and change PHANTOM for yourself,{X}"))
        print("  " + ui.center(f"{C}{B}but not publish or share it. See LICENSE.{X}"))
        print()
        for line in (
            "Runs a local proxy on 127.0.0.1 and rotates traffic through",
            "proxies from your own lists (HTTP, HTTPS, SOCKS4, SOCKS5).",
            "Windows proxy changes ONLY when you enable it, and is",
            "restored automatically when rotation stops or you exit.",
            "",
            "Use only proxies you are authorized to use. Never log in",
            "to accounts through untrusted free proxies.",
        ):
            print("  " + ui.center(f"{G}{line}{X}"))
        if ui.wait():
            return self.about()

    # ------------------------------------------------------------ lifecycle
    def shutdown(self):
        if getattr(self, "_down", False):
            return
        self._down = True
        self.sysproxy_off("PHANTOM exit")
        self.engine.stop()
        logger.info("PHANTOM shut down")
        print(f"\n  {ui.center(f'{G}PHANTOM shut down safely.{X}  {C}{SLOGAN}{X}')}\n")


LINE_W = ui.LAYOUT_W - 8

TERMS = (
    "PHANTOM is intended for legitimate purposes only, such as",
    "protecting your privacy, testing your own services and",
    "learning about networking.",
    "",
    "By using PHANTOM you agree that:",
    "",
    "  1. You use it only lawfully and only with proxies you are",
    "     authorized to use.",
    "  2. You will not use it for unauthorized access, evading",
    "     bans or security measures, attacks, fraud or spam.",
    "  3. You are solely responsible for how you use it.",
    "  4. The author does not endorse any illegal activity and",
    "     accepts no liability for misuse or damage.",
)


def terms_accepted(cfg):
    return cfg["terms_accepted"] == TERMS_VERSION


WELCOME_BACK = (
    "Welcome back! Last time you chose not to accept the",
    "Terms of Use.",
    "",
    "Before we continue, please tell us honestly why you are",
    "here. There is no wrong answer.",
)

ONLY_TO_GET_IN = (
    "Thank you for being honest - we appreciate it.",
    "",
    "Accepting the Terms of Use is not just a click to get in.",
    "It is a promise that you will use PHANTOM only lawfully",
    "and never for illegal or harmful purposes.",
    "",
    "Please read the terms again, and only type 'yes' if you",
    "truly agree with them. If you don't, that's okay -",
    "just type 'no' and PHANTOM will close.",
)


def welcome_back():
    """Shown when the user previously declined the terms.
    Returns False if the user chose to exit."""
    while True:
        ui.title("Welcome Back")
        for line in WELCOME_BACK:
            print(f"      {G}{line}{X}")
        print()
        ui.opt(1, "I changed my mind - I agree to use PHANTOM responsibly")
        ui.opt(2, "I'm only back because PHANTOM wouldn't let me in")
        ui.opt(0, "Exit")
        print()
        c = ui.choose()
        if c == "1":
            logger.info("Returning user: changed their mind about the terms")
            return True
        if c == "2":
            logger.info("Returning user: came back only to get in - terms explained again")
            ui.title("A Quick Word")
            for line in ONLY_TO_GET_IN:
                color = C if line.startswith("Thank you") else G
                print(f"      {color}{line}{X}")
            ui.pause("Press Enter to read the terms...")
            return True
        if c == "0":
            return False


def accept_terms(cfg):
    """First-run terms of use. Asked again only when TERMS_VERSION changes.
    Users who declined before are asked why they came back."""
    if terms_accepted(cfg):
        return True
    if cfg["terms_declined"] and not welcome_back():
        logger.info("Returning user exited without reviewing the terms")
        return False
    while True:
        ui.title("Terms of Use")
        for line in TERMS:
            print(f"      {G if not line.startswith('  ') else W}{line}{X}")
        print()
        print(f"      {GR}Full text: app/DISCLAIMER.md  ·  License: see LICENSE{X}")
        ui.sep()
        answer = ui.choose("Type 'yes' to accept, 'no' to exit")
        if answer == ui.REDRAW:
            continue
        if answer.lower() in ("yes", "y"):
            cfg["terms_accepted"] = TERMS_VERSION
            cfg["terms_declined"] = False
            logger.info(f"Terms of use accepted (version {TERMS_VERSION})")
            return True
        if answer.lower() in ("no", "n"):
            cfg["terms_declined"] = True
            logger.info("Terms of use declined - exiting")
            show_declined()
            return False


DECLINED = (
    "We're sorry, but PHANTOM can't be used without accepting",
    "the Terms of Use.",
    "",
    "These terms exist to keep everyone safe. Please never use",
    "PHANTOM - or any similar tool - for illegal or harmful",
    "purposes, such as attacking systems, evading bans, fraud",
    "or spam.",
    "",
    "If you change your mind, simply start PHANTOM again and",
    "type 'yes' to accept.",
    "",
    "Thank you for understanding. Stay safe!",
)


def show_declined():
    ui.title("Terms Not Accepted")
    for line in DECLINED:
        color = C if line.startswith("Thank you") else G
        print(f"      {color}{line}{X}")
    print()
    ui.pause("Press Enter to exit...")


def setup_folder_icon():
    try:
        if winshell.apply_folder_icon():
            logger.info("PHANTOM folder icon applied")
    except OSError as ex:
        logger.warn(f"Could not apply folder icon: {ex}")


def toggle_shortcut():
    try:
        if winshell.shortcut_exists():
            winshell.remove_shortcut()
            logger.info("Desktop shortcut removed")
            ui.ok("Desktop shortcut removed.")
        else:
            winshell.create_shortcut()
            logger.info("Desktop shortcut created")
            ui.ok("Desktop shortcut created with the PHANTOM icon.")
    except OSError as ex:
        logger.error(f"Desktop shortcut failed: {ex}")
        ui.err(f"Could not change the desktop shortcut: {ex}")


def offer_shortcut(cfg):
    """Ask once, after the terms are accepted, whether to create a desktop shortcut."""
    if cfg["shortcut_asked"] or not winshell.SUPPORTED or winshell.shortcut_exists():
        return
    ui.title("Desktop Shortcut")
    for line in (
        "Would you like a PHANTOM shortcut on your desktop?",
        "",
        "It starts PHANTOM with one double-click and shows the",
        "PHANTOM icon. You can add or remove it any time in",
        "Rotation Settings -> [D] Desktop shortcut.",
    ):
        print(f"      {G}{line}{X}")
    print()
    answer = ui.ask("Create desktop shortcut? (y/n)", "y").lower()
    cfg["shortcut_asked"] = True
    if answer.startswith("y"):
        toggle_shortcut()
        time.sleep(1.5)


def main():
    ui.init()
    logger.info(f"PHANTOM {VERSION} started")
    setup_folder_icon()
    app = App()
    atexit.register(app.shutdown)   # restore Windows proxy even on errors
    if os.name == "nt":             # ...and when the window is closed with X
        import ctypes
        handler_type = ctypes.WINFUNCTYPE(ctypes.c_int, ctypes.c_uint)

        def on_console_event(event):
            if event in (2, 5, 6):  # CLOSE, LOGOFF, SHUTDOWN
                app.shutdown()
            return 0
        app._console_handler = handler_type(on_console_event)
        ctypes.windll.kernel32.SetConsoleCtrlHandler(app._console_handler, True)
    try:
        if accept_terms(app.cfg):
            offer_shortcut(app.cfg)
            app.main_menu()
    except (KeyboardInterrupt, EOFError):
        pass
    finally:
        app.shutdown()
