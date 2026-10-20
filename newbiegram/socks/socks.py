from __future__ import annotations

import asyncio
import functools
import logging
import socket
import struct
from base64 import b64encode
from collections.abc import Callable
from errno import EAGAIN, EINVAL, EOPNOTSUPP
from io import BytesIO
from os import SEEK_CUR
from typing import Any

__version__ = "2.0.0"

log = logging.getLogger(__name__)

PROXY_TYPE_SOCKS4 = SOCKS4 = 1
PROXY_TYPE_SOCKS5 = SOCKS5 = 2
PROXY_TYPE_HTTP = HTTP = 3

PROXY_TYPES = {"SOCKS4": SOCKS4, "SOCKS5": SOCKS5, "HTTP": HTTP}
PRINTABLE_PROXY_TYPES = dict(zip(PROXY_TYPES.values(), PROXY_TYPES.keys()))

DEFAULT_PORTS = {SOCKS4: 1080, SOCKS5: 1080, HTTP: 8080}

_orig_socket = socket.socket

type ProxyConfig = tuple[int | None, str | None, int | None, bool, bytes | None, bytes | None]
type AddressPair = tuple[str, int]


def set_self_blocking[F: Callable[..., Any]](function: F) -> F:
    @functools.wraps(function)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        self = args[0]
        _is_blocking: float | None = None
        try:
            _is_blocking = self.gettimeout()
            if _is_blocking == 0:
                self.setblocking(True)
            return function(*args, **kwargs)
        finally:
            if _is_blocking == 0:
                self.setblocking(False)
    return wrapper  # type: ignore


class ProxyError(IOError):
    def __init__(self, msg: str, socket_err: Exception | None = None) -> None:
        self.msg = msg
        self.socket_err = socket_err
        if socket_err:
            self.msg += f": {socket_err}"

    def __str__(self) -> str:
        return self.msg


class GeneralProxyError(ProxyError):
    pass


class ProxyConnectionError(ProxyError):
    pass


class SOCKS5AuthError(ProxyError):
    pass


class SOCKS5Error(ProxyError):
    pass


class SOCKS4Error(ProxyError):
    pass


class HTTPError(ProxyError):
    pass


SOCKS4_ERRORS = {
    0x5B: "Request rejected or failed",
    0x5C: "Request rejected because SOCKS server cannot connect to identd on the client",
    0x5D: "Request rejected because the client program and identd report different user-ids"
}

SOCKS5_ERRORS = {
    0x01: "General SOCKS server failure",
    0x02: "Connection not allowed by ruleset",
    0x03: "Network unreachable",
    0x04: "Host unreachable",
    0x05: "Connection refused",
    0x06: "TTL expired",
    0x07: "Command not supported, or protocol error",
    0x08: "Address type not supported"
}


def set_default_proxy(
    proxy_type: int | None = None,
    addr: str | None = None,
    port: int | None = None,
    rdns: bool = True,
    username: str | None = None,
    password: str | None = None
) -> None:
    socksocket.default_proxy = (
        proxy_type, addr, port, rdns,
        username.encode() if username else None,
        password.encode() if password else None
    )


def setdefaultproxy(*args: Any, **kwargs: Any) -> None:
    if "proxytype" in kwargs:
        kwargs["proxy_type"] = kwargs.pop("proxytype")
    return set_default_proxy(*args, **kwargs)


def get_default_proxy() -> ProxyConfig:
    return socksocket.default_proxy


getdefaultproxy = get_default_proxy


def wrap_module(module: Any) -> None:
    if socksocket.default_proxy[0] is not None and socksocket.default_proxy[1] is not None:
        module.socket.socket = socksocket
    else:
        raise GeneralProxyError("No default proxy specified")


wrapmodule = wrap_module


