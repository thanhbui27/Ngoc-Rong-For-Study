"""Cross-check local BE costume mappings against a captured client catalog.

The source is the repository's clean SQL seed, never the remote server. A row
is offered only when item identity and every mapped part frame match the clone.
"""

from __future__ import annotations

import csv
import json
from functools import lru_cache
from pathlib import Path

SEED = Path(__file__).resolve().parents[2] / "ngocrong-clean.sql"


def rows(path: Path):
    table = None
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        if line.startswith("INSERT INTO "):
            table = next((name for name in ("item_template", "cai_trang", "mini_pet", "part")
                          if f"`{name}`" in line), None)
            continue
        if table and line.startswith("("):
            try:
                values = next(csv.reader([line.strip().removesuffix(",").removesuffix(";")[1:-1]],
                                         delimiter=",", quotechar="'", escapechar="\\", skipinitialspace=True))
                yield table, values
            except (ValueError, csv.Error):
                continue


@lru_cache(maxsize=4)
def verified(seed: str, seed_mtime: int, items_file: str, items_mtime: int,
             parts_file: str, parts_mtime: int) -> dict[str, dict[int, dict]]:
    local_items, local_parts, local_costumes, local_pets = {}, {}, {}, {}
    for table, values in rows(Path(seed)):
        try:
            if table == "item_template" and len(values) == 9:
                item_id = int(values[0])
                local_items[item_id] = {"type": int(values[1]), "gender": int(values[2]), "name": values[3],
                                        "icon_id": int(values[5]), "part_id": int(values[6])}
            elif table == "cai_trang" and len(values) >= 4:
                local_costumes[int(values[0])] = {"head": int(values[1]),
                                                   "body": int(values[2]), "leg": int(values[3])}
            elif table == "mini_pet" and len(values) >= 4:
                local_pets[int(values[0])] = {"head": int(values[1]),
                                               "body": int(values[2]), "leg": int(values[3])}
            elif table == "part" and len(values) >= 3:
                local_parts[int(values[0])] = {"type": int(values[1]),
                                               "frames": json.loads(values[2])}
        except (ValueError, IndexError, json.JSONDecodeError):
            continue
    observed_items = json.loads(Path(items_file).read_text(encoding="utf-8"))["items"]
    observed_parts = json.loads(Path(parts_file).read_text(encoding="utf-8"))
    costumes, pets = {}, {}
    def part_matches(mapping: dict) -> bool:
        return all(part_id < 0 or (part_id < len(observed_parts)
                                    and local_parts.get(part_id) == {"type": observed_parts[part_id]["type"],
                                                                     "frames": observed_parts[part_id]["frames"]})
                   for part_id in mapping.values())

    for item in observed_items:
        item_id = item["id"]
        if item["type"] == 5:
            before = local_items.get(item_id)
            mapping = local_costumes.get(item_id)
            if (before and mapping and all(before[key] == item[key] for key in
                                           ("type", "gender", "name", "icon_id", "part_id"))
                    and part_matches(mapping)):
                costumes[item_id] = mapping
        elif item["type"] in (18, 21):
            candidates = []
            for local_id, before in local_items.items():
                if (before["type"] in (18, 21, 27) and before["gender"] == item["gender"]
                        and before["name"] == item["name"] and local_id in local_pets):
                    mapping = local_pets[local_id]
                    if all(value >= 0 for value in mapping.values()) and part_matches(mapping):
                        candidates.append(mapping)
            if len(candidates) == 1:
                pets[item_id] = candidates[0]
    return {"costume": costumes, "mini_pet": pets}


def for_clone(root: Path) -> dict[str, dict[int, dict]]:
    items_file = root / "decoded" / "items.json"
    parts_file = root / "decoded" / "part.json"
    if not (SEED.is_file() and items_file.is_file() and parts_file.is_file()):
        return {"costume": {}, "mini_pet": {}}
    return verified(str(SEED), SEED.stat().st_mtime_ns,
                    str(items_file), items_file.stat().st_mtime_ns,
                    str(parts_file), parts_file.stat().st_mtime_ns)
