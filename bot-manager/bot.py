"""Headless game clients managed by the local dashboard."""

from __future__ import annotations

import logging
import hashlib
import re
import socket
import struct
import threading
import time
import uuid
from collections import deque
from dataclasses import asdict, dataclass, field
from logging.handlers import RotatingFileHandler
from pathlib import Path

from protocol import ItemMap, Reader, Wire, java_utf, parse_map, parse_player, parse_shop, parse_stats, parse_task, read_items
from routes import Routes
from storage import ConfigStore

LOG_DIR = Path(__file__).resolve().parent / "logs"
ROUTES = Routes()
PEA_ITEMS = (13, 60, 61, 62, 63, 64, 65, 352, 523, 595)


class AuthenticationError(Exception):
    """A server notice that prevents this bot from entering the game."""


@dataclass
class BotConfig:
    name: str
    username: str
    password: str = field(repr=False)
    host: str = "127.0.0.1"
    port: int = 14445
    mode: str = "auto"
    stat: str = "balanced"
    heal_item: int = 0
    shop_map: int = -1
    shop_npc: int = -1
    shop_menu: int = 0
    shop_item: int = 0
    shop_min: int = 0
    shop_target: int = 0
    trade_partner: int = 0
    auto_register: bool = True
    gender: int = 0


