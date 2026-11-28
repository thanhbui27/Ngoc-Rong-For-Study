"""Read-only catalog views and local costume mapping for Clone Studio."""

from __future__ import annotations

import json
from pathlib import Path

from clone_server import save
from reference_mappings import for_clone
from extended_studio import bindings

TYPES = {0: "Đầu", 1: "Thân", 2: "Chân", 3: "Phụ"}
ITEM_TYPES = {5: "Cải trang", 18: "Mini pet", 21: "Mini pet", 72: "Pet đi theo"}


def read_json(path: Path, default):
    return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else default


def parts(root: Path) -> list[dict]:
    return read_json(root / "decoded" / "part.json", [])


def items(root: Path) -> list[dict]:
    return read_json(root / "decoded" / "items.json", {}).get("items", [])


def mapping_path(root: Path, item_type: int) -> Path:
    return root / "mappings" / ("costume-parts.json" if item_type == 5 else "mini-pet-parts.json")


def mappings(root: Path, item_type: int = 5) -> dict:
    return read_json(mapping_path(root, item_type), {})


def part(root: Path, part_id: int) -> dict:
    records = parts(root)
    if not 0 <= part_id < len(records) or records[part_id]["id"] != part_id:
        raise ValueError(f"Không có part #{part_id}")
    record = dict(records[part_id])
    record["type_name"] = TYPES.get(record["type"], "Khác")
    record["frames"] = [{"index": index, "image_id": frame[0], "dx": frame[1], "dy": frame[2],
                         "available": {str(zoom): (root / "icons" / f"zoom{zoom}" / f"{frame[0]}.png").is_file()
                                       for zoom in range(1, 5)}}
                        for index, frame in enumerate(record["frames"])]
    return record


def costume(root: Path, item_id: int) -> dict:
    matches = [row for row in items(root) if row["id"] == item_id]
    if not matches:
        raise ValueError(f"Không có item #{item_id}")
    item = dict(matches[0])
    records = parts(root)
    kind = item["type"]
    item["category"] = ITEM_TYPES.get(kind, "Item khác")
    item["mapping"] = mappings(root, kind).get(str(item_id)) if kind in (5, 18, 21) else None
    references = for_clone(root)
    item["reference_mapping"] = references["costume" if kind == 5 else "mini_pet"].get(item_id) if kind in (5, 18, 21) else None
    item["reference_kind"] = "cai_trang" if kind == 5 else "mini_pet" if kind in (18, 21) else None
    candidate = item.get("part_id", -1)
    item["template_part"] = None
    if 0 <= candidate < len(records):
        item["template_part"] = {"id": candidate, "type": records[candidate]["type"],
                                 "type_name": TYPES.get(records[candidate]["type"], "Khác")}
    item["suggested"] = None
    item["visual_layers"] = bindings(root, item_id)
    if kind in (0, 1) and item["template_part"] and item["template_part"]["type"] == (1 if kind == 0 else 2):
        item["equipment_parts"] = {"head": 0, "body": candidate if kind == 0 else 1,
                                   "leg": candidate if kind == 1 else 2}
    if kind in (23, 24) and candidate >= 0 and str(item_id) not in read_json(root / "mappings/item-visuals.json", {}):
        item["visual_layers"] = [{"kind": "sprite", "id": f"mount_{candidate}_0", "dx": 0, "dy": 0, "behind": True},
                                 {"kind": "sprite", "id": f"mount_{candidate}_1", "dx": 0, "dy": 0, "behind": False}]
    if kind in (11, 23, 24) and item["visual_layers"]:
        item["equipment_parts"] = {"head": 0, "body": 1, "leg": 2}
    if 0 <= candidate and candidate + 2 < len(records) and [records[candidate + i]["type"] for i in range(3)] == [0, 1, 2]:
        item["suggested"] = {"head": candidate, "body": candidate + 1, "leg": candidate + 2}
    return item


def save_mapping(root: Path, item_id: int, selected: dict) -> dict:
    item = costume(root, item_id)
    if item["type"] not in (5, 18, 21):
        raise ValueError("Loại item này không dùng mapping đầu/thân/chân")
    records = parts(root)
    clean = {}
    for key, kind in (("head", 0), ("body", 1), ("leg", 2)):
        raw = selected.get(key)
        if raw in (None, "", -1, "-1"):
            clean[key] = -1
            continue
        value = int(raw)
        if not 0 <= value < len(records) or records[value]["type"] != kind:
            raise ValueError(f"Part {key} #{value} không tồn tại hoặc sai loại")
        clean[key] = value
    data = mappings(root, item["type"])
    data[str(item_id)] = clean
    save(mapping_path(root, item["type"]),
         (json.dumps(data, ensure_ascii=False, indent=2) + "\n").encode("utf-8"))
    return clean


