"""Small per-bot decision journal used as feedback in later ChatGPT calls."""

from __future__ import annotations

import json
from collections import deque
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent / "memory"


def append(bot_id: str, choice: str, reason: str, outcome: str) -> None:
    ROOT.mkdir(parents=True, exist_ok=True)
    path = ROOT / f"{bot_id}.jsonl"
    if path.exists() and path.stat().st_size > 256_000:
        with path.open(encoding="utf-8") as source:
            retained = deque(source, maxlen=100)
        path.write_text("".join(retained), encoding="utf-8")
    with path.open("a", encoding="utf-8") as output:
        output.write(json.dumps({"at": datetime.now().astimezone().isoformat(timespec="seconds"),
                                 "choice": choice, "reason": reason[:160],
                                 "outcome": outcome[:160]}, ensure_ascii=False) + "\n")


def recent(bot_id: str, limit: int = 5) -> list[dict]:
    path = ROOT / f"{bot_id}.jsonl"
    if not path.exists():
        return []
    with path.open(encoding="utf-8") as source:
        lines = deque(source, maxlen=limit)
    result = []
    for line in lines:
        try:
            entry = json.loads(line)
            if isinstance(entry, dict):
                result.append(entry)
        except json.JSONDecodeError:
            continue
    return result
