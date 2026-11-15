"""Terminal styling: colors, centered layout, banner, boxes, status tags."""
import builtins
import os
import re
import shutil
import sys
import time

from . import SLOGAN, VERSION

G = "\033[92m"    # green text
C = "\033[96m"    # cyan highlight
GR = "\033[90m"   # gray lines
R = "\033[91m"
Y = "\033[93m"
W = "\033[97m"
B = "\033[1m"
X = "\033[0m"

_ANSI = re.compile(r"\x1b\[[0-9;]*m")
BOX_W = 54
LAYOUT_W = 70          # width of the centered content block
WIN_COLS, WIN_ROWS = 100, 42   # window size requested in classic console

BANNER = [
    "██████╗ ██╗  ██╗ █████╗ ███╗   ██╗████████╗ ██████╗ ███╗   ███╗",
    "██╔══██╗██║  ██║██╔══██╗████╗  ██║╚══██╔══╝██╔═══██╗████╗ ████║",
    "██████╔╝███████║███████║██╔██╗ ██║   ██║   ██║   ██║██╔████╔██║",
    "██╔═══╝ ██╔══██║██╔══██║██║╚██╗██║   ██║   ██║   ██║██║╚██╔╝██║",
    "██║     ██║  ██║██║  ██║██║ ╚████║   ██║   ╚██████╔╝██║ ╚═╝ ██║",
    "╚═╝     ╚═╝  ╚═╝╚═╝  ╚═╝╚═╝  ╚═══╝   ╚═╝    ╚═════╝ ╚═╝     ╚═╝",
]

SMALL_BANNER = [   # 2-line logo for windows too short for the full banner
    "█▀█ █ █ ▄▀█ █▄ █ ▀█▀ █▀█ █▀▄▀█",
    "█▀▀ █▀█ █▀█ █ ▀█  █  █▄█ █ ▀ █",
]

TAG_COLORS = {
    "ONLINE": G, "OFFLINE": R, "CONNECTED": C, "ERROR": R, "ROTATING": Y,
    "UNTESTED": GR, "READY": G, "STOPPED": GR, "OK": G, "INFO": C, "WARN": Y,
    "ON": Y, "OFF": GR,
}

header_h = 0   # lines used by the current header


# ------------------------------------------------------------------ layout
def size():
    s = shutil.get_terminal_size((WIN_COLS, WIN_ROWS))
    return s.columns, s.lines


