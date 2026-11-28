"""Link captured costumes to parts when their identity and frames are known."""

from __future__ import annotations

import hashlib
import json
from collections import defaultdict
from pathlib import Path

from clone_server import save
from reference_mappings import for_clone

HERE = Path(__file__).resolve().parent
REFERENCE = HERE / "known-costume-parts.json"
KEYS = ("head", "body", "leg")


def fingerprint(part: dict) -> str:
    data = json.dumps([part["type"], part["frames"]], separators=(",", ":"))
    return hashlib.sha256(data.encode("utf-8")).hexdigest()[:32]


def known_mapping(item: dict, references: list[dict]) -> dict | None:
    identity = (item["type"], item["gender"], item["name"], item["icon_id"])
    candidates = [row for row in references if
                  (row["type"], row["gender"], row["name"], row["icon_id"]) == identity]
    if not candidates:
        candidates = [row for row in references if
                      (row["type"], row["gender"], row["name"]) == identity[:3]
                      and all(row[key] for key in KEYS)]
    exact = [row for row in candidates if row["id"] == item["id"]]
    if exact:
        candidates = exact
    # Duplicate item names are common. A shared identity is safe only when
    # all matching rows describe the same three source part signatures.
    signatures = {tuple((row[key][1] if row[key] else None) for key in KEYS)
                  for row in candidates}
    return candidates[0] if len(signatures) == 1 else None


def resolve(reference: dict, candidates: dict[str, list[int]], template_head: int) -> dict:
    options = {}
    for key in KEYS:
        source = reference[key]
        options[key] = [] if source is None else candidates.get(source[1], [])
    if reference["head"] and template_head in options["head"]:
        options["head"] = [template_head]
    # A common ID shift is useful only after the actual frame signatures match.
    offsets = {target - reference[key][0]
               for key in KEYS if reference[key]
               for target in options[key]}
    coherent = [offset for offset in offsets if all(
        reference[key] is None or reference[key][0] + offset in options[key]
        for key in KEYS)]
    if len(coherent) == 1:
        offset = coherent[0]
        return {key: reference[key][0] + offset if reference[key] else -1
                for key in KEYS}
    return {key: options[key][0] if len(options[key]) == 1 else -1
            for key in KEYS}


def link(root: Path) -> dict:
    """Add proven mappings to a clone; never replace a saved mapping."""
    items_file = root / "decoded" / "items.json"
    parts_file = root / "decoded" / "part.json"
    if not (items_file.is_file() and parts_file.is_file()):
        return {"costume": 0, "mini_pet": 0, "skipped": "missing decoded items or parts"}
    items = json.loads(items_file.read_text(encoding="utf-8"))["items"]
    parts = json.loads(parts_file.read_text(encoding="utf-8"))
    references = json.loads(REFERENCE.read_text(encoding="utf-8"))
    candidates = defaultdict(list)
    for part in parts:
        candidates[fingerprint(part)].append(part["id"])
    verified = for_clone(root)
    counts = {"costume": 0, "mini_pet": 0}
    for kind, types, filename in (("costume", (5,), "costume-parts.json"),
                                  ("mini_pet", (18, 21), "mini-pet-parts.json")):
        path = root / "mappings" / filename
        saved = json.loads(path.read_text(encoding="utf-8")) if path.is_file() else {}
        for item in items:
            if item["type"] not in types or str(item["id"]) in saved:
                continue
            mapping = None
            reference = known_mapping(item, references)
            if reference:
                mapping = resolve(reference, candidates, item["part_id"])
                if reference["icon_id"] != item["icon_id"] and any(
                    mapping[key] < 0 for key in KEYS
                ):
                    mapping = None
            if mapping is None or all(mapping[key] < 0 for key in KEYS):
                mapping = verified[kind].get(item["id"])
            if mapping is None and kind == "costume":
                head = item["part_id"]
                if 0 <= head < len(parts) and parts[head]["type"] == 0:
                    mapping = {"head": head, "body": -1, "leg": -1}
            if mapping and any(mapping[key] >= 0 for key in KEYS):
                saved[str(item["id"])] = {key: mapping[key] for key in KEYS}
                counts[kind] += 1
        if counts[kind]:
            save(path, (json.dumps(saved, ensure_ascii=False, indent=2) + "\n").encode("utf-8"))
    return counts