class BotRunner:
    def __init__(self, config: BotConfig, bot_id: str | None = None):
        self.id = bot_id or uuid.uuid4().hex[:10]
        self.config = config
        self._lock = threading.RLock()
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._socket: socket.socket | None = None
        self._wire: Wire | None = None
        self._send_lock = threading.Lock()
        self.status = "stopped"
        self.action = "Chưa chạy"
        self.error = ""
        self.logs: deque[dict] = deque(maxlen=400)
        self.log_seq = 0
        self.player_id = 0
        self.gender = 0
        self.character = ""
        self.map_id = -1
        self.map_name = ""
        self.zone = -1
        self.home_map = -1
        self.x = self.y = 0
        self.hp = self.mp = self.max_hp = self.max_mp = 0
        self.gold = self.potential = self.power = 0
        self.damage = self.defense = 0
        self.base_hp = self.base_mp = self.base_damage = self.base_defense = 0
        self.mobs: dict = {}
        self.npcs: dict = {}
        self.waypoints: list[dict] = []
        self.items: dict[int, ItemMap] = {}
        self.bag: dict[int, int] = {}
        self.bag_slots: dict[int, int] = {}
        self.box_slots: dict[int, int] = {}
        self.shop: dict = {}
        self.task: dict = {}
        self.kills = 0
        self.picks = 0
        self.purchases = 0
        self.last_packet = 0.0
        self._ready = False
        self._client_ok = False
        self._finish_sent = False
        self._next_action = 0.0
        self._next_stat = 0.0
        self._next_heal = 0.0
        self._next_shop = 0.0
        self._shop_phase = 0
        self._shop_attempts = 0
        self._shop_before = -1
        self._quest_step_done = ""
        self._quest_request_due = 0.0
        self._trade_phase = 0
        self._trade_due = 0.0
        self._stat_cursor = 0
        self._connected_at = 0.0
        self._auth_phase = ""
        self._registration_checked = False
        self._character_name = ""
        self._travel_goal = -1
        self._travel_map = -1
        self._travel_attempts = 0
        self._travel_next = 0.0
        self._empty_maps: set[int] = set()
        self._focused_mob: int | None = None
        self._mob_last_killed: dict[int, float] = {}
        self._quest_target_templates: set[int] = set()
        self._reconnect_attempt = 0
        self._recovering = False
        self._recover_due = 0.0
        self._tree_peas = -1
        self._tree_seconds = 0
        self._tree_menu_open = False
        self._harvest_attempts = 0
        LOG_DIR.mkdir(parents=True, exist_ok=True)
        self.log_path = LOG_DIR / f"bot-{self.id}.log"
        if self.log_path.exists():
            with self.log_path.open("rb") as history:
                history.seek(max(0, self.log_path.stat().st_size - 65536))
                recent = history.read().decode("utf-8", errors="replace")
            for line in recent.splitlines()[-400:]:
                if len(line) > 24:
                    self.logs.append({"time": line[11:19], "level": "error" if "Lỗi" in line[24:] else "info", "message": line[24:]})
        self._logger = logging.getLogger(f"nro-bot-{self.id}")
        self._logger.setLevel(logging.INFO)
        self._logger.propagate = False
        handler = RotatingFileHandler(self.log_path, maxBytes=2_000_000, backupCount=2, encoding="utf-8")
        handler.setFormatter(logging.Formatter("%(asctime)s %(message)s"))
        self._logger.addHandler(handler)

    def log(self, message: str, level: str = "info") -> None:
        event = {"time": time.strftime("%H:%M:%S"), "level": level, "message": message}
        with self._lock:
            self.logs.append(event)
            self.log_seq += 1
        self._logger.log(logging.ERROR if level == "error" else logging.INFO, message)

    def set_action(self, action: str) -> None:
        with self._lock:
            if self.action == action:
                return
            self.action = action
        self.log("Đang làm: " + action)

    def snapshot(self, include_logs: bool = False) -> dict:
        with self._lock:
            result = {
                "id": self.id, "name": self.config.name, "username": self.config.username,
                "host": self.config.host, "port": self.config.port, "mode": self.config.mode,
                "stat": self.config.stat, "auto_register": self.config.auto_register,
                "create_gender": self.config.gender, "gender": self.gender,
                "reconnect_attempt": self._reconnect_attempt,
                "status": self.status, "action": self.action,
                "error": self.error, "player_id": self.player_id, "character": self.character,
                "map_id": self.map_id, "map_name": self.map_name, "zone": self.zone,
                "x": self.x, "y": self.y,
                "hp": self.hp, "max_hp": self.max_hp, "mp": self.mp, "max_mp": self.max_mp,
                "gold": self.gold, "power": self.power, "potential": self.potential,
                "damage": self.damage, "defense": self.defense, "kills": self.kills,
                "picks": self.picks, "purchases": self.purchases, "mobs": len(self.mobs),
                "items": len(self.items), "task": self.task.get("name", ""),
                "task_step": self.task.get("index", -1), "last_packet": self.last_packet,
                "task_title": self._task_title(), "task_count": self.task.get("count", 0),
                "bag": dict(self.bag), "shop_item": self.config.shop_item,
                "shop_map": self.config.shop_map, "shop_npc": self.config.shop_npc,
                "shop_menu": self.config.shop_menu, "shop_min": self.config.shop_min,
                "shop_target": self.config.shop_target, "trade_partner": self.config.trade_partner,
                "heal_item": self.config.heal_item,
                "recovering": self._recovering, "tree_peas": self._tree_peas,
                "tree_seconds": self._tree_seconds,
                "log_file": str(self.log_path),
                "log_seq": self.log_seq,
            }
            if include_logs:
                result["logs"] = list(self.logs)
            return result

    def start(self) -> bool:
        with self._lock:
            if self._thread and self._thread.is_alive():
                return False
            self._stop.clear()
            self._ready = self._client_ok = self._finish_sent = False
            self._next_action = self._next_stat = self._next_heal = 0
            self._shop_phase = self._shop_attempts = 0
            self._quest_step_done = ""
            self._quest_request_due = 0
            self._trade_phase = 0
            self._travel_goal = self._travel_map = -1
            self._travel_attempts = 0
            self._empty_maps.clear()
            self._focused_mob = None
            self._mob_last_killed.clear()
            self._quest_target_templates.clear()
            self._reconnect_attempt = 0
            self._recovering = False
            self._recover_due = 0
            self._tree_peas = -1
            self._tree_seconds = 0
            self._tree_menu_open = False
            self._harvest_attempts = 0
            self._connected_at = 0
            self._auth_phase = ""
            self._registration_checked = False
            self._character_name = ""
            self.player_id = 0
            self.character = ""
            self.gender = self.config.gender
            self.power = self.potential = self.gold = 0
            self.hp = self.mp = self.max_hp = self.max_mp = 0
            self.damage = self.defense = 0
            self.home_map = self.map_id = -1
            self.mobs, self.npcs, self.items, self.bag, self.bag_slots, self.box_slots, self.shop, self.task = {}, {}, {}, {}, {}, {}, {}, {}
            self.status = "connecting"
            self.error = ""
            self._thread = threading.Thread(target=self._run, name=f"Bot-{self.id}", daemon=True)
            self._thread.start()
        return True

    def stop(self) -> None:
        self._stop.set()
        sock = self._socket
        if sock:
            try:
                sock.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass
            sock.close()
        thread = self._thread
        if thread and thread is not threading.current_thread():
            thread.join(timeout=3)

    def close(self) -> None:
        self.stop()
        for handler in list(self._logger.handlers):
            handler.close()
            self._logger.removeHandler(handler)

    def _send(self, command: int, payload: bytes = b"") -> None:
        if not self._wire:
            raise ConnectionError("No active connection")
        with self._send_lock:
            self._wire.send(command, payload)

    def invite_trade(self) -> None:
        if self.status != "running" or self.config.trade_partner <= 0:
            raise ValueError("Bot chưa chạy hoặc chưa cấu hình player giao dịch")
        self._send(-86, bytes([0]) + struct.pack(">i", self.config.trade_partner))
        self.log(f"Mời giao dịch trống với player {self.config.trade_partner}")

    def _reset_session(self) -> None:
        self._ready = self._client_ok = self._finish_sent = False
        self._auth_phase = ""
        self._registration_checked = False
        self._connected_at = 0
        self._next_action = self._next_stat = self._next_heal = 0
        self._next_shop = 0
        self._shop_phase = self._shop_attempts = self._trade_phase = 0
        self._quest_step_done = ""
        self._quest_request_due = 0
        self._travel_goal = self._travel_map = -1
        self._travel_attempts = 0
        self._travel_next = 0
        self._empty_maps.clear()
        self._focused_mob = None
        self._mob_last_killed.clear()
        self._quest_target_templates.clear()
        self._recovering = False
        self._recover_due = 0
        self._tree_peas = -1
        self._tree_seconds = 0
        self._tree_menu_open = False
        self._harvest_attempts = 0
        self.player_id = 0
        self.character = ""
        self.gender = self.config.gender
        self.hp = self.mp = self.max_hp = self.max_mp = 0
        self.gold = self.power = self.potential = 0
        self.damage = self.defense = 0
        self.home_map = self.map_id = -1
        self.mobs, self.npcs, self.items, self.bag, self.bag_slots, self.box_slots, self.shop, self.task = {}, {}, {}, {}, {}, {}, {}, {}

    def _run(self) -> None:
        while not self._stop.is_set():
            self._reset_session()
            with self._lock:
                self.status = "connecting"
            self.set_action("Kết nối lại server" if self._reconnect_attempt else "Kết nối server")
            try:
                with socket.create_connection((self.config.host, self.config.port), timeout=5) as sock:
                    self._socket = sock
                    self._connected_at = time.monotonic()
                    sock.settimeout(0.4)
                    self._wire = Wire(sock)
                    self._send(-27)
                    self.log(f"Đã kết nối {self.config.host}:{self.config.port}; chờ khóa phiên")
                    while not self._stop.is_set():
                        try:
                            command, payload = self._wire.read()
                            self.last_packet = time.time()
                            self._packet(command, payload)
                        except socket.timeout:
                            pass
                        self._tick()
            except AuthenticationError as exc:
                if not self._stop.is_set():
                    with self._lock:
                        self.error = str(exc)
                        self.status = "error"
                    self.log("Lỗi xác thực: " + str(exc), "error")
                    self.set_action("Đăng nhập thất bại")
                break
            except (OSError, ConnectionError) as exc:
                if self._stop.is_set():
                    break
                self._reconnect_attempt += 1
                delay = min(30, 2 ** min(self._reconnect_attempt, 5))
                with self._lock:
                    self.error = str(exc)
                    self.status = "reconnecting"
                self.log(f"Mất kết nối: {exc}; sẽ thử lại sau {delay} giây (lần {self._reconnect_attempt})", "error")
                self.set_action(f"Chờ kết nối lại sau {delay} giây")
                if self._stop.wait(delay):
                    break
            except Exception as exc:
                if not self._stop.is_set():
                    with self._lock:
                        self.error = str(exc)
                        self.status = "error"
                    self.log("Bot dừng vì lỗi: " + str(exc), "error")
                    self.set_action("Lỗi bot")
                break
            finally:
                self._socket = None
                self._wire = None
                self._ready = False
        if self._stop.is_set():
            with self._lock:
                self.status = "stopped"
            self.set_action("Đã dừng")

    def _packet(self, command: int, payload: bytes) -> None:
        try:
            reader = Reader(payload)
            if command == -27:
                self._wire.accept_key(payload)
                self._send(-29, bytes([2, 1, 1, 0]) + struct.pack(">ii", 640, 360) +
                           bytes([1, 0]) + java_utf("Python|2.3.1"))
                if self.config.auto_register:
                    self._register()
                else:
                    self._login()
            elif command == -28 and reader.u8() == 4 and not self._finish_sent:
                self._finish_sent = True
                self._send(-38)
                self.set_action("Tải nhân vật")
                self.log("Server xác nhận phiên; đã gửi FINISH_UPDATE")
            elif command == -30:
                self._subcommand(payload)
            elif command == 2 and self._auth_phase == "login":
                self._character_name = "b" + hashlib.sha256(self.config.username.encode()).hexdigest()[:9]
                self._send(-28, bytes([2]) + java_utf(self._character_name) + bytes([self.config.gender, (64, 9, 6)[self.config.gender]]))
                self.set_action("Tạo nhân vật")
                self.log(f"Tài khoản chưa có nhân vật; đã gửi tạo nhân vật {self._character_name}")
            elif command == -42:
                stats = parse_stats(payload)
                with self._lock:
                    for key, value in stats.items():
                        setattr(self, key, value)
            elif command == -24:
                data = parse_map(payload)
                with self._lock:
                    self.map_id, self.map_name, self.zone = data["map_id"], data["map_name"], data["zone"]
                    if self.home_map < 0:
                        self.home_map = self.map_id
                    self.x, self.y = data["x"], data["y"]
                    self.mobs, self.npcs, self.items = data["mobs"], data["npcs"], data["items"]
                    self._focused_mob = None
                    self._mob_last_killed.clear()
                    self.waypoints = data["waypoints"]
                    self._ready = True
                    self._auth_phase = "ready"
                    self.status = "running"
                    self.error = ""
                    self._reconnect_attempt = 0
                    self._travel_attempts = 0
                    self._travel_map = self.map_id
                self._send(-39)
                if not self._client_ok:
                    self._client_ok = True
                    self._send(-28, bytes([13]))
                self._shop_phase = 0
                self.log(f"Vào map {self.map_id} {self.map_name}, khu {self.zone}; {len(self.mobs)} quái")
            elif command == -9:
                mob_id, hp = reader.u8(), reader.i32()
                with self._lock:
                    if mob_id in self.mobs:
                        self.mobs[mob_id].hp = hp
            elif command == -12:
                mob_id = reader.u8()
                reader.raw(5)  # damage and critical flag
                with self._lock:
                    if mob_id in self.mobs:
                        self.mobs[mob_id].hp = 0
                    self.kills += 1
                    self._mob_last_killed[mob_id] = time.monotonic()
                    if self._focused_mob == mob_id:
                        self._focused_mob = None
                for _ in range(reader.u8()):
                    item_map_id, item_id = reader.u16(), reader.u16()
                    x, y, owner = reader.i16(), reader.i16(), reader.i32()
                    self.items[item_map_id] = ItemMap(item_map_id, item_id, x, y, owner)
                self.log(f"Quái {mob_id} chết; vật phẩm trên map: {len(self.items)}")
            elif command == -13:
                mob_id, template, level, hp = reader.u8(), reader.u8(), reader.u8(), reader.i32()
                with self._lock:
                    if mob_id in self.mobs:
                        self.mobs[mob_id].hp = hp
                        self.mobs[mob_id].template_id = template
                        self.mobs[mob_id].boss_level = level
            elif command in (-21, -20):
                item_map_id = reader.u16()
                with self._lock:
                    self.items.pop(item_map_id, None)
                    if command == -20:
                        self.picks += 1
                if command == -20:
                    self.log(f"Nhặt vật phẩm map ID {item_map_id}")
            elif command == -36:
                if reader.u8() == 0:
                    slots: dict[int, int] = {}
                    bag = read_items(reader, slots)
                    with self._lock:
                        self.bag = bag
                        self.bag_slots = slots
            elif command == -35:
                if reader.u8() == 0:
                    slots: dict[int, int] = {}
                    read_items(reader, slots)
                    with self._lock:
                        self.box_slots = slots
            elif command == -34:
                kind = reader.u8()
                if kind == 0:
                    reader.raw(2)
                    reader.utf()
                    reader.raw(5)
                    with self._lock:
                        self._tree_peas = reader.i16()
                        reader.raw(2)
                        reader.utf()
                        self._tree_seconds = reader.i32()
                    self.log(f"Cây đậu có {self._tree_peas} hạt")
                elif kind == 1:
                    with self._lock:
                        self._tree_menu_open = reader.utf().startswith("Thu")
                elif kind == 2:
                    with self._lock:
                        self._tree_peas = reader.i16()
                        self._tree_seconds = reader.i32()
                    self.log(f"Thu hoạch xong; cây còn {self._tree_peas} hạt")
            elif command == 40:
                task = parse_task(payload)
                with self._lock:
                    self.task = task
                    self._quest_step_done = ""
                    self._quest_request_due = 0
                self.log(f"Nhiệm vụ {task['task_id']}: {task['name']} (bước {task['index']})")
            elif command == 41:
                with self._lock:
                    self.task["index"] = self.task.get("index", 0) + 1
                    self._quest_step_done = ""
                    self._quest_request_due = 0
                self.log("Nhiệm vụ sang bước " + str(self.task["index"]))
            elif command == 43:
                with self._lock:
                    self.task["count"] = reader.i16()
            elif command == -44:
                with self._lock:
                    self.shop = parse_shop(payload)
                self.log(f"Shop mở: {len(self.shop)} món")
            elif command == -86:
                self._trade_packet(reader)
            elif command == -17:
                with self._lock:
                    self.hp = 0
                self.log("Nhân vật đã chết")
            elif command == 6:
                with self._lock:
                    self.gold = reader.i64()
            elif command == -3:
                kind, amount = reader.u8(), reader.i32()
                with self._lock:
                    if kind in (0, 2):
                        self.power += amount
                    if kind in (1, 2):
                        self.potential += amount
            elif command in (-25, -26):
                try:
                    notice = reader.utf()
                    self.log("Server: " + notice[:200])
                    self._auth_notice(notice)
                except (ValueError, UnicodeError):
                    self.log(f"Server thông báo cmd {command}")
        except (ValueError, UnicodeError) as exc:
            self.log(f"Không đọc được cmd {command}: {exc}", "error")

    def _register(self) -> None:
        if not 4 <= len(self.config.username) <= 18 or not 5 <= len(self.config.password) <= 18:
            raise AuthenticationError("Đăng ký yêu cầu tài khoản 4–18 và mật khẩu 5–18 ký tự")
        self._auth_phase = "register"
        self._send(42, java_utf("") * 7 + java_utf(self.config.username) + java_utf(self.config.password))
        self.set_action("Kiểm tra tài khoản")
        self.log("Đã gửi kiểm tra/đăng ký tài khoản")

    def _login(self) -> None:
        self._auth_phase = "login"
        self._send(-29, bytes([0]) + java_utf(self.config.username) +
                   java_utf(self.config.password) + java_utf("2.3.1") + bytes([0]))
        self.set_action("Đăng nhập")
        self.log("Đã gửi đăng nhập" + (" sau khi kiểm tra tài khoản" if self._registration_checked else ""))

    def _auth_notice(self, notice: str) -> None:
        if self._auth_phase == "register":
            if "Đăng ký thành công" in notice:
                self.log("Đăng ký tài khoản mới thành công")
            elif "Tài khoản đã tồn tại" in notice:
                self.log("Tài khoản đã tồn tại; chuyển sang đăng nhập")
            else:
                raise AuthenticationError("Đăng ký thất bại: " + notice)
            self._registration_checked = True
            self._login()
        elif self._auth_phase == "login" and "Thông tin tài khoản hoặc mật khẩu không chính xác" in notice:
            raise AuthenticationError("Tài khoản đã tồn tại nhưng mật khẩu không đúng" if self._registration_checked else notice)

    def _subcommand(self, payload: bytes) -> None:
        reader = Reader(payload)
        sub = reader.i8()
        if sub == 0:
            info = parse_player(payload)
            with self._lock:
                for key, value in info.items():
                    setattr(self, key, value)
            self.log(f"Nhân vật {self.character} (ID {self.player_id}) đã vào game")
        elif sub == 4:
            with self._lock:
                self.gold = reader.i64()
                reader.raw(4)
                self.hp, self.mp = reader.i32(), reader.i32()
        elif sub == 5:
            with self._lock:
                self.hp = reader.i32()
        elif sub == 6:
            with self._lock:
                self.mp = reader.i32()
        elif sub == 15:
            reader.raw(4)
            with self._lock:
                self.hp, self.mp = reader.i32(), reader.i32()

    def _task_title(self) -> str:
        index = self.task.get("index", -1)
        steps = self.task.get("steps", [])
        return steps[index].get("title", "") if 0 <= index < len(steps) else ""

    def _trade_packet(self, reader: Reader) -> None:
        action = reader.u8()
        if action == 0:
            player_id = reader.i32()
            if self.config.trade_partner > 0 and player_id == self.config.trade_partner:
                self._send(-86, bytes([1]) + struct.pack(">i", player_id))
                self.log(f"Nhận lời mời giao dịch từ {player_id}")
        elif action == 1:
            player_id = reader.i32()
            if player_id == self.config.trade_partner:
                self._trade_phase = 1
                self._trade_due = time.monotonic() + 1
                self.log(f"Mở giao dịch trống với {player_id}")
        elif action == 7:
            self._trade_phase = 0
            self.log("Giao dịch đã đóng")

    def _tick(self) -> None:
        if not self._ready:
            if self._connected_at and time.monotonic() - self._connected_at > 45:
                raise ConnectionError("Đăng nhập hoặc tải map quá 45 giây")
            return
        if self.status != "running":
            return
        now = time.monotonic()
        if now < self._next_action:
            return
        self._next_action = now + 0.8
        if self._trade_phase:
            self.set_action("Giao dịch trống")
            if now >= self._trade_due:
                if self._trade_phase == 1:
                    self._send(-86, bytes([5]))
                    self._trade_phase = 2
                    self._trade_due = now + 1
                else:
                    self._send(-86, bytes([7]))
                    self._trade_phase = 0
            return
        if self.hp <= 0:
            self.set_action("Về làng hồi sinh")
            self._send(-15)
            self._next_action = now + 5
            return
        if self.config.stat != "off" and now >= self._next_stat:
            self._next_stat = now + 3
            self._upgrade_stat()
        if self._recover(now):
            return
        if self.config.heal_item > 0 and self.bag.get(self.config.heal_item, 0) > 0 and self.max_hp and self.hp * 100 < self.max_hp * 35 and now >= self._next_heal and self.config.heal_item in self.bag_slots:
            self._send(-43, bytes([0, 1, self.bag_slots[self.config.heal_item]]))
            self._next_heal = now + 10
            self.set_action(f"Dùng vật phẩm hồi phục {self.config.heal_item}")
            return
        if self._supply(now):
            return
        self._quest_target_templates.clear()
        if self._quest(now):
            return
        owned_items = [item for item in self.items.values() if item.owner_id in (-1, self.player_id)]
        if owned_items:
            nearest = min(owned_items, key=lambda item: (item.x - self.x) ** 2 + (item.y - self.y) ** 2)
            if abs(nearest.x - self.x) <= 55 and abs(nearest.y - self.y) <= 55:
                self._send(-20, struct.pack(">H", nearest.map_id))
                self.set_action(f"Nhặt item {nearest.template_id}")
                self._next_action = now + 1.1
            else:
                self._move_towards(nearest.x, nearest.y)
                self.set_action(f"Đi nhặt item {nearest.template_id}")
            return
        farm_map = ROUTES.best_farm_map(self.map_id, self.power, self.damage, self._empty_maps)
        if not self._quest_target_templates and farm_map is not None and farm_map != self.map_id:
            if self._travel_to(farm_map, now):
                return
        living = [mob for mob in self.mobs.values() if mob.hp > 0 and mob.status not in (0, 1) and mob.boss_level == 0]
        if not living:
            if not self.mobs:
                self._empty_maps.add(self.map_id)
                farm_map = ROUTES.nearest_farm_map(self.map_id, self._empty_maps)
                if farm_map is not None:
                    self._travel_to(farm_map, now)
                    return
                self.set_action("Đứng yên: map này không có quái và chưa tìm được map farm")
            else:
                self.set_action("Đứng yên: chờ quái hồi sinh")
            return
        hp_limit = max(250, self.damage * 25)
        suitable = [mob for mob in living if mob.level <= ROUTES.player_level(self.power) + 2 and mob.max_hp <= hp_limit]
        if self._quest_target_templates:
            quest_mobs = [mob for mob in living if mob.template_id in self._quest_target_templates]
            if quest_mobs:
                suitable = quest_mobs
        if not suitable:
            self.set_action("Đứng yên: chờ quái phù hợp hồi sinh")
            return
        focused = next((mob for mob in suitable if mob.mob_id == self._focused_mob), None)
        target = focused or max(suitable, key=lambda mob: (mob.level,
                            -self._mob_last_killed.get(mob.mob_id, 0),
                            -((mob.x - self.x) ** 2 + (mob.y - self.y) ** 2)))
        self._focused_mob = target.mob_id
        mob_name = ROUTES.mob_names.get(target.template_id, f"loại {target.template_id}")
        if abs(target.x - self.x) > 55 or abs(target.y - self.y) > 55:
            self._move_towards(target.x, target.y)
            self.set_action(f"Đang đi tới quái {mob_name} (ID {target.mob_id})")
        else:
            self._send(54, bytes([target.mob_id]))
            self.set_action(f"Đang đánh quái {mob_name} (ID {target.mob_id}, HP {target.hp})")

    def _recover(self, now: float) -> bool:
        if self.max_mp <= 0:
            return False
        low_ki = self.mp <= max(5, self.max_mp // 10)
        if not self._recovering and not low_ki:
            return False
        if self._recovering and self.mp >= max(10, self.max_mp // 2):
            self._recovering = False
            self._harvest_attempts = 0
            self.set_action("KI đã hồi; quay lại farm")
            return False
        self._recovering = True
        self._focused_mob = None
        if now < self._recover_due:
            return True
        pea = next((item for item in PEA_ITEMS if self.bag.get(item, 0) > 0 and item in self.bag_slots), None)
        if pea is not None:
            self._send(-43, bytes([0, 1, self.bag_slots[pea]]))
            self._recover_due = now + 2
            self.set_action(f"Ăn đậu thần cấp {PEA_ITEMS.index(pea) + 1} để hồi KI")
            return True
        home = 21 + self.gender
        if self.map_id != home:
            self._send(-15)
            self._recover_due = now + 5
            self.set_action("Hết KI; về nhà thu hoạch đậu")
            return True
        if self._tree_menu_open:
            self._send(22, bytes([0, 0]))
            self._tree_menu_open = False
            self._tree_peas = -1
            self._recover_due = now + 3
            self._harvest_attempts += 1
            self.set_action("Đang thu hoạch đậu thần")
            return True
        if self._tree_peas > 0 and self._harvest_attempts < 3:
            self._send(-34, bytes([1]))
            self._recover_due = now + 2
            self.set_action(f"Cây có {self._tree_peas} hạt; mở menu thu hoạch")
            return True
        if self._tree_peas == -1:
            self._send(-34, bytes([2]))
            self._recover_due = now + 3
            self.set_action("Kiểm tra cây đậu ở nhà")
            return True
        self._recover_due = now + 30
        self.set_action("Đứng ở nhà chờ cây đậu kết hạt")
        return True

    def _move_towards(self, target_x: int, target_y: int) -> None:
        dx, dy = target_x - self.x, target_y - self.y
        x = self.x + max(-42, min(42, dx))
        y = self.y + max(-24, min(24, dy))
        if y <= 0:
            y = max(1, self.y)
        self._send(-7, bytes([0]) + struct.pack(">hh", x, y))
        self.x, self.y = x, y

    def _upgrade_stat(self) -> None:
        choices = {"balanced": (0, 1, 2, 3), "hp": (0,), "mp": (1,), "attack": (2,), "def": (3,)}.get(self.config.stat, ())
        for offset in range(len(choices)):
            stat = choices[(self._stat_cursor + offset) % len(choices)]
            cost = (self.base_hp + 1000, self.base_mp + 1000, self.base_damage * 100,
                    (self.base_defense + 5) * 100000)[stat]
            if 0 < cost <= self.potential:
                self._send(-30, bytes([16, stat]) + struct.pack(">h", 1))
                self._stat_cursor = (self._stat_cursor + offset + 1) % len(choices)
                self.log(f"Cộng 1 điểm {('HP', 'KI', 'sức đánh', 'giáp')[stat]}")
                return

    def _supply(self, now: float) -> bool:
        cfg = self.config
        if cfg.shop_item <= 0 or cfg.shop_min <= 0 or (self._shop_phase != 3 and self.bag.get(cfg.shop_item, 0) >= cfg.shop_min):
            self._shop_phase = 0
            return False
        if self._shop_phase == 4:
            return False
        if cfg.shop_map >= 0 and cfg.shop_map != self.map_id:
            return self._travel_to(cfg.shop_map, now)
        npc = self.npcs.get(cfg.shop_npc)
        if npc is None:
            self.set_action(f"Thiếu item {cfg.shop_item}; chờ NPC shop {cfg.shop_npc} ở map hiện tại")
            return True
        if abs(npc[0] - self.x) > 55:
            self._move_towards(*npc)
            self.set_action(f"Đi tới NPC shop {cfg.shop_npc}")
            return True
        if self._shop_phase == 0:
            self.shop = {}
            self._send(33, struct.pack(">h", cfg.shop_npc))
            self._shop_phase = 1
            self._next_shop = now + 0.8
            self.set_action(f"Mở shop NPC {cfg.shop_npc}")
            return True
        if self._shop_phase == 1 and now >= self._next_shop:
            self._send(32, struct.pack(">hb", cfg.shop_npc, cfg.shop_menu))
            self._shop_phase = 2
            self._next_shop = now + 8
            self.set_action("Chờ danh sách shop")
            return True
        if self._shop_phase == 2:
            price = self.shop.get(cfg.shop_item)
            if price and price["gold"] > 0 and price["gems"] == 0 and self.gold >= price["gold"]:
                self._shop_phase = 3
                self._shop_attempts = 0
                self._shop_before = -1
            elif now >= self._next_shop:
                self.set_action("Không mua được: shop thiếu item hoặc thiếu vàng")
                self._shop_phase = 4
            return True
        if self._shop_phase == 3:
            count = self.bag.get(cfg.shop_item, 0)
            if count >= cfg.shop_target:
                self._shop_phase = 0
                self.set_action("Mua tiếp tế xong")
            elif count == self._shop_before and self._shop_attempts >= 3:
                self._shop_phase = 4
                self.set_action("Dừng mua: túi không tăng sau 3 lần")
            elif now >= self._next_shop:
                self._shop_attempts = self._shop_attempts + 1 if count == self._shop_before else 1
                self._shop_before = count
                self._send(6, bytes([0]) + struct.pack(">h", cfg.shop_item))
                self.purchases += 1
                self._next_shop = now + 1.3
                self.set_action(f"Mua item {cfg.shop_item} ({count}/{cfg.shop_target})")
            return True
        return True

    def _quest(self, now: float) -> bool:
        task = self.task
        task_id = task.get("task_id", -1)
        index = task.get("index", -1)
        steps = task.get("steps", [])
        if index < 0 or index >= len(steps):
            return False
        step = steps[index]
        if task_id == 0 and index == 0:
            training_map = 39 + self.gender
            if self.map_id != training_map:
                return self._travel_to(training_map, now)
            self._move_towards(650, self.y)
            self.set_action("Nhiệm vụ 0: đi tới mũi tên trong nhà")
            return True
        if step["map_id"] >= 0 and step["map_id"] != self.map_id:
            return self._travel_to(step["map_id"], now)
        if task_id == 0 and index == 3:
            npc = self.npcs.get(3)
            if npc is None:
                self.set_action("Nhiệm vụ 0: chờ rương đồ trong nhà")
                return True
            if (npc[0] - self.x) ** 2 + (npc[1] - self.y) ** 2 > 55 ** 2:
                self._move_towards(*npc)
                self.set_action("Nhiệm vụ 0: đi tới rương đồ")
                return True
            if not self.box_slots:
                if now >= self._quest_request_due:
                    self._send(33, struct.pack(">h", 3))
                    self._quest_request_due = now + 3
                self.set_action("Nhiệm vụ 0: mở rương đồ")
                return True
            if now >= self._quest_request_due:
                self._send(-40, bytes([0, min(self.box_slots.values())]))
                self._quest_request_due = now + 5
            self.set_action("Nhiệm vụ 0: lấy vật phẩm từ rương")
            return True
        if task_id == 0 and index == 4:
            if self._tree_menu_open:
                self._send(22, bytes([0, 0]))
                self._tree_menu_open = False
                self._quest_request_due = now + 5
                self.set_action("Nhiệm vụ 0: thu hoạch đậu thần")
                return True
            if now >= self._quest_request_due:
                self._send(-34, bytes([1]))
                self._quest_request_due = now + 3
            self.set_action("Nhiệm vụ 0: mở cây đậu")
            return True
        npc_id = step["npc_id"]
        if npc_id < 0:
            title = step.get("title", "").casefold()
            if title.startswith(("tiêu diệt", "diệt ", "đánh ", "hạ ")):
                matches = {template for template, name in ROUTES.mob_names.items() if name.casefold() in title}
                if matches:
                    self._quest_target_templates = matches
                    goal = ROUTES.best_farm_map(self.map_id, self.power, self.damage,
                                               target_templates=matches)
                    if goal is not None and goal != self.map_id:
                        return self._travel_to(goal, now)
            return False
        key = f"{task['task_id']}:{index}"
        if self._quest_step_done == key and now < self._quest_request_due:
            self.set_action(f"Chờ server xác nhận nhiệm vụ NPC {npc_id}")
            return True
        npc = self.npcs.get(npc_id)
        if npc is None:
            self.set_action(f"Chờ NPC nhiệm vụ {npc_id}")
            return True
        if (npc[0] - self.x) ** 2 + (npc[1] - self.y) ** 2 > 55 ** 2:
            self._move_towards(*npc)
            self.set_action(f"Đi tới NPC nhiệm vụ {npc_id}")
            return True
        self._send(33, struct.pack(">h", npc_id))
        self._quest_step_done = key
        self._quest_request_due = now + 5
        self.set_action(f"Nói chuyện NPC nhiệm vụ {npc_id}")
        return True

    def _travel_to(self, goal: int, now: float) -> bool:
        if goal == self.map_id:
            return False
        waypoint = ROUTES.next_hop(self.map_id, goal)
        if waypoint is None:
            self.set_action(f"Đứng yên: không có đường từ map {self.map_id} tới {goal}")
            return True
        live = next((wp for wp in self.waypoints if tuple(wp["bounds"]) == waypoint["bounds"]), None)
        if live is None:
            self.set_action(f"Đứng yên: không thấy cổng sang map {waypoint['go_map']}")
            return True
        if self._travel_goal != goal or self._travel_map != self.map_id:
            self._travel_goal, self._travel_map = goal, self.map_id
            self._travel_attempts = 0
            self._travel_next = 0
        x1, y1, x2, y2 = live["bounds"]
        x, y = (x1 + x2) // 2, (y1 + y2) // 2
        if abs(x - self.x) > 12 or abs(y - self.y) > 12:
            self._move_towards(x, y)
            self.set_action(f"Đang đi tới cổng sang map {waypoint['go_map']}")
            return True
        if now >= self._travel_next and self._travel_attempts < 3:
            self._send(-23)
            self._travel_attempts += 1
            self._travel_next = now + 5
            self.set_action(f"Đang qua cổng tới map {waypoint['go_map']} (lần {self._travel_attempts})")
        elif self._travel_attempts >= 3 and now >= self._travel_next:
            self.set_action(f"Đứng yên: kẹt tại cổng sang map {waypoint['go_map']}")
        return True


class BotManager:
    MAX_BOTS = 50

    def __init__(self, store: ConfigStore | None = None):
        self._lock = threading.RLock()
        self._bots: dict[str, BotRunner] = {}
        self._store = store or ConfigStore()
        self._closing = False
        for record in self._store.load():
            bot_id = record["id"]
            if not isinstance(bot_id, str) or not re.fullmatch(r"[0-9a-f]{10}", bot_id):
                raise ValueError("ID bot đã lưu không hợp lệ")
            config = BotConfig(**record["config"])
            self._bots[bot_id] = BotRunner(config, bot_id)

    def _save(self) -> None:
        self._store.save([{"id": bot.id, "config": asdict(bot.config)} for bot in self._bots.values()])

    def create(self, config: BotConfig) -> BotRunner:
        return self.create_many([config])[0]

    def create_many(self, configs: list[BotConfig]) -> list[BotRunner]:
        with self._lock:
            if not configs or len(self._bots) + len(configs) > self.MAX_BOTS:
                raise ValueError(f"Tối đa {self.MAX_BOTS} bot trong một ứng dụng")
            existing = {(bot.config.host, bot.config.port, bot.config.username.lower()) for bot in self._bots.values()}
            for config in configs:
                key = (config.host, config.port, config.username.lower())
                if key in existing:
                    raise ValueError(f"Tài khoản {config.username} đã có bot trên server này")
                existing.add(key)
            created = [BotRunner(config) for config in configs]
            for bot in created:
                self._bots[bot.id] = bot
            try:
                self._save()
            except Exception:
                for bot in created:
                    self._bots.pop(bot.id, None)
                    bot.close()
                raise
            return created

    def start_many(self, bots: list[BotRunner]) -> None:
        def stagger() -> None:
            for bot in bots:
                with self._lock:
                    if self._closing:
                        return
                    present = self._bots.get(bot.id) is bot
                if present:
                    bot.start()
                time.sleep(0.3)
        threading.Thread(target=stagger, name="BotBatchStart", daemon=True).start()

    def get(self, bot_id: str) -> BotRunner:
        with self._lock:
            if bot_id not in self._bots:
                raise KeyError(bot_id)
            return self._bots[bot_id]

    def all(self) -> list[dict]:
        with self._lock:
            return [bot.snapshot() for bot in self._bots.values()]

    def remove(self, bot_id: str) -> None:
        bot = self.get(bot_id)
        bot.close()
        with self._lock:
            self._bots.pop(bot_id, None)
            self._save()

    def update_config(self, bot_id: str, config: BotConfig) -> BotRunner:
        with self._lock:
            bot = self.get(bot_id)
            old = bot.config
            if (config.username, config.host, config.port) != (old.username, old.host, old.port):
                raise ValueError("Không thể đổi tài khoản hoặc server của bot đã tạo")
            bot.config = config
            bot._shop_phase = 0
            try:
                self._save()
            except Exception:
                bot.config = old
                raise
            return bot

    def close(self) -> None:
        with self._lock:
            self._closing = True
            bots = list(self._bots.values())
        for bot in bots:
            bot.close()