def create_connection(
    dest_pair: AddressPair,
    timeout: float | None = None,
    source_address: AddressPair | None = None,
    proxy_type: int | None = None,
    proxy_addr: str | None = None,
    proxy_port: int | None = None,
    proxy_rdns: bool = True,
    proxy_username: str | None = None,
    proxy_password: str | None = None,
    socket_options: list[tuple[int, int, int]] | None = None
) -> socksocket:
    remote_host, remote_port = dest_pair
    if remote_host.startswith("["):
        remote_host = remote_host.strip("[]")

    if proxy_type is None:
        sock = socksocket(socket.AF_INET, socket.SOCK_STREAM)
        if socket_options:
            for opt in socket_options:
                sock.setsockopt(*opt)
        if isinstance(timeout, (int, float)):
            sock.settimeout(timeout)
        if source_address:
            sock.bind(source_address)
        sock.connect((remote_host, remote_port))
        return sock

    if proxy_addr and proxy_addr.startswith("["):
        proxy_addr = proxy_addr.strip("[]")

    proxy_port = proxy_port or DEFAULT_PORTS.get(proxy_type)
    if not proxy_addr or not proxy_port:
        raise GeneralProxyError("Proxy address and port are required")

    err: Exception | None = None

    for r in socket.getaddrinfo(proxy_addr, proxy_port, 0, socket.SOCK_STREAM):
        family, socket_type, proto, canonname, sa = r
        sock = None
        try:
            sock = socksocket(family, socket_type, proto)

            if socket_options:
                for opt in socket_options:
                    sock.setsockopt(*opt)

            if isinstance(timeout, (int, float)):
                sock.settimeout(timeout)

            sock.set_proxy(proxy_type, sa[0], sa[1], proxy_rdns,
                           proxy_username, proxy_password)
            if source_address:
                sock.bind(source_address)

            sock.connect((remote_host, remote_port))
            return sock

        except (OSError, ProxyError) as e:
            err = e
            if sock:
                sock.close()
                sock = None

    if err:
        raise err

    raise OSError("gai returned empty list.")


async def async_create_connection(
    dest_pair: AddressPair,
    timeout: float | None = None,
    source_address: AddressPair | None = None,
    proxy_type: int | None = None,
    proxy_addr: str | None = None,
    proxy_port: int | None = None,
    proxy_rdns: bool = True,
    proxy_username: str | None = None,
    proxy_password: str | None = None,
) -> tuple[asyncio.StreamReader, asyncio.StreamWriter]:
    remote_host, remote_port = dest_pair
    if remote_host.startswith("["):
        remote_host = remote_host.strip("[]")

    if proxy_type is None:
        reader, writer = await asyncio.wait_for(
            asyncio.open_connection(remote_host, remote_port),
            timeout=timeout
        )
        return reader, writer

    if proxy_addr and proxy_addr.startswith("["):
        proxy_addr = proxy_addr.strip("[]")

    proxy_port = proxy_port or DEFAULT_PORTS.get(proxy_type)
    if not proxy_addr or not proxy_port:
        raise GeneralProxyError("Proxy address and port are required")

    reader, writer = await asyncio.wait_for(
        asyncio.open_connection(proxy_addr, proxy_port),
        timeout=timeout
    )

    try:
        if proxy_type == SOCKS5:
            await _async_negotiate_socks5(
                reader, writer, remote_host, remote_port, proxy_rdns,
                proxy_username.encode() if proxy_username else None,
                proxy_password.encode() if proxy_password else None
            )
        elif proxy_type == SOCKS4:
            await _async_negotiate_socks4(
                reader, writer, remote_host, remote_port, proxy_rdns,
                proxy_username.encode() if proxy_username else None
            )
        elif proxy_type == HTTP:
            await _async_negotiate_http(
                reader, writer, remote_host, remote_port, proxy_rdns,
                proxy_username.encode() if proxy_username else None,
                proxy_password.encode() if proxy_password else None
            )
        else:
            raise GeneralProxyError("Invalid proxy type")

        return reader, writer
    except Exception:
        writer.close()
        await writer.wait_closed()
        raise


async def _async_readall(reader: asyncio.StreamReader, count: int) -> bytes:
    try:
        data = await reader.readexactly(count)
    except asyncio.IncompleteReadError as e:
        raise GeneralProxyError("Connection closed unexpectedly") from e
    return data


