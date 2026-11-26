"""Compare BE item templates with item templates observed in a live client session.

Usage: python tools/part-editor/compare_observed_items.py path/to/items-from-client.json
This reads the clean SQL seed; it does not change a database or game assets.
"""

from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from pathlib import Path

SEED = Path(__file__).resolve().parents[2] / "ngocrong-clean.sql"
FIELDS = ("id", "type", "gender", "name", "description", "icon_id", "part_id", "upgradable", "power_required")


def seed_items(path: Path) -> dict[int, dict]:
    rows = {}
    inside = False
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        if line.startswith("INSERT INTO "):
            inside = "`item_template`" in line
            continue
        if not inside or not line.startswith("("):
            continue
        values = next(csv.reader([line.strip().removesuffix(",").removesuffix(";")[1:-1]],
                                 delimiter=",", quotechar="'", escapechar="\\", skipinitialspace=True))
        if len(values) != 9:
            raise ValueError(f"Cannot parse item_template row: {line[:120]}")
        item = dict(zip(FIELDS, values))
        for field in FIELDS:
            if field not in ("name", "description"):
                item[field] = int(item[field])
        item["upgradable"] = bool(item["upgradable"])
        rows[item["id"]] = item
    return rows


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("catalog", type=Path)
    parser.add_argument("--json", type=Path, help="Write the detailed comparison")
    args = parser.parse_args()
    observed = json.loads(args.catalog.read_text(encoding="utf-8"))
    local = seed_items(SEED)
    target = [item for item in observed["items"] if item["type"] in (5, 18)]
    mismatches = []
    for item in target:
        before = local.get(item["id"])
        if before is None:
            mismatches.append({"id": item["id"], "missing": True})
            continue
        differences = {field: {"local": before[field], "observed": item[field]}
                       for field in FIELDS if before[field] != item[field]}
        if differences:
            mismatches.append({"id": item["id"], "name": item["name"], "differences": differences})
    counts = Counter(field for row in mismatches for field in row.get("differences", {}))
    print(f"Observed relevant items: {len(target)}; local seed items: {len(local)}")
    print(f"Missing rows: {sum('missing' in row for row in mismatches)}; differing rows: {len(mismatches)}")
    print("Differing fields:", dict(counts))
    for row in mismatches[:25]:
        print(row)
    if args.json:
        args.json.write_text(json.dumps({"summary": dict(counts), "mismatches": mismatches},
                                        ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
