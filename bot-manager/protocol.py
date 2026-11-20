"""Minimal NRO wire protocol and decoders used by the test bots.

Packets match the Java server under Server/src/main/java/nro/server/io.
Only the fields needed by this manager are decoded; unknown packets are ignored.
"""

from __future__ import annotations

import socket
import struct
from dataclasses import dataclass

BIG_COMMANDS = {-32, -66, -74, 11, -67, -87, 66}
MAX_PACKET = 12 * 1024 * 1024


def java_utf(value: str) -> bytes:
    # DataOutputStream.writeUTF uses modified UTF-8 over UTF-16 code units.
    units = value.encode("utf-16-be", "surrogatepass")
    data = bytearray()
    for offset in range(0, len(units), 2):
        unit = (units[offset] << 8) | units[offset + 1]
        if 0x0001 <= unit <= 0x007F:
            data.append(unit)
        elif unit <= 0x07FF:
            data.extend((0xC0 | (unit >> 6), 0x80 | (unit & 0x3F)))
        else:
            data.extend((0xE0 | (unit >> 12), 0x80 | ((unit >> 6) & 0x3F), 0x80 | (unit & 0x3F)))
    if len(data) > 65535:
        raise ValueError("String exceeds Java writeUTF limit")
    return struct.pack(">H", len(data)) + data


def bytes_to_utf(raw: bytes) -> str:
    # Replace the modified NUL encoding before decoding UTF-16 surrogates.
    raw = raw.replace(b"\xC0\x80", b"\x00")
    return raw.decode("utf-8", "surrogatepass").encode("utf-16-le", "surrogatepass").decode("utf-16-le")


class Reader:
    def __init__(self, data: bytes):
        self.data = data
        self.pos = 0

    def raw(self, length: int) -> bytes:
        if length < 0 or self.pos + length > len(self.data):
            raise ValueError("Truncated game packet")
        result = self.data[self.pos:self.pos + length]
        self.pos += length
        return result

    def u8(self) -> int:
        return self.raw(1)[0]

    def i8(self) -> int:
        return struct.unpack(">b", self.raw(1))[0]

    def u16(self) -> int:
        return struct.unpack(">H", self.raw(2))[0]

    def i16(self) -> int:
        return struct.unpack(">h", self.raw(2))[0]

    def i32(self) -> int:
        return struct.unpack(">i", self.raw(4))[0]

    def i64(self) -> int:
        return struct.unpack(">q", self.raw(8))[0]

    def utf(self) -> str:
        return bytes_to_utf(self.raw(self.u16()))


class Wire:
    def __init__(self, sock: socket.socket):
        self.sock = sock
        self.key: bytes | None = None
        self.read_index = 0
        self.write_index = 0

    def _read_exact(self, size: int) -> bytes:
        data = bytearray()
        while len(data) < size:
            try:
                part = self.sock.recv(size - len(data))
            except socket.timeout:
                if data:
                    continue  # Keep an in-flight frame together.
                raise
            if not part:
                raise ConnectionError("Server closed connection")
            data.extend(part)
        return bytes(data)

    def _read_key(self, value: int) -> int:
        if self.key is None:
            return value
        result = value ^ self.key[self.read_index]
        self.read_index = (self.read_index + 1) % len(self.key)
        return result

    def _write_key(self, value: int) -> int:
        if self.key is None:
            return value
        result = value ^ self.key[self.write_index]
        self.write_index = (self.write_index + 1) % len(self.key)
        return result

    def send(self, command: int, payload: bytes = b"") -> None:
        if not -128 <= command <= 127 or len(payload) > 1024:
            raise ValueError("Invalid client packet")
        head = [command & 255, (len(payload) >> 8) & 255, len(payload) & 255]
        packet = bytes(self._write_key(part) for part in head)
        packet += bytes(self._write_key(part) for part in payload)
        self.sock.sendall(packet)

    def read(self) -> tuple[int, bytes]:
        command = struct.unpack(">b", bytes([self._read_key(self._read_exact(1)[0])]))[0]
        old_timeout = self.sock.gettimeout()
        self.sock.settimeout(5)
        try:
            if self.key is not None and command in BIG_COMMANDS:
                size_bytes = [self._read_key(part) for part in self._read_exact(3)]
                size = sum(((value + 128) & 255) << (8 * i) for i, value in enumerate(size_bytes))
            elif self.key is not None:
                size_bytes = [self._read_key(part) for part in self._read_exact(2)]
                size = size_bytes[0] << 8 | size_bytes[1]
            else:
                size = struct.unpack(">H", self._read_exact(2))[0]
            if size > MAX_PACKET:
                raise ValueError("Server packet exceeds size limit")
            return command, bytes(self._read_key(part) for part in self._read_exact(size))
        except socket.timeout as exc:
            raise ConnectionError("Timed out during a server packet") from exc
        finally:
            self.sock.settimeout(old_timeout)

    def accept_key(self, payload: bytes) -> None:
        reader = Reader(payload)
        length = reader.u8()
        if not 1 <= length <= 128:
            raise ValueError("Invalid session key")
        encoded = reader.raw(length)
        key = bytearray(encoded)
        for index in range(1, length):
            key[index] ^= key[index - 1]
        self.key = bytes(key)
        self.read_index = self.write_index = 0


@dataclass
class Mob:
    mob_id: int
    template_id: int
    level: int
    x: int
    y: int
    hp: int
    max_hp: int
    status: int
    boss_level: int


@dataclass
class ItemMap:
    map_id: int
    template_id: int
    x: int
    y: int
    owner_id: int


