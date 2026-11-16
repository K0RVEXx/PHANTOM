"""Rotation engine: a local HTTP proxy on 127.0.0.1 that forwards traffic
through the currently selected upstream proxy and rotates it.

Only applications explicitly pointed at 127.0.0.1:<port> are affected.
The Windows network configuration is never modified.
"""
import asyncio
import random
import threading
import time
from collections import deque
from urllib.parse import urlsplit

from . import logger
from .proxy import check_many
from .tunnel import TunnelError, open_tunnel

HOP_HEADERS = {"proxy-connection", "proxy-authorization", "connection", "keep-alive"}


class Engine:
    def __init__(self, cfg, pool):
        self.cfg = cfg
        self.pool = pool
        self.lock = threading.RLock()
        self.running = False
        self.current = None
        self.next_rotation = None
        self.started_at = None
        self.rotations = 0
        self.connections = 0
        self.failures = 0
        self.last_error = None
        self._recent = deque(maxlen=13)
        self._sticky = {}        # site -> (proxy, expires_at)
        self._seq = -1
        self._thread = None
        self.loop = None

    # ---------------------------------------------------------------- control
    def start(self):
        if self.running:
            return
        self._ready = threading.Event()
        self._start_error = None
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()
        self._ready.wait(10)
        if self._start_error:
            raise self._start_error

    def stop(self):
        if not self.running or not self.loop:
            return
        self.loop.call_soon_threadsafe(self._stop_evt.set)
        self._thread.join(10)
        self.running = False
        self.next_rotation = None
        logger.info("Rotation engine stopped")

    def _run(self):
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        try:
            self.loop.run_until_complete(self._main())
        except Exception as e:
            self._start_error = e
            logger.error(f"Engine failed: {e}")
        finally:
            self.running = False
            self._ready.set()
            try:
                self.loop.close()
            except Exception:
                pass

    async def _main(self):
        self._stop_evt = asyncio.Event()
        port = self.cfg["listen_port"]
        server = await asyncio.start_server(self._handle, "127.0.0.1", port)
        self.running = True
        self.started_at = time.time()
        logger.info(f"Rotation engine started on 127.0.0.1:{port}")
        self.rotate("start")
        self._ready.set()
        ticker = asyncio.create_task(self._ticker())
        await self._stop_evt.wait()
        ticker.cancel()
        server.close()
        for task in asyncio.all_tasks():
            if task is not asyncio.current_task():
                task.cancel()
        await asyncio.sleep(0.1)

    async def _ticker(self):
        last_health = time.time()
        health_task = None
        while True:
            await asyncio.sleep(1)
            nr = self.next_rotation
            if nr and time.time() >= nr:
                self.rotate("scheduled")
            hi = self.cfg["health_interval"]
            if hi > 0 and time.time() - last_health >= hi and (health_task is None or health_task.done()):
                last_health = time.time()
                health_task = asyncio.get_running_loop().run_in_executor(None, self._health_check)

    def _health_check(self):
        """Re-measure online proxies in the background so the speed ranking stays fresh."""
        targets = [p for p in self.pool if p.status == "ONLINE"]
        if not targets:
            return
        check_many(targets, self.cfg["timeout"])
        on = [p for p in targets if p.status == "ONLINE"]
        logger.info(f"Health check: {len(on)}/{len(targets)} still online"
                    + (f", fastest {min(p.latency for p in on)}ms" if on else ""))
        cur = self.current
        if cur is not None and cur not in self._candidates() and self.cfg["auto_failover"]:
            self.rotate("health check")

    # --------------------------------------------------------------- rotation
    def _candidates(self):
        online = [p for p in self.pool if p.status == "ONLINE"]
        fast = [p for p in online if p.latency and p.latency <= self.cfg["max_latency"]]
        cands = fast or online or [p for p in self.pool if p.status == "UNTESTED"]
        if self.cfg["mode"] == "fastest":
            cands = sorted(cands, key=lambda p: p.latency or 99999)[:max(1, self.cfg["fast_pool"])]
        return cands

    def _backup_for(self, tried):
        """Fastest usable proxy not yet tried for this connection."""
        rest = [p for p in self._candidates() if p.key not in tried]
        return min(rest, key=lambda p: p.latency or 99999) if rest else None

    def rotate(self, reason="manual"):
        with self.lock:
            cands = self._candidates()
            if not cands:
                self.current = None
                self.next_rotation = None
                logger.warn("No usable proxies left in pool")
                return None
            if self.cfg["mode"] == "sequential":
                self._seq = (self._seq + 1) % len(cands)
                nxt = cands[self._seq]
                if nxt is self.current and len(cands) > 1:
                    self._seq = (self._seq + 1) % len(cands)
                    nxt = cands[self._seq]
            else:
                others = [p for p in cands if p is not self.current]
                fresh = [p for p in others if p.key not in self._recent] \
                    if self.cfg["avoid_repeat"] else others
                nxt = random.choice(fresh or others or cands)
            prev = self.current
            self.current = nxt
            self._recent.append(nxt.key)
            self.rotations += 1
            iv = self.cfg["interval"]
            self.next_rotation = time.time() + iv if iv > 0 and self.running else None
            logger.info(f"Proxy switch [{reason}]: "
                        f"{prev.label() if prev else 'none'} -> {nxt.label()}")
            return nxt

    def report_failure(self, proxy, err):
        with self.lock:
            self.failures += 1
            self.last_error = f"{proxy.label()}: {err}"
            proxy.fails += 1
            if proxy.fails >= 2:
                proxy.status = "OFFLINE"
            logger.error(f"Connection failed via {proxy.label()}: {err}")
            if proxy is self.current and self.cfg["auto_failover"]:
                self.rotate("failover")

    # ---------------------------------------------------------------- traffic
    async def _handle(self, c_reader, c_writer):
        try:
            head = await asyncio.wait_for(c_reader.readuntil(b"\r\n\r\n"), 30)
        except Exception:
            c_writer.close()
            return

        lines = head.decode("latin-1").split("\r\n")
        try:
            method, target, version = lines[0].split(" ", 2)
        except ValueError:
            c_writer.close()
            return

        if method.upper() == "CONNECT":
            host, _, port = target.rpartition(":")
            host, port = host.strip("[]"), int(port or 443)
            payload = None
        else:
            u = urlsplit(target)
            if u.scheme != "http" or not u.hostname:
                c_writer.write(b"HTTP/1.1 400 Bad Request\r\n\r\n")
                c_writer.close()
                return
            host, port = u.hostname, u.port or 80
            path = (u.path or "/") + (f"?{u.query}" if u.query else "")
            headers = [h for h in lines[1:] if h and h.split(":", 1)[0].strip().lower() not in HOP_HEADERS]
            payload = "\r\n".join([f"{method} {path} {version}", *headers,
                                   "Connection: close", "", ""]).encode("latin-1")

        result = await self._connect(host, port)
        if result is None:
            c_writer.write(b"HTTP/1.1 502 Bad Gateway\r\nContent-Type: text/plain\r\n\r\n"
                           b"PHANTOM: no working proxy available\r\n")
            try:
                await c_writer.drain()
            finally:
                c_writer.close()
            return

        proxy, u_reader, u_writer = result
        self.connections += 1
        if payload is None:
            c_writer.write(b"HTTP/1.1 200 Connection established\r\n\r\n")
            await c_writer.drain()
        else:
            u_writer.write(payload)
            await u_writer.drain()
        await asyncio.gather(_pipe(c_reader, u_writer), _pipe(u_reader, c_writer))

    # ------------------------------------------------------------ sticky sites
    @staticmethod
    def site_of(host):
        """Registrable part of a host name: www.google.com -> google.com,
        news.bbc.co.uk -> bbc.co.uk. IP addresses are returned unchanged."""
        host = host.lower().rstrip(".")
        if host.replace(".", "").isdigit() or ":" in host:
            return host
        parts = host.split(".")
        n = 3 if len(parts) >= 3 and len(parts[-2]) <= 3 and len(parts[-1]) == 2 else 2
        return ".".join(parts[-n:])

    def _sticky_get(self, site):
        if not self.cfg["sticky"]:
            return None
        item = self._sticky.get(site)
        if not item:
            return None
        proxy, expires = item
        if time.time() > expires or proxy.status == "OFFLINE" or proxy not in self.pool:
            self._sticky.pop(site, None)
            return None
        return proxy

    def _sticky_set(self, site, proxy):
        if not self.cfg["sticky"]:
            return
        now = time.time()
        if len(self._sticky) > 500:
            self._sticky = {s: v for s, v in self._sticky.items() if v[1] > now}
        old = self._sticky.get(site)
        if old is None or old[0] is not proxy:
            logger.info(f"Sticky: {site} -> {proxy.label()}")
        self._sticky[site] = (proxy, now + self.cfg["sticky_minutes"] * 60)

    def sticky_count(self):
        now = time.time()
        return sum(1 for _, exp in self._sticky.values() if exp > now)

    def _promote(self, winner, tried):
        """A backup beat the current proxy -> current is too slow; switch to the winner."""
        with self.lock:
            old = self.current
            if old is None or winner is old or old.key not in tried or not self.cfg["auto_failover"]:
                return
            old.fails += 1
            if old.fails >= 2:
                old.status = "OFFLINE"
            self.failures += 1
            self.last_error = f"{old.label()}: too slow, backup was faster"
            self.current = winner
            self.rotations += 1
            iv = self.cfg["interval"]
            self.next_rotation = time.time() + iv if iv > 0 else None
            logger.warn(f"Proxy switch [slow failover]: {old.label()} -> {winner.label()}")

    async def _attempt(self, proxy, host, port):
        try:
            r, w = await open_tunnel(proxy, host, port, self.cfg["timeout"])
            proxy.fails = 0
            return proxy, r, w
        except TunnelError as e:
            self.report_failure(proxy, e)
            return None

    async def _connect(self, host, port):
        """Connect through the current proxy. If it has not answered within
        hedge_ms, race a backup proxy in parallel; the first success wins."""
        tried, pending = set(), set()
        site = self.site_of(host)
        hedge = max(0.2, self.cfg["hedge_ms"] / 1000)
        launches = max(1, self.cfg["max_retries"])
        try:
            while True:
                if launches > 0:
                    cur = self._sticky_get(site) or self.current or self.rotate("no active proxy")
                    if cur is not None and cur.key not in tried:
                        p = cur
                    elif self.cfg["auto_failover"] or not tried:
                        p = self._backup_for(tried)
                    else:
                        p = None
                    if p is not None:
                        tried.add(p.key)
                        launches -= 1
                        pending.add(asyncio.create_task(self._attempt(p, host, port)))
                if not pending:
                    return None
                can_launch = launches > 0 and (self.cfg["auto_failover"] or not tried) \
                    and self._backup_for(tried) is not None
                done, pending = await asyncio.wait(
                    pending, timeout=hedge if can_launch else None,
                    return_when=asyncio.FIRST_COMPLETED)
                winner = None
                for t in done:
                    res = t.result()
                    if res and winner is None:
                        winner = res
                    elif res:
                        res[2].close()     # a second success at the same moment
                if winner:
                    self._promote(winner[0], tried)
                    self._sticky_set(site, winner[0])
                    return winner
        finally:
            for t in pending:
                t.cancel()


async def _pipe(reader, writer):
    try:
        while True:
            data = await reader.read(65536)
            if not data:
                break
            writer.write(data)
            await writer.drain()
    except Exception:
        pass
    finally:
        try:
            writer.close()
        except Exception:
            pass
