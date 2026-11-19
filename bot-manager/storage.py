"""Local bot configuration storage. Windows secrets are protected by DPAPI."""

from __future__ import annotations

import base64
import ctypes
import json
import os
from ctypes import wintypes
from pathlib import Path


class ConfigStore:
    def __init__(self, path: Path | None = None):
        self.path = path or Path(__file__).resolve().parent / "state" / "bots.dat"

    def load(self) -> list[dict]:
        if not self.path.exists():
            return []
        data = self.path.read_bytes()
        if data.startswith(b"DPAPI1\n"):
            if os.name != "nt":
                raise RuntimeError("Cấu hình bot đã mã hóa bằng Windows DPAPI; cần mở trên cùng tài khoản Windows")
            plain = _dpapi(base64.b64decode(data[7:]), protect=False)
        elif data.startswith(b"PLAIN1\n"):
            plain = data[7:]
        else:
            raise ValueError("Định dạng file lưu bot không hợp lệ")
        document = json.loads(plain)
        if document.get("version") != 1 or not isinstance(document.get("bots"), list):
            raise ValueError("Phiên bản file lưu bot không hợp lệ")
        return document["bots"]

    def save(self, bots: list[dict]) -> None:
        plain = json.dumps({"version": 1, "bots": bots}, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        if os.name == "nt":
            data = b"DPAPI1\n" + base64.b64encode(_dpapi(plain, protect=True))
        else:
            data = b"PLAIN1\n" + plain
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_suffix(".tmp")
        try:
            with os.fdopen(os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600), "wb") as output:
                output.write(data)
                output.flush()
                os.fsync(output.fileno())
            os.replace(temporary, self.path)
        finally:
            temporary.unlink(missing_ok=True)


def _dpapi(data: bytes, protect: bool) -> bytes:
    class Blob(ctypes.Structure):
        _fields_ = [("size", wintypes.DWORD), ("data", ctypes.POINTER(ctypes.c_ubyte))]

    buffer = (ctypes.c_ubyte * len(data)).from_buffer_copy(data)
    source = Blob(len(data), ctypes.cast(buffer, ctypes.POINTER(ctypes.c_ubyte)))
    target = Blob()
    crypt = ctypes.windll.crypt32
    function = crypt.CryptProtectData if protect else crypt.CryptUnprotectData
    function.restype = wintypes.BOOL
    function.argtypes = [ctypes.POINTER(Blob), ctypes.c_void_p, ctypes.c_void_p,
                         ctypes.c_void_p, ctypes.c_void_p, wintypes.DWORD, ctypes.POINTER(Blob)]
    if not function(ctypes.byref(source), None, None, None, None, 1, ctypes.byref(target)):
        raise ctypes.WinError()
    try:
        return ctypes.string_at(target.data, target.size)
    finally:
        local_free = ctypes.windll.kernel32.LocalFree
        local_free.argtypes = [ctypes.c_void_p]
        local_free.restype = ctypes.c_void_p
        local_free(ctypes.cast(target.data, ctypes.c_void_p))