async def _async_negotiate_socks5(
    reader: asyncio.StreamReader,
    writer: asyncio.StreamWriter,
    dest_addr: str,
    dest_port: int,
    rdns: bool,
    username: bytes | None,
    password: bytes | None
) -> tuple[AddressPair, AddressPair]:
    if username and password:
        writer.write(b"\x05\x02\x00\x02")
    else:
        writer.write(b"\x05\x01\x00")
    await writer.drain()

    chosen_auth = await _async_readall(reader, 2)

    if chosen_auth[0:1] != b"\x05":
        raise GeneralProxyError("SOCKS5 proxy server sent invalid data")

    if chosen_auth[1:2] == b"\x02":
        if not (username and password):
            raise SOCKS5AuthError("No username/password supplied. Server requested authentication")

        writer.write(
            b"\x01" + bytes([len(username)]) + username +
            bytes([len(password)]) + password
        )
        await writer.drain()

        auth_status = await _async_readall(reader, 2)
        if auth_status[0:1] != b"\x01":
            raise GeneralProxyError("SOCKS5 proxy server sent invalid data")
        if auth_status[1:2] != b"\x00":
            raise SOCKS5AuthError("SOCKS5 authentication failed")
    elif chosen_auth[1:2] == b"\xFF":
        raise SOCKS5AuthError("All offered SOCKS5 authentication methods were rejected")
    elif chosen_auth[1:2] != b"\x00":
        raise GeneralProxyError("SOCKS5 proxy server sent invalid data")

    request = BytesIO()
    request.write(b"\x05\x01\x00")
    resolved = await _async_write_socks5_address((dest_addr, dest_port), request, rdns)
    writer.write(request.getvalue())
    await writer.drain()

    resp = await _async_readall(reader, 3)
    if resp[0:1] != b"\x05":
        raise GeneralProxyError("SOCKS5 proxy server sent invalid data")

    status = resp[1]
    if status != 0x00:
        error = SOCKS5_ERRORS.get(status, "Unknown error")
        raise SOCKS5Error(f"{status:#04x}: {error}")

    bnd = await _async_read_socks5_address(reader)
    return resolved, bnd


async def _async_write_socks5_address(
    addr: AddressPair,
    file: BytesIO,
    rdns: bool = True
) -> AddressPair:
    host, port = addr
    family_to_byte = {socket.AF_INET: b"\x01", socket.AF_INET6: b"\x04"}

    for family in (socket.AF_INET, socket.AF_INET6):
        try:
            addr_bytes = socket.inet_pton(family, host)
            file.write(family_to_byte[family] + addr_bytes)
            host = socket.inet_ntop(family, addr_bytes)
            file.write(struct.pack(">H", port))
            return host, port
        except OSError:
            continue

    if rdns:
        host_bytes = host.encode("idna")
        file.write(b"\x03" + bytes([len(host_bytes)]) + host_bytes)
    else:
        loop = asyncio.get_running_loop()
        addresses = await loop.getaddrinfo(
            host, port, family=socket.AF_UNSPEC, type=socket.SOCK_STREAM,
            proto=socket.IPPROTO_TCP, flags=socket.AI_ADDRCONFIG
        )
        target_addr = addresses[0]
        family = target_addr[0]
        host = target_addr[4][0]
        addr_bytes = socket.inet_pton(family, host)
        file.write(family_to_byte[family] + addr_bytes)
        host = socket.inet_ntop(family, addr_bytes)

    file.write(struct.pack(">H", port))
    return host, port


async def _async_read_socks5_address(reader: asyncio.StreamReader) -> AddressPair:
    atyp = await _async_readall(reader, 1)
    if atyp == b"\x01":
        addr = socket.inet_ntoa(await _async_readall(reader, 4))
    elif atyp == b"\x03":
        length = await _async_readall(reader, 1)
        addr = (await _async_readall(reader, length[0])).decode("idna")
    elif atyp == b"\x04":
        addr = socket.inet_ntop(socket.AF_INET6, await _async_readall(reader, 16))
    else:
        raise GeneralProxyError("SOCKS5 proxy server sent invalid data")

    port = struct.unpack(">H", await _async_readall(reader, 2))[0]
    return addr, port


