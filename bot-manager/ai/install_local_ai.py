"""Install the pinned CPU model and runtime inside bot-manager/ai only."""

from __future__ import annotations

import hashlib
import os
import urllib.request
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent
MODEL = ROOT / "models" / "Qwen3-1.7B-Q4_K_M.gguf"
RUNTIME = ROOT / "runtime" / "llama-server.exe"
MODEL_URL = "https://huggingface.co/ggml-org/Qwen3-1.7B-GGUF/resolve/main/Qwen3-1.7B-Q4_K_M.gguf"
MODEL_SHA256 = "d2387ca2dbfee2ffabce7120d3770dadca0b293052bc2f0e138fdc940d9bc7b5"
RUNTIME_URL = "https://github.com/ggml-org/llama.cpp/releases/download/b12804/llama-b12804-bin-win-cpu-x64.zip"
RUNTIME_SHA256 = "62d49f13f25064246c9df13291f92060d80b490018fcef805899ebc9ef0456b5"


def download(url: str, path: Path, expected_hash: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        existing = hashlib.sha256()
        with path.open("rb") as current:
            while block := current.read(1024 * 1024):
                existing.update(block)
        if existing.hexdigest() == expected_hash:
            print(f"Already verified: {path}", flush=True)
            return
    temporary = path.with_suffix(path.suffix + ".part")
    digest = hashlib.sha256()
    with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "NroBotLocalAI/1.0"}), timeout=60) as source, temporary.open("wb") as output:
        while block := source.read(1024 * 1024):
            output.write(block)
            digest.update(block)
        output.flush()
        os.fsync(output.fileno())
    if digest.hexdigest() != expected_hash:
        raise ValueError(f"SHA-256 mismatch for {url}")
    temporary.replace(path)
    print(f"Installed: {path}", flush=True)


def main() -> None:
    archive = ROOT / "runtime" / "llama-cpu.zip"
    download(RUNTIME_URL, archive, RUNTIME_SHA256)
    with zipfile.ZipFile(archive) as source:
        for member in source.infolist():
            if member.is_dir():
                continue
            target = ROOT / "runtime" / Path(member.filename).name
            if not target.name:
                continue
            with source.open(member) as incoming, target.open("wb") as outgoing:
                while block := incoming.read(1024 * 1024):
                    outgoing.write(block)
    if not RUNTIME.exists():
        raise FileNotFoundError("Archive does not contain llama-server.exe")
    download(MODEL_URL, MODEL, MODEL_SHA256)


if __name__ == "__main__":
    main()
