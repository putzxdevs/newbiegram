from __future__ import annotations

import asyncio
import logging
import socket
from typing import TypedDict

from newbiegram import socks

log = logging.getLogger(__name__)


class Proxy(TypedDict):
    scheme: str
    hostname: str
    port: int
    username: str | None
    password: str | None


class TCP:
    TIMEOUT = 10

    def __init__(self, ipv6: bool, proxy: Proxy | None = None) -> None:
        self.reader: asyncio.StreamReader | None = None
        self.writer: asyncio.StreamWriter | None = None
        self.lock = asyncio.Lock()
        self.proxy = proxy
        self.ipv6 = ipv6

    async def connect(self, address: tuple[str, int]) -> None:
        if self.proxy:
            hostname = self.proxy.get("hostname")
            scheme = self.proxy.get("scheme", "socks5").upper()
            port = self.proxy.get("port")
            username = self.proxy.get("username")
            password = self.proxy.get("password")

            log.info("Using proxy %s", hostname)

            self.reader, self.writer = await asyncio.wait_for(
                socks.async_create_connection(
                    dest_pair=address,
                    timeout=TCP.TIMEOUT,
                    proxy_type=getattr(socks, scheme),
                    proxy_addr=hostname,
                    proxy_port=port,
                    proxy_username=username,
                    proxy_password=password,
                ),
                timeout=TCP.TIMEOUT,
            )
        else:
            try:
                self.reader, self.writer = await asyncio.wait_for(
                    asyncio.open_connection(
                        host=address[0],
                        port=address[1],
                        family=socket.AF_INET6 if self.ipv6 else socket.AF_INET,
                    ),
                    timeout=TCP.TIMEOUT,
                )
            except TimeoutError:
                raise TimeoutError("Connection timed out") from None

    async def close(self) -> None:
        try:
            if self.writer is not None:
                self.writer.close()
                await asyncio.wait_for(self.writer.wait_closed(), TCP.TIMEOUT)
        except Exception as e:
            log.info("Close exception: %s %s", type(e).__name__, e)

    async def send(self, data: bytes) -> None:
        async with self.lock:
            if self.writer is None:
                raise OSError("Not connected")
            try:
                self.writer.write(data)
                await self.writer.drain()
            except Exception as e:
                log.info("Send exception: %s %s", type(e).__name__, e)
                raise OSError(e) from e

    async def recv(self, length: int) -> bytes | None:
        if self.reader is None:
            return None

        data = b""
        while len(data) < length:
            try:
                chunk = await asyncio.wait_for(
                    self.reader.read(length - len(data)),
                    TCP.TIMEOUT,
                )
            except (TimeoutError, OSError):
                return None

            if not chunk:
                return None
            data += chunk

        return data
