"""Read-only byte comparison of downloaded images and BE images.

The audit distinguishes tracked BE files (pre-existing) from newly copied
untracked files, and reports duplicate exact PNGs within each zoom level.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BE = ROOT / "Server" / "resources" / "normal"


def digest(path: Path) -> bytes:
    return hashlib.sha256(path.read_bytes()).digest()


def tracked_paths() -> set[str]:
    raw = subprocess.check_output(["git", "ls-files", "-z", "--", "Server/resources/normal"], cwd=ROOT)
    return {path.decode("utf-8").replace("\\", "/") for path in raw.split(b"\0") if path}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--server14", type=Path, required=True)
    parser.add_argument("--server15", type=Path, required=True)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    tracked = tracked_paths()
    report = {"icon": {}, "data": {}}
    for zoom in range(1, 5):
        candidates = {}
        for base in (args.server15, args.server14):
            for path in (base / "image" / f"zoom{zoom}" / "icon").glob("*.png"):
                if path.stem.isdigit():
                    candidates[int(path.stem)] = path
        result = {"source": len(candidates), "tracked_same": 0, "tracked_different": [],
                  "new_same": 0, "new_different": [], "missing": [], "duplicate_groups": []}
        by_hash = defaultdict(list)
        for image_id, source in sorted(candidates.items()):
            relative = f"Server/resources/normal/image/{zoom}/icon/{image_id}.png"
            destination = ROOT / relative
            source_hash = digest(source)
            by_hash[source_hash].append(image_id)
            if not destination.exists():
                result["missing"].append(image_id)
                continue
            prefix = "tracked" if relative in tracked else "new"
            if digest(destination) == source_hash:
                result[prefix + "_same"] += 1
            else:
                result[prefix + "_different"].append(image_id)
        result["duplicate_groups"] = [ids for ids in by_hash.values() if len(ids) > 1]
        report["icon"][str(zoom)] = result
        print(f"Icon x{zoom}: tracked same {result['tracked_same']}, different {len(result['tracked_different'])}; "
              f"new same {result['new_same']}, different {len(result['new_different'])}; "
              f"missing {len(result['missing'])}; exact duplicate groups {len(result['duplicate_groups'])}")
        print("  differing existing IDs sample:", result["tracked_different"][:20])

        source_root = args.server15 / "data" / f"zoom{zoom}"
        files = list(source_root.rglob("*.png"))
        data_result = {"source": len(files), "tracked_same": 0, "tracked_different": [],
                       "new_same": 0, "new_different": [], "missing": []}
        for source in files:
            relative = f"Server/resources/normal/data/{zoom}/{source.relative_to(source_root).as_posix()}"
            destination = ROOT / relative
            if not destination.exists():
                data_result["missing"].append(relative)
                continue
            prefix = "tracked" if relative in tracked else "new"
            if digest(destination) == digest(source):
                data_result[prefix + "_same"] += 1
            else:
                data_result[prefix + "_different"].append(relative)
        report["data"][str(zoom)] = data_result
        print(f"Data x{zoom}: tracked same {data_result['tracked_same']}, different {len(data_result['tracked_different'])}; "
              f"new same {data_result['new_same']}, different {len(data_result['new_different'])}; "
              f"missing {len(data_result['missing'])}")
    if args.out:
        args.out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
