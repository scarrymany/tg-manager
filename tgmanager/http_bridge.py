"""Локальный SOCKS5 (127.0.0.1) → HTTP CONNECT к пользовательскому HTTP-прокси.

proxychains-windows умеет SOCKS5, а TG Manager на Linux через proxychains4
поддерживает и HTTP. Мост даёт тот же функционал на Windows.
"""
from __future__ import annotations

import argparse
import asyncio
import base64
import sys


async def _pipe(src: asyncio.StreamReader, dst: asyncio.StreamWriter) -> None:
    try:
        while True:
            data = await src.read(65536)
            if not data:
                break
            dst.write(data)
            await dst.drain()
    except (ConnectionError, OSError, asyncio.CancelledError):
        pass
    finally:
        try:
            dst.close()
        except Exception:
            pass


async def _http_connect(host: str, port: int, proxy_host: str, proxy_port: int,
                        user: str, password: str) -> tuple[asyncio.StreamReader, asyncio.StreamWriter]:
    reader, writer = await asyncio.open_connection(proxy_host, proxy_port)
    req = f"CONNECT {host}:{port} HTTP/1.1\r\nHost: {host}:{port}\r\n"
    if user:
        token = base64.b64encode(f"{user}:{password}".encode("utf-8")).decode("ascii")
        req += f"Proxy-Authorization: Basic {token}\r\n"
    req += "\r\n"
    writer.write(req.encode("ascii"))
    await writer.drain()
    header = b""
    while b"\r\n\r\n" not in header:
        chunk = await reader.read(1)
        if not chunk:
            raise ConnectionError("HTTP-прокси закрыл соединение")
        header += chunk
        if len(header) > 8192:
            raise ConnectionError("Слишком большой ответ HTTP-прокси")
    status_line = header.split(b"\r\n", 1)[0].decode("ascii", "replace")
    parts = status_line.split(" ", 2)
    if len(parts) < 2 or not parts[1].startswith("2"):
        raise ConnectionError(f"HTTP CONNECT отклонён: {status_line}")
    return reader, writer


async def _handle(client_r: asyncio.StreamReader, client_w: asyncio.StreamWriter,
                  proxy_host: str, proxy_port: int, user: str, password: str) -> None:
    try:
        greet = await client_r.readexactly(2)
        if greet[0] != 0x05:
            return
        nmethods = greet[1]
        await client_r.readexactly(nmethods)
        client_w.write(b"\x05\x00")  # no auth — мост только на localhost
        await client_w.drain()

        req = await client_r.readexactly(4)
        if req[0] != 0x05 or req[1] != 0x01:
            client_w.write(b"\x05\x07\x00\x01\x00\x00\x00\x00\x00\x00")
            await client_w.drain()
            return
        atyp = req[3]
        if atyp == 0x01:
            raw = await client_r.readexactly(4)
            host = ".".join(str(b) for b in raw)
        elif atyp == 0x03:
            ln = await client_r.readexactly(1)
            host = (await client_r.readexactly(ln[0])).decode("idna")
        elif atyp == 0x04:
            raw = await client_r.readexactly(16)
            host = ":".join(f"{raw[i]:02x}{raw[i+1]:02x}" for i in range(0, 16, 2))
        else:
            client_w.write(b"\x05\x08\x00\x01\x00\x00\x00\x00\x00\x00")
            await client_w.drain()
            return
        port_b = await client_r.readexactly(2)
        port = int.from_bytes(port_b, "big")

        up_r, up_w = await _http_connect(host, port, proxy_host, proxy_port, user, password)
        client_w.write(b"\x05\x00\x00\x01\x00\x00\x00\x00\x00\x00")
        await client_w.drain()
        await asyncio.gather(_pipe(client_r, up_w), _pipe(up_r, client_w))
    except Exception:
        try:
            client_w.write(b"\x05\x01\x00\x01\x00\x00\x00\x00\x00\x00")
            await client_w.drain()
        except Exception:
            pass
    finally:
        try:
            client_w.close()
        except Exception:
            pass


async def run_bridge(bind_host: str, bind_port: int, proxy_host: str, proxy_port: int,
                     user: str, password: str) -> None:
    server = await asyncio.start_server(
        lambda r, w: _handle(r, w, proxy_host, proxy_port, user, password),
        bind_host, bind_port,
    )
    sockets = server.sockets or []
    port = sockets[0].getsockname()[1] if sockets else bind_port
    sys.stdout.write(f"READY {bind_host}:{port}\n")
    sys.stdout.flush()
    async with server:
        await server.serve_forever()


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--bind-host", default="127.0.0.1")
    p.add_argument("--bind-port", type=int, default=0)
    p.add_argument("--proxy-host", required=True)
    p.add_argument("--proxy-port", type=int, required=True)
    p.add_argument("--proxy-user", default="")
    p.add_argument("--proxy-pass", default="")
    args = p.parse_args()
    try:
        asyncio.run(run_bridge(
            args.bind_host, args.bind_port,
            args.proxy_host, args.proxy_port,
            args.proxy_user, args.proxy_pass,
        ))
        return 0
    except KeyboardInterrupt:
        return 0


if __name__ == "__main__":
    sys.exit(main())