def margin():
    return " " * max(0, (size()[0] - LAYOUT_W) // 2)


def print(*args, sep=" ", end="\n", **kw):   # noqa: A001 - centered print
    m = margin()
    s = sep.join(str(a) for a in args)
    s = "\n".join(m + line if line else line for line in s.split("\n"))
    builtins.print(s, end=end, **kw)


def center(text, width=LAYOUT_W - 4):
    pad = max(0, width - vlen(text))
    return " " * (pad // 2) + text


def avail_rows(used):
    """Rows left on screen after the header and `used` other lines."""
    return max(3, size()[1] - header_h - used)


def init():
    if os.name == "nt":
        os.system("")                       # enable ANSI colors in cmd
        os.system("title PHANTOM - Proxy Rotation System")
        os.system("color 0A")               # black background, green text
        if not os.environ.get("WT_SESSION"):  # classic console: fixed size, no scrollbar
            os.system(f"mode con: cols={WIN_COLS} lines={WIN_ROWS}")
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8")
        except Exception:
            pass


def clear():
    os.system("cls" if os.name == "nt" else "clear")


def vlen(s):
    return len(_ANSI.sub("", s))


def tag(state, width=0):
    t = f"{TAG_COLORS.get(state, W)}[{state}]{X}"
    return t + " " * max(0, width - len(state) - 2)


# ------------------------------------------------------------------ header
def banner():
    """Full ASCII banner when the window is tall enough, compact otherwise."""
    global header_h
    clear()
    if size()[1] >= 38:
        print()
        for line in BANNER:
            print(G + B + "  " + center(line) + X)
        print()
        print(C + "  " + center(SLOGAN) + X)
        print(G + "  " + center("PROXY ROTATION SYSTEM") + X)
        print(GR + "  " + center(f"VERSION {VERSION}") + X)
        header_h = 12
    else:
        print()
        for line in SMALL_BANNER:
            print(G + B + "  " + center(line) + X)
        print(C + "  " + center(SLOGAN) + X)
        header_h = 5
    sep()


def sep():
    print(GR + "  " + "─" * (LAYOUT_W - 4) + X)


def title(text):
    global header_h
    banner()
    print("  " + center(f"{C}{B}» {text.upper()} «{X}"))
    sep()
    header_h += 2


# ------------------------------------------------------------------ box
def _box(left, fill, right):
    print(GR + "  " + " " * ((LAYOUT_W - 4 - BOX_W - 2) // 2) + left + fill * BOX_W + right + X)


def box_top():
    _box("╔", "═", "╗")


def box_mid():
    _box("╠", "═", "╣")


def box_bot():
    _box("╚", "═", "╝")


def box_row(text="", center_text=False):
    pad = max(0, BOX_W - vlen(text))
    left = pad // 2 if center_text else 0
    indent = " " * ((LAYOUT_W - 4 - BOX_W - 2) // 2)
    print(f"{GR}  {indent}║{X}{' ' * left}{text}{' ' * (pad - left)}{GR}║{X}")


# ------------------------------------------------------------------ text
def kv(key, value, width=24):
    print(f"      {GR}{key:<{width}}{X}{G}{value}{X}")


def opt(key, label, extra=""):
    print(f"      {C}[{key}]{X} {G}{label}{X}{extra}")


def ok(msg):
    print(f"      {tag('OK')} {G}{msg}{X}")


def err(msg):
    print(f"      {tag('ERROR')} {R}{msg}{X}")


def info(msg):
    print(f"      {tag('INFO')} {W}{msg}{X}")


def warn(msg):
    print(f"      {tag('WARN')} {Y}{msg}{X}")


def progress(i, n, label=""):
    width = 34
    done = int(width * i / n) if n else width
    bar = f"{G}{'█' * done}{GR}{'░' * (width - done)}{X}"
    sys.stdout.write(f"\r{margin()}      {bar} {C}{i:>3}/{n}{X} {GR}{label[:16]:<16}{X}")
    sys.stdout.flush()
    if i >= n:
        builtins.print()


def ask(prompt, default=None):
    hint = f" {GR}[{default}]{X}" if default not in (None, "") else ""
    try:
        val = input(f"{margin()}      {C}›{X} {prompt}{hint}: {G}").strip()
    finally:
        builtins.print(X, end="")
    return val if val else ("" if default is None else str(default))


def pause():
    try:
        input(f"\n{margin()}      {GR}Press Enter to return...{X}")
    except EOFError:
        pass


# ------------------------------------------------------- resize-aware input
REDRAW = "\x00redraw"   # returned by choose()/wait() when the window size changed

try:
    import msvcrt
except ImportError:      # not Windows
    msvcrt = None


def _live_input(prompt):
    """Like input(), but returns REDRAW as soon as the window is resized
    (maximize, full screen F11/Alt+Enter, dragging the border)."""
    if msvcrt is None or not sys.stdin.isatty():
        return input(prompt)
    builtins.print(prompt, end="", flush=True)
    start, buf = size(), []
    while True:
        if msvcrt.kbhit():
            ch = msvcrt.getwch()
            if ch in ("\r", "\n"):
                builtins.print()
                return "".join(buf)
            if ch == "\x03":
                raise KeyboardInterrupt
            if ch in ("\x00", "\xe0"):        # arrow / function keys
                msvcrt.getwch()
            elif ch == "\b":
                if buf:
                    buf.pop()
                    sys.stdout.write("\b \b")
                    sys.stdout.flush()
            elif ch.isprintable():
                buf.append(ch)
                sys.stdout.write(ch)
                sys.stdout.flush()
        else:
            if size() != start:
                return REDRAW
            time.sleep(0.05)


def choose(prompt="Select an option"):
    try:
        val = _live_input(f"{margin()}      {C}›{X} {prompt}: {G}")
    finally:
        builtins.print(X, end="")
    return val if val == REDRAW else val.strip()


def wait():
    """Pause screen. Returns True if the screen must be redrawn (resize)."""
    try:
        return _live_input(f"\n{margin()}      {GR}Press Enter to return...{X}") == REDRAW
    except EOFError:
        return False
