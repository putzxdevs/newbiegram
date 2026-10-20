from __future__ import annotations

import asyncio
import http.client
import socket
import ssl
import urllib.request
from typing import Any

from newbiegram.socks import (
    PROXY_TYPE_SOCKS5,
    SOCKS4Error,
    async_create_connection,
    create_connection,
)


def merge_dict[K, V](a: dict[K, V], b: dict[K, V]) -> dict[K, V]:
    """Merge two dictionaries."""
    d = a.copy()
    d.update(b)
    return d


def is_ip(s: str) -> bool:
    """Check if string is a valid IP address."""
    try:
        if ':' in s:
            socket.inet_pton(socket.AF_INET6, s)
        elif '.' in s:
            socket.inet_aton(s)
        else:
            return False
    except OSError:
        return False
    return True


socks4_no_rdns: set[str] = set()


class SocksiPyConnection(http.client.HTTPConnection):
    """HTTP connection through a SOCKS proxy."""

    def __init__(
        self,
        proxytype: int,
        proxyaddr: str,
        proxyport: int | None = None,
        rdns: bool = True,
        username: str | None = None,
        password: str | None = None,
        *args: Any,
        **kwargs: Any
    ) -> None:
        self.proxyargs = (proxytype, proxyaddr, proxyport, rdns, username, password)
        super().__init__(*args, **kwargs)

    def connect(self) -> None:
        proxytype, proxyaddr, proxyport, rdns, username, password = self.proxyargs
        rdns = rdns and proxyaddr not in socks4_no_rdns

        while True:
            try:
                sock = create_connection(
                    (self.host, self.port), self.timeout, None,
                    proxytype, proxyaddr, proxyport, rdns, username, password,
                    [(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)]
                )
                break
            except SOCKS4Error as e:
                if rdns and "0x5b" in str(e) and not is_ip(self.host):
                    rdns = False
                    socks4_no_rdns.add(proxyaddr)
                else:
                    raise
        self.sock = sock


class SocksiPyConnectionS(http.client.HTTPSConnection):
    """HTTPS connection through a SOCKS proxy."""

    def __init__(
        self,
        proxytype: int,
        proxyaddr: str,
        proxyport: int | None = None,
        rdns: bool = True,
        username: str | None = None,
        password: str | None = None,
        *args: Any,
        **kwargs: Any
    ) -> None:
        self.proxyargs = (proxytype, proxyaddr, proxyport, rdns, username, password)
        super().__init__(*args, **kwargs)

    def connect(self) -> None:
        SocksiPyConnection.connect(self)
        self.sock = self._context.wrap_socket(self.sock, server_hostname=self.host)
        if not self._context.check_hostname and self._check_hostname:
            try:
                ssl.match_hostname(self.sock.getpeercert(), self.host)
            except Exception:
                self.sock.shutdown(socket.SHUT_RDWR)
                self.sock.close()
                raise


class SocksiPyHandler(urllib.request.HTTPHandler, urllib.request.HTTPSHandler):
    """urllib handler for SOCKS proxies."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        self.args = args
        self.kw = kwargs
        super().__init__()

    def http_open(self, req: urllib.request.Request) -> http.client.HTTPResponse:
        def build(
            host: str,
            port: int | None = None,
            timeout: float = 0,
            **kwargs: Any
        ) -> SocksiPyConnection:
            kw = merge_dict(self.kw, kwargs)
            return SocksiPyConnection(*self.args, host=host, port=port, timeout=timeout, **kw)
        return self.do_open(build, req)

    def https_open(self, req: urllib.request.Request) -> http.client.HTTPResponse:
        def build(
            host: str,
            port: int | None = None,
            timeout: float = 0,
            **kwargs: Any
        ) -> SocksiPyConnectionS:
            kw = merge_dict(self.kw, kwargs)
            return SocksiPyConnectionS(*self.args, host=host, port=port, timeout=timeout, **kw)
        return self.do_open(build, req)


class AsyncSocksConnector:
    """Async SOCKS connector for use with asyncio."""

    def __init__(
        self,
        proxy_type: int,
        proxy_addr: str,
        proxy_port: int | None = None,
        rdns: bool = True,
        username: str | None = None,
        password: str | None = None
    ) -> None:
        self.proxy_type = proxy_type
        self.proxy_addr = proxy_addr
        self.proxy_port = proxy_port
        self.rdns = rdns
        self.username = username
        self.password = password

    async def connect(
        self,
        host: str,
        port: int,
        timeout: float | None = None
    ) -> tuple[asyncio.StreamReader, asyncio.StreamWriter]:
        """Create an async connection through the SOCKS proxy."""
        return await async_create_connection(
            (host, port),
            timeout=timeout,
            proxy_type=self.proxy_type,
            proxy_addr=self.proxy_addr,
            proxy_port=self.proxy_port,
            proxy_rdns=self.rdns,
            proxy_username=self.username,
            proxy_password=self.password
        )


async def async_fetch(
    url: str,
    proxy_type: int,
    proxy_addr: str,
    proxy_port: int | None = None,
    timeout: float | None = 30.0
) -> bytes:
    """Simple async HTTP GET through a SOCKS proxy."""
    from urllib.parse import urlparse

    parsed = urlparse(url)
    host = parsed.hostname
    port = parsed.port or (443 if parsed.scheme == "https" else 80)
    path = parsed.path or "/"
    if parsed.query:
        path = f"{path}?{parsed.query}"

    reader, writer = await async_create_connection(
        (host, port),
        timeout=timeout,
        proxy_type=proxy_type,
        proxy_addr=proxy_addr,
        proxy_port=proxy_port
    )

    try:
        if parsed.scheme == "https":
            ssl_context = ssl.create_default_context()
            transport = writer.transport
            protocol = writer.transport.get_protocol()

            loop = asyncio.get_event_loop()
            new_transport = await loop.start_tls(
                transport, protocol, ssl_context, server_hostname=host
            )
            writer._transport = new_transport

        request = f"GET {path} HTTP/1.1\r\nHost: {host}\r\nConnection: close\r\n\r\n"
        writer.write(request.encode())
        await writer.drain()

        return await reader.read()
    finally:
        writer.close()
        await writer.wait_closed()


if __name__ == "__main__":
    import sys

    try:
        port = int(sys.argv[1])
    except (ValueError, IndexError):
        port = 9050

    # Sync example
    opener = urllib.request.build_opener(
        SocksiPyHandler(PROXY_TYPE_SOCKS5, "localhost", port)
    )
    print(f"HTTP: {opener.open('http://httpbin.org/ip').read().decode()}")
    print(f"HTTPS: {opener.open('https://httpbin.org/ip').read().decode()}")

    # Async example
    async def async_main() -> None:
        connector = AsyncSocksConnector(PROXY_TYPE_SOCKS5, "localhost", port)
        reader, writer = await connector.connect("httpbin.org", 80)

        writer.write(b"GET /ip HTTP/1.1\r\nHost: httpbin.org\r\nConnection: close\r\n\r\n")
        await writer.drain()

        response = await reader.read()
        print(f"Async HTTP: {response.decode()}")

        writer.close()
        await writer.wait_closed()

    asyncio.run(async_main())
