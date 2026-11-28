"""Bounded, resumable requests for client effects, monsters, flags and named images."""
from __future__ import annotations

import json
import struct
import re
import time
from pathlib import Path

from extended_data import decode_templates, read_json, store_asset

COMMANDS = {"dynamic": -66, "mob-animation": 11, "flag": -63, "flag-icon": -62, "sprite": 66}


def candidates(root: Path, effect_range: range, names: list[str]) -> dict:
    items = read_json(root / "decoded/items.json", {}).get("items", [])
    named = {name for name in names if isinstance(name, str) and re.fullmatch(r"[\w.-]{1,120}", name, re.ASCII)}
    for item in items:
        if item["type"] in (23, 24) and item["part_id"] >= 0:
            named.update(f"mount_{item['part_id']}_{layer}" for layer in (0, 1))
    return {"dynamic": list(effect_range),
            "mob-animation": [row["id"] for row in read_json(root / "decoded/mob.json", [])],
            "flag": list(range(128)), "flag-icon": list(range(128)), "sprite": sorted(named)}


def capture(root: Path, host: str, port: int, zoom: int, version: str, timeout: float,
            effect_range: range, names: list[str]) -> dict:
    from clone_server import connect, get_icons, save
    try:
        template_result = decode_templates(root)
    except (OSError, ValueError, IndexError) as error:
        template_result = {"error": str(error)}
    groups = candidates(root, effect_range, names)
    report = {"templates": template_result}
    for category, ids in groups.items():
        command = COMMANDS[category]
        target = root / "decoded/animations" / f"zoom{zoom}" / category
        existing = [value for value in ids if (target / f"{value}.json").is_file()
                    and (category in ("flag", "flag-icon") or
                         (root / "assets" / f"zoom{zoom}" / category / f"{value}.png").is_file())]
        todo = [value for value in ids if value not in existing]
        received, errors = set(), []
        connect_failures = 0
        for start in range(0, len(todo), 24):
            batch = todo[start:start + 24]
            sock = None
            stage = "connect"
            try:
                sock, wire, _ = connect(host, port, zoom, version, timeout, require_resources=False)
                stage = "receive"
                connect_failures = 0
                sock.settimeout(min(timeout, 3))
                for asset_id in batch:
                    if command == 66:
                        encoded = str(asset_id).encode("utf-8")
                        payload = struct.pack(">H", len(encoded)) + encoded
                    else:
                        payload = struct.pack(">h" if command == -66 else ">B", asset_id)
                    wire.send(command, payload)
                deadline = time.monotonic() + min(timeout, 5)
                waiting = {str(value) for value in batch}
                while waiting and time.monotonic() < deadline:
                    reply_command, payload = wire.read()
                    if reply_command != command:
                        continue
                    # Save original packet even if its variant is not yet understood.
                    if command == 66:
                        from nro_wire import modified_utf
                        reply_id, _ = modified_utf(payload, 0)
                    else:
                        reply_id = str(struct.unpack_from(">h" if command == -66 else ">B", payload)[0])
                    if reply_id not in waiting:
                        continue
                    safe_id = reply_id if command != 66 else str(batch[[str(x) for x in batch].index(reply_id)])
                    save(root / "raw/animations" / f"zoom{zoom}" / category / (safe_id + ".bin"), payload)
                    try:
                        _, saved_id = store_asset(root, zoom, command, payload)
                        received.add(saved_id)
                    except (ValueError, KeyError, IndexError, struct.error) as error:
                        errors.append({"id": reply_id, "error": str(error)})
                    waiting.discard(reply_id)
            except (OSError, ValueError, ConnectionError, struct.error) as error:
                errors.append({"batch": start, "stage": stage, "error": str(error)})
                if stage == "connect":
                    connect_failures += 1
            finally:
                if sock is not None:
                    sock.close()
            print(f"  extra x{zoom} {category}: {start + len(batch)}/{len(todo)}; saved {len(received)}", flush=True)
            if connect_failures >= 3:
                break
        report[category] = {"requested": len(ids), "existing": len(existing), "saved": len(received),
                            "missing": [value for value in todo if str(value) not in received], "errors": errors}
    # Flag frame IDs are not included in update-data, so request their icon PNGs too.
    flag_images = set()
    for path in (root / "decoded/animations" / f"zoom{zoom}" / "flag").glob("*.json"):
        flag_images.update(value for value in read_json(path, {}).get("image_ids", []) if value >= 0)
    for path in (root / "decoded/animations" / f"zoom{zoom}" / "flag-icon").glob("*.json"):
        image_id = read_json(path, {}).get("icon_id", -1)
        if image_id >= 0:
            flag_images.add(image_id)
    if flag_images:
        report["flag_images"] = get_icons(host, port, root, zoom, version, timeout, sorted(flag_images), 24)
    return report


def default_names() -> list[str]:
    # Names are discovery candidates, never mappings imported from another server.
    names = {f"{prefix}_{index}_{layer}" for prefix, stop in (("mount", 40), ("aura", 24), ("set_eff", 16))
             for index in range(stop) for layer in (0, 1)}
    seed = Path(__file__).resolve().parents[2] / "Server/resources/normal/ibn.json"
    for row in read_json(seed, []):
        names.add(row["filename"])
    return sorted(names)
