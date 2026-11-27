"""Small waypoint graph from the repository's clean map template seed."""

from __future__ import annotations

import re
from collections import deque
from pathlib import Path

SEED = Path(__file__).resolve().parent.parent / "ngocrong-clean.sql"
ROW = re.compile(r"^\((\d+), '((?:''|[^'])*)', '[^']*', \d+, \d+, '([^']*)', '([^']*)'")
MOB_ROW = re.compile(r"^\((\d+), \d+, '((?:''|[^'])*)', (\d+),")
NPC_ROW = re.compile(r"^\((\d+), '((?:''|[^'])*)',")
ITEM_ROW = re.compile(r"^\((\d+), (\d+), \d+, '((?:''|[^'])*)', '((?:''|[^'])*)', (\d+),")
OPTION_ROW = re.compile(r"^\((\d+), '((?:''|[^'])*)', \d+\)[,;]$")
MOB_SPAWN = re.compile(r"\[(\d+),(\d+),(\d+),-?\d+,-?\d+\]")
CAPTION_ROW = re.compile(r"^\((\d+), .*, (\d+)\)[,;]$")
WAYPOINT = re.compile(r'"([^"\[\]]+)",(-?\d+),(-?\d+),(-?\d+),(-?\d+),([01]),([01]),(-?\d+),(-?\d+),(-?\d+)\]')
HEAD_AVATAR_ROW = re.compile(r"^\((\d+), (\d+)\)[,;]$")


