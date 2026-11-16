"""Build a fresh-install SQL seed without saved players or live service data."""

from pathlib import Path
import re

ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / "ngocrong.sql"
DESTINATION = ROOT / "ngocrong-clean.sql"

# These tables contain game definitions, not accounts or player-owned state.
TEMPLATE_TABLES = {
    b"achivements", b"attribute_template", b"cai_trang", b"caption",
    b"category", b"collection_book", b"flag_bag", b"head_avatar",
    b"img_by_name", b"intrinsic", b"item_option_template", b"item_shop",
    b"item_shop_option", b"item_template", b"map_template", b"mini_pet",
    b"mob_template", b"nclass", b"npc_template", b"part", b"pet_follow",
    b"power_limit", b"shop", b"side_task_template", b"skill_template",
    b"small_version", b"tab_shop", b"task_main_template",
    b"task_sub_template", b"type_map",
}

statement_start = re.compile(rb"^(INSERT|REPLACE) INTO `([^`]+)`")
output = []
skipping = False
seen = set()
for line in SOURCE.read_bytes().splitlines(keepends=True):
    if not skipping:
        match = statement_start.match(line)
        if match:
            table = match.group(2)
            seen.add(table)
            skipping = table not in TEMPLATE_TABLES
    if not skipping:
        output.append(line)
    elif line.rstrip().endswith(b";"):
        skipping = False

if skipping:
    raise RuntimeError("SQL dump ended inside a skipped INSERT statement")
if not {b"account", b"player"}.issubset(seen):
    raise RuntimeError("Expected account and player data in source dump")

result = b"".join(output)
if re.search(rb"^(INSERT|REPLACE) INTO `(account|player)`", result, re.MULTILINE):
    raise RuntimeError("Personal account or player rows were not removed")
DESTINATION.write_bytes(result)
print(f"Created {DESTINATION.name} from {SOURCE.name}; original dump is unchanged")