async def _async_negotiate_socks4(
    reader: asyncio.StreamReader,
    writer: asyncio.StreamWriter,
    dest_addr: str,
    dest_port: int,
    rdns: bool,
    username: bytes | None
) -> tuple[AddressPair, AddressPair]:
    remote_resolve = False
    try:
        addr_bytes = socket.inet_aton(dest_addr)
    except OSError:
        if rdns:
            addr_bytes = b"\x00\x00\x00\x01"
            remote_resolve = True
        else:
            loop = asyncio.get_running_loop()
            infos = await loop.getaddrinfo(dest_addr, dest_port, proto=socket.IPPROTO_TCP)
            addr_bytes = socket.inet_aton(infos[0][4][0])

    writer.write(struct.pack(">BBH", 0x04, 0x01, dest_port))
    writer.write(addr_bytes)
    if username:
        writer.write(username)
    writer.write(b"\x00")

    if remote_resolve:
        writer.write(dest_addr.encode("idna") + b"\x00")
    await writer.drain()

    resp = await _async_readall(reader, 8)
    if resp[0:1] != b"\x00":
        raise GeneralProxyError("SOCKS4 proxy server sent invalid data")

    status = resp[1]
    if status != 0x5A:
        error = SOCKS4_ERRORS.get(status, "Unknown error")
        raise SOCKS4Error(f"{status:#04x}: {error}")

    proxy_sockname = (
        socket.inet_ntoa(resp[4:]),
        struct.unpack(">H", resp[2:4])[0]
    )
    if remote_resolve:
        proxy_peername = (dest_addr, dest_port)
    else:
        proxy_peername = (dest_addr, dest_port)

    return proxy_sockname, proxy_peername


async def _async_negotiate_http(
    reader: asyncio.StreamReader,
    writer: asyncio.StreamWriter,
    dest_addr: str,
    dest_port: int,
    rdns: bool,
    username: bytes | None,
    password: bytes | None
) -> None:
    if rdns:
        addr = dest_addr
    else:
        loop = asyncio.get_running_loop()
        infos = await loop.getaddrinfo(dest_addr, dest_port, proto=socket.IPPROTO_TCP)
        addr = infos[0][4][0]

    http_headers = [
        f"CONNECT {addr}:{dest_port} HTTP/1.1".encode(),
        f"Host: {dest_addr}:{dest_port}".encode()
    ]

    if username and password:
        http_headers.append(b"Proxy-Authorization: basic " + b64encode(username + b":" + password))

    http_headers.append(b"\r\n")
    writer.write(b"\r\n".join(http_headers))
    await writer.drain()

    status_line = await reader.readline()
    if not status_line:
        raise GeneralProxyError("Connection closed unexpectedly")

    while True:
        line = await reader.readline()
        if line in (b"\r\n", b"\n", b""):
            break

    status_line = status_line.decode()
    try:
        proto, status_code, status_msg = status_line.split(" ", 2)
    except ValueError:
        raise GeneralProxyError("HTTP proxy server sent invalid response")

    if not proto.startswith("HTTP/"):
        raise GeneralProxyError("Proxy server does not appear to be an HTTP proxy")

    try:
        status_code = int(status_code)
    except ValueError:
        raise HTTPError("HTTP proxy server did not return a valid HTTP status")

    if status_code != 200:
        error = f"{status_code}: {status_msg}"
        if status_code in (400, 403, 405):
            error += "\n[*] Note: The HTTP proxy server may not support CONNECT tunneling"
        raise HTTPError(error)


def _write_socks5_address(
    addr: AddressPair,
    file: BytesIO,
    rdns: bool = True
) -> AddressPair:
    host, port = addr
    family_to_byte = {socket.AF_INET: b"\x01", socket.AF_INET6: b"\x04"}

    for family in (socket.AF_INET, socket.AF_INET6):
        try:
            addr_bytes = socket.inet_pton(family, host)
            file.write(family_to_byte[family] + addr_bytes)
            host = socket.inet_ntop(family, addr_bytes)
            file.write(struct.pack(">H", port))
            return host, port
        except OSError:
            continue

    if rdns:
        host_bytes = host.encode("idna")
        file.write(b"\x03" + bytes([len(host_bytes)]) + host_bytes)
    else:
        addresses = socket.getaddrinfo(
            host, port, socket.AF_UNSPEC, socket.SOCK_STREAM,
            socket.IPPROTO_TCP, socket.AI_ADDRCONFIG
        )
        target_addr = addresses[0]
        family = target_addr[0]
        host = target_addr[4][0]
        addr_bytes = socket.inet_pton(family, host)
        file.write(family_to_byte[family] + addr_bytes)
        host = socket.inet_ntop(family, addr_bytes)

    file.write(struct.pack(">H", port))
    return host, port