def catalog(root: Path, kind: str, query: str = "", limit: int = 100, offset: int = 0,
            category: str = "featured") -> dict:
    query = query.strip().casefold()
    if offset < 0:
        raise ValueError("Offset không hợp lệ")
    if kind == "part":
        source = parts(root)
        filtered = [row for row in source if not query or query in str(row["id"]) or query in TYPES.get(row["type"], "").casefold()]
        entries = [{"id": row["id"], "type": row["type"], "type_name": TYPES.get(row["type"], "Khác"),
                    "frames": len(row["frames"]), "images": len({frame[0] for frame in row["frames"] if frame[0] >= 0})}
                   for row in filtered[offset:offset + limit]]
    elif kind == "sets":
        records = parts(root)
        source = [{"id": index, "head": index, "body": index + 1, "leg": index + 2}
                  for index in range(len(records) - 2)
                  if [records[index + shift]["type"] for shift in range(3)] == [0, 1, 2]]
        filtered = [row for row in source if not query or query in str(row["id"])]
        entries = filtered[offset:offset + limit]
    elif kind in ("costume", "visual"):
        all_items = items(root)
        if kind == "costume" or category == "costume":
            source = [row for row in all_items if row["type"] == 5]
        elif category == "mini":
            source = [row for row in all_items if row["type"] in (18, 21)]
        elif category == "follow":
            source = [row for row in all_items if row["type"] == 72]
        elif category == "all":
            source = all_items
        elif category == "equipment":
            source = [row for row in all_items if row["type"] in (0, 1)]
        elif category == "mount":
            source = [row for row in all_items if row["type"] in (23, 24)]
        elif category == "flag":
            source = [row for row in all_items if row["type"] == 11]
        elif category == "featured":
            source = [row for row in all_items if row["type"] in ITEM_TYPES]
        else:
            raise ValueError("Bộ lọc item không hợp lệ")
        filtered = [row for row in source if not query or query in str(row["id"]) or query in row["name"].casefold()]
        costume_mapped = mappings(root, 5)
        pet_mapped = mappings(root, 18)
        references = for_clone(root)
        entries = [{"id": row["id"], "name": row["name"], "type": row["type"],
                    "category": ITEM_TYPES.get(row["type"], "Item khác"),
                    "icon_id": row["icon_id"], "part_id": row["part_id"],
                    "mapped": str(row["id"]) in (costume_mapped if row["type"] == 5 else pet_mapped),
                    "reference": row["id"] in references["costume" if row["type"] == 5 else "mini_pet"]}
                   for row in filtered[offset:offset + limit]]
    elif kind == "map":
        names = read_json(root / "decoded" / "map-names.json", [])
        filtered = [(index, name) for index, name in enumerate(names) if not query or query in str(index) or query in name.casefold()]
        entries = [{"id": index, "name": name, "has_tiles": (root / "raw" / "maps" / f"{index:03}.bin").is_file()}
                   for index, name in filtered[offset:offset + limit]]
    else:
        raise ValueError("Danh mục không hợp lệ")
    return {"total": len(source) if kind != "map" else len(names), "matches": len(filtered),
            "offset": offset, "entries": entries, "has_more": offset + len(entries) < len(filtered)}


def map_detail(root: Path, map_id: int) -> dict:
    names = read_json(root / "decoded" / "map-names.json", [])
    if not 0 <= map_id < len(names):
        raise ValueError(f"Không có map #{map_id}")
    path = root / "raw" / "maps" / f"{map_id:03}.bin"
    result = {"id": map_id, "name": names[map_id], "has_tiles": path.is_file(),
              "tileset": read_json(root / "mappings/map-tilesets.json", {}).get(str(map_id), "")}
    if path.is_file():
        data = path.read_bytes()
        if len(data) < 3 or data[0] != 10:
            result["error"] = "Gói tile không đúng action 10"
        else:
            width, height = data[1], data[2]
            size = width * height
            if size <= 0 or len(data) < 3 + size:
                result["error"] = "Gói tile thiếu dữ liệu"
            else:
                tiles = list(data[3:3 + size])
                result.update(width=width, height=height, tiles=tiles,
                              unique_tiles=len(set(tiles)), trailing_bytes=len(data) - 3 - size)
    return result
