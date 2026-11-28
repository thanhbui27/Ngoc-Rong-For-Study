"""Client template and sprite decoders shared by capture and preview."""
from __future__ import annotations

import json
import re
from pathlib import Path

from decode_game_data import Reader
from nro_wire import modified_utf


def read_json(path: Path, default=None):
    return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else default


def write_json(path: Path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".partial")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


def text(reader: Reader) -> str:
    value, reader.pos = modified_utf(reader.data, reader.pos)
    return value


def decode_templates(root: Path) -> dict:
    source = root / "raw/updates/sub6-000.bin"
    if not source.is_file():
        return {"status": "missing"}
    r = Reader(source.read_bytes())
    if r.u8() != 6:
        raise ValueError("Not a map template packet")
    version = r.u8()
    maps = [text(r) for _ in range(r.u8())]
    npcs = []
    for index in range(r.small_count("NPC")):
        row = {"id": index, "name": text(r), "head": r.i16(), "body": r.i16(), "leg": r.i16()}
        row["menu"] = [[text(r) for _ in range(r.small_count("menu row"))]
                       for _ in range(r.small_count("menu"))]
        npcs.append(row)
    mobs = [{"id": index, "type": r.i8(), "name": text(r), "hp": r.number("i"),
             "range": r.i8(), "speed": r.i8(), "dart_type": r.i8()}
            for index in range(r.small_count("mob"))]
    r.finish()
    for name, rows in (("map-names", maps), ("npc", npcs), ("mob", mobs)):
        write_json(root / "decoded" / (name + ".json"), rows)
    return {"version": version, "maps": len(maps), "npcs": len(npcs), "mobs": len(mobs)}


def decode_sprite(data: bytes, kind: int = 0) -> dict:
    """Unity EffectData.readData/readMobNew; coordinates are logical x1 pixels."""
    r = Reader(data)
    sprites = []
    for _ in range(r.small_count("sprite")):
        sprites.append({"id": r.i8(), "x": r.u8() if kind in (0, 1) else r.i16(),
                        "y": r.u8() if kind in (0, 1) else r.i16(), "w": r.u8(), "h": r.u8()})
    frames = [[{"dx": r.i16(), "dy": r.i16(), "sprite": r.i8()}
               for _ in range(r.small_count("frame piece"))]
              for _ in range(r.count("sprite frame"))]
    sequence = [r.i16() for _ in range(r.count("animation"))]
    r.finish()
    known = {sprite["id"] for sprite in sprites}
    if any(piece["sprite"] not in known for frame in frames for piece in frame):
        raise ValueError("Frame references an unknown sprite")
    if any(index >= len(frames) for index in sequence if index >= 0):
        raise ValueError("Animation references an unknown frame")
    groups, pending = {}, []
    for index in sequence:
        if index >= 0:
            pending.append(index)
        else:
            groups[str(abs(index + 500))] = pending
            pending = []
    if pending:
        groups.setdefault("0", pending)
    return {"sprites": sprites, "frames": frames, "sequence": sequence, "actions": groups}


def blob(r: Reader) -> bytes:
    return r.take(r.number("i"))


def decode_asset_packet(command: int, payload: bytes) -> tuple[str, str, dict, bytes | None]:
    r = Reader(payload)
    if command == -66:
        asset_id = r.i16()
        data = blob(r)
        kind = r.i8()
        value, png = decode_sprite(data, kind), blob(r)
        value.update(id=asset_id, type=kind)
        # Effect 78 supplies its own named animation arrays after the image.
        if r.pos < len(r.data) and asset_id == 78:
            value["actions"] = {str(i): [r.i16() for _ in range(r.u8())]
                                for i in range(r.small_count("effect action"))}
        category = "dynamic"
    elif command == 11:
        asset_id, kind = r.u8(), r.i8()
        value, png = decode_sprite(blob(r), kind), blob(r)
        value.update(id=asset_id, type=kind, type_data=r.i8())
        if value["type_data"] in (1, 2):
            value["actions"] = {str(i): [r.i8() for _ in range(r.small_count("boss action frame"))]
                                for i in range(r.small_count("boss action"))}
        category = "mob-animation"
    elif command == 66:
        asset_id, frames = text(r), r.u8()
        if not re.fullmatch(r"[\w.-]{1,120}", asset_id, re.ASCII):
            raise ValueError("Unsafe image name")
        value, png, category = {"id": asset_id, "frame_count": frames}, blob(r), "sprite"
    elif command in (-62, -63):
        asset_id = r.u8()
        if command == -63:
            value = {"id": asset_id, "image_ids": [r.i16() for _ in range(r.u8())]}
        else:
            value = {"id": asset_id, "choice_type": r.u8(), "icon_id": r.i16()}
        png, category = None, "flag" if command == -63 else "flag-icon"
    else:
        raise ValueError("Unsupported asset packet")
    r.finish()
    if png is not None and not png.startswith(b"\x89PNG\r\n\x1a\n"):
        raise ValueError("Asset image is not PNG")
    return category, str(asset_id), value, png


def store_asset(root: Path, zoom: int, command: int, payload: bytes) -> tuple[str, str]:
    category, asset_id, value, png = decode_asset_packet(command, payload)
    if png is not None:
        image = root / "assets" / f"zoom{zoom}" / category / (asset_id + ".png")
        image.parent.mkdir(parents=True, exist_ok=True)
        image.write_bytes(png)
    write_json(root / "decoded/animations" / f"zoom{zoom}" / category / (asset_id + ".json"), value)
    return category, asset_id


def decode_saved_assets(root: Path) -> dict:
    commands = {"dynamic": -66, "mob-animation": 11, "sprite": 66, "flag": -63, "flag-icon": -62}
    errors = []
    for zoom in range(1, 5):
        for category, command in commands.items():
            for path in (root / "raw/animations" / f"zoom{zoom}" / category).glob("*.bin"):
                target = root / "decoded/animations" / f"zoom{zoom}" / category / (path.stem + ".json")
                image = root / "assets" / f"zoom{zoom}" / category / (path.stem + ".png")
                if target.is_file() and (category in ("flag", "flag-icon") or image.is_file()):
                    continue
                try:
                    store_asset(root, zoom, command, path.read_bytes())
                except (ValueError, KeyError, IndexError) as error:
                    errors.append({"path": str(path), "error": str(error)})
    return {"errors": errors}
