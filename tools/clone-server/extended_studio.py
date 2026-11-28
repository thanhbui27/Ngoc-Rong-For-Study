"""Catalogs, asset paths and explicit item visual bindings for Clone Studio."""
from pathlib import Path
import re

from extended_data import read_json, write_json

KINDS = ("effect", "dynamic", "npc", "mob", "skill", "dart", "arrow", "flag", "sprite", "resource", "tileset", "reference")


def animation(root, kind, asset_id, zoom):
    category = "mob-animation" if kind == "mob" else kind
    for actual in dict.fromkeys((zoom, 4, 3, 2, 1)):
        path = root / "decoded/animations" / f"zoom{actual}" / category / (str(asset_id) + ".json")
        if path.is_file():
            return {**read_json(path), "zoom": actual,
                    "image_path": f"assets/zoom{actual}/{category}/{asset_id}.png"}
    return None


def catalog(root: Path, kind: str, query="", offset=0):
    if kind not in KINDS or offset < 0:
        raise ValueError("Loại dữ liệu hoặc offset không hợp lệ")
    if kind in ("effect", "npc", "mob", "skill", "dart", "arrow"):
        values = read_json(root / "decoded" / (kind + ".json"), [])
        rows = [{"id": row["id"], "name": row.get("name", kind + " #" + str(row["id"])),
                 "index": row.get("index", row["id"])} for row in values]
    elif kind == "tileset":
        ids = set()
        for path in (root / "resources").rglob("*.png"):
            encoded = re.fullmatch(r"(\d+)\$(\d+)", path.stem)
            if path.parent.name == "t" and encoded:
                ids.add(str((path.parent / encoded[1]).relative_to(root)).replace("\\", "/"))
            elif path.parent.name == "t":
                ids.add(str(path.relative_to(root)).replace("\\", "/"))
            elif path.parent.parent.name == "t":
                ids.add(str(path.parent.relative_to(root)).replace("\\", "/"))
        rows = [{"id": value, "name": value} for value in sorted(ids)]
    elif kind == "resource":
        rows = [{"id": str(path.relative_to(root)).replace("\\", "/"), "name": str(path.relative_to(root))}
                for path in sorted((root / "resources").rglob("*.png"))]
    else:
        ids = set()
        for zoom in range(1, 5):
            ids.update(path.stem for path in (root / "decoded/animations" / f"zoom{zoom}" / kind).glob("*.json"))
        rows = [{"id": value, "name": kind + " #" + value} for value in sorted(ids, key=lambda x: (not x.isdigit(), int(x) if x.isdigit() else x))]
    filtered = [row for row in rows if query.casefold() in (str(row["id"]) + " " + row["name"]).casefold()]
    return {"total": len(rows), "matches": len(filtered), "entries": filtered[offset:offset + 100],
            "has_more": offset + 100 < len(filtered)}


def asset_path(root: Path, relative: str) -> Path:
    path = (root / relative).resolve()
    try:
        parts = path.relative_to(root.resolve()).parts
    except ValueError:
        raise ValueError("Đường dẫn ảnh không hợp lệ")
    if not parts or parts[0] not in ("resources", "assets") or path.suffix.lower() != ".png":
        raise ValueError("Chỉ đọc PNG của bản clone")
    return path


def detail(root: Path, kind: str, asset_id: str, zoom=4):
    if kind not in KINDS or zoom not in range(1, 5):
        raise ValueError("Loại dữ liệu hoặc zoom không hợp lệ")
    if kind == "resource":
        asset_path(root, asset_id)
        actual = next((int(part[-1]) for part in Path(asset_id).parts if re.fullmatch(r"zoom[1-4]", part)), zoom)
        return {"id": asset_id, "kind": kind, "image_path": asset_id, "zoom": actual,
                "frame_count": 1}
    if not re.fullmatch(r"[\w.-]{1,120}", str(asset_id), re.ASCII):
        raise ValueError("ID không hợp lệ")
    result = {"id": asset_id, "kind": kind}
    if kind in ("dynamic", "mob", "flag", "sprite", "reference"):
        result.update(animation(root, kind, asset_id, zoom) or {"missing": True})
    if kind in ("effect", "npc", "mob", "skill", "dart", "arrow"):
        row = next((row for row in read_json(root / "decoded" / (kind + ".json"), [])
                    if str(row["id"]) == str(asset_id)), None)
        if row is None:
            raise ValueError("Không có bản ghi này")
        result.update(row)
    if kind == "skill":
        # Unity accesses GameScr.efs[effectId - 1], not the stored idEf field.
        result["effects"] = read_json(root / "decoded/effect.json", [])
        result["arrows"] = read_json(root / "decoded/arrow.json", [])
        result["darts"] = read_json(root / "decoded/dart.json", [])
    return result


