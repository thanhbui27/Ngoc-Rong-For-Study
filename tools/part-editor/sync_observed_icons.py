"""Fill missing BE icon PNGs from server-downloaded assets, without overwriting.

The server 14 selected collection takes priority when both sources have an ID.
The server 15 collection supplies the wider part-image ID range. No images are
inferred from SQL or from the BE's existing item_template rows.
"""

from __future__ import annotations

import argparse
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DESTINATION = ROOT / "Server" / "resources" / "normal" / "image"
PNG_HEADER = b"\x89PNG\r\n\x1a\n"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--server14", type=Path, required=True)
    parser.add_argument("--server15", type=Path, required=True)
    parser.add_argument("--min-id", type=int, default=0)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    for zoom in range(1, 5):
        sources = [
            args.server15 / "image" / f"zoom{zoom}" / "icon",
            args.server14 / "image" / f"zoom{zoom}" / "icon",
        ]
        available = {}
        for folder in sources:
            for path in folder.glob("*.png"):
                if path.stem.isdigit() and int(path.stem) >= args.min_id:
                    available[int(path.stem)] = path
        destination = DESTINATION / str(zoom) / "icon"
        missing = [(image_id, path) for image_id, path in sorted(available.items())
                   if not (destination / f"{image_id}.png").exists()]
        copied = 0
        if args.apply:
            destination.mkdir(parents=True, exist_ok=True)
            for image_id, path in missing:
                if not path.read_bytes().startswith(PNG_HEADER):
                    raise ValueError(f"Not a PNG: {path}")
                try:
                    with (destination / f"{image_id}.png").open("xb") as output, path.open("rb") as source:
                        shutil.copyfileobj(source, output)
                    copied += 1
                except FileExistsError:
                    # Exclusive create keeps old data intact even if another process
                    # created the same file after the dry-run inventory.
                    continue
        print(f"x{zoom}: {len(available)} observed IDs >= {args.min_id}, "
              f"{copied if args.apply else len(missing)} {'copied' if args.apply else 'missing in BE (dry run)'}")


if __name__ == "__main__":
    main()
