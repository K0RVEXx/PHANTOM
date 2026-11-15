"""Opens a TCP tunnel to host:port through an upstream HTTP/HTTPS/SOCKS4/SOCKS5 proxy."""
import asyncio
import base64


class TunnelError(Exception):
    pass


async def open_tunnel(proxy, host, port, timeout):
    async def t(coro):
        return await asyncio.wait_for(coro, timeout)

    try:
        reader, writer = await t(asyncio.open_connection(proxy.host, proxy.port))
    except Exception as e:
        raise TunnelError(f"cannot reach proxy ({type(e).__name__})") from None

    try:
        if proxy.protocol in ("http", "https"):
            req = f"CONNECT {host}:{port} HTTP/1.1\r\nHost: {host}:{port}\r\n"
            if proxy.user:
                token = base64.b64encode(f"{proxy.user}:{proxy.password or ''}".encode()).decode()
                req += f"Proxy-Authorization: Basic {token}\r\n"
            writer.write((req + "\r\n").encode())
            await writer.drain()
            head = await t(reader.readuntil(b"\r\n\r\n"))
            parts = head.split(b"\r\n", 1)[0].split()
            if len(parts) < 2 or parts[1] != b"200":
                raise TunnelError(f"CONNECT refused ({b' '.join(parts[1:3]).decode(errors='replace')})")

        elif proxy.protocol == "socks5":
            methods = b"\x00\x02" if proxy.user else b"\x00"
            writer.write(b"\x05" + bytes([len(methods)]) + methods)
            await writer.drain()
            ver, method = await t(reader.readexactly(2))
            if ver != 5:
                raise TunnelError("not a SOCKS5 proxy")
            if method == 2:
                u = (proxy.user or "").encode()
                p = (proxy.password or "").encode()
                writer.write(b"\x01" + bytes([len(u)]) + u + bytes([len(p)]) + p)
                await writer.drain()
                if (await t(reader.readexactly(2)))[1] != 0:
                    raise TunnelError("SOCKS5 authentication failed")
            elif method != 0:
                raise TunnelError("SOCKS5 auth method rejected")
            hb = host.encode("idna")
            writer.write(b"\x05\x01\x00\x03" + bytes([len(hb)]) + hb + port.to_bytes(2, "big"))
            await writer.drain()
            rep = await t(reader.readexactly(4))
            if rep[1] != 0:
                raise TunnelError(f"SOCKS5 connect failed (code {rep[1]})")
            atyp = rep[3]
            alen = {1: 4, 4: 16}.get(atyp)
            if alen is None:
                alen = (await t(reader.readexactly(1)))[0]
            await t(reader.readexactly(alen + 2))

        elif proxy.protocol == "socks4":
            uid = (proxy.user or "").encode()
            writer.write(b"\x04\x01" + port.to_bytes(2, "big") + b"\x00\x00\x00\x01"
                         + uid + b"\x00" + host.encode("idna") + b"\x00")
            await writer.drain()
            rep = await t(reader.readexactly(8))
            if rep[1] != 0x5A:
                raise TunnelError(f"SOCKS4 request rejected (code {rep[1]})")
        return reader, writer

    except (TunnelError, asyncio.CancelledError):
        writer.close()
        raise
    except Exception as e:
        writer.close()
        raise TunnelError(f"handshake failed ({type(e).__name__})") from None