def tileset(root, relative):
    path = (root / relative).resolve()
    if not path.is_relative_to((root / "resources").resolve()):
        raise ValueError("Tileset phải nằm trong resources của bản clone")
    zoom = next((int(part[-1]) for part in path.parts if re.fullmatch(r"zoom[1-4]", part)), 1)
    if path.is_file():
        asset_path(root, relative)
        return {"zoom": zoom, "strip": relative}
    if path.parent.name == "t" and path.name.isdigit():
        files = list(path.parent.glob(path.name + "$*.png"))
        if files:
            return {"zoom": zoom, "tiles": {p.stem.split("$")[1]: str(p.relative_to(root)).replace("\\", "/")
                                             for p in files if p.stem.split("$")[1].isdigit()}}
    if not path.is_dir() or path.parent.name != "t":
        raise ValueError("Không có tileset")
    return {"zoom": zoom, "tiles": {p.stem: str(p.relative_to(root)).replace("\\", "/")
                                     for p in path.glob("*.png") if p.stem.isdigit()}}


def bindings(root: Path, item_id: int):
    return read_json(root / "mappings/item-visuals.json", {}).get(str(item_id), [])


def save_bindings(root: Path, item_id: int, layers):
    items = read_json(root / "decoded/items.json", {}).get("items", [])
    if not any(row["id"] == item_id for row in items) or not isinstance(layers, list) or len(layers) > 8:
        raise ValueError("Item hoặc danh sách lớp không hợp lệ (tối đa 8 lớp)")
    clean = []
    for layer in layers:
        if not isinstance(layer, dict):
            raise ValueError("Lớp phải là một object")
        kind, asset_id = layer.get("kind"), str(layer.get("id", ""))
        if kind not in ("dynamic", "effect", "flag", "sprite", "sheet", "resource", "reference"):
            raise ValueError("Loại lớp không hợp lệ")
        if kind == "resource":
            asset_path(root, asset_id)
        elif not re.fullmatch(r"[\w.-]{1,120}", asset_id, re.ASCII):
            raise ValueError("ID lớp không hợp lệ")
        row = {"kind": kind, "id": asset_id, "dx": int(layer.get("dx", 0)),
               "dy": int(layer.get("dy", 0)), "behind": bool(layer.get("behind", False))}
        if any(abs(row[key]) > 1000 for key in ("dx", "dy")):
            raise ValueError("Tọa độ vượt giới hạn")
        if kind == "sheet":
            row.update(width=int(layer.get("width", 32)), height=int(layer.get("height", 32)),
                       count=int(layer.get("count", 1)))
            if not asset_id.isdigit() or not 0 <= int(asset_id) <= 100000 or not all(1 <= row[key] <= 1024 for key in ("width", "height")) or not 1 <= row["count"] <= 127:
                raise ValueError("Kích thước hoặc số frame sprite không hợp lệ")
            sequence = layer.get("sequence", list(range(row["count"])))
            if not isinstance(sequence, list) or not 1 <= len(sequence) <= 1024 or any(type(index) is not int or not 0 <= index < row["count"] for index in sequence):
                raise ValueError("Dãy frame nằm ngoài sprite sheet")
            row["sequence"] = sequence
        clean.append(row)
    path = root / "mappings/item-visuals.json"
    saved = read_json(path, {})
    saved[str(item_id)] = clean
    write_json(path, saved)
    return clean
