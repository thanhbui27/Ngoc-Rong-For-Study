"""Minimal read-only NRO client protocol for public resource requests."""

from __future__ import annotations

import socket
import struct
from pathlib import Path, PurePosixPath

BIG_COMMANDS = {-32, -66, -74, 11, -67, -87, 66}
MAX_PACKET = 32 * 1024 * 1024


def read_exact(sock: socket.socket, size: int) -> bytes:
    data = bytearray()
    while len(data) < size:
        part = sock.recv(size - len(data))
        if not part:
            raise ConnectionError("Server closed the connection")
        data.extend(part)
    return bytes(data)


class NroWire:
    def __init__(self, sock: socket.socket):
        self.sock = sock
        self.key: bytes | None = None
        self.read_index = 0
        self.write_index = 0

    def _crypt(self, value: int, writing: bool) -> int:
        if self.key is None:
            return value
        if writing:
            index = self.write_index
            self.write_index = (index + 1) % len(self.key)
        else:
            index = self.read_index
            self.read_index = (index + 1) % len(self.key)
        return value ^ self.key[index]

    def send(self, command: int, payload: bytes = b"") -> None:
        if len(payload) > 65535:
            raise ValueError("Request is too large")
        header = bytes((command & 255, len(payload) >> 8, len(payload) & 255))
        self.sock.sendall(bytes(self._crypt(byte, True) for byte in header + payload))

    def read(self) -> tuple[int, bytes]:
        command = struct.unpack("b", bytes((self._crypt(read_exact(self.sock, 1)[0], False),)))[0]
        if self.key is not None and command in BIG_COMMANDS:
            encoded = [self._crypt(byte, False) for byte in read_exact(self.sock, 3)]
            size = sum((((byte + 128) & 255) << (8 * index)) for index, byte in enumerate(encoded))
        elif self.key is not None:
            encoded = [self._crypt(byte, False) for byte in read_exact(self.sock, 2)]
            size = (encoded[0] << 8) | encoded[1]
        else:
            size = struct.unpack(">H", read_exact(self.sock, 2))[0]
        if size > MAX_PACKET:
            raise ValueError(f"Packet too large: {size}")
        return command, bytes(self._crypt(byte, False) for byte in read_exact(self.sock, size))

    def accept_key(self, payload: bytes) -> tuple[str, int, bool]:
        if not payload:
            raise ValueError("Missing session key")
        length = payload[0]
        if not 1 <= length <= 128 or len(payload) < length + 8:
            raise ValueError("Invalid session key")
        key = bytearray(payload[1:1 + length])
        for index in range(1, length):
            key[index] ^= key[index - 1]
        pos = length + 1
        host_length = struct.unpack_from(">H", payload, pos)[0]
        pos += 2
        if pos + host_length + 5 > len(payload):
            raise ValueError("Truncated session route")
        host = payload[pos:pos + host_length].decode("utf-8", "replace")
        pos += host_length
        port = struct.unpack_from(">i", payload, pos)[0]
        pos += 4
        second = payload[pos] != 0
        self.key = bytes(key)
        self.read_index = self.write_index = 0
        return host, port, second


def modified_utf(data: bytes, pos: int) -> tuple[str, int]:
    if pos + 2 > len(data):
        raise ValueError("Truncated UTF length")
    length = struct.unpack_from(">H", data, pos)[0]
    pos += 2
    if pos + length > len(data):
        raise ValueError("Truncated UTF string")
    return data[pos:pos + length].replace(b"\xc0\x80", b"\0").decode("utf-8", "replace"), pos + length


def safe_relative_path(server_path: str) -> Path:
    normalized = server_path.replace("\\", "/")
    if normalized.startswith("//"):
        raise ValueError(f"Unsafe server path: {server_path!r}")
    if any(part in (".", "..") or ":" in part for part in normalized.split("/")):
        raise ValueError(f"Unsafe server path: {server_path!r}")
    path = PurePosixPath(normalized.lstrip("/"))
    if not path.parts:
        raise ValueError(f"Unsafe server path: {server_path!r}")
    return Path(*path.parts)
