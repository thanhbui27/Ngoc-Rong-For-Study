"""Append non-colliding server 14 parts 2042..2096 to both BE SQL seeds.

The existing BE part namespace is 0..2041. This tool refuses to alter existing
part rows and writes a forward-only migration for already initialized DBs.
"""

from __future__ import annotations

import json
import re
import struct
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT.parent / "NRO-server14-assets" / "game-data" / "part.bin"
SEEDS = [ROOT / "ngocrong-clean.sql", ROOT / "ngocrong.sql"]
MIGRATION = ROOT / "db" / "migrations" / "V6__append_observed_server14_parts.sql"
REFERENCE_MIGRATION = ROOT / "db" / "migrations" / "V7__add_server14_reference_parts.sql"
FIRST_NEW = 2042
LAST_NEW = 2096


def read_parts(path: Path) -> list[tuple[int, list[list[int]]]]:
    raw = path.read_bytes()
    count = struct.unpack_from(">h", raw)[0]
    offset = 2
    parts = []
    for _ in range(count):
        kind = struct.unpack_from(">b", raw, offset)[0]
        offset += 1
        frames = []
        for _ in range({0: 3, 1: 17, 2: 14, 3: 2}[kind]):
            frames.append(list(struct.unpack_from(">hbb", raw, offset)))
            offset += 4
        parts.append((kind, frames))
    if count != LAST_NEW + 1 or offset != len(raw):
        raise ValueError("Unexpected observed part file")
    return parts


def seed_part_ids(sql: str) -> set[int]:
    section = False
    found = set()
    for line in sql.splitlines():
        if line.startswith("INSERT INTO "):
            section = line.startswith("INSERT INTO `part` ")
            continue
        if section and line.startswith("("):
            found.add(int(line.split(",", 1)[0][1:]))
    return found


def main() -> None:
    parts = read_parts(SOURCE)
    rows = [f"({part_id}, {parts[part_id][0]}, '"
            + json.dumps(parts[part_id][1], separators=(",", ":")) + "')"
            for part_id in range(FIRST_NEW, LAST_NEW + 1)]
    seed_insert = ("\n-- Additional non-colliding parts observed from server 14.\n"
                   "INSERT INTO `part` (`id`, `TYPE`, `DATA`) VALUES\n"
                   + ",\n".join(rows) + ";\n")
    marker = re.compile(r"(?m)^\(2041, 2, '.*?\]\]'\);\r?$")
    for path in SEEDS:
        raw = path.read_bytes()
        newline = "\r\n" if b"\r\n" in raw else "\n"
        sql = raw.decode("utf-8")
        ids = seed_part_ids(sql)
        if ids == set(range(LAST_NEW + 1)):
            continue
        if ids != set(range(FIRST_NEW)):
            raise ValueError(f"Unexpected existing part IDs in {path.name}: {len(ids)}")
        updated, count = marker.subn(lambda match: match.group(0) + seed_insert.replace("\n", newline), sql, count=1)
        if count != 1:
            raise ValueError(f"Could not locate end of part table in {path.name}")
        path.write_bytes(updated.encode("utf-8"))

    migration = (
        "-- Append only IDs absent from the original BE part table.\n"
        "-- Existing part rows are never updated; INSERT IGNORE also preserves\n"
        "-- any project-specific rows already using these IDs.\n"
        "INSERT IGNORE INTO `part` (`id`, `TYPE`, `DATA`) VALUES\n"
        + ",\n".join(rows) + ";\n"
    )
    if MIGRATION.exists() and MIGRATION.read_text(encoding="utf-8") != migration:
        raise ValueError("Existing V6 migration differs; do not rewrite an applied migration")
    MIGRATION.write_text(migration, encoding="utf-8", newline="\n")

    reference_rows = [
        "('dragon14.teamobi.com:18001', " + str(part_id) + ", "
        + str(kind) + ", '" + json.dumps(frames, separators=(",", ":")) + "')"
        for part_id, (kind, frames) in enumerate(parts)
    ]
    reference_migration = (
        "-- Full observed server 14 part set, isolated from the BE's runtime part IDs.\n"
        "CREATE TABLE IF NOT EXISTS `reference_part` (\n"
        "  `source_server` varchar(100) NOT NULL,\n"
        "  `id` int NOT NULL,\n"
        "  `part_type` smallint NOT NULL,\n"
        "  `data` text NOT NULL,\n"
        "  PRIMARY KEY (`source_server`, `id`)\n"
        ") ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;\n"
        "INSERT IGNORE INTO `reference_part` (`source_server`, `id`, `part_type`, `data`) VALUES\n"
        + ",\n".join(reference_rows) + ";\n"
    )
    if REFERENCE_MIGRATION.exists() and REFERENCE_MIGRATION.read_text(encoding="utf-8") != reference_migration:
        raise ValueError("Existing V7 migration differs; do not rewrite an applied migration")
    REFERENCE_MIGRATION.write_text(reference_migration, encoding="utf-8", newline="\n")
    print(f"Prepared {len(rows)} new runtime part rows, and {len(reference_rows)} isolated reference rows")


if __name__ == "__main__":
    main()
