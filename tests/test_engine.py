import time

import pytest
from conftest import make_proxy

from phantom.engine import Engine


@pytest.mark.parametrize("host, site", [
    ("www.google.com", "google.com"),
    ("mail.google.com", "google.com"),
    ("google.com", "google.com"),
    ("news.bbc.co.uk", "bbc.co.uk"),
    ("api.ipify.org", "ipify.org"),
    ("1.2.3.4", "1.2.3.4"),
    ("WWW.Example.COM.", "example.com"),
])
def test_site_of(host, site):
    assert Engine.site_of(host) == site


def test_fastest_mode_uses_top_n(cfg):
    pool = [make_proxy(f"10.0.0.{i}", latency=l) for i, l in enumerate([3000, 300, 900, 500, 2000])]
    cfg.update(mode="fastest", fast_pool=2, max_latency=5000)
    hosts = {p.host for p in Engine(cfg, pool)._candidates()}
    assert hosts == {"10.0.0.1", "10.0.0.3"}


def test_latency_filter_falls_back_to_all_online(cfg):
    pool = [make_proxy("10.0.0.1", latency=4000), make_proxy("10.0.0.2", latency=5000)]
    cfg.update(mode="random", max_latency=1000)
    assert len(Engine(cfg, pool)._candidates()) == 2


def test_offline_proxies_never_selected(cfg):
    pool = [make_proxy("10.0.0.1", 100, status="OFFLINE"), make_proxy("10.0.0.2", 900)]
    e = Engine(cfg, pool)
    for _ in range(5):
        assert e.rotate("test").host == "10.0.0.2"


def test_rotate_changes_proxy(cfg):
    pool = [make_proxy(f"10.0.0.{i}", latency=100 + i) for i in range(3)]
    cfg.update(mode="random")
    e = Engine(cfg, pool)
    prev = e.rotate("test")
    for _ in range(10):
        nxt = e.rotate("test")
        assert nxt is not prev
        prev = nxt


def test_sequential_cycles(cfg):
    pool = [make_proxy(f"10.0.0.{i}", latency=100) for i in range(3)]
    cfg.update(mode="sequential")
    e = Engine(cfg, pool)
    seen = [e.rotate("test").host for _ in range(3)]
    assert sorted(seen) == sorted(p.host for p in pool)


def test_empty_pool_returns_none(cfg):
    assert Engine(cfg, []).rotate("test") is None


def test_failover_marks_offline_after_two_failures(cfg):
    a, b = make_proxy("10.0.0.1", 100), make_proxy("10.0.0.2", 200)
    e = Engine(cfg, [a, b])
    e.current = a
    e.report_failure(a, "boom")
    assert e.current is b and a.status == "ONLINE"
    e.report_failure(a, "boom")
    assert a.status == "OFFLINE"


def test_sticky_site_binding(cfg):
    a, b = make_proxy("10.0.0.1", 100), make_proxy("10.0.0.2", 200)
    e = Engine(cfg, [a, b])
    e._sticky_set("google.com", a)
    e.current = b
    assert e._sticky_get("google.com") is a
    assert e.sticky_count() == 1


def test_sticky_expires_and_skips_offline(cfg):
    a = make_proxy("10.0.0.1", 100)
    e = Engine(cfg, [a])
    e._sticky["x.com"] = (a, time.time() - 1)
    assert e._sticky_get("x.com") is None
    e._sticky_set("y.com", a)
    a.status = "OFFLINE"
    assert e._sticky_get("y.com") is None


def test_sticky_disabled(cfg):
    a = make_proxy("10.0.0.1", 100)
    cfg["sticky"] = False
    e = Engine(cfg, [a])
    e._sticky_set("google.com", a)
    assert e._sticky_get("google.com") is None
