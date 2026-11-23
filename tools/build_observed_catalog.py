"""Stage a server-observed costume/pet catalog without changing game templates.

Run from this repository or pass absolute paths. The input must be the decoded
client cache captured during a live server 14 session, plus its part.bin.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "Server" / "resources" / "reference" / "server14"
MIGRATION = ROOT / "db" / "migrations" / "V4__add_server14_reference_catalog.sql"
SERVER = "dragon14.teamobi.com:18001"


def quote_sql(value: str) -> str:
    return "'" + value.replace("\\", "\\\\").replace("'", "''") + "'"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("catalog", type=Path)
    parser.add_argument("part_file", type=Path)
    args = parser.parse_args()
    source_bytes = args.catalog.read_bytes()
    source = json.loads(source_bytes)
    if source.get("server") != SERVER or source.get("source_kind") != "client_cache_used_during_server14_session":
        raise ValueError("Expected the verified server 14 client-cache export")
    if source.get("item_versions") != [2]:
        raise ValueError("Unexpected item version")
    items = [item for item in source["items"] if item["type"] in (5, 18)]
    if len(items) != 599 or len({item["id"] for item in items}) != 599:
        raise ValueError("Unexpected costume/pet catalog count or duplicate ID")
    part_bytes = args.part_file.read_bytes()
    if len(part_bytes) != 90255:
        raise ValueError("Unexpected server 14 part file")

    OUTPUT.mkdir(parents=True, exist_ok=True)
    catalog = {
        "source_server": SERVER,
        "source_kind": source["source_kind"],
        "item_version": 2,
        "item_export_sha256": hashlib.sha256(source_bytes).hexdigest(),
        "part_sha256": hashlib.sha256(part_bytes).hexdigest(),
        "server15_item_equality_verified": False,
        "notes": "Item templates from the client cache used in a live server 14 session; no per-instance combat option values or full pet/costume part mappings.",
        "items": items,
    }
    (OUTPUT / "item-templates.json").write_text(
        json.dumps(catalog, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    shutil.copy2(args.part_file, OUTPUT / "part.bin")

    sql = [
        "-- Server 14 reference catalog from a live Dragonboy252 client session.",
        "-- Separate from item_template/cai_trang/mini_pet because this BE fork reuses IDs",
        "-- with different meanings and has a different part.bin. No gameplay rows are changed.",
        "CREATE TABLE IF NOT EXISTS `reference_item_template` (",
        "  `source_server` varchar(100) NOT NULL,",
        "  `id` int NOT NULL,",
        "  `item_type` smallint NOT NULL,",
        "  `gender` smallint NOT NULL,",
        "  `name` varchar(255) NOT NULL,",
        "  `description` varchar(255) NOT NULL,",
        "  `level` smallint NOT NULL,",
        "  `power_required` int NOT NULL,",
        "  `icon_id` int NOT NULL,",
        "  `part_id` int NOT NULL,",
        "  `upgradable` tinyint(1) NOT NULL,",
        "  PRIMARY KEY (`source_server`, `id`),",
        "  KEY `idx_reference_item_type` (`source_server`, `item_type`)",
        ") ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;",
        "INSERT INTO `reference_item_template`",
        "  (`source_server`, `id`, `item_type`, `gender`, `name`, `description`, `level`,",
        "   `power_required`, `icon_id`, `part_id`, `upgradable`) VALUES",
    ]
    rows = []
    for item in sorted(items, key=lambda item: item["id"]):
        values = [
            quote_sql(SERVER), str(item["id"]), str(item["type"]), str(item["gender"]),
            quote_sql(item["name"]), quote_sql(item["description"]), str(item["level"]),
            str(item["power_required"]), str(item["icon_id"]), str(item["part_id"]),
            "1" if item["upgradable"] else "0",
        ]
        rows.append("(" + ", ".join(values) + ")")
    sql.append(",\n".join(rows) + ";")
    MIGRATION.write_text("\n".join(sql) + "\n", encoding="utf-8")
    print(f"Staged {len(items)} items at {OUTPUT} and {MIGRATION}")


if __name__ == "__main__":
    main()
