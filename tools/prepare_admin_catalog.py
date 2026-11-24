"""Stage observed costume/pet shop items and non-overwriting icon aliases.

Run from any directory. The catalog is the verified server-14 client snapshot;
this script never infers item identity from sprite filenames alone.
"""

from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path

from compare_observed_items import seed_items

ROOT = Path(__file__).resolve().parents[1]
CATALOG = ROOT / "Server/resources/reference/server14/item-templates.json"
SOURCE_ICONS = ROOT.parent / "NRO-server14-assets/image"
BE_ICONS = ROOT / "Server/resources/normal/image"
MIGRATION = ROOT / "db/migrations/V9__append_observed_costumes_and_pets.sql"
ALIAS_START = 32212


def prepare() -> tuple[list[dict], dict[int, int]]:
    snapshot = json.loads(CATALOG.read_text(encoding="utf-8"))
    if snapshot["source_server"] != "dragon14.teamobi.com:18001":
        raise ValueError("Unexpected catalog source")
    items = snapshot["items"]
    if len(items) != 599 or len({item["id"] for item in items}) != 599:
        raise ValueError("Expected 599 unique costume/pet templates")

    local = seed_items(ROOT / "ngocrong-clean.sql")
    aliases: dict[int, int] = {}
    for icon_id in sorted({item["icon_id"] for item in items}):
        sources = [SOURCE_ICONS / f"zoom{zoom}/icon/{icon_id}.png" for zoom in range(1, 5)]
        targets = [BE_ICONS / f"{zoom}/icon/{icon_id}.png" for zoom in range(1, 5)]
        if not all(path.is_file() for path in sources):
            # The one unavailable source icon, Uub 8586, already exists in BE.
            if not all(path.is_file() for path in targets):
                raise ValueError(f"No complete source or BE icon for {icon_id}")
            continue
        if any(not target.is_file() or source.read_bytes() != target.read_bytes()
               for source, target in zip(sources, targets)):
            aliases[icon_id] = ALIAS_START + len(aliases)

    if aliases and max(aliases.values()) > 32767:
        raise ValueError("Icon alias exceeds the signed-short client limit")
    for original_id, alias_id in aliases.items():
        for zoom in range(1, 5):
            target = BE_ICONS / f"{zoom}/icon/{alias_id}.png"
            source = SOURCE_ICONS / f"zoom{zoom}/icon/{original_id}.png"
            if target.exists() and target.read_bytes() != source.read_bytes():
                raise ValueError(f"Icon alias collision: {target}")

    def already_present(item: dict) -> bool:
        effective_icon = aliases.get(item["icon_id"], item["icon_id"])
        types = (18, 21) if item["type"] == 18 else (item["type"],)
        return any(row["type"] in types and row["gender"] == item["gender"]
                   and row["name"] == item["name"] and row["icon_id"] == effective_icon
                   for row in local.values())

    selected = [item for item in items if not already_present(item)]
    for item in selected:
        if item["icon_id"] not in aliases and not all(
                (BE_ICONS / f"{zoom}/icon/{item['icon_id']}.png").is_file()
                for zoom in range(1, 5)):
            raise ValueError(f"Missing icon for selected item {item['id']}")
    return selected, aliases


