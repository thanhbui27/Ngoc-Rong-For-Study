"""Decode item templates and options from captured -28/8 update packets."""

from __future__ import annotations

import json
import struct
from pathlib import Path

from nro_wire import modified_utf


def parse_item(data: bytes, position: int, item_id: int) -> tuple[dict, int]:
    if position + 2 > len(data):
        raise ValueError("Truncated item header")
    kind, gender = struct.unpack_from(">bb", data, position)
    position += 2
    name, position = modified_utf(data, position)
    description, position = modified_utf(data, position)
    if position + 10 > len(data):
        raise ValueError("Truncated item fields")
    level, power, icon, part, upgrade = struct.unpack_from(">bihhB", data, position)
    position += 10
    return {"id": item_id, "type": kind, "gender": gender, "name": name,
            "description": description, "level": level, "power_required": power,
            "icon_id": icon, "part_id": part, "upgradable": bool(upgrade)}, position


def decode_packet(data: bytes) -> tuple[int, int, list[dict], list[dict], list[list[int]]]:
    if len(data) < 5 or data[0] != 8:
        raise ValueError("Not an item update packet")
    version, packet_type = data[1:3]
    position = 3
    items, options, heads = [], [], []
    if packet_type == 0:
        count = struct.unpack_from(">H", data, position)[0]
        position += 2
        # Some servers encode the option count as a single unsigned byte.
        if count > 4096:
            count = data[3]
            position = 4
        for option_id in range(count):
            name, position = modified_utf(data, position)
            if position >= len(data):
                raise ValueError("Truncated item option")
            kind = struct.unpack_from("b", data, position)[0]
            position += 1
            options.append({"id": option_id, "name": name, "type": kind})
    elif packet_type in (1, 2):
        if packet_type == 1:
            count = struct.unpack_from(">h", data, position)[0]
            position += 2
            start, end = 0, count
        else:
            start, end = struct.unpack_from(">hh", data, position)
            position += 4
        if start < 0 or end < start:
            raise ValueError("Invalid item range")
        for item_id in range(start, end):
            item, position = parse_item(data, position, item_id)
            items.append(item)
    elif packet_type == 100:
        count = struct.unpack_from(">h", data, position)[0]
        position += 2
        if count < 0:
            raise ValueError("Invalid alternate head count")
        for _ in range(count):
            size = data[position]
            position += 1
            heads.append(list(struct.unpack_from(">" + "h" * size, data, position)))
            position += size * 2
    else:
        # Custom server extensions remain in raw/updates, with their type listed.
        return version, packet_type, items, options, heads
    if position != len(data):
        raise ValueError(f"Trailing item packet bytes: {len(data) - position}")
    return version, packet_type, items, options, heads


def decode_directory(raw_dir: Path, out: Path) -> dict:
    paths = sorted(raw_dir.glob("sub8-*.bin"))
    items, options, heads, versions, kinds, errors = {}, {}, [], set(), set(), []
    for path in paths:
        try:
            version, kind, packet_items, packet_options, packet_heads = decode_packet(path.read_bytes())
            versions.add(version)
            kinds.add(kind)
            items.update({row["id"]: row for row in packet_items})
            options.update({row["id"]: row for row in packet_options})
            if packet_heads:
                heads = packet_heads
        except (ValueError, struct.error) as error:
            errors.append({"file": path.name, "error": str(error)})
    result = {"source": "live_server_update_packets", "packets": len(paths),
              "versions": sorted(versions), "packet_types": sorted(kinds),
              "items": [items[key] for key in sorted(items)],
              "options": [options[key] for key in sorted(options)],
              "alternate_heads": heads, "errors": errors}
    if paths:
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return {"packets": len(paths), "items": len(items), "options": len(options),
            "alternate_heads": len(heads), "packet_types": sorted(kinds),
            "errors": errors, "path": str(out) if paths else None}
