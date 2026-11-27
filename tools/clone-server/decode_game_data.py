"""Decode the six NRO update-data blobs using the Unity client's readers.

The original .bin files are never modified. Unknown or truncated formats fail
closed instead of producing a plausible but incorrect part/image mapping.
"""

from __future__ import annotations

import argparse
import json
import struct
from pathlib import Path

FRAME_COUNTS = {0: 3, 1: 17, 2: 14, 3: 2}
NAMES = ("dart", "arrow", "effect", "image", "part", "skill")


class Reader:
    def __init__(self, data: bytes):
        self.data = data
        self.pos = 0

    def take(self, size: int) -> bytes:
        if size < 0 or self.pos + size > len(self.data):
            raise ValueError(f"Truncated binary at offset {self.pos}, need {size} bytes")
        result = self.data[self.pos:self.pos + size]
        self.pos += size
        return result

    def number(self, fmt: str) -> int:
        return struct.unpack(">" + fmt, self.take(struct.calcsize(fmt)))[0]

    def u8(self) -> int:
        return self.number("B")

    def i8(self) -> int:
        return self.number("b")

    def u16(self) -> int:
        return self.number("H")

    def i16(self) -> int:
        return self.number("h")

    def count(self, label: str, maximum: int = 32767) -> int:
        value = self.i16()
        if value < 0 or value > maximum:
            raise ValueError(f"Invalid {label} count {value} at offset {self.pos - 2}")
        return value

    def small_count(self, label: str) -> int:
        value = self.i8()
        if value < 0:
            raise ValueError(f"Invalid {label} count {value} at offset {self.pos - 1}")
        return value

    def finish(self) -> None:
        if self.pos != len(self.data):
            raise ValueError(f"{len(self.data) - self.pos} trailing bytes at offset {self.pos}")


def decode_part(reader: Reader) -> list[dict]:
    parts = []
    for part_id in range(reader.count("part")):
        kind = reader.i8()
        if kind not in FRAME_COUNTS:
            raise ValueError(f"Unknown part type {kind} at part {part_id}")
        frames = [[reader.i16(), reader.i8(), reader.i8()]
                  for _ in range(FRAME_COUNTS[kind])]
        parts.append({"id": part_id, "type": kind, "frames": frames})
    return parts


def decode_image(reader: Reader) -> list[dict]:
    return [{"id": image_id, "atlas": reader.u8(), "x": reader.i16(),
             "y": reader.i16(), "width": reader.i16(), "height": reader.i16()}
            for image_id in range(reader.count("image"))]


def decode_arrow(reader: Reader) -> list[dict]:
    return [{"index": index, "id": reader.i16(),
             "image_ids": [reader.i16() for _ in range(3)]}
            for index in range(reader.count("arrow"))]


def decode_effect(reader: Reader) -> list[dict]:
    effects = []
    for index in range(reader.count("effect")):
        effect_id = reader.i16()
        frames = [{"image_id": reader.i16(), "dx": reader.i8(), "dy": reader.i8()}
                  for _ in range(reader.small_count("effect frame"))]
        effects.append({"index": index, "id": effect_id, "frames": frames})
    return effects


def short_array(reader: Reader, label: str) -> list[int]:
    return [reader.i16() for _ in range(reader.count(label))]


def decode_dart(reader: Reader) -> list[dict]:
    darts = []
    for index in range(reader.count("dart")):
        dart = {"index": index, "id": reader.i16(), "updates": reader.i16(),
                "speed": reader.i16() * 256, "xd_percent": reader.i16()}
        for name in ("tail", "tail_border", "xd1", "xd2"):
            dart[name] = short_array(reader, name)
        for name in ("head", "head_border"):
            dart[name] = [short_array(reader, name + " row")
                          for _ in range(reader.count(name))]
        darts.append(dart)
    return darts


def skill_frames(reader: Reader, label: str) -> list[dict]:
    frames = []
    for _ in range(reader.small_count(label)):
        frame = {"status": reader.i8()}
        for n in range(3):
            frame[f"effect_{n}"] = reader.i16()
            frame[f"effect_{n}_dx"] = reader.i16()
            frame[f"effect_{n}_dy"] = reader.i16()
        frame["arrow_id"] = reader.i16()
        frame["arrow_dx"] = reader.i16()
        frame["arrow_dy"] = reader.i16()
        frames.append(frame)
    return frames


def decode_skill(reader: Reader) -> list[dict]:
    skills = []
    for index in range(reader.count("skill")):
        skill = {"index": index, "id": reader.i16(),
                 "effect_on_mob": reader.i16(), "effect_count": reader.i8(),
                 "stand": skill_frames(reader, "skill stand"),
                 "fly": skill_frames(reader, "skill fly")}
        skills.append(skill)
    return skills


DECODERS = {"dart": decode_dart, "arrow": decode_arrow, "effect": decode_effect,
            "image": decode_image, "part": decode_part, "skill": decode_skill}


def decode_blob(name: str, data: bytes) -> list[dict]:
    if name not in DECODERS:
        raise ValueError(f"Unknown game-data file: {name}")
    reader = Reader(data)
    records = DECODERS[name](reader)
    reader.finish()
    return records


def decode_directory(data_dir: Path, output_dir: Path) -> dict[str, dict]:
    output_dir.mkdir(parents=True, exist_ok=True)
    report = {}
    for name in NAMES:
        source = data_dir / f"{name}.bin"
        if not source.is_file():
            report[name] = {"status": "missing"}
            continue
        try:
            records = decode_blob(name, source.read_bytes())
            target = output_dir / f"{name}.json"
            target.write_text(json.dumps(records, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            report[name] = {"status": "decoded", "records": len(records), "path": str(target)}
        except (ValueError, struct.error) as error:
            report[name] = {"status": "decode_error", "error": str(error)}
    return report


def referenced_image_ids(decoded_dir: Path) -> set[int]:
    ids = set()
    for name, values in (("part", "frames"), ("effect", "frames")):
        path = decoded_dir / f"{name}.json"
        if path.is_file():
            for record in json.loads(path.read_text(encoding="utf-8")):
                for frame in record[values]:
                    image_id = frame[0] if name == "part" else frame["image_id"]
                    if image_id >= 0:
                        ids.add(image_id)
    for name in ("dart", "arrow"):
        path = decoded_dir / f"{name}.json"
        if not path.is_file():
            continue
        for record in json.loads(path.read_text(encoding="utf-8")):
            values = record["image_ids"] if name == "arrow" else [image
                     for key in ("tail", "tail_border", "xd1", "xd2", "head", "head_border")
                     for group in record[key]
                     for image in (group if isinstance(group, list) else [group])]
            ids.update(value for value in values if value >= 0)
    return ids


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("data_dir", type=Path, help="Directory containing dart.bin ... skill.bin")
    parser.add_argument("--out", type=Path, help="Output directory for decoded JSON")
    args = parser.parse_args()
    destination = args.out or args.data_dir.parent / "decoded"
    report = decode_directory(args.data_dir, destination)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if any(row["status"] == "decode_error" for row in report.values()):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