def sql_text(aliases: dict[int, int]) -> str:
    lines = [
        "-- Append observed server-14 costumes/pets while preserving all existing BE IDs.",
        "-- Sprite files alone do not establish head/body/leg mappings.",
        "CREATE TABLE IF NOT EXISTS `admin_catalog_item_source` (",
        "  `source_server` varchar(100) NOT NULL,",
        "  `source_item_id` int NOT NULL,",
        "  `item_id` int NOT NULL,",
        "  PRIMARY KEY (`source_server`, `source_item_id`),",
        "  UNIQUE KEY `uq_admin_catalog_item_id` (`item_id`)",
        ") ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;",
        "CREATE TABLE IF NOT EXISTS `admin_catalog_icon_alias` (",
        "  `source_icon_id` int NOT NULL PRIMARY KEY,",
        "  `item_icon_id` int NOT NULL UNIQUE",
        ") ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;",
    ]
    if aliases:
        rows = [f"({source_id}, {alias_id})" for source_id, alias_id in aliases.items()]
        lines.append("INSERT INTO `admin_catalog_icon_alias` (`source_icon_id`, `item_icon_id`) VALUES\n"
                     + ",\n".join(rows) + ";")
    lines.extend([
        "CREATE TEMPORARY TABLE `admin_catalog_import` AS",
        "SELECT r.`source_server`, r.`id` AS `source_item_id`, r.`item_type`,",
        "       r.`gender`, r.`name`, r.`description`,",
        "       COALESCE(icon.`item_icon_id`, r.`icon_id`) AS `icon_id`,",
        "       ROW_NUMBER() OVER (ORDER BY r.`id`) AS `ordinal`",
        "FROM `reference_item_template` r",
        "LEFT JOIN `admin_catalog_icon_alias` icon ON icon.`source_icon_id` = r.`icon_id`",
        "WHERE r.`source_server` = 'dragon14.teamobi.com:18001'",
        "  AND r.`item_type` IN (5, 18)",
        "  AND r.`icon_id` BETWEEN 0 AND 32767",
        "  AND NOT EXISTS (",
        "      SELECT 1 FROM `item_template` existing",
        "      WHERE (existing.`TYPE` = r.`item_type`",
        "             OR (r.`item_type` = 18 AND existing.`TYPE` = 21))",
        "        AND existing.`gender` = r.`gender`",
        "        AND BINARY existing.`NAME` = BINARY r.`name`",
        "        AND existing.`icon_id` = COALESCE(icon.`item_icon_id`, r.`icon_id`)",
        "  );",
        "SET @admin_catalog_start = (SELECT COALESCE(MAX(`id`), -1) + 1 FROM `item_template`);",
        "INSERT INTO `item_template`",
        "  (`id`, `TYPE`, `gender`, `NAME`, `description`, `icon_id`, `part`, `is_up_to_up`, `power_require`)",
        "SELECT @admin_catalog_start + i.`ordinal` - 1, i.`item_type`, i.`gender`, i.`name`,",
        "       CONCAT('S14 #', i.`source_item_id`, ': chưa xác minh ngoại hình. ', i.`description`),",
        "       i.`icon_id`, -1, 0, 0",
        "FROM `admin_catalog_import` i ORDER BY i.`ordinal`;",
        "INSERT INTO `admin_catalog_item_source` (`source_server`, `source_item_id`, `item_id`)",
        "SELECT i.`source_server`, i.`source_item_id`, @admin_catalog_start + i.`ordinal` - 1",
        "FROM `admin_catalog_import` i ORDER BY i.`ordinal`;",
        "DROP TEMPORARY TABLE `admin_catalog_import`;",
    ])
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true", help="Write migration and copy absent icon aliases")
    args = parser.parse_args()
    selected, aliases = prepare()
    print(f"Observed missing/changed items: {len(selected)} "
          f"({sum(x['type'] == 5 for x in selected)} costumes, "
          f"{sum(x['type'] == 18 for x in selected)} pets); icon aliases: {len(aliases)}")
    if not args.apply:
        return
    migration = sql_text(aliases)
    MIGRATION.write_text(migration, encoding="utf-8")
    copied = 0
    for original_id, alias_id in aliases.items():
        for zoom in range(1, 5):
            target = BE_ICONS / f"{zoom}/icon/{alias_id}.png"
            if not target.exists():
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(SOURCE_ICONS / f"zoom{zoom}/icon/{original_id}.png", target)
                copied += 1
    print(f"Wrote {MIGRATION.name}; copied {copied} PNGs without overwriting old images")


if __name__ == "__main__":
    main()