def read_items(reader: Reader, slots: dict[int, int] | None = None,
               details: dict[int, dict] | None = None) -> dict[int, int]:
    items: dict[int, int] = {}
    for index in range(reader.u8()):
        item_id = reader.i16()
        if item_id == -1:
            continue
        count = reader.i32()
        info, description = reader.utf(), reader.utf()
        options = [{"id": reader.u8(), "param": reader.u16()} for _ in range(reader.u8())]
        items[item_id] = items.get(item_id, 0) + count
        if slots is not None:
            slots.setdefault(item_id, index)
        if details is not None:
            details[item_id] = {"id": item_id, "count": count, "info": info,
                                "description": description, "options": options, "slot": index}
    return items


def parse_player(payload: bytes) -> dict:
    reader = Reader(payload)
    if reader.i8() != 0:
        return {}
    player_id = reader.i32()
    reader.u8()  # task id
    gender = reader.u8()
    head_id = reader.u16()
    name = reader.utf()
    result = {"player_id": player_id, "character": name, "gender": gender, "head_id": head_id}
    try:
        reader.raw(2)  # PK status
        result["power"] = reader.i64()
        reader.raw(5)  # two shorts and gender
        skill_count = reader.u8()
        result["skill_ids"] = [reader.u16() for _ in range(skill_count)]
        result["gold"] = reader.i64()
        reader.raw(8)  # ruby and gems
        worn_slots: dict[int, int] = {}
        worn_details: dict[int, dict] = {}
        worn_items = read_items(reader, worn_slots, worn_details)
        result["worn_items"] = worn_items
        result["worn_details"] = worn_details
        slots: dict[int, int] = {}
        details: dict[int, dict] = {}
        result["bag"] = read_items(reader, slots, details)
        result["bag_slots"] = slots
        result["bag_details"] = details
    except ValueError:
        pass
    return result


def parse_stats(payload: bytes) -> dict:
    reader = Reader(payload)
    base_hp, base_mp, base_damage = reader.i32(), reader.i32(), reader.i32()
    max_hp, max_mp, hp, mp = (reader.i32() for _ in range(4))
    reader.raw(4)
    damage, defense = reader.i32(), reader.i32()
    reader.raw(1)
    potential = reader.i64()
    reader.raw(2)
    base_defense = reader.i16()
    return dict(base_hp=base_hp, base_mp=base_mp, base_damage=base_damage,
                max_hp=max_hp, max_mp=max_mp, hp=hp, mp=mp, damage=damage,
                defense=defense, base_defense=base_defense, potential=potential)


def parse_map(payload: bytes) -> dict:
    reader = Reader(payload)
    map_id = reader.u8()
    reader.raw(4)
    name = reader.utf()
    zone = reader.u8()
    x, y = reader.i16(), reader.i16()
    waypoints = []
    for _ in range(reader.u8()):
        bounds = [reader.i16() for _ in range(4)]
        enter, offline = reader.u8(), reader.u8()
        waypoints.append(dict(bounds=bounds, enter=bool(enter), offline=bool(offline), name=reader.utf()))
    mobs = {}
    for mob_id in range(reader.u8()):
        reader.raw(5)
        template_id = reader.u8()
        reader.raw(1)
        hp = reader.i32()
        level = reader.u8()
        max_hp = reader.i32()
        mob_x, mob_y = reader.i16(), reader.i16()
        status, boss_level = reader.u8(), reader.u8()
        reader.raw(1)
        mobs[mob_id] = Mob(mob_id, template_id, level, mob_x, mob_y, hp, max_hp, status, boss_level)
    reader.raw(reader.u8())  # empty player list in this server's map packet
    npcs = {}
    for _ in range(reader.u8()):
        reader.raw(1)
        npc_x, npc_y = reader.i16(), reader.i16()
        npc_id = reader.u8()
        reader.raw(2)
        npcs[npc_id] = (npc_x, npc_y)
    items = {}
    for _ in range(reader.u8()):
        item_map_id, item_id = reader.u16(), reader.u16()
        item_x, item_y, owner = reader.i16(), reader.i16(), reader.i32()
        if owner == -2:
            reader.raw(2)
        items[item_map_id] = ItemMap(item_map_id, item_id, item_x, item_y, owner)
    return dict(map_id=map_id, map_name=name, zone=zone, x=x, y=y,
                waypoints=waypoints, mobs=mobs, npcs=npcs, items=items)


def parse_task(payload: bytes) -> dict:
    reader = Reader(payload)
    task_id, index = reader.i16(), reader.u8()
    name, detail = reader.utf(), reader.utf()
    steps = []
    for _ in range(reader.u8()):
        title, npc_id, map_id, hint = reader.utf(), reader.i8(), reader.i16(), reader.utf()
        steps.append(dict(title=title, npc_id=npc_id, map_id=map_id, hint=hint))
    count = reader.i16() if reader.pos + 2 <= len(payload) else 0
    return dict(task_id=task_id, index=index, name=name, detail=detail, steps=steps, count=count)


def parse_shop(payload: bytes) -> dict[int, dict]:
    reader = Reader(payload)
    if reader.u8() != 0:  # normal gold/gem shop only
        return {}
    items = {}
    for _ in range(reader.u8()):
        reader.utf()
        for _ in range(reader.u8()):
            item_id, gold, gems = reader.u16(), reader.i32(), reader.i32()
            for _ in range(reader.u8()):
                reader.raw(3)
            reader.raw(1)
            if reader.u8():
                reader.raw(8)
            items[item_id] = {"gold": gold, "gems": gems}
    return items
