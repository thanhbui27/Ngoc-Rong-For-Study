"""Run a small GGUF model on CPU and request one constrained bot decision."""

from __future__ import annotations

import atexit
import json
import os
import subprocess
import threading
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parent
MODEL = ROOT / "models" / "Qwen3-1.7B-Q4_K_M.gguf"
SERVER = ROOT / "runtime" / "llama-server.exe"
ENDPOINT = "http://127.0.0.1:18766"
EXECUTOR = ThreadPoolExecutor(max_workers=1, thread_name_prefix="NroLocalAI")


class LocalModel:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._process: subprocess.Popen | None = None
        self._idle_timer: threading.Timer | None = None
        atexit.register(self.stop)

    @staticmethod
    def installed() -> bool:
        return SERVER.is_file() and MODEL.is_file()

    def running(self) -> bool:
        process = self._process
        return process is not None and process.poll() is None

    def _health(self) -> bool:
        try:
            with urllib.request.urlopen(ENDPOINT + "/health", timeout=2) as response:
                return response.status == 200
        except (OSError, urllib.error.URLError):
            return False

    def start(self) -> None:
        if not self.installed():
            raise RuntimeError("Chưa cài AI cục bộ; chạy python ai/install_local_ai.py")
        with self._lock:
            if self._idle_timer is not None:
                self._idle_timer.cancel()
                self._idle_timer = None
            if self._health():
                return
            if self._process is None or self._process.poll() is not None:
                log = (ROOT / "local-model.log").open("ab")
                flags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
                self._process = subprocess.Popen(
                    [str(SERVER), "-m", str(MODEL), "--host", "127.0.0.1",
                     "--port", "18766", "-t", "2", "-c", "2048", "-np", "1",
                     "--reasoning", "off", "--no-webui"],
                    cwd=SERVER.parent, stdout=log, stderr=subprocess.STDOUT,
                    creationflags=flags,
                )
                log.close()
            deadline = time.monotonic() + 90
            while time.monotonic() < deadline:
                if self._health():
                    return
                if self._process.poll() is not None:
                    raise RuntimeError("AI cục bộ không khởi động được; xem ai/local-model.log")
                time.sleep(1)
            raise TimeoutError("AI cục bộ khởi động quá 90 giây")

    def decide(self, observation: dict, choices: list[dict]) -> dict:
        self.start()
        allowed = [entry["id"] for entry in choices]
        body = {
            "model": MODEL.name,
            "stream": False,
            "temperature": 0.2,
            "max_tokens": 120,
            "reasoning_effort": "none",
            "chat_template_kwargs": {"enable_thinking": False},
            "messages": [
                {"role": "system", "content": (
                    "Bạn là AI điều khiển một bot thử nghiệm game Ngọc Rồng. "
                    "Chọn đúng một ID hành động có sẵn từ choices dựa trên dữ liệu hiện tại. "
                    "Ưu tiên trang bị và kỹ năng giúp bot sống và gây sát thương tốt hơn, "
                    "tự chọn làm nhiệm vụ hay luyện sức mạnh, chọn hướng cộng chỉ số cho nhân vật. "
                    "Chỉ chuyển sang luyện sức mạnh khi nhiệm vụ khó hoặc cần tăng sức mạnh. "
                    "chỉ mua món đủ tiền và đúng hệ. Không bịa ID. "
                    "Nếu không có lựa chọn rõ ràng, chọn none. Trả JSON ngắn."
                )},
                {"role": "user", "content": json.dumps({"observation": observation,
                                                       "choices": choices}, ensure_ascii=False)},
            ],
            "response_format": {"type": "json_schema", "schema": {
                "type": "object", "properties": {
                    "choice": {"type": "string", "enum": allowed},
                    "reason": {"type": "string"},
                }, "required": ["choice", "reason"], "additionalProperties": False,
            }},
        }
        request = urllib.request.Request(
            ENDPOINT + "/v1/chat/completions",
            data=json.dumps(body, ensure_ascii=False).encode("utf-8"),
            headers={"Content-Type": "application/json"}, method="POST",
        )
        with urllib.request.urlopen(request, timeout=90) as response:
            output = json.load(response)
        decision = json.loads(output["choices"][0]["message"]["content"])
        if decision.get("choice") not in allowed:
            raise ValueError("AI trả hành động ngoài danh sách cho phép")
        with self._lock:
            self._idle_timer = threading.Timer(300, self.stop)
            self._idle_timer.daemon = True
            self._idle_timer.start()
        return decision

    def stop(self) -> None:
        with self._lock:
            if self._idle_timer is not None:
                self._idle_timer.cancel()
                self._idle_timer = None
            if self._process is not None and self._process.poll() is None:
                self._process.terminate()
                try:
                    self._process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    self._process.kill()
            self._process = None


MODEL_CLIENT = LocalModel()
