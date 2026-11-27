"""Fill missing normal/data PNGs from the downloaded server asset tree.

The source layout is data/zoomN/<relative path>; the BE layout is
Server/resources/normal/data/N/<relative path>. Existing files are untouched.
"""

from __future__ import annotations

import argparse
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DESTINATION = ROOT / "Server" / "resources" / "normal" / "data"
PNG_HEADER = b"\x89PNG\r\n\x1a\n"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--server15", type=Path, required=True)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    for zoom in range(1, 5):
        source_root = args.server15 / "data" / f"zoom{zoom}"
        target_root = DESTINATION / str(zoom)
        files = sorted(source_root.rglob("*.png"))
        missing = [file for file in files if not (target_root / file.relative_to(source_root)).exists()]
        copied = 0
        if args.apply:
            for file in missing:
                if not file.read_bytes().startswith(PNG_HEADER):
                    raise ValueError(f"Not a PNG: {file}")
                target = target_root / file.relative_to(source_root)
                target.parent.mkdir(parents=True, exist_ok=True)
                try:
                    with target.open("xb") as output, file.open("rb") as source:
                        shutil.copyfileobj(source, output)
                    copied += 1
                except FileExistsError:
                    continue
        print(f"x{zoom}: {len(files)} downloaded data PNGs, "
              f"{copied if args.apply else len(missing)} {'copied' if args.apply else 'missing in BE (dry run)'}")


if __name__ == "__main__":
    main()
