"""Import an explicitly selected BE resource folder as separately labelled assets."""
import shutil
import csv
from pathlib import Path

from extended_data import read_json, write_json


def import_assets(root: Path, source: Path) -> dict:
    source = source.expanduser().resolve()
    if not (source / "effect_data").is_dir() and not (source / "monster_data").is_dir():
        raise ValueError("Chọn thư mục resource có effect_data hoặc monster_data")
    counts, errors = {"dynamic": 0, "mob": 0, "sprite": 0, "flag": 0, "pet": 0}, []
    names = read_json(source / "ibn.json", [])
    named_frames = {row["filename"]: row["number_frame"] for row in names}
    seed = source.parents[2] / "ngocrong-clean.sql"
    flags, pets = [], []
    if seed.is_file():
        table = None
        for line in seed.read_text(encoding="utf-8-sig").splitlines():
            if line.startswith("INSERT INTO "):
                table = next((name for name in ("flag_bag", "pet_follow", "img_by_name") if f"`{name}`" in line), None)
            elif table and line.startswith("("):
                values = next(csv.reader([line.strip().rstrip(",;")[1:-1]], delimiter=",", quotechar="'", escapechar="\\", skipinitialspace=True))
                if table == "img_by_name":
                    named_frames[values[1]] = int(values[2])
                else:
                    (flags if table == "flag_bag" else pets).append(values)
    for zoom in range(1, 5):
        output = root / "decoded/animations" / f"zoom{zoom}" / "reference"
        images = source / "image" / str(zoom)
        for kind, data_folder, image_folder in (("dynamic", "effect_data", "effect"), ("mob", "monster_data", "monster")):
            for path in (source / data_folder).glob("*.json"):
                try:
                    value = read_json(path)
                    asset_id = int(value["id"])
                    image = images / image_folder / f"{asset_id}.png"
                    if not image.is_file():
                        continue
                    sprites = [{key: int(sprite[key]) for key in ("id", "x", "y", "w", "h")}
                               for sprite in value["sprites"]]
                    frames = [[{"dx": int(piece["dx"]), "dy": int(piece["dy"]), "sprite": int(piece["sprite_id"])}
                               for piece in frame] for frame in value["frames"]]
                    known = {sprite["id"] for sprite in sprites}
                    if any(piece["sprite"] not in known for frame in frames for piece in frame):
                        raise ValueError("Unknown sprite reference")
                    sequence = value["animations"]
                    if any(index >= len(frames) for index in sequence if index >= 0):
                        raise ValueError("Unknown animation frame")
                    result = {"sprites": sprites, "frames": frames, "sequence": sequence, "render_kind": kind}
                    key = f"{kind}-{asset_id}"
                    target = root / "assets" / f"zoom{zoom}" / "reference" / (key + ".png")
                    target.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copyfile(image, target)
                    result.update(id=key, source_id=asset_id, source=str(source), source_kind="local-reference")
                    write_json(output / (key + ".json"), result)
                    counts[kind] += 1
                except (OSError, ValueError, KeyError, TypeError) as error:
                    errors.append({"path": str(path), "error": str(error)})
        for name, frame_count in named_frames.items():
            if not isinstance(name, str) or any(char not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_.-" for char in name):
                continue
            image = images / "imgbyname" / (name + ".png")
            if not image.is_file():
                image = source.parent / "ThanhBN/img_by_name" / f"x{zoom}" / (name + ".png")
            if not image.is_file():
                continue
            key = "sprite-" + name
            target = root / "assets" / f"zoom{zoom}" / "reference" / (key + ".png")
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(image, target)
            write_json(output / (key + ".json"), {"id": key, "render_kind": "sprite", "frame_count": frame_count,
                                                   "source": str(image.parent), "source_kind": "local-reference"})
            counts["sprite"] += 1
        for row in flags:
            key, paths = "flag-" + str(int(row[0])), []
            image_ids = [int(value.strip()) for value in row[1].split(",") if value.strip()]
            if not image_ids or any(not (images / "icon" / f"{image_id}.png").is_file() for image_id in image_ids):
                continue
            for index, image_id in enumerate(image_ids):
                target = root / "assets" / f"zoom{zoom}" / "reference" / f"{key}-{index}.png"
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(images / "icon" / f"{image_id}.png", target)
                paths.append(str(target.relative_to(root)).replace("\\", "/"))
            write_json(output / (key + ".json"), {"id": key, "name": row[2], "render_kind": "flag", "frame_paths": paths,
                                                   "source": str(seed), "source_kind": "local-reference"})
            counts["flag"] += 1
        for row in pets:
            item_id, image_id, width, height, count = map(int, row[:5])
            image = images / "icon" / f"{image_id}.png"
            if not image.is_file() or min(width, height, count) <= 0:
                continue
            key = f"pet-{item_id}"
            target = root / "assets" / f"zoom{zoom}" / "reference" / (key + ".png")
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(image, target)
            write_json(output / (key + ".json"), {"id": key, "render_kind": "sheet", "width": width, "height": height,
                                                   "count": count, "source": str(seed), "source_kind": "local-reference"})
            counts["pet"] += 1
    return {"files": counts, "errors": errors, "source": str(source)}