class Routes:
    def __init__(self, seed: Path = SEED):
        self.maps: dict[int, list[dict]] = {}
        self.farm_maps: set[int] = set()
        self.mob_names: dict[int, str] = {}
        self.npc_names: dict[int, str] = {}
        self.item_names: dict[int, str] = {}
        self.item_descriptions: dict[int, str] = {}
        self.item_types: dict[int, int] = {}
        self.item_icon_ids: dict[int, int] = {}
        self.option_names: dict[int, str] = {}
        self.avatar_by_head: dict[int, int] = {}
        self.mob_hp: dict[int, int] = {}
        self.map_mobs: dict[int, list[tuple[int, int, int]]] = {}
        self.power_thresholds: list[int] = []
        if not seed.exists():
            return
        in_maps = False
        in_mobs = False
        in_captions = False
        in_npcs = False
        in_items = False
        in_options = False
        in_head_avatars = False
        with seed.open(encoding="utf-8") as source:
            for line in source:
                if line.startswith("INSERT INTO `map_template`"):
                    in_maps = True
                    in_mobs = False
                    in_captions = False
                    continue
                if line.startswith("INSERT INTO `item_template`"):
                    in_items = True
                    in_maps = in_mobs = in_captions = in_npcs = False
                    continue
                if line.startswith("INSERT INTO `item_option_template`"):
                    in_options = True
                    in_items = in_maps = in_mobs = in_captions = in_npcs = False
                    continue
                if in_options:
                    match = OPTION_ROW.match(line.rstrip())
                    if match:
                        self.option_names[int(match.group(1))] = match.group(2).replace("''", "'")
                    elif line.startswith("CREATE TABLE") or line.strip() == "--":
                        in_options = False
                    continue
                if line.startswith("INSERT INTO `head_avatar`"):
                    in_head_avatars = True
                    in_maps = in_mobs = in_captions = in_npcs = in_items = False
                    continue
                if in_head_avatars:
                    match = HEAD_AVATAR_ROW.match(line)
                    if match:
                        self.avatar_by_head[int(match.group(1))] = int(match.group(2))
                    elif line.startswith("CREATE TABLE") or line.strip() == "--":
                        in_head_avatars = False
                    continue
                if in_items:
                    match = ITEM_ROW.match(line)
                    if match:
                        item_id, item_type = int(match.group(1)), int(match.group(2))
                        self.item_types[item_id] = item_type
                        self.item_names[item_id] = match.group(3).replace("''", "'")
                        self.item_descriptions[item_id] = match.group(4).replace("''", "'")
                        self.item_icon_ids[item_id] = int(match.group(5))
                    elif line.startswith("CREATE TABLE") or line.strip() == "--":
                        in_items = False
                    continue
                if line.startswith("INSERT INTO `mob_template`"):
                    in_mobs = True
                    in_maps = False
                    in_captions = False
                    continue
                if line.startswith("INSERT INTO `caption`"):
                    in_captions = True
                    in_mobs = in_maps = False
                    continue
                if line.startswith("INSERT INTO `npc_template`"):
                    in_npcs = True
                    in_maps = in_mobs = in_captions = False
                    continue
                if in_npcs:
                    match = NPC_ROW.match(line)
                    if match:
                        self.npc_names[int(match.group(1))] = match.group(2).replace("''", "'")
                    elif line.startswith("CREATE TABLE"):
                        in_npcs = False
                    continue
                if in_captions:
                    match = CAPTION_ROW.match(line)
                    if match:
                        self.power_thresholds.append(int(match.group(2)))
                    elif line.startswith("CREATE TABLE"):
                        in_captions = False
                    continue
                if in_mobs:
                    match = MOB_ROW.match(line)
                    if match:
                        self.mob_names[int(match.group(1))] = match.group(2).replace("''", "'")
                        self.mob_hp[int(match.group(1))] = int(match.group(3))
                    elif line.startswith("CREATE TABLE"):
                        in_mobs = False
                    continue
                if not in_maps:
                    continue
                match = ROW.match(line)
                if not match:
                    if line.strip() == "--" or line.startswith("CREATE TABLE"):
                        in_maps = False
                    continue
                map_id = int(match.group(1))
                spawns = [tuple(map(int, spawn)) for spawn in MOB_SPAWN.findall(match.group(4))]
                self.map_mobs[map_id] = spawns
                if spawns:
                    self.farm_maps.add(map_id)
                self.maps[map_id] = [
                    {"name": hit[0], "bounds": tuple(int(value) for value in hit[1:5]),
                     "enter": hit[5] == "1", "offline": hit[6] == "1", "go_map": int(hit[7])}
                    for hit in WAYPOINT.findall(match.group(3))
                ]

    def player_level(self, power: int) -> int:
        return max((index for index, threshold in enumerate(self.power_thresholds) if power >= threshold), default=0)

    def best_farm_map(self, start: int, power: int, damage: int,
                      excluded: set[int] | None = None, target_templates: set[int] | None = None) -> int | None:
        if start not in self.maps:
            return None
        excluded = excluded or set()
        queue = deque([(start, 0)])
        seen = {start}
        best: tuple[tuple[int, int, int], int] | None = None
        level_limit = self.player_level(power) + 2
        hp_limit = max(250, damage * 25)
        while queue:
            current, distance = queue.popleft()
            if current not in excluded:
                spawns = self.map_mobs.get(current, [])
                eligible = [(template, level, reward) for template, level, reward in spawns
                            if (target_templates is not None and template in target_templates)
                            or (target_templates is None and level <= level_limit and self.mob_hp.get(template, 0) <= hp_limit)]
                if eligible:
                    score = (max(level for _, level, _ in eligible), max(reward for _, _, reward in eligible), -distance)
                    if best is None or score > best[0]:
                        best = (score, current)
            for waypoint in self.maps.get(current, []):
                destination = waypoint["go_map"]
                if destination in self.maps and destination not in seen:
                    seen.add(destination)
                    queue.append((destination, distance + 1))
        return best[1] if best else None

    def nearest_farm_map(self, start: int, excluded: set[int] | None = None) -> int | None:
        if start not in self.maps:
            return None
        excluded = excluded or set()
        queue = deque([start])
        seen = {start}
        while queue:
            current = queue.popleft()
            if current in self.farm_maps and current not in excluded:
                return current
            for waypoint in self.maps.get(current, []):
                destination = waypoint["go_map"]
                if destination not in seen and destination in self.maps:
                    seen.add(destination)
                    queue.append(destination)
        return None

    def next_hop(self, start: int, goal: int) -> dict | None:
        if start == goal or start not in self.maps or goal not in self.maps:
            return None
        queue = deque([(start, None)])
        seen = {start}
        while queue:
            current, first = queue.popleft()
            for waypoint in self.maps.get(current, []):
                destination = waypoint["go_map"]
                if destination in seen or destination not in self.maps:
                    continue
                hop = first or waypoint
                if destination == goal:
                    return hop
                seen.add(destination)
                queue.append((destination, hop))
        return None
