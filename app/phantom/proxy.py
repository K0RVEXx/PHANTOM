"""Proxy model, list parsing and availability checks."""
import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from urllib.parse import quote

import requests

PROTOCOLS = ("http", "https", "socks4", "socks5")

_LINE = re.compile(
    r"^(?:(?P<proto>https?|socks4a?|socks5h?)://)?"
    r"(?:(?P<u1>[^:@\s]+):(?P<p1>[^@\s]+)@)?"
    r"(?P<host>[A-Za-z0-9.\-]+|\[[0-9a-fA-F:]+\]):(?P<port>\d{1,5})"
    r"(?::(?P<u2>[^:\s]+):(?P<p2>\S+))?$",
    re.IGNORECASE,
)

GEO_URL = "http://ip-api.com/json/{ip}?fields=status,country,regionName"
IP_URL = "https://api.ipify.org?format=json"


@dataclass
class Proxy:
    protocol: str
    host: str
    port: int
    user: str = None
    password: str = field(default=None, repr=False)
    status: str = "UNTESTED"      # UNTESTED | ONLINE | OFFLINE
    latency: int = None
    exit_ip: str = None
    country: str = None
    region: str = None
    last_check: float = None
    fails: int = 0

    @property
    def key(self):
        return (self.protocol, self.host, self.port, self.user)

    def label(self):
        """Display/log form - credentials are always masked."""
        auth = "***:***@" if self.user else ""
        return f"{self.protocol}://{auth}{self.host}:{self.port}"

    def requests_url(self):
        scheme = {"http": "http", "https": "http",
                  "socks4": "socks4a", "socks5": "socks5h"}[self.protocol]
        auth = ""
        if self.user:
            auth = f"{quote(self.user, safe='')}:{quote(self.password or '', safe='')}@"
        return f"{scheme}://{auth}{self.host}:{self.port}"

    @property
    def geo(self):
        parts = [p for p in (self.country, self.region) if p]
        return ", ".join(parts) if parts else "-"


def parse_line(line, default_protocol="http"):
    line = line.strip()
    if not line or line.startswith("#"):
        return None
    m = _LINE.match(line)
    if not m:
        return None
    proto = (m.group("proto") or default_protocol).lower()
    proto = {"socks4a": "socks4", "socks5h": "socks5"}.get(proto, proto)
    port = int(m.group("port"))
    if not 1 <= port <= 65535 or proto not in PROTOCOLS:
        return None
    user = m.group("u1") or m.group("u2")
    pw = m.group("p1") or m.group("p2")
    return Proxy(proto, m.group("host").strip("[]"), port, user, pw)


def load_file(path, default_protocol="http"):
    """Returns (proxies, invalid_line_count). Duplicates are dropped."""
    proxies, seen, invalid = [], set(), 0
    with open(path, encoding="utf-8", errors="ignore") as f:
        for raw in f:
            if not raw.strip() or raw.strip().startswith("#"):
                continue
            p = parse_line(raw, default_protocol)
            if p is None:
                invalid += 1
            elif p.key not in seen:
                seen.add(p.key)
                proxies.append(p)
    return proxies, invalid


_geo_cache = {}


def geolocate(ip, timeout=6):
    """Country/region of an exit IP (direct lookup, cached). Returns (country, region)."""
    if ip in _geo_cache:
        return _geo_cache[ip]
    try:
        d = requests.get(GEO_URL.format(ip=ip), timeout=timeout).json()
        if d.get("status") == "success":
            _geo_cache[ip] = (d.get("country"), d.get("regionName"))
            return _geo_cache[ip]
    except Exception:
        pass
    return (None, None)


def check(proxy, timeout=8):
    """Real check: an HTTPS request through the proxy must succeed
    (this proves CONNECT tunnelling works). Updates and returns the proxy."""
    url = proxy.requests_url()
    proxies = {"http": url, "https": url}
    start = time.time()
    ok = False
    try:
        r = requests.get(IP_URL, proxies=proxies, timeout=timeout)
        ip = r.json().get("ip") if r.status_code == 200 else None
        ok = bool(ip and re.fullmatch(r"[0-9a-fA-F.:]+", ip))
        if ok:
            proxy.latency = int((time.time() - start) * 1000)
            proxy.exit_ip = ip
            proxy.country, proxy.region = geolocate(ip)
    except Exception:
        ok = False
    if not ok:
        proxy.latency = None
    proxy.status = "ONLINE" if ok else "OFFLINE"
    proxy.fails = 0 if ok else proxy.fails + 1
    proxy.last_check = time.time()
    return proxy


def check_many(proxies, timeout=8, on_result=None):
    if not proxies:
        return
    with ThreadPoolExecutor(max_workers=min(64, len(proxies))) as ex:
        futures = [ex.submit(check, p, timeout) for p in proxies]
        for i, fut in enumerate(as_completed(futures), 1):
            p = fut.result()
            if on_result:
                on_result(i, len(proxies), p)
