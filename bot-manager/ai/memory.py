"""Small per-bot decision journal used as feedback in later ChatGPT calls."""

from __future__ import annotations

import json
import uuid
from collections import deque
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent / "memory"


def append(bot_id: str, choice: str, reason: str, outcome: str,
           status: str = "completed") -> str:
    ROOT.mkdir(parents=True, exist_ok=True)
    path = ROOT / f"{bot_id}.jsonl"
    if path.exists() and path.stat().st_size > 256_000:
        with path.open(encoding="utf-8") as source:
            retained = deque(source, maxlen=100)
        path.write_text("".join(retained), encoding="utf-8")
    entry_id = uuid.uuid4().hex[:12]
    with path.open("a", encoding="utf-8") as output:
        output.write(json.dumps({"id": entry_id,
                                 "at": datetime.now().astimezone().isoformat(timespec="seconds"),
                                 "choice": choice, "reason": reason[:160],
                                 "outcome": outcome[:160], "status": status},
                                ensure_ascii=False) + "\n")
    return entry_id


def update(bot_id: str, entry_id: str, outcome: str, status: str = "completed") -> bool:
    """Update one recorded response while preserving its original timestamp and reason."""
    path = ROOT / f"{bot_id}.jsonl"
    if not path.exists():
        return False
    entries = []
    changed = False
    with path.open(encoding="utf-8") as source:
        for line in source:
            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(entry, dict):
                if entry.get("id") == entry_id:
                    entry["outcome"] = outcome[:160]
                    entry["status"] = status
                    changed = True
                entries.append(entry)
    if changed:
        temp = path.with_suffix(".tmp")
        with temp.open("w", encoding="utf-8") as output:
            for entry in entries:
                output.write(json.dumps(entry, ensure_ascii=False) + "\n")
        temp.replace(path)
    return changed


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
