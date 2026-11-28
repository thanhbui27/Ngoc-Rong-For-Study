"""Audit BE runtime resources against a local SQL seed, without connecting to a DB."""
from __future__ import annotations

import argparse
import json
import re
import struct
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools/clone-server"))
from sql_seed import rows


def dimensions(path):
    with path.open("rb") as stream:
        header = stream.read(24)
    return struct.unpack(">II", header[16:24]) if len(header) >= 24 and header[:8] == b"\x89PNG\r\n\x1a\n" else (0, 0)


def audit(root=ROOT, seed=None):
    seed = seed or root / "ngocrong-clean.sql"
    tables = {}
    for table, row in rows(seed, {"part", "cai_trang", "mini_pet", "npc_template", "mob_template", "pet_follow", "flag_bag", "img_by_name", "item_template"}):
        tables.setdefault(table, []).append(row)
    issues = []
    def issue(kind, owner, zoom, path, **extra):
        issues.append({"kind": kind, "owner": str(owner), "zoom": zoom,
                       "path": str(path.relative_to(root)).replace("\\", "/"), **extra})
    parts = {}
    for row in tables["part"]:
        try:
            parts[int(row["id"])] = json.loads(row["DATA"])
        except ValueError:
            issue("invalid_part", row["id"], 0, seed)
    for kind in ("cai_trang", "mini_pet", "npc_template"):
        for row in tables[kind]:
            owner = row.get("id_temp", row.get("id"))
            for slot in ("head", "body", "leg"):
                part_id = int(row[slot])
                if part_id < 0:
                    continue
                if part_id not in parts:
                    issue(kind, owner, 0, seed, reason="missing_part", part_id=part_id)
                    continue
                for image_id in {frame[0] for frame in parts[part_id] if frame[0] >= 0}:
                    for zoom in range(1, 5):
                        path = root / f"Server/resources/normal/image/{zoom}/icon/{image_id}.png"
                        if not path.is_file():
                            issue(kind, owner, zoom, path, image_id=image_id, part_id=part_id)
    for zoom in range(1, 5):
        for path in (root / f"Server/Eff/effect/x{zoom}/data").glob("DataEffect_*"):
            asset_id = path.name.removeprefix("DataEffect_")
            image = path.parent.parent / "img" / f"ImgEffect_{asset_id}.png"
            if not image.is_file():
                issue("effect", asset_id, zoom, image, data_path=str(path.relative_to(root)).replace("\\", "/"))
        for row in tables["mob_template"]:
            path = root / f"Server/mob/x{zoom}" / row["id"]
            if not path.is_file():
                issue("mob", row["id"], zoom, path)
        for row in tables["img_by_name"]:
            path = root / f"Server/resources/ThanhBN/img_by_name/x{zoom}" / (row["NAME"] + ".png")
            if not path.is_file():
                issue("named", row["NAME"], zoom, path, frames=int(row["n_frame"]))
        for row in tables["flag_bag"]:
            for image_id in {int(value.strip()) for value in row["icon_data"].split(",") if value.strip()}:
                path = root / f"Server/resources/normal/image/{zoom}/icon/{image_id}.png"
                if not path.is_file():
                    issue("flag", row["id"], zoom, path, image_id=image_id)
        for row in tables["pet_follow"]:
            path = root / f"Server/resources/normal/image/{zoom}/icon" / (row["icon"] + ".png")
            if not path.is_file():
                issue("pet_follow", row["id_temp"], zoom, path, reason="missing", image_id=int(row["icon"]))
            else:
                width, height = dimensions(path)
                required = [int(row["width"]) * zoom, int(row["height"]) * zoom * int(row["frame"])]
                if width < required[0] or height < required[1]:
                    issue("pet_follow", row["id_temp"], zoom, path, reason="undersized", actual=[width, height], required=required, image_id=int(row["icon"]))
    return {"scope": "filesystem and SQL seed, not live DB", "seed": str(seed),
            "table_rows": {table: len(records) for table, records in tables.items()},
            "affected": dict(Counter(kind for kind, owner in {(row["kind"], row["owner"]) for row in issues})),
            "issues": issues}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    report = audit()
    args.out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"affected": report["affected"], "issues": len(report["issues"])}, ensure_ascii=False))


if __name__ == "__main__":
    main()