class socksocket(socket.socket):
    default_proxy: ProxyConfig = (None, None, None, True, None, None)

    def __init__(
        self,
        family: int = socket.AF_INET,
        type: int = socket.SOCK_STREAM,
        proto: int = 0,
        *args: Any,
        **kwargs: Any
    ) -> None:
        if type not in (socket.SOCK_STREAM, socket.SOCK_DGRAM):
            raise ValueError(f"Socket type must be stream or datagram, not {type!r}")

        super().__init__(family, type, proto, *args, **kwargs)
        self._proxyconn: socket.socket | None = None

        if self.default_proxy[0] is not None:
            self.proxy: ProxyConfig = self.default_proxy
        else:
            self.proxy = (None, None, None, True, None, None)
        self.proxy_sockname: AddressPair | None = None
        self.proxy_peername: AddressPair | None = None
        self._timeout: float | None = None

    def _readall(self, file: Any, count: int) -> bytes:
        data = b""
        while len(data) < count:
            d = file.read(count - len(data))
            if not d:
                raise GeneralProxyError("Connection closed unexpectedly")
            data += d
        return data

    def settimeout(self, timeout: float | None) -> None:
        self._timeout = timeout
        try:
            self.get_proxy_peername()
            super().settimeout(self._timeout)
        except OSError:
            pass

    def gettimeout(self) -> float | None:
        return self._timeout

    def setblocking(self, v: bool) -> None:
        if v:
            self.settimeout(None)
        else:
            self.settimeout(0.0)

    def set_proxy(
        self,
        proxy_type: int | None = None,
        addr: str | None = None,
        port: int | None = None,
        rdns: bool = True,
        username: str | None = None,
        password: str | None = None
    ) -> None:
        self.proxy = (
            proxy_type, addr, port, rdns,
            username.encode() if username else None,
            password.encode() if password else None
        )

    def setproxy(self, *args: Any, **kwargs: Any) -> None:
        if "proxytype" in kwargs:
            kwargs["proxy_type"] = kwargs.pop("proxytype")
        return self.set_proxy(*args, **kwargs)

    def bind(self, *pos: Any, **kw: Any) -> None:
        proxy_type, proxy_addr, proxy_port, rdns, username, password = self.proxy
        if not proxy_type or self.type != socket.SOCK_DGRAM:
            return _orig_socket.bind(self, *pos, **kw)

        if self._proxyconn:
            raise OSError(EINVAL, "Socket already bound to an address")
        if proxy_type != SOCKS5:
            raise OSError(EOPNOTSUPP, "UDP only supported by SOCKS5 proxy type")

        super().bind(*pos, **kw)

        _, port = self.getsockname()
        dst = ("0", port)

        self._proxyconn = _orig_socket()
        proxy = self._proxy_addr()
        self._proxyconn.connect(proxy)

        UDP_ASSOCIATE = b"\x03"
        _, relay = self._SOCKS5_request(self._proxyconn, UDP_ASSOCIATE, dst)

        relay_host, relay_port = relay
        if relay_host in ("0.0.0.0", "::"):
            relay_host = proxy[0]
        super().connect((relay_host, relay_port))
        super().settimeout(self._timeout)
        self.proxy_sockname = ("0.0.0.0", 0)

    def sendto(self, data: bytes, *args: Any, **kwargs: Any) -> int:
        if self.type != socket.SOCK_DGRAM:
            return super().sendto(data, *args, **kwargs)
        if not self._proxyconn:
            self.bind(("", 0))

        address = args[-1]
        flags = args[:-1]

        header = BytesIO()
        RSV = b"\x00\x00"
        header.write(RSV)
        STANDALONE = b"\x00"
        header.write(STANDALONE)
        self._write_SOCKS5_address(address, header)

        sent = super().send(header.getvalue() + data, *flags, **kwargs)
        return sent - header.tell()

    def send(self, data: bytes, flags: int = 0, **kwargs: Any) -> int:
        if self.type == socket.SOCK_DGRAM:
            return self.sendto(data, flags, self.proxy_peername, **kwargs)
        return super().send(data, flags, **kwargs)

    def recvfrom(self, bufsize: int, flags: int = 0) -> tuple[bytes, AddressPair]:
        if self.type != socket.SOCK_DGRAM:
            return super().recvfrom(bufsize, flags)
        if not self._proxyconn:
            self.bind(("", 0))

        buf = BytesIO(super().recv(bufsize + 1024, flags))
        buf.seek(2, SEEK_CUR)
        frag = buf.read(1)
        if frag and frag[0] != 0:
            raise NotImplementedError("Received UDP packet fragment")
        fromhost, fromport = self._read_SOCKS5_address(buf)

        if self.proxy_peername:
            peerhost, peerport = self.proxy_peername
            if fromhost != peerhost or peerport not in (0, fromport):
                raise OSError(EAGAIN, "Packet filtered")

        return buf.read(), (fromhost, fromport)

    def recv(self, *pos: Any, **kw: Any) -> bytes:
        bytes_data, _ = self.recvfrom(*pos, **kw)
        return bytes_data

    def close(self) -> None:
        if self._proxyconn:
            self._proxyconn.close()
        return super().close()

    def get_proxy_sockname(self) -> AddressPair | None:
        return self.proxy_sockname

    getproxysockname = get_proxy_sockname

    def get_proxy_peername(self) -> AddressPair | None:
        return super().getpeername()

    getproxypeername = get_proxy_peername

    def get_peername(self) -> AddressPair | None:
        return self.proxy_peername

    getpeername = get_peername

    def _negotiate_SOCKS5(self, *dest_addr: Any) -> None:
        CONNECT = b"\x01"
        self.proxy_peername, self.proxy_sockname = self._SOCKS5_request(
            self, CONNECT, dest_addr
        )

    def _SOCKS5_request(
        self,
        conn: socket.socket,
        cmd: bytes,
        dst: tuple[Any, ...]
    ) -> tuple[AddressPair, AddressPair]:
        proxy_type, addr, port, rdns, username, password = self.proxy

        writer = conn.makefile("wb")
        reader = conn.makefile("rb", 0)
        try:
            if username and password:
                writer.write(b"\x05\x02\x00\x02")
            else:
                writer.write(b"\x05\x01\x00")

            writer.flush()
            chosen_auth = self._readall(reader, 2)

            if chosen_auth[0:1] != b"\x05":
                raise GeneralProxyError("SOCKS5 proxy server sent invalid data")

            if chosen_auth[1:2] == b"\x02":
                if not (username and password):
                    raise SOCKS5AuthError(
                        "No username/password supplied. Server requested authentication"
                    )

                writer.write(
                    b"\x01" + bytes([len(username)]) + username +
                    bytes([len(password)]) + password
                )
                writer.flush()
                auth_status = self._readall(reader, 2)
                if auth_status[0:1] != b"\x01":
                    raise GeneralProxyError("SOCKS5 proxy server sent invalid data")
                if auth_status[1:2] != b"\x00":
                    raise SOCKS5AuthError("SOCKS5 authentication failed")

            elif chosen_auth[1:2] != b"\x00":
                if chosen_auth[1:2] == b"\xFF":
                    raise SOCKS5AuthError(
                        "All offered SOCKS5 authentication methods were rejected"
                    )
                raise GeneralProxyError("SOCKS5 proxy server sent invalid data")

            writer.write(b"\x05" + cmd + b"\x00")
            resolved = self._write_SOCKS5_address(dst, writer)
            writer.flush()

            resp = self._readall(reader, 3)
            if resp[0:1] != b"\x05":
                raise GeneralProxyError("SOCKS5 proxy server sent invalid data")

            status = resp[1]
            if status != 0x00:
                error = SOCKS5_ERRORS.get(status, "Unknown error")
                raise SOCKS5Error(f"{status:#04x}: {error}")

            bnd = self._read_SOCKS5_address(reader)
            super().settimeout(self._timeout)
            return resolved, bnd
        finally:
            reader.close()
            writer.close()

    def _write_SOCKS5_address(self, addr: tuple[Any, ...], file: Any) -> AddressPair:
        host, port = addr
        _, _, _, rdns, _, _ = self.proxy
        family_to_byte = {socket.AF_INET: b"\x01", socket.AF_INET6: b"\x04"}

        for family in (socket.AF_INET, socket.AF_INET6):
            try:
                addr_bytes = socket.inet_pton(family, host)
                file.write(family_to_byte[family] + addr_bytes)
                host = socket.inet_ntop(family, addr_bytes)
                file.write(struct.pack(">H", port))
                return host, port
            except OSError:
                continue

        if rdns:
            host_bytes = host.encode("idna")
            file.write(b"\x03" + bytes([len(host_bytes)]) + host_bytes)
        else:
            addresses = socket.getaddrinfo(
                host, port, socket.AF_UNSPEC, socket.SOCK_STREAM,
                socket.IPPROTO_TCP, socket.AI_ADDRCONFIG
            )
            target_addr = addresses[0]
            family = target_addr[0]
            host = target_addr[4][0]
            addr_bytes = socket.inet_pton(family, host)
            file.write(family_to_byte[family] + addr_bytes)
            host = socket.inet_ntop(family, addr_bytes)

        file.write(struct.pack(">H", port))
        return host, port

    def _read_SOCKS5_address(self, file: Any) -> AddressPair:
        atyp = self._readall(file, 1)
        if atyp == b"\x01":
            addr = socket.inet_ntoa(self._readall(file, 4))
        elif atyp == b"\x03":
            length = self._readall(file, 1)
            addr = self._readall(file, length[0]).decode("idna")
        elif atyp == b"\x04":
            addr = socket.inet_ntop(socket.AF_INET6, self._readall(file, 16))
        else:
            raise GeneralProxyError("SOCKS5 proxy server sent invalid data")

        port = struct.unpack(">H", self._readall(file, 2))[0]
        return addr, port

    def _negotiate_SOCKS4(self, dest_addr: str, dest_port: int) -> None:
        _, _, _, rdns, username, _ = self.proxy

        writer = self.makefile("wb")
        reader = self.makefile("rb", 0)
        try:
            remote_resolve = False
            try:
                addr_bytes = socket.inet_aton(dest_addr)
            except OSError:
                if rdns:
                    addr_bytes = b"\x00\x00\x00\x01"
                    remote_resolve = True
                else:
                    addr_bytes = socket.inet_aton(socket.gethostbyname(dest_addr))

            writer.write(struct.pack(">BBH", 0x04, 0x01, dest_port))
            writer.write(addr_bytes)

            if username:
                writer.write(username)
            writer.write(b"\x00")

            if remote_resolve:
                writer.write(dest_addr.encode("idna") + b"\x00")
            writer.flush()

            resp = self._readall(reader, 8)
            if resp[0:1] != b"\x00":
                raise GeneralProxyError("SOCKS4 proxy server sent invalid data")

            status = resp[1]
            if status != 0x5A:
                error = SOCKS4_ERRORS.get(status, "Unknown error")
                raise SOCKS4Error(f"{status:#04x}: {error}")

            self.proxy_sockname = (
                socket.inet_ntoa(resp[4:]),
                struct.unpack(">H", resp[2:4])[0]
            )
            if remote_resolve:
                self.proxy_peername = (dest_addr, dest_port)
            else:
                self.proxy_peername = (dest_addr, dest_port)
        finally:
            reader.close()
            writer.close()

    def _negotiate_HTTP(self, dest_addr: str, dest_port: int) -> None:
        _, _, _, rdns, username, password = self.proxy

        addr = dest_addr if rdns else socket.gethostbyname(dest_addr)

        http_headers = [
            f"CONNECT {addr}:{dest_port} HTTP/1.1".encode(),
            f"Host: {dest_addr}:{dest_port}".encode()
        ]

        if username and password:
            http_headers.append(
                b"Proxy-Authorization: basic " + b64encode(username + b":" + password)
            )

        http_headers.append(b"\r\n")
        self.sendall(b"\r\n".join(http_headers))

        fobj = self.makefile()
        try:
            status_line = fobj.readline()

            while True:
                line = fobj.readline()
                if line in ("\r\n", "\n", ""):
                    break
        finally:
            fobj.close()

        if not status_line:
            raise GeneralProxyError("Connection closed unexpectedly")

        try:
            proto, status_code, status_msg = status_line.split(" ", 2)
        except ValueError:
            raise GeneralProxyError("HTTP proxy server sent invalid response")

        if not proto.startswith("HTTP/"):
            raise GeneralProxyError("Proxy server does not appear to be an HTTP proxy")

        try:
            status_code = int(status_code)
        except ValueError:
            raise HTTPError("HTTP proxy server did not return a valid HTTP status")

        if status_code != 200:
            error = f"{status_code}: {status_msg}"
            if status_code in (400, 403, 405):
                error += "\n[*] Note: The HTTP proxy server may not support CONNECT tunneling"
            raise HTTPError(error)

        self.proxy_sockname = ("0.0.0.0", 0)
        self.proxy_peername = (addr, dest_port)

    _proxy_negotiators = {
        SOCKS4: _negotiate_SOCKS4,
        SOCKS5: _negotiate_SOCKS5,
        HTTP: _negotiate_HTTP
    }

    @set_self_blocking
    def connect(self, dest_pair: AddressPair, catch_errors: bool | None = None) -> None:
        if not isinstance(dest_pair, (list, tuple)) or len(dest_pair) != 2:
            raise GeneralProxyError("Invalid destination-connection (host, port) pair")

        dest_addr, dest_port = dest_pair

        if dest_addr.startswith("["):
            raise OSError(f"PySocks doesn't support IPv6: {dest_pair}")

        if self.type == socket.SOCK_DGRAM:
            if not self._proxyconn:
                self.bind(("", 0))
            dest_addr = socket.gethostbyname(dest_addr)

            if dest_addr == "0.0.0.0" and not dest_port:
                self.proxy_peername = None
            else:
                self.proxy_peername = (dest_addr, dest_port)
            return

        proxy_type, proxy_addr, proxy_port, rdns, username, password = self.proxy

        if not dest_addr or not isinstance(dest_port, int):
            raise GeneralProxyError("Invalid destination-connection (host, port) pair")

        super().settimeout(self._timeout)

        if proxy_type is None:
            self.proxy_peername = dest_pair
            super().connect((dest_addr, dest_port))
            return

        proxy_addr = self._proxy_addr()

        try:
            super().connect(proxy_addr)
        except OSError as error:
            self.close()
            if not catch_errors:
                proxy_server = f"{proxy_addr[0]}:{proxy_addr[1]}"
                printable_type = PRINTABLE_PROXY_TYPES[proxy_type]
                msg = f"Error connecting to {printable_type} proxy {proxy_server}"
                log.debug("%s due to: %s", msg, error)
                raise ProxyConnectionError(msg, error)
            raise error
        else:
            try:
                negotiate = self._proxy_negotiators[proxy_type]
                negotiate(self, dest_addr, dest_port)
            except OSError as error:
                if not catch_errors:
                    self.close()
                    raise GeneralProxyError("Socket error", error)
                raise error
            except ProxyError:
                self.close()
                raise

    def connect_ex(self, dest_pair: AddressPair) -> int:
        try:
            self.connect(dest_pair, catch_errors=True)
            return 0
        except OSError as e:
            if e.errno:
                return e.errno
            raise

    def _proxy_addr(self) -> AddressPair:
        proxy_type, proxy_addr, proxy_port, rdns, username, password = self.proxy
        proxy_port = proxy_port or DEFAULT_PORTS.get(proxy_type)
        if not proxy_port:
            raise GeneralProxyError("Invalid proxy type")
        if not proxy_addr:
            raise GeneralProxyError("Proxy address not set")
        return proxy_addr, proxy_port
