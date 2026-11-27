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
from concurrent.futures import Future
from dataclasses import asdict, dataclass, field
from logging.handlers import RotatingFileHandler
from pathlib import Path

from protocol import ItemMap, Reader, Wire, java_utf, parse_map, parse_player, parse_shop, parse_stats, parse_task, read_items
from movement import MovementUtility
from routes import Routes
from storage import ConfigStore
from ai.local_model import EXECUTOR as AI_EXECUTOR, MODEL_CLIENT
from ai import memory as ai_memory

LOG_DIR = Path(__file__).resolve().parent / "logs"
ROUTES = Routes()
MOVEMENT = MovementUtility(ROUTES)
PEA_ITEMS = (13, 60, 61, 62, 63, 64, 65, 352, 523, 595)
GREEN_GRAPE_ID = 212
STARTER_GEAR = ((21, 6, 0, 27, 12), (22, 7, 1, 28, 12),
                (23, 8, 2, 29, 12))  # Gloves, pants, shirt, shoes, radar.
PLANET_VILLAGE_MAPS = (0, 7, 14)  # Earth, Namek, Xayda
PLANET_SHOP_NPCS = (7, 8, 9)  # Bunma, Dende, Appule
DRAGON_BALL_7_STAR_ID = 20
MOTHER_LIZARD_TEMPLATE_ID = 10
MOTHER_LIZARD_MAP_ID = 4  # Rừng Xương, Trái Đất
# Verified against Server/services/MobService.dropItemTask(): these are the
# mobs that actually produce quest drops, paired with the race-specific maps.
QUEST_ITEM_HUNT_RULES = {
    (2, 0): {"maps": (1, 8, 15), "mobs": (1, 2, 3), "item": 73, "name": "đùi gà"},
    (8, 1): {"maps": (MOTHER_LIZARD_MAP_ID,) * 3,
             "mobs": (MOTHER_LIZARD_TEMPLATE_ID,) * 3, "item": DRAGON_BALL_7_STAR_ID,
             "name": "Ngọc Rồng 7 sao"},
    (14, 1): {"maps": (5, 13, 20), "mobs": (13, 14, 15), "item": 85,
              "name": "Truyện Doremon tập 2"},
}
XAYDA_ENERGY_SKILL_IDS = frozenset(range(56, 63))
SKILL_BOOK_BASES = {66: 0, 79: 2, 87: 4, 94: 1, 101: 3,
                    108: 5, 115: 6, 122: 7, 129: 8}
HOME_NPC_IDS = (0, 2, 1)  # Gohan, Moori, Paragus
PLANET_MAPS = (
    frozenset((*range(0, 7), 21, 24, 39, 42)),
    frozenset((*range(7, 14), 22, 25, 40, 43)),
    frozenset((*range(14, 21), 23, 26, 41, 44)),
)
NICKNAME_BASES = (
    "Bao", "Bap", "Bin", "BoSu", "CuTi", "Duc", "Goku", "Huy", "Khanh",
    "KemDau", "Kiet", "Linh", "MeoMun", "Minh", "MiuMiu", "Nam", "Ngoc",
    "Phuc", "Quang", "TuanAnh",
)


def human_nickname(seed: str) -> str:
    """Build a short, game-safe nickname that looks like a player handle."""
    digest = hashlib.sha256(seed.casefold().encode("utf-8")).digest()
    base = NICKNAME_BASES[digest[0] % len(NICKNAME_BASES)]
    suffix = 100 + int.from_bytes(digest[1:3], "big") % 900
    return f"{base}{suffix}"


def character_nickname(config: BotConfig) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9]", "", config.name)
    if 5 <= len(cleaned) <= 10 and not cleaned.casefold().startswith("bot"):
        return cleaned
    return human_nickname(config.username)


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
        self.head_id = -1
        self.learned_skill_ids: set[int] = set()
        self.character = ""
        self.map_id = -1
        self.map_name = ""
        self.zone = -1
        self.home_map = -1
        self.x = self.y = 0
        self.hp = self.mp = self.max_hp = self.max_mp = 0
        self.stamina = self.max_stamina = 0
        self.gold = self.gems = self.potential = self.power = 0
        self.damage = self.defense = 0
        self.base_hp = self.base_mp = self.base_damage = self.base_defense = 0
        self.mobs: dict = {}
        self.npcs: dict = {}
        self.waypoints: list[dict] = []
        self.items: dict[int, ItemMap] = {}
        self.bag: dict[int, int] = {}
        self.bag_slots: dict[int, int] = {}
        self.box_slots: dict[int, int] = {}
        self.bag_details: dict[int, dict] = {}
        self.box_details: dict[int, dict] = {}
        self.worn_details: dict[int, dict] = {}
        self._pending_item_action: tuple[str, int, int] | None = None
        self._item_feedback = ""
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
        self._next_gear = 0.0
        self._shop_phase = 0
        self._shop_attempts = 0
        self._shop_before = -1
        self._shop_current_item = 0
        self._quest_step_done = ""
        self._quest_request_due = 0.0
        self._karin_boss_id: int | None = None
        self._karin_boss_pos = (0, 0)
        self._karin_boss_due = 0.0
        self._tau_boss_pos = (775, 0)
        self._skip_quest_id: int | None = None
        self._skip_quest_due = 0.0
        self._skip_quest_sent = False
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
        self._travel_step: tuple[int, int, str] | None = None
        self._travel_phase = ""
        self._travel_npc = -1
        self._travel_menu = -1
        self._travel_blocked: dict[tuple[int, int, str], float] = {}
        self._travel_progress_at = 0.0
        self._travel_last_distance = 0
        self._empty_maps: set[int] = set()
        self._focused_mob: int | None = None
        self._mob_last_killed: dict[int, float] = {}
        self._mob_attack_watch: dict[int, tuple[int, float]] = {}
        self._quest_target_templates: set[int] = set()
        self._ai_future: Future | None = None
        self._ai_next = 0.0
        self._ai_shop_goal: tuple[int, int] | None = None
        self._ai_shop_phase = ""
        self._ai_shop_due = 0.0
        self._ai_shop_cooldown: dict[str, float] = {}
        self._ai_action_cooldown: dict[str, float] = {}
        self._ai_selected_skill = -1
        self._ai_feedback: tuple[str, str, dict, float] | None = None
        self._ai_goal = "quest"
        self._ai_goal_until = 0.0
        self._ai_stat_focus = ""
        self._reconnect_attempt = 0
        self._recovering = False
        self._recover_hp_target = False
        self._recover_mp_target = False
        self._recover_due = 0.0
        self._pending_recovery_bean: tuple[int, int, int] | None = None
        self._stamina_recovery = False
        self._stamina_return_map = -1
        self._stamina_shop_phase = 0
        self._stamina_shop_next = 0.0
        self._stamina_shop_attempts = 0
        self._stamina_shop_before = -1
        self._stamina_shop_target = 0
        self._stamina_retry_after = 0.0
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
                "head_id": self.head_id, "avatar_id": ROUTES.avatar_by_head.get(self.head_id, -1),
                "reconnect_attempt": self._reconnect_attempt,
                "status": self.status, "action": self.action,
                "error": self.error, "player_id": self.player_id, "character": self.character,
                "map_id": self.map_id, "map_name": self.map_name, "zone": self.zone,
                "x": self.x, "y": self.y,
                "hp": self.hp, "max_hp": self.max_hp, "mp": self.mp, "max_mp": self.max_mp,
                "stamina": self.stamina, "max_stamina": self.max_stamina,
                "gold": self.gold, "gems": self.gems, "power": self.power, "potential": self.potential,
                "ai_installed": MODEL_CLIENT.installed(),
                "ai_goal": self._ai_goal, "ai_stat_focus": self._ai_stat_focus,
                "damage": self.damage, "defense": self.defense, "kills": self.kills,
                "picks": self.picks, "purchases": self.purchases, "mobs": len(self.mobs),
                "items": len(self.items), "task": self.task.get("name", ""),
                "task_step": self.task.get("index", -1), "last_packet": self.last_packet,
                "task_title": self._task_title(), "task_count": self.task.get("count", 0),
                "bag": dict(self.bag), "bag_details": self._named_items(self.bag_details),
                "box_details": self._named_items(self.box_details), "worn_details": self._named_items(self.worn_details),
                "item_feedback": self._item_feedback,
                "shop_item": self.config.shop_item,
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

    @staticmethod
    def _named_items(items: dict[int, dict]) -> dict[int, dict]:
        return {item_id: {**item, "name": ROUTES.item_names.get(item_id, f"Vật phẩm #{item_id}"),
                          "description": ROUTES.item_descriptions.get(item_id, item.get("description", "")),
                          "type": ROUTES.item_types.get(item_id, -1),
                          "icon_id": ROUTES.item_icon_ids.get(item_id, -1),
                          "options": [{**option, "label": (name.replace("#", str(option["param"]))
                                                  if name else "")}
                                      for option in item.get("options", [])
                                      for name in [ROUTES.option_names.get(option["id"],
                                                   f"Chỉ số {option['id']}: {option['param']}")]]}
                for item_id, item in items.items()}

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
            self._karin_boss_id = None
            self._skip_quest_id = None
            self._skip_quest_due = 0
            self._skip_quest_sent = False
            self._trade_phase = 0
            self._travel_goal = self._travel_map = -1
            self._travel_attempts = 0
            self._travel_step = None
            self._travel_phase = ""
            self._travel_npc = self._travel_menu = -1
            self._travel_blocked.clear()
            self._travel_next = self._travel_progress_at = 0
            self._travel_last_distance = 0
            self._empty_maps.clear()
            self._focused_mob = None
            self._mob_last_killed.clear()
            self._mob_attack_watch.clear()
            self._quest_target_templates.clear()
            self._ai_future = None
            self._ai_next = 0
            self._ai_shop_goal = None
            self._ai_shop_phase = ""
            self._ai_shop_cooldown.clear()
            self._ai_action_cooldown.clear()
            self._ai_selected_skill = -1
            self._ai_feedback = None
            self._ai_goal = "quest"
            self._ai_goal_until = 0
            self._ai_stat_focus = ""
            self._reconnect_attempt = 0
            self._recovering = False
            self._recover_hp_target = False
            self._recover_mp_target = False
            self._recover_due = 0
            self._pending_recovery_bean = None
            self._stamina_recovery = False
            self._stamina_return_map = -1
            self._stamina_shop_phase = 0
            self._stamina_shop_next = 0
            self._stamina_shop_attempts = 0
            self._stamina_shop_before = -1
            self._stamina_shop_target = 0
            self._stamina_retry_after = 0
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
            self.learned_skill_ids.clear()
            self.power = self.potential = self.gold = self.gems = 0
            self.hp = self.mp = self.max_hp = self.max_mp = 0
            self.stamina = self.max_stamina = 0
            self.damage = self.defense = 0
            self.home_map = self.map_id = -1
            self.mobs, self.npcs, self.items, self.bag, self.bag_slots, self.box_slots = {}, {}, {}, {}, {}, {}
            self.bag_details, self.box_details, self.worn_details, self.shop, self.task = {}, {}, {}, {}, {}
            self._pending_item_action = None
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

    def item_action(self, action: str, location: str, item_id: int) -> None:
        if self.status != "running":
            raise ValueError("Bot phải đang chạy để thao tác vật phẩm")
        if location == "box":
            slot = self.box_details.get(item_id, {}).get("slot")
            if slot is None or action not in ("take", "take_use", "take_throw", "take_equip"):
                raise ValueError("Không tìm thấy vật phẩm trong rương")
            self._send(-40, bytes([0, slot]))
            if action in ("take_use", "take_throw", "take_equip"):
                self._pending_item_action = (action, item_id, 0)
            self.log(f"Chuyển {self.box_details[item_id].get('info') or f'vật phẩm #{item_id}'} từ rương vào túi")
            return
        if location == "worn":
            if action != "unequip" or item_id not in self.worn_details:
                raise ValueError("Trang bị này không thể tháo")
            slot = self.worn_details[item_id]["slot"]
            self._send(-40, bytes([5, slot]))
            self.log(f"Tháo {self.worn_details[item_id].get('info') or f'vật phẩm #{item_id}'} vào túi")
            return
        if location != "bag" or item_id not in self.bag_details:
            raise ValueError("Không tìm thấy vật phẩm trong túi")
        slot = self.bag_details[item_id]["slot"]
        if action == "equip":
            item_type = ROUTES.item_types.get(item_id, -1)
            if item_type not in (0, 1, 2, 3, 4):
                raise ValueError("Vật phẩm này không phải trang bị")
            self._send(-40, bytes([4, slot]))
            self.log(f"Mặc {ROUTES.item_names.get(item_id, f'vật phẩm #{item_id}')}")
            return
        if action == "use":
            self._item_feedback = "Đã gửi yêu cầu sử dụng; chờ server phản hồi."
            self._pending_item_action = ("use", 1, slot)
            self._send(-43, bytes([0, 1, slot]))
            self.log(f"Dùng {self.bag_details[item_id].get('info') or f'vật phẩm #{item_id}'}")
        elif action == "throw":
            self._item_feedback = "Đã gửi yêu cầu bỏ vật phẩm."
            self._pending_item_action = ("throw", 1, slot)
            self._send(-43, bytes([1, 1, slot]))
            self.log(f"Bỏ {self.bag_details[item_id].get('info') or f'vật phẩm #{item_id}'}")
        else:
            raise ValueError("Thao tác vật phẩm không hợp lệ")

    def request_box(self) -> None:
        if self.status != "running":
            raise ValueError("Bot phải đang chạy để mở rương")
        home = 21 + self.gender
        if self.map_id != home:
            raise ValueError(f"Rương chỉ mở được ở {self._map_label(home)}; bot đang ở {self._map_label(self.map_id)}")
        npc = self.npcs.get(3)
        if npc is None or (npc[0] - self.x) ** 2 + (npc[1] - self.y) ** 2 > 55 ** 2:
            raise ValueError("Bot cần đứng gần rương đồ trong nhà")
        self._send(33, struct.pack(">h", 3))
        self.log("Mở rương đồ để tải vật phẩm")

    def request_skip_quest(self) -> None:
        if self.status != "running" or not self._ready:
            raise ValueError("Bot cần vào game trước khi bỏ qua nhiệm vụ")
        task_id = self.task.get("task_id")
        if task_id is None:
            raise ValueError("Chưa nhận được nhiệm vụ hiện tại từ server")
        with self._lock:
            if self._skip_quest_id is not None:
                raise ValueError("Bot đang chờ bỏ qua nhiệm vụ")
            self._skip_quest_id = task_id
            self._skip_quest_due = 0
            self._skip_quest_sent = False
            self._next_action = 0
            self.error = ""
            if self.config.mode == "ai":
                self._ai_goal = "quest"
                self._ai_goal_until = 0
                self._ai_action_cooldown["goal:farm"] = time.monotonic() + 300
        self.log(f"Yêu cầu bỏ qua nhiệm vụ {task_id}; bot sẽ về nhà trước")

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
        self._travel_step = None
        self._travel_phase = ""
        self._travel_npc = self._travel_menu = -1
        self._travel_blocked.clear()
        self._travel_progress_at = self._travel_last_distance = 0
        self._empty_maps.clear()
        self._focused_mob = None
        self._mob_last_killed.clear()
        self._mob_attack_watch.clear()
        self._quest_target_templates.clear()
        self._recovering = False
        self._recover_hp_target = False
        self._recover_mp_target = False
        self._recover_due = 0
        self._pending_recovery_bean = None
        self._stamina_recovery = False
        self._stamina_return_map = -1
        self._stamina_shop_phase = 0
        self._stamina_shop_next = 0
        self._stamina_shop_attempts = 0
        self._stamina_shop_before = -1
        self._stamina_shop_target = 0
        self._stamina_retry_after = 0
        self._tree_peas = -1
        self._tree_seconds = 0
        self._tree_menu_open = False
        self._harvest_attempts = 0
        self.player_id = 0
        self.character = ""
        self.gender = self.config.gender
        self.learned_skill_ids.clear()
        self.hp = self.mp = self.max_hp = self.max_mp = 0
        self.stamina = self.max_stamina = 0
        self.gold = self.gems = self.power = self.potential = 0
        self.damage = self.defense = 0
        self.home_map = self.map_id = -1
        self.mobs, self.npcs, self.items, self.bag, self.bag_slots, self.box_slots, self.shop, self.task = {}, {}, {}, {}, {}, {}, {}, {}
        self.bag_details = self.box_details = self.worn_details = {}
        self._pending_item_action = None

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
                self._character_name = character_nickname(self.config)
                self._send(-28, bytes([2]) + java_utf(self._character_name) + bytes([self.config.gender, (64, 9, 6)[self.config.gender]]))
                self.set_action("Tạo nhân vật")
                self.log(f"Tài khoản chưa có nhân vật; đã gửi tạo nhân vật {self._character_name}")
            elif command == -42:
                stats = parse_stats(payload)
                with self._lock:
                    for key, value in stats.items():
                        setattr(self, key, value)
            elif command == -68:
                stamina = reader.i16()
                previous_stamina = self.stamina
                self.stamina = stamina
                if self._stamina_recovery and stamina != previous_stamina:
                    self.log(f"Thể lực: {stamina}/{self.max_stamina}")
            elif command == -69:
                self.max_stamina = reader.i16()
            elif command == -24:
                data = parse_map(payload)
                with self._lock:
                    self.map_id, self.map_name, self.zone = data["map_id"], data["map_name"], data["zone"]
                    if self.home_map < 0:
                        self.home_map = self.map_id
                    self.x, self.y = data["x"], data["y"]
                    self.mobs, self.npcs, self.items = data["mobs"], data["npcs"], data["items"]
                    self.shop = {}
                    self._focused_mob = None
                    self._mob_last_killed.clear()
                    self._mob_attack_watch.clear()
                    self._karin_boss_id = None
                    self.waypoints = data["waypoints"]
                    self._ready = True
                    self._auth_phase = "ready"
                    self.status = "running"
                    self.error = ""
                    self._reconnect_attempt = 0
                    self._travel_attempts = 0
                    self._travel_map = self.map_id
                    self._travel_step = None
                    self._travel_phase = ""
                    self._travel_npc = self._travel_menu = -1
                self._send(-39)
                if not self._client_ok:
                    self._client_ok = True
                    self._send(-28, bytes([13]))
                self._shop_phase = 0
                self.log(f"Vào {self._map_label(self.map_id)}, khu {self.zone}; {len(self.mobs)} quái")
            elif command == 46:
                with self._lock:
                    self.x, self.y = reader.i16(), reader.i16()
            elif command == -7:
                moving_id, moving_x, moving_y = reader.i32(), reader.i16(), reader.i16()
                if moving_id == self._karin_boss_id:
                    self._karin_boss_pos = (moving_x, moving_y)
                elif moving_id == -10251003 - self.player_id:
                    self._tau_boss_pos = (moving_x, moving_y)
            elif command == 32:
                npc_id, _ = reader.i16(), reader.utf()
                option_count = reader.u8()
                options = [reader.utf() for _ in range(option_count)]
                if (npc_id == 18 and self.map_id == 46 and self.task.get("task_id") == 10
                        and self.task.get("index") == 0):
                    labels = [option.casefold().replace("\n", " ") for option in options]
                    selected = next((index for index, label in enumerate(labels)
                                     if "đồng ý" in label and "giao đấu" in label), None)
                    if selected is None:
                        selected = next((index for index, label in enumerate(labels)
                                         if "thách đấu" in label and "thần mèo" in label), None)
                    if selected is not None:
                        self._send(32, struct.pack(">hb", npc_id, selected))
                        self._quest_request_due = time.monotonic() + 10
                        if "đồng ý" in labels[selected] and "giao đấu" in labels[selected]:
                            signed_id = ((self.player_id + 128) % 256) - 128
                            self._karin_boss_id = -351003 - signed_id
                            self._karin_boss_pos = (420, 408)
                            self._karin_boss_due = time.monotonic() + 60
                        self.set_action("Chọn thách đấu Thần Mèo Karin")
                        return
                step = self._travel_step
                if (step and step[2] == "spaceship" and self._travel_phase == "menu"
                        and npc_id == self._travel_npc):
                    if 0 <= self._travel_menu < option_count:
                        self._send(32, struct.pack(">hb", npc_id, self._travel_menu))
                        self._travel_phase = "wait"
                        self._travel_next = time.monotonic() + 8
                        self.set_action(f"Đã chọn tàu từ {self._map_label(step[0])} tới {self._map_label(step[1])}")
                    else:
                        self._block_travel_step(time.monotonic(), "Menu tàu không có lựa chọn đích")
            elif command == 38:
                if self._travel_step and self._travel_step[2] == "spaceship" and self._travel_phase == "menu":
                    npc_id = reader.i16()
                    notice = reader.utf() if reader.pos < len(payload) else "NPC không mở menu tàu"
                    if "cứu đứa bé" in notice.casefold():
                        reason = "Tàu liên hành tinh đang khóa trong Nhiệm vụ giải cứu"
                    else:
                        reason = f"NPC {npc_id} không mở menu tàu: {notice[:100]}"
                    self._block_travel_step(time.monotonic(), reason)
            elif command == -9:
                mob_id, hp = reader.u8(), reader.i32()
                with self._lock:
                    if mob_id in self.mobs:
                        mob = self.mobs[mob_id]
                        if mob.hp != hp:
                            self._mob_attack_watch[mob_id] = (hp, time.monotonic())
                        mob.hp = hp
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
                        mob = self.mobs[mob_id]
                        if mob.hp != hp:
                            self._mob_attack_watch[mob_id] = (hp, time.monotonic())
                        mob.hp = hp
                        self.mobs[mob_id].template_id = template
                        self.mobs[mob_id].boss_level = level
            elif command == -5:
                self._quest_boss_player_packet(reader)
            elif command == 68:
                item_map_id, item_id = reader.u16(), reader.u16()
                x, y, owner_id = reader.i16(), reader.i16(), reader.i32()
                if owner_id == -2 and reader.pos + 2 <= len(payload):
                    reader.u16()  # range for items shared with everyone
                item = ItemMap(item_map_id, item_id, x, y, owner_id)
                with self._lock:
                    self.items[item_map_id] = item
                item_name = ROUTES.item_names.get(item_id, f"vật phẩm ID {item_id}")
                self.log(f"Vật phẩm rơi: {item_name} (ID vật phẩm trên map: {item_map_id}, chủ sở hữu {owner_id})")
            elif command in (-21, -20):
                item_map_id = reader.u16()
                with self._lock:
                    self.items.pop(item_map_id, None)
                    if command == -20:
                        self.picks += 1
                if command == -20:
                    self.log(f"Nhặt vật phẩm có ID trên map: {item_map_id}")
            elif command == -36:
                if reader.u8() == 0:
                    slots: dict[int, int] = {}
                    details: dict[int, dict] = {}
                    bag = read_items(reader, slots, details)
                    old_grapes = self.bag.get(GREEN_GRAPE_ID, 0)
                    new_grapes = bag.get(GREEN_GRAPE_ID, 0)
                    with self._lock:
                        self.bag = bag
                        self.bag_slots = slots
                        self.bag_details = details
                    if self._stamina_recovery and new_grapes > old_grapes:
                        bought = new_grapes - old_grapes
                        self.purchases += bought
                        self.log(f"Mua Nho xanh thành công: +{bought}, trong túi {new_grapes}")
                    elif self._stamina_recovery and new_grapes < old_grapes:
                        self.log(f"Đã dùng Nho xanh: còn {new_grapes}")
                    recovery_bean = self._pending_recovery_bean
                    if recovery_bean:
                        item_id, count_before, level = recovery_bean
                        if bag.get(item_id, 0) < count_before:
                            self._pending_recovery_bean = None
                            self.log(f"Server xác nhận đã ăn đậu thần cấp {level}; còn {bag.get(item_id, 0)} hạt")
                    pending = self._pending_item_action
                    if pending and pending[0] in ("take_use", "take_throw", "take_equip"):
                        item_id = pending[1]
                        slot = self.bag_details.get(item_id, {}).get("slot")
                        if slot is not None:
                            action = "use" if pending[0] == "take_use" else "throw" if pending[0] == "take_throw" else "equip"
                            if action == "equip":
                                self._send(-40, bytes([4, slot]))
                            else:
                                self._pending_item_action = (action, 1, slot)
                                self._send(-43, bytes([0 if action == "use" else 1, 1, slot]))
                            self.log(f"{'Dùng' if action == 'use' else 'Bỏ' if action == 'throw' else 'Mặc'} vật phẩm vừa chuyển vào túi (ID: {item_id})")
                        else:
                            self._pending_item_action = None
            elif command == -37:
                if reader.u8() == 0:
                    reader.raw(2)  # head
                    details: dict[int, dict] = {}
                    read_items(reader, details=details)
                    with self._lock:
                        self.worn_details = details
            elif command == -35:
                if reader.u8() == 0:
                    slots: dict[int, int] = {}
                    details: dict[int, dict] = {}
                    read_items(reader, slots, details)
                    with self._lock:
                        self.box_slots = slots
                        self.box_details = details
            elif command == -43:
                kind, where, slot = reader.u8(), reader.u8(), reader.u8()
                prompt = reader.utf() if reader.pos < len(payload) else ""
                pending = self._pending_item_action
                if pending and pending[1:] == (where, slot) and kind == 1 and pending[0] == "throw":
                    self._send(-43, bytes([2, where, slot]))
                    self._pending_item_action = None
                    self.log("Server xác nhận bỏ vật phẩm")
                elif pending and pending[1:] == (where, slot) and kind == 0 and pending[0] == "use":
                    self._send(-43, bytes([3, where, slot]))
                    self._pending_item_action = None
                    self.log("Server xác nhận sử dụng vật phẩm")
                elif prompt:
                    self.log("Server yêu cầu xác nhận vật phẩm: " + prompt[:160])
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
                # The server template still resolves MAP_VACH_NUI to 39–41, which
                # are dead ends without the baby item. Keep the quest on the
                # planet where this character currently is (including saved map).
                if task["task_id"] == 3 and task["index"] == 1 and task["index"] < len(task["steps"]):
                    task["steps"][task["index"]]["map_id"] = 42 + self._planet_index()
                # The server DB stores map 0 for this race-specific flying-mob
                # step, so route directly to each planet's intended hunting map.
                if task["task_id"] == 7 and task["index"] < len(task["steps"]):
                    gender = self.gender if self.gender in (0, 1, 2) else self.config.gender
                    step = task["steps"][task["index"]]
                    if task["index"] == 0:
                        step["map_id"] = -1
                    elif task["index"] == 1:
                        step["map_id"] = (3, 11, 17)[gender]
                    elif task["index"] == 2:
                        step["map_id"] = (0, 7, 14)[gender]
                        step["npc_id"] = 7 + gender
                    elif task["index"] == 3:
                        step["map_id"] = 21 + gender
                        step["npc_id"] = HOME_NPC_IDS[gender]
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
                    if self._ai_shop_goal:
                        self._ai_next = 0
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
                    self.gems = reader.i32()
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
                    lowered_notice = notice.casefold()
                    if (self._travel_step and self._travel_phase in ("menu", "wait")
                            and any(message in lowered_notice for message in (
                                "không thể đến khu vực này", "từ chối vận chuyển",
                                "không thể di chuyển tới", "không thể di chuyển đến",
                            ))):
                        self._block_travel_step(
                            time.monotonic(), f"Đường tới {self._map_label(self._travel_step[1])} bị server từ chối"
                        )
                    if self._pending_item_action:
                        self._item_feedback = notice[:200]
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
                    if key == "skill_ids":
                        self.learned_skill_ids = set(value)
                    else:
                        setattr(self, key, value)
            self.log(f"Nhân vật {self.character} (ID {self.player_id}) đã vào game")
        elif sub == 4:
            with self._lock:
                self.gold = reader.i64()
                self.gems = reader.i32()
                self.hp, self.mp = reader.i32(), reader.i32()
        elif sub == 5:
            with self._lock:
                self.hp = reader.i32()
        elif sub == 6:
            with self._lock:
                self.mp = reader.i32()
        elif sub == 7:
            self._quest_boss_player_packet(reader)
        elif sub == 15:
            reader.raw(4)
            with self._lock:
                self.hp, self.mp = reader.i32(), reader.i32()
        elif sub in (23, 62):
            skill_id = reader.u16()
            template_id = ROUTES.skills_by_id.get(skill_id, {}).get("template_id")
            with self._lock:
                if template_id is not None:
                    self.learned_skill_ids = {old for old in self.learned_skill_ids
                                              if ROUTES.skills_by_id.get(old, {}).get("template_id") != template_id}
                self.learned_skill_ids.add(skill_id)
                self._ai_next = 0
            self.log(f"Đã học kỹ năng {ROUTES.skills_by_id.get(skill_id, {}).get('name', skill_id)}")

    def _quest_boss_player_packet(self, reader: Reader) -> None:
        if self.task.get("task_id") != 10 or self.task.get("index") not in (0, 1):
            return
        player_id = reader.i32()
        reader.raw(11)  # clan, level, invisibility, PK, gender and head
        name = reader.utf()
        reader.raw(8)  # HP and maximum HP
        reader.raw(6)  # body, leg, flag and pet marker
        x, y = reader.i16(), reader.i16()
        signed_id = ((self.player_id + 128) % 256) - 128
        if (self.map_id == 46 and self.task.get("index") == 0
                and player_id == -351003 - signed_id and name.casefold() == "karin"):
            self._karin_boss_id = player_id
            self._karin_boss_pos = (x, y)
            self._karin_boss_due = time.monotonic() + 60
            self.log("Thần Mèo Karin đã xuất hiện; bắt đầu thách đấu")
        elif (self.map_id == 47 and self.task.get("index") == 1
              and player_id == -10251003 - self.player_id
              and name.casefold() == "tàu pảy pảy"):
            self._tau_boss_pos = (x, y)
            self.log("Tàu Pảy Pảy đã xuất hiện ở Rừng Karin")

    def _task_title(self) -> str:
        index = self.task.get("index", -1)
        steps = self.task.get("steps", [])
        return steps[index].get("title", "") if 0 <= index < len(steps) else ""

    @staticmethod
    def _npc_label(npc_id: int) -> str:
        name = ROUTES.npc_names.get(npc_id)
        return f"{name} (ID: {npc_id})" if name else f"NPC (ID: {npc_id})"

    def _map_label(self, map_id: int) -> str:
        name = self.map_name if map_id == self.map_id and self.map_name else ROUTES.map_names.get(map_id)
        return f"{name or 'Map'} (ID: {map_id})"

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
        if self._skip_quest_id is not None:
            if self.task.get("task_id") != self._skip_quest_id:
                self._skip_quest_id = None
                self._skip_quest_sent = False
                self.error = ""
                self.set_action("Đã nhận nhiệm vụ tiếp theo từ server")
                return
            home_map = 21 + self.gender
            if self.map_id != home_map:
                if now >= self._skip_quest_due:
                    self._send(-15)
                    self._skip_quest_due = now + 5
                self.set_action(f"Về {self._map_label(home_map)} để bỏ qua nhiệm vụ")
                return
            if not self._skip_quest_sent:
                self._send(126)
                self._skip_quest_sent = True
                self._skip_quest_due = now + 10
                self.set_action("Đã yêu cầu server bỏ qua nhiệm vụ; chờ nhiệm vụ tiếp theo")
                return
            if now < self._skip_quest_due:
                return
            self._skip_quest_id = None
            self._skip_quest_sent = False
            self.error = "Server chưa xác nhận bỏ qua nhiệm vụ; cần cập nhật server hỗ trợ lệnh 126"
            self.log(self.error, "error")
            self.set_action(self.error)
            return
        doing_quest = self.config.mode != "farm" and not (self.config.mode == "ai" and self._ai_goal == "farm")
        needs_potential_for_quest = doing_quest and self.task.get("task_id") == 3 and self.task.get("index") == 0
        stat_mode = (self._ai_stat_focus or ("balanced" if needs_potential_for_quest else "off")
                     if self.config.mode == "ai" else self.config.stat)
        if (stat_mode != "off" or needs_potential_for_quest) and now >= self._next_stat:
            self._next_stat = now + 3
            self._upgrade_stat(force=needs_potential_for_quest, mode=stat_mode)
        # A character with no stamina cannot keep fighting.  Let it buy/use
        # grapes before the low-KI recovery loop sends it home for beans.
        if self.max_stamina > 0 and self.stamina <= 0 and self.hp * 100 > self.max_hp * 35:
            if self._restore_stamina(now):
                return
        if self._recover(now):
            return
        if self._restore_stamina(now):
            return
        if self.config.heal_item > 0 and self.bag.get(self.config.heal_item, 0) > 0 and self.max_hp and self.hp * 100 < self.max_hp * 35 and now >= self._next_heal and self.config.heal_item in self.bag_slots:
            self._send(-43, bytes([0, 1, self.bag_slots[self.config.heal_item]]))
            self._next_heal = now + 10
            self.set_action(f"Dùng vật phẩm hồi phục {self.config.heal_item}")
            return
        if self._equip_starter_gear(now):
            return
        if self._supply(now):
            return
        if self.config.mode == "ai" and self._ai_tick(now):
            return
        self._quest_target_templates.clear()
        doing_quest = self.config.mode != "farm" and not (self.config.mode == "ai" and self._ai_goal == "farm")
        if doing_quest and self._quest(now):
            return
        owned_items = [item for item in self.items.values() if item.owner_id in (-1, self.player_id)]
        quest_hunt = (self.task.get("task_id"), self.task.get("index"))
        if doing_quest and quest_hunt in QUEST_ITEM_HUNT_RULES:
            quest_item_id = QUEST_ITEM_HUNT_RULES[quest_hunt]["item"]
            quest_items = [item for item in owned_items if item.template_id == quest_item_id]
            if quest_items:
                owned_items = quest_items
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
            if self._quest_target_templates:
                self.set_action("Đứng yên: chờ quái nhiệm vụ hồi sinh")
                return
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
        distance_squared = (target.x - self.x) ** 2 + (target.y - self.y) ** 2
        # The game server rejects attacks beyond Skill.RANGE_ATTACK_CHIEU_DAM (50 px).
        # Approach to 40 px to allow for coordinate rounding and movement updates.
        if distance_squared > 40 ** 2:
            self._move_towards(target.x, target.y)
            self.set_action(f"Đang áp sát quái {mob_name} (ID {target.mob_id})")
        else:
            watch = self._mob_attack_watch.get(target.mob_id)
            if watch is None or watch[0] != target.hp:
                self._mob_attack_watch[target.mob_id] = (target.hp, now)
            elif now - watch[1] >= 8:
                # A focused mob with unchanged HP usually means the server considered
                # the client out of range. Move directly toward it and retry.
                self._mob_attack_watch[target.mob_id] = (target.hp, now)
                basic_skill = (0, 2, 4)[min(max(self.gender, 0), 2)]
                if self.config.mode == "ai" and self._ai_selected_skill not in (-1, basic_skill):
                    self._send(34, struct.pack(">h", basic_skill))
                    self._ai_selected_skill = basic_skill
                    self.log(f"AI đổi về đòn cơ bản khi quái {mob_name} không mất HP")
                self._move_towards(target.x, target.y)
                self.set_action(f"Quái {mob_name} (ID {target.mob_id}) chưa mất HP; áp sát lại")
                return
            self._send(54, bytes([target.mob_id]))
            self.set_action(f"Đang đánh quái {mob_name} (ID {target.mob_id}, HP {target.hp})")

    def _ai_skill_levels(self) -> dict[int, int]:
        levels: dict[int, int] = {}
        for skill_id in self.learned_skill_ids:
            skill = ROUTES.skills_by_id.get(skill_id)
            if skill and skill["gender"] == self.gender:
                template = skill["template_id"]
                levels[template] = max(levels.get(template, 0), skill["point"])
        return levels

    @staticmethod
    def _ai_book(item_id: int) -> tuple[int, int] | None:
        for first, template in SKILL_BOOK_BASES.items():
            if first <= item_id <= first + 6:
                return template, item_id - first + 1
        if item_id == 86:
            return 2, 7
        return None

    def _ai_book_usable(self, book: tuple[int, int] | None, levels: dict[int, int]) -> bool:
        if book is None or levels.get(book[0], 0) != book[1] - 1:
            return False
        return any(skill["gender"] == self.gender and skill["template_id"] == book[0]
                   and skill["point"] == book[1] and skill["power_require"] <= self.power
                   for skill in ROUTES.skills_by_id.values())

    @staticmethod
    def _ai_option_labels(options: list[dict]) -> list[str]:
        return [ROUTES.option_names.get(option["id"], f"Chỉ số {option['id']}: #")
                .replace("#", str(option["param"]))
                for option in options if ROUTES.option_names.get(option["id"], "unknown")]

    def _ai_choices(self, now: float) -> list[dict]:
        choices = [{"id": "none", "description": "Tiếp tục nhiệm vụ hoặc đánh quái hiện tại"}]
        if self._ai_goal == "quest":
            if now >= self._ai_action_cooldown.get("goal:farm", 0):
                choices.append({"id": "goal:farm", "description":
                                "Tạm luyện sức mạnh bằng quái phù hợp trong 5 phút, rồi quay lại nhiệm vụ"})
        else:
            choices.append({"id": "goal:quest", "description": "Quay lại làm nhiệm vụ hiện tại ngay"})
        stat_costs = {"hp": self.base_hp + 1000, "mp": self.base_mp + 1000,
                      "attack": self.base_damage * 100, "def": (self.base_defense + 5) * 100000}
        if any(0 < cost <= self.potential for cost in stat_costs.values()):
            for stat in ("attack", "hp", "mp", "def", "balanced"):
                if stat != self._ai_stat_focus:
                    choices.append({"id": f"stat:{stat}", "description":
                                    f"Tập trung cộng {stat} bằng tiềm năng sau mỗi 3 giây; "
                                    f"chi phí kế tiếp {stat_costs.get(stat, min(stat_costs.values()))}"})
        levels = self._ai_skill_levels()
        worn_power = {ROUTES.item_types.get(item_id): ROUTES.item_power_require.get(item_id, 0)
                      for item_id in self.worn_details}
        for item_id, slot in self.bag_slots.items():
            item_type = ROUTES.item_types.get(item_id, -1)
            if (item_type in (0, 1, 2, 3, 4)
                    and ROUTES.item_genders.get(item_id, 3) in (self.gender, 3)
                    and worn_power.get(item_type, -1) <= ROUTES.item_power_require.get(item_id, 0)
                    and ROUTES.item_power_require.get(item_id, 0) <= self.power
                    and now >= self._ai_action_cooldown.get(f"equip:{item_id}", 0)):
                choices.append({"id": f"equip:{item_id}", "description":
                                f"Mặc {ROUTES.item_names.get(item_id, item_id)} từ túi; loại {item_type}; "
                                f"chỉ số {self._ai_option_labels(self.bag_details.get(item_id, {}).get('options', []))}"})
            book = self._ai_book(item_id)
            if (item_type == 7 and self._ai_book_usable(book, levels)
                    and ROUTES.item_genders.get(item_id, 3) in (self.gender, 3)
                    and now >= self._ai_action_cooldown.get(f"learn:{item_id}", 0)):
                choices.append({"id": f"learn:{item_id}", "description":
                                f"Dùng {ROUTES.item_names.get(item_id, item_id)} trong túi"})
        affordable_gear: dict[int, list[tuple[int, dict]]] = {}
        for item_id, price in self.shop.items():
            if (price["gold"] > self.gold or price["gems"] > self.gems
                    or not (price["gold"] > 0 or price["gems"] > 0)
                    or ROUTES.item_genders.get(item_id, 3) not in (self.gender, 3)
                    or ROUTES.item_power_require.get(item_id, 0) > self.power
                    or item_id in self.bag or item_id in self.worn_details
                    or now < self._ai_action_cooldown.get(f"buy:{item_id}", 0)):
                continue
            item_type = ROUTES.item_types.get(item_id, -1)
            if item_type in (0, 1, 2, 3, 4):
                if ROUTES.item_power_require.get(item_id, 0) >= worn_power.get(item_type, -1):
                    affordable_gear.setdefault(item_type, []).append((item_id, price))
            elif item_type == 7:
                book = self._ai_book(item_id)
                if self._ai_book_usable(book, levels):
                    choices.append({"id": f"buy:{item_id}", "description":
                                    f"Mua {ROUTES.item_names.get(item_id, item_id)}; "
                                    f"giá {price['gold']} vàng, {price['gems']} ngọc"})
        for group in affordable_gear.values():
            group.sort(key=lambda entry: ROUTES.item_power_require.get(entry[0], 0), reverse=True)
            for item_id, price in group[:2]:
                choices.append({"id": f"buy:{item_id}", "description":
                                f"Mua {ROUTES.item_names.get(item_id, item_id)}; "
                                f"yêu cầu {ROUTES.item_power_require.get(item_id, 0)} sức mạnh; "
                                f"giá {price['gold']} vàng, {price['gems']} ngọc; "
                                f"chỉ số {self._ai_option_labels(price.get('options', []))}"})
        for template in (0, 1, 2, 3, 4, 5):
            known = [ROUTES.skills_by_id[skill_id] for skill_id in self.learned_skill_ids
                     if skill_id in ROUTES.skills_by_id
                     and ROUTES.skills_by_id[skill_id]["template_id"] == template
                     and ROUTES.skills_by_id[skill_id]["gender"] == self.gender]
            if known and template != self._ai_selected_skill:
                skill = max(known, key=lambda entry: entry["point"])
                if skill["mana_use"] <= self.mp:
                    choices.append({"id": f"skill:{template}", "description":
                                    f"Chọn {skill['name']} cấp {skill['point']} để đánh; "
                                    f"KI {skill['mana_use']}, sát thương {skill['damage']}%, "
                                    f"hồi chiêu {skill['cool_down']} ms"})
        if self._ai_shop_goal is None and not self.shop:
            if self.gold >= 500 and now >= self._ai_shop_cooldown.get("gear", 0):
                choices.append({"id": "visit:gear", "description": "Đến cửa hàng ở làng để xem trang bị theo hệ"})
            if self.gems >= 5 and now >= self._ai_shop_cooldown.get("skill", 0):
                choices.append({"id": "visit:skill", "description": "Đến Uron ở trạm tàu để xem sách kỹ năng"})
        return choices[:24]

    def _ai_observation(self) -> dict:
        return {
            "gender": self.gender, "map": self._map_label(self.map_id),
            "power": self.power, "damage": self.damage, "defense": self.defense,
            "hp": self.hp, "max_hp": self.max_hp, "mp": self.mp, "max_mp": self.max_mp,
            "gold": self.gold, "gems": self.gems,
            "potential": self.potential, "goal": self._ai_goal,
            "stat_focus": self._ai_stat_focus or "chưa chọn", "kills": self.kills,
            "quest_count": self.task.get("count", 0), "current_action": self.action,
            "worn": [{"name": ROUTES.item_names.get(item_id, str(item_id)),
                      "type": ROUTES.item_types.get(item_id, -1),
                      "options": self._ai_option_labels(info.get("options", []))}
                     for item_id, info in self.worn_details.items()],
            "skills": self._ai_skill_levels(), "task": self._task_title(),
            "recent_feedback": ai_memory.recent(self.id),
        }

    def _ai_shop_step(self, now: float) -> bool:
        goal = self._ai_shop_goal
        if goal is None:
            return False
        map_id, npc_id = goal
        if self.map_id != map_id:
            return self._travel_to(map_id, now)
        npc = self.npcs.get(npc_id)
        if npc is None:
            self.set_action(f"AI chờ {self._npc_label(npc_id)} ở {self._map_label(map_id)}")
            return True
        if (npc[0] - self.x) ** 2 + (npc[1] - self.y) ** 2 > 55 ** 2:
            self._move_towards(*npc)
            self.set_action(f"AI đi tới {self._npc_label(npc_id)}")
            return True
        if self.shop:
            self._ai_shop_phase = "ready"
            return False
        if not self._ai_shop_phase:
            self._send(33, struct.pack(">h", npc_id))
            self._ai_shop_phase = "opened"
            self._ai_shop_due = now + 1
            self.set_action(f"AI mở shop {self._npc_label(npc_id)}")
            return True
        if self._ai_shop_phase == "opened" and now >= self._ai_shop_due and npc_id != 16:
            self._send(32, struct.pack(">hb", npc_id, 0))
            self._ai_shop_phase = "waiting"
            self._ai_shop_due = now + 8
            return True
        if self._ai_shop_phase == "opened" and npc_id == 16 and now >= self._ai_shop_due:
            self._ai_shop_phase = "waiting"
            self._ai_shop_due = now + 8
        if self._ai_shop_phase == "waiting" and now >= self._ai_shop_due:
            self.log("AI không nhận được danh sách shop", "error")
            self._ai_shop_goal = None
            self._ai_shop_phase = ""
            self._ai_next = now + 120
            return False
        return True

    def _ai_tick(self, now: float) -> bool:
        if self._ai_goal == "farm" and now >= self._ai_goal_until:
            self._ai_goal = "quest"
            self.log("AI kết thúc lượt luyện sức mạnh; quay lại nhiệm vụ")
        if self._ai_feedback and now - self._ai_feedback[3] >= 3:
            choice, reason, before, _ = self._ai_feedback
            outcome = "Chưa thấy thay đổi từ server"
            if choice.startswith("buy:") and self.bag.get(int(choice.split(":")[1]), 0) > before["count"]:
                outcome = "Đã mua và nhận vật phẩm"
            elif choice.startswith("equip:") and int(choice.split(":")[1]) in self.worn_details:
                outcome = "Đã mặc trang bị"
            elif choice.startswith("learn:") and self.learned_skill_ids != before["skills"]:
                outcome = "Server đã cập nhật kỹ năng"
            elif choice.startswith("skill:"):
                outcome = "Đã gửi lệnh chọn kỹ năng; chờ hiệu quả chiến đấu"
            ai_memory.append(self.id, choice, reason, outcome)
            if outcome == "Chưa thấy thay đổi từ server":
                self._ai_action_cooldown[choice] = now + 300
            self._ai_feedback = None
        if self._ai_shop_goal and self._ai_shop_phase != "ready":
            if self._ai_shop_step(now):
                return True
        if self._ai_future is not None:
            if not self._ai_future.done():
                if self._ai_shop_goal:
                    self.set_action("AI đang đọc dữ liệu shop và chọn hành động")
                    return True
                return False
            try:
                decision = self._ai_future.result()
            except Exception as exc:
                self.log(f"AI cục bộ chưa trả quyết định: {exc}", "error")
                self._ai_next = now + 120
                self._ai_shop_goal = None
                self._ai_shop_phase = ""
                self._ai_future = None
                return False
            self._ai_future = None
            self._ai_next = now + 60
            return self._ai_apply(decision, now)
        if now < self._ai_next:
            return bool(self._ai_shop_goal)
        choices = self._ai_choices(now)
        if len(choices) <= 1:
            self._ai_next = now + 60
            return bool(self._ai_shop_goal)
        self._ai_future = AI_EXECUTOR.submit(MODEL_CLIENT.decide, self._ai_observation(), choices)
        self._ai_next = now + 60
        if self._ai_shop_goal:
            self.set_action("AI đang đánh giá trang bị và sách kỹ năng trong shop")
            return True
        return False

    def _ai_apply(self, decision: dict, now: float) -> bool:
        choice = decision["choice"]
        reason = str(decision.get("reason", ""))[:160]
        if choice not in {entry["id"] for entry in self._ai_choices(now)}:
            self.log(f"AI bỏ hành động đã lỗi thời: {choice}")
            self._ai_shop_goal = None
            self._ai_shop_phase = ""
            return False
        if choice == "none":
            self._ai_shop_goal = None
            self._ai_shop_phase = ""
            return False
        if choice.startswith("goal:"):
            self._ai_goal = choice.split(":", 1)[1]
            self._ai_goal_until = now + 300 if self._ai_goal == "farm" else 0
            self.set_action(f"AI chọn mục tiêu {self._ai_goal}: {reason}")
            ai_memory.append(self.id, choice, reason, "Đã đổi mục tiêu chơi")
            return True
        if choice.startswith("stat:"):
            self._ai_stat_focus = choice.split(":", 1)[1]
            self.set_action(f"AI chọn hướng cộng chỉ số {self._ai_stat_focus}: {reason}")
            ai_memory.append(self.id, choice, reason, "Đã đổi hướng xây dựng nhân vật")
            return True
        if choice.startswith("visit:"):
            kind = choice.split(":", 1)[1]
            if kind == "gear":
                self._ai_shop_goal = (PLANET_VILLAGE_MAPS[self.gender], PLANET_SHOP_NPCS[self.gender])
            elif kind == "skill":
                self._ai_shop_goal = (24 + self.gender, 16)
            else:
                return False
            self._ai_shop_phase = ""
            self._ai_shop_cooldown[kind] = now + 300
            self.shop = {}
            self.set_action(f"AI chọn đến shop {kind}: {reason}")
            return True
        action, value = choice.split(":", 1)
        item_id = int(value)
        before = {"count": self.bag.get(item_id, 0), "skills": set(self.learned_skill_ids)}
        if action == "buy" and item_id in self.shop:
            price = self.shop[item_id]
            if price["gold"] > self.gold or price["gems"] > self.gems:
                return False
            self._send(6, bytes([0]) + struct.pack(">h", item_id))
            self.purchases += 1
        elif action == "equip" and item_id in self.bag_slots:
            self._send(-40, bytes([4, self.bag_slots[item_id]]))
        elif action == "learn" and item_id in self.bag_slots:
            self._send(-43, bytes([0, 1, self.bag_slots[item_id]]))
        elif action == "skill" and item_id in {meta["template_id"] for meta in
                                             (ROUTES.skills_by_id.get(sid) for sid in self.learned_skill_ids)
                                             if meta}:
            self._send(34, struct.pack(">h", item_id))
            self._ai_selected_skill = item_id
        else:
            return False
        self._ai_feedback = (choice, reason, before, now)
        self._ai_shop_goal = None
        self._ai_shop_phase = ""
        self.set_action(f"AI chọn {choice}: {reason}")
        return True

    def _recover(self, now: float) -> bool:
        low_hp = self.max_hp > 0 and self.hp * 100 <= self.max_hp * 35
        low_ki = self.max_mp > 0 and self.mp * 100 <= self.max_mp * 20
        if not self._recovering:
            if not low_hp and not low_ki:
                return False
            self._recovering = True
            self._recover_hp_target = low_hp
            self._recover_mp_target = low_ki
        if self._recover_hp_target and self.hp * 100 >= self.max_hp * 60:
            self._recover_hp_target = False
        if self._recover_mp_target and self.mp * 100 >= self.max_mp * 60:
            self._recover_mp_target = False
        if not self._recover_hp_target and not self._recover_mp_target:
            self._recovering = False
            self._harvest_attempts = 0
            self.set_action("HP/KI đã hồi; quay lại farm")
            return False
        self._focused_mob = None
        if now < self._recover_due:
            return True

        # The server consumes the first bean in bag order, so select that slot
        # and report the level that will actually be eaten.
        peas = [(slot, item_id) for item_id, slot in self.bag_slots.items()
                if item_id in PEA_ITEMS and self.bag.get(item_id, 0) > 0]
        if peas:
            slot, pea = min(peas)
            level = PEA_ITEMS.index(pea) + 1
            self._pending_recovery_bean = (pea, self.bag.get(pea, 0), level)
            self._send(-43, bytes([0, 1, slot]))
            self._recover_due = now + 2
            reason = "HP/KI thấp" if self._recover_hp_target and self._recover_mp_target else "HP thấp" if self._recover_hp_target else "KI thấp"
            self.set_action(f"Ăn đậu thần cấp {level} ({reason})")
            return True

        if self.config.heal_item > 0 and self.bag.get(self.config.heal_item, 0) > 0 and self.config.heal_item in self.bag_slots:
            self._send(-43, bytes([0, 1, self.bag_slots[self.config.heal_item]]))
            self._recover_due = now + 4
            self.set_action(f"Dùng vật phẩm hồi phục {self.config.heal_item}")
            return True

        if self.gender == 2 and self.learned_skill_ids.intersection(XAYDA_ENERGY_SKILL_IDS):
            self._send(34, struct.pack(">h", 8))
            self._send(-45, bytes([1]))
            self._recover_due = now + 8
            self.set_action("Dùng skill Tái tạo năng lượng của Xayda")
            return True

        home = 21 + self.gender
        if self.map_id != home:
            self._send(-15)
            self._recover_due = now + 5
            self.set_action("Thiếu đồ hồi phục; về nhà thu hoạch đậu")
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

    def _restore_stamina(self, now: float) -> bool:
        if self.max_stamina <= 0:
            return False
        if not self._stamina_recovery:
            if self.stamina > 0 or now < self._stamina_retry_after:
                return False
            self._stamina_recovery = True
            self._stamina_return_map = self.map_id
            self._stamina_shop_phase = 0
            self.set_action("Hết thể lực; về làng mua Nho xanh")

        if self.stamina * 100 > self.max_stamina * 50:
            if self._stamina_return_map >= 0 and self.map_id != self._stamina_return_map:
                if self._travel_to(self._stamina_return_map, now):
                    self.set_action("Thể lực đã hồi; quay lại map trước đó")
                    return True
            self._stamina_recovery = False
            self._stamina_return_map = -1
            self._stamina_shop_phase = 0
            self.set_action("Thể lực đã hồi; tiếp tục farm")
            return False

        if now < self._stamina_shop_next:
            return True

        grape_slot = self.bag_slots.get(GREEN_GRAPE_ID)
        if self.bag.get(GREEN_GRAPE_ID, 0) > 0 and grape_slot is not None:
            self._send(-43, bytes([0, 1, grape_slot]))
            self._stamina_shop_next = now + 2
            self.set_action(f"Ăn Nho xanh hồi thể lực ({self.stamina}/{self.max_stamina})")
            return True

        if self._stamina_shop_phase == 4:
            if now < self._stamina_retry_after:
                self.set_action("Chờ cửa hàng hành tinh sẵn sàng bán Nho xanh")
                return True
            self._stamina_shop_phase = 0
            self._stamina_retry_after = now + 60

        village_map = PLANET_VILLAGE_MAPS[min(max(self.gender, 0), len(PLANET_VILLAGE_MAPS) - 1)]
        if self.map_id != village_map:
            self._stamina_shop_phase = 0
            if self._travel_to(village_map, now):
                self.set_action("Đang về làng mua Nho xanh")
                return True

        npc_id = PLANET_SHOP_NPCS[min(max(self.gender, 0), len(PLANET_SHOP_NPCS) - 1)]
        npc = self.npcs.get(npc_id)
        if npc is None:
            self.set_action(f"Chờ NPC cửa hàng ở làng (NPC {npc_id})")
            return True
        if abs(npc[0] - self.x) > 55 or abs(npc[1] - self.y) > 55:
            self._move_towards(*npc)
            self.set_action(f"Đi tới cửa hàng ở làng (NPC {npc_id})")
            return True

        if self._stamina_shop_phase == 0:
            self.shop = {}
            self._send(33, struct.pack(">h", npc_id))
            self._stamina_shop_phase = 1
            self._stamina_shop_next = now + 0.8
            self.set_action("Mở cửa hàng ở làng")
            return True
        if self._stamina_shop_phase == 1:
            self._send(32, struct.pack(">hb", npc_id, 0))
            self._stamina_shop_phase = 2
            self._stamina_shop_next = now + 8
            self.set_action("Chờ shop Nho xanh")
            return True
        if self._stamina_shop_phase == 2:
            price = self.shop.get(GREEN_GRAPE_ID)
            if price and price["gold"] > 0 and price["gems"] == 0:
                target_stamina = (self.max_stamina * 60 + 99) // 100
                stamina_per_grape = max(1, self.max_stamina * 20 // 100)
                target_count = max(1, (target_stamina - self.stamina + stamina_per_grape - 1)
                                   // stamina_per_grape)
                if self.gold < price["gold"] * target_count:
                    self.set_action("Không đủ vàng mua Nho xanh hồi thể lực")
                    self._stamina_shop_phase = 4
                    self._stamina_retry_after = now + 60
                    return True
                self._stamina_shop_phase = 3
                self._stamina_shop_attempts = 0
                self._stamina_shop_before = -1
                self._stamina_shop_target = target_count
            elif now >= self._stamina_shop_next:
                self.set_action("Shop ở làng không có Nho xanh; kiểm tra dữ liệu shop")
                self._stamina_shop_phase = 4
                self._stamina_retry_after = now + 60
            return True
        if self._stamina_shop_phase == 3:
            count = self.bag.get(GREEN_GRAPE_ID, 0)
            target_count = self._stamina_shop_target or 1
            if count >= target_count:
                self._stamina_shop_phase = 0
                self.set_action(f"Đã mua {count} Nho xanh; dùng để hồi thể lực")
            elif count == self._stamina_shop_before and self._stamina_shop_attempts >= 3:
                self.set_action("Dừng mua Nho xanh: túi không tăng sau 3 lần")
                self._stamina_shop_phase = 4
                self._stamina_retry_after = now + 60
            elif now >= self._stamina_shop_next:
                self._stamina_shop_attempts = self._stamina_shop_attempts + 1 if count == self._stamina_shop_before else 1
                self._stamina_shop_before = count
                self._send(6, bytes([0]) + struct.pack(">h", GREEN_GRAPE_ID))
                self._stamina_shop_next = now + 1.3
                self.set_action(f"Mua Nho xanh ({count}/{target_count})")
            return True
        return True

    def _move_towards(self, target_x: int, target_y: int) -> None:
        dx, dy = target_x - self.x, target_y - self.y
        x = self.x + max(-42, min(42, dx))
        y = self.y + max(-24, min(24, dy))
        if y <= 0:
            y = max(1, self.y)
        self._send(-7, bytes([0]) + struct.pack(">hh", x, y))
        self.x, self.y = x, y

    def _upgrade_stat(self, force: bool = False, mode: str | None = None) -> None:
        choices = {"balanced": (0, 1, 2, 3), "hp": (0,), "mp": (1,), "attack": (2,), "def": (3,)}.get(mode or self.config.stat, ())
        if force and not choices:
            choices = (0, 1, 2, 3)
        for offset in range(len(choices)):
            stat = choices[(self._stat_cursor + offset) % len(choices)]
            cost = (self.base_hp + 1000, self.base_mp + 1000, self.base_damage * 100,
                    (self.base_defense + 5) * 100000)[stat]
            if 0 < cost <= self.potential:
                self._send(-30, bytes([16, stat]) + struct.pack(">h", 1))
                self._stat_cursor = (self._stat_cursor + offset + 1) % len(choices)
                self.log(f"Cộng 1 điểm {('HP', 'KI', 'sức đánh', 'giáp')[stat]}")
                return

    def _equip_starter_gear(self, now: float) -> bool:
        if now < self._next_gear:
            return False
        worn_types = {ROUTES.item_types.get(item_id) for item_id in self.worn_details}
        for item_id, slot in self.bag_slots.items():
            item_type = ROUTES.item_types.get(item_id)
            if item_type in (0, 1, 2, 3, 4) and item_type not in worn_types:
                self._send(-40, bytes([4, slot]))
                self._next_gear = now + 30
                self.set_action(f"Mặc {ROUTES.item_names.get(item_id, 'trang bị')} từ túi")
                return True
        return False

    def _supply(self, now: float) -> bool:
        cfg = self.config
        item_id, shop_map, shop_npc = cfg.shop_item, cfg.shop_map, cfg.shop_npc
        minimum, target = cfg.shop_min, cfg.shop_target
        menu = cfg.shop_menu
        if item_id <= 0:
            planet = min(max(self.gender, 0), 2)
            village = PLANET_VILLAGE_MAPS[planet]
            if self.map_id != village and self.task:
                return False
            worn_types = {ROUTES.item_types.get(item) for item in self.worn_details}
            bag_types = {ROUTES.item_types.get(item) for item in self.bag if self.bag[item] > 0}
            item_id = next((item for item in STARTER_GEAR[planet]
                            if ROUTES.item_types.get(item) not in worn_types
                            and ROUTES.item_types.get(item) not in bag_types), 0)
            if item_id <= 0 or self.gold < 1500:
                self._shop_phase = 0
                self._shop_current_item = 0
                return False
            shop_map, shop_npc = village, PLANET_SHOP_NPCS[planet]
            minimum = target = 1
            menu = 0
        if item_id <= 0 or minimum <= 0 or (self._shop_phase != 3 and self.bag.get(item_id, 0) >= minimum):
            self._shop_phase = 0
            return False
        if self._shop_current_item != item_id:
            self._shop_current_item = item_id
            self._shop_phase = 0
            self._shop_attempts = 0
            self._shop_before = -1
        if self._shop_phase == 4:
            if now < self._next_shop:
                return False
            self._shop_phase = 0
        if shop_map >= 0 and shop_map != self.map_id:
            return self._travel_to(shop_map, now)
        npc = self.npcs.get(shop_npc)
        if npc is None:
            self.set_action(f"Thiếu item {item_id}; chờ NPC shop {shop_npc} ở map hiện tại")
            if cfg.shop_item <= 0:
                self._shop_phase = 4
                self._next_shop = now + 60
                return False
            return True
        if abs(npc[0] - self.x) > 55:
            self._move_towards(*npc)
            self.set_action(f"Đi tới NPC shop {shop_npc}")
            return True
        if self._shop_phase == 0:
            self.shop = {}
            self._send(33, struct.pack(">h", shop_npc))
            self._shop_phase = 1
            self._next_shop = now + 0.8
            self.set_action(f"Mở shop NPC {shop_npc}")
            return True
        if self._shop_phase == 1 and now >= self._next_shop:
            self._send(32, struct.pack(">hb", shop_npc, menu))
            self._shop_phase = 2
            self._next_shop = now + 8
            self.set_action("Chờ danh sách shop")
            return True
        if self._shop_phase == 2:
            price = self.shop.get(item_id)
            if price and price["gold"] > 0 and price["gems"] == 0 and self.gold >= price["gold"]:
                self._shop_phase = 3
                self._shop_attempts = 0
                self._shop_before = -1
            elif now >= self._next_shop:
                self.set_action("Không mua được: shop thiếu item hoặc thiếu vàng")
                self._shop_phase = 4
                self._next_shop = now + 60
            return True
        if self._shop_phase == 3:
            count = self.bag.get(item_id, 0)
            if count >= target:
                self._shop_phase = 0
                self.set_action("Mua tiếp tế xong")
            elif count == self._shop_before and self._shop_attempts >= 3:
                self._shop_phase = 4
                self.set_action("Dừng mua: túi không tăng sau 3 lần")
                self._next_shop = now + 60
            elif now >= self._next_shop:
                self._shop_attempts = self._shop_attempts + 1 if count == self._shop_before else 1
                self._shop_before = count
                self._send(6, bytes([0]) + struct.pack(">h", item_id))
                self.purchases += 1
                self._next_shop = now + 1.3
                self.set_action(f"Mua {ROUTES.item_names.get(item_id, 'item ' + str(item_id))} ({count}/{target})")
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
        task_planet = min(max(self.gender, 0), 2)
        if (task_id == 7
                and (self.map_id in (24, 25, 26)
                     or self.map_id not in PLANET_MAPS[task_planet])):
            if now >= self._quest_request_due:
                self._send(-15)  # The server allows returning home while transport NPCs are quest-locked.
                self._quest_request_due = now + 5
            self.set_action("Nhiệm vụ giải cứu khóa tàu; đang về hành tinh gốc để đi bộ tới mục tiêu")
            return True
        if task_id == 0 and index == 0:
            training_map = 39 + self.gender
            if self.map_id != training_map:
                return self._travel_to(training_map, now)
            self._move_towards(650, self.y)
            self.set_action("Nhiệm vụ 0: đi tới mũi tên trong nhà")
            return True
        if task_id == 3 and index == 1:
            # This objective is the personal baby item on the character's own
            # planet cliff. It is not a generic farming step: don't let the
            # power-based farm planner send the bot to another planet.
            quest_map = 42 + self._planet_index()
            if self.map_id != quest_map:
                return self._travel_to(quest_map, now, allow_spaceships=False)
            quest_item = next((item for item in self.items.values()
                               if item.template_id == 78
                               and item.owner_id in (-1, self.player_id)), None)
            if quest_item:
                self.set_action("Đang tìm vật thể lạ: Đứa bé")
                return False  # Let the common item handler approach and pick it up.
            self.set_action(f"Chờ vật thể lạ xuất hiện trên hành tinh của mình ở {self._map_label(quest_map)}")
            return True
        if task_id == 3 and index == 2:
            home_map = 21 + self.gender
            if self.map_id != home_map:
                return self._travel_to(home_map, now)
            npc_id = HOME_NPC_IDS[self.gender]
            key = f"{task_id}:{index}"
            if self._quest_step_done == key and now < self._quest_request_due:
                self.set_action("Chờ server xác nhận đã báo cáo nhiệm vụ sao băng")
                return True
            npc = self.npcs.get(npc_id)
            if npc is None:
                self.set_action(f"Chờ {self._npc_label(npc_id)} ở nhà để báo cáo nhiệm vụ sao băng")
                return True
            if (npc[0] - self.x) ** 2 + (npc[1] - self.y) ** 2 > 55 ** 2:
                self._move_towards(*npc)
                self.set_action(f"Về gặp {self._npc_label(npc_id)} báo cáo nhiệm vụ sao băng")
                return True
            self._send(33, struct.pack(">h", npc_id))
            self._quest_step_done = key
            self._quest_request_due = now + 5
            self.set_action(f"Báo cáo nhiệm vụ sao băng với {self._npc_label(npc_id)}")
            return True
        hunt_rule = QUEST_ITEM_HUNT_RULES.get((task_id, index))
        if hunt_rule:
            planet = min(max(self.gender, 0), 2)
            target_map = hunt_rule["maps"][planet]
            target_mob = hunt_rule["mobs"][planet]
            self._quest_target_templates = {target_mob}
            mob_name = ROUTES.mob_names.get(target_mob, f"quái ID {target_mob}")
            if self.map_id != target_map:
                self.set_action(f"Đang tới {self._map_label(target_map)} săn {mob_name} lấy {hunt_rule['name']}")
                return self._travel_to(target_map, now)
            self.set_action(f"Nhiệm vụ: săn {mob_name} để nhặt {hunt_rule['name']}")
            return False  # Farm only the mob verified to drop this quest item.
        if task_id == 8 and index == 2:
            home_map = 21 + self.gender
            if self.map_id != home_map:
                return self._travel_to(home_map, now)
            npc_id = HOME_NPC_IDS[self.gender]
            key = f"{task_id}:{index}"
            if self._quest_step_done == key and now < self._quest_request_due:
                self.set_action("Chờ server xác nhận đã đem Ngọc Rồng 7 sao về nhà")
                return True
            npc = self.npcs.get(npc_id)
            if npc is None:
                self.set_action(f"Chờ {self._npc_label(npc_id)} để giao Ngọc Rồng 7 sao")
                return True
            if (npc[0] - self.x) ** 2 + (npc[1] - self.y) ** 2 > 55 ** 2:
                self._move_towards(*npc)
                self.set_action(f"Đem Ngọc Rồng 7 sao về cho {self._npc_label(npc_id)}")
                return True
            self._send(33, struct.pack(">h", npc_id))
            self._quest_step_done = key
            self._quest_request_due = now + 5
            self.set_action(f"Báo cáo Ngọc Rồng 7 sao với {self._npc_label(npc_id)}")
            return True
        if task_id == 8 and index == 3:
            karin_forest_map = 47
            if self.map_id != karin_forest_map:
                return self._travel_to(karin_forest_map, now)
            self.set_action("Đã tới Rừng Karin; chờ server cập nhật nhiệm vụ")
            return True
        if task_id == 14 and index == 2:
            planet = min(max(self.gender, 0), 2)
            npc_id = 13 + planet  # Quy Lão, Trưởng lão Guru, or Vua Vegeta
            target_map = (5, 13, 20)[planet]
            if self.map_id != target_map:
                return self._travel_to(target_map, now)
            npc = self.npcs.get(npc_id)
            if npc is None:
                self.set_action(f"Chờ {self._npc_label(npc_id)} để giao Truyện Doremon tập 2")
                return True
            if (npc[0] - self.x) ** 2 + (npc[1] - self.y) ** 2 > 55 ** 2:
                self._move_towards(*npc)
                self.set_action(f"Đem Truyện Doremon tập 2 về cho {self._npc_label(npc_id)}")
                return True
            key = f"{task_id}:{index}"
            if self._quest_step_done == key and now < self._quest_request_due:
                self.set_action("Chờ server xác nhận đã giao Truyện Doremon tập 2")
                return True
            self._send(33, struct.pack(">h", npc_id))
            self._quest_step_done = key
            self._quest_request_due = now + 5
            self.set_action(f"Báo cáo Truyện Doremon tập 2 với {self._npc_label(npc_id)}")
            return True
        mentor_map = (5, 13, 20)[task_planet]
        if task_id == 9:
            if index in (0, 1) and self.map_id != 47:
                return self._travel_to(47, now)
            if index == 1:
                self.set_action("Chờ Tàu Pảy Pảy xuất hiện ở Rừng Karin để hoàn thành bước đụng độ")
                return True
            if index in (2, 3) and self.map_id != 46:
                return self._travel_to(46, now)
            if index == 2:
                self.set_action("Đã lên Tháp Karin; chờ server xác nhận nhiệm vụ")
                return True
        if task_id == 10 and index == 0:
            if self.map_id != 46:
                return self._travel_to(46, now)
            if self._karin_boss_id is not None and now >= self._karin_boss_due:
                self._karin_boss_id = None
            if self._karin_boss_id is not None:
                bx, by = self._karin_boss_pos
                if (bx - self.x) ** 2 + (by - self.y) ** 2 > 40 ** 2:
                    self._move_towards(bx, by)
                    self.set_action("Áp sát Thần Mèo Karin để thách đấu")
                else:
                    self._send(-60, struct.pack(">i", self._karin_boss_id))
                    self.set_action("Đang đánh Thần Mèo Karin")
                return True
            npc = self.npcs.get(18)
            if npc is None:
                self.set_action("Chờ Thần Mèo Karin xuất hiện trên Tháp Karin")
                return True
            if (npc[0] - self.x) ** 2 + (npc[1] - self.y) ** 2 > 55 ** 2:
                self._move_towards(*npc)
                self.set_action("Đến gặp Thần Mèo Karin để thách đấu")
                return True
            if now >= self._quest_request_due:
                self._send(33, struct.pack(">h", 18))
                self._quest_request_due = now + 8
            self.set_action("Chờ menu thách đấu Thần Mèo Karin")
            return True
        if task_id == 10 and index == 1:
            if self.damage < 500 or self.max_hp < 4000:
                if self.map_id in (46, 47):
                    self._send(-15)
                    self.set_action("Tàu Pảy Pảy quá mạnh; về nhà luyện sức mạnh trước")
                    return True
                self.set_action("Đang luyện sức mạnh để đấu Tàu Pảy Pảy")
                return False
            if self.map_id != 47:
                return self._travel_to(47, now)
            boss_id = -10251003 - self.player_id
            if self._tau_boss_pos[1] == 0:
                self._tau_boss_pos = (775, self.y)
            bx, by = self._tau_boss_pos
            if (bx - self.x) ** 2 + (by - self.y) ** 2 > 40 ** 2:
                self._move_towards(bx, by)
                self.set_action("Áp sát Tàu Pảy Pảy ở Rừng Karin")
            else:
                self._send(-60, struct.pack(">i", boss_id))
                self.set_action("Đang đánh Tàu Pảy Pảy")
            return True
        if task_id == 10 and index == 2 and self.map_id != 47:
            return self._travel_to(47, now)
        if task_id == 11 and index == 0 and self.map_id != mentor_map:
            return self._travel_to(mentor_map, now)
        if task_id == 11 and index == 1 and self.map_id != 21 + task_planet:
            return self._travel_to(21 + task_planet, now)
        if task_id == 12 and index == 1 and self.map_id != mentor_map:
            return self._travel_to(mentor_map, now)
        if (task_id in (13, 15, 16, 17, 20, 21, 22, 23)
                and step.get("title", "").casefold().startswith("báo cáo với")
                and self.map_id != mentor_map):
            return self._travel_to(mentor_map, now)
        if step["map_id"] >= 0 and step["map_id"] != self.map_id:
            return self._travel_to(step["map_id"], now)
        if task_id == 0 and index == 3:
            npc = self.npcs.get(3)
            if npc is None:
                self.set_action(f"Nhiệm vụ 0: chờ {self._npc_label(3)}")
                return True
            if (npc[0] - self.x) ** 2 + (npc[1] - self.y) ** 2 > 55 ** 2:
                self._move_towards(*npc)
                self.set_action(f"Nhiệm vụ 0: đi tới {self._npc_label(3)}")
                return True
            if not self.box_slots:
                if now >= self._quest_request_due:
                    self._send(33, struct.pack(">h", 3))
                    self._quest_request_due = now + 3
                self.set_action(f"Nhiệm vụ 0: mở {self._npc_label(3)}")
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
        if task_id == 4 and index in (0, 1, 2):
            if self._quest_planet(target=index, now=now):
                return True
        npc_id = step["npc_id"]
        if npc_id < 0:
            title = step.get("title", "").casefold()
            if task_id == 11 and index == 0:
                npc_id = 13 + self.gender
            elif (task_id == 9 and index == 0) or (task_id == 10 and index == 2):
                npc_id = 17  # Bò Mộng ở Rừng Karin.
            elif task_id == 9 and index == 3:
                npc_id = 18  # Thần Mèo trên Tháp Karin.
            elif task_id == 11 and index == 1:
                npc_id = HOME_NPC_IDS[self.gender]
            elif task_id == 7 and index == 2:
                npc_id = 7 + self.gender
            elif task_id == 7 and index == 3:
                npc_id = HOME_NPC_IDS[self.gender]
            elif task_id == 12 and index == 0:
                self.set_action("Chờ được mời vào bang hội để tiếp tục nhiệm vụ")
                return True
            elif task_id == 12 and index == 1:
                npc_id = 13 + self.gender
            elif (task_id in (13, 15, 16, 17, 20, 21, 22, 23)
                  and title.startswith("báo cáo với")):
                npc_id = 13 + self.gender
            elif task_id == 16:
                self.set_action("Nhiệm vụ cần thắng thách đấu PvP với người chơi khác")
                return True
            if npc_id >= 0:
                key = f"{task_id}:{index}"
                if self._quest_step_done == key and now < self._quest_request_due:
                    self.set_action(f"Chờ server xác nhận nhiệm vụ NPC {npc_id}")
                    return True
                npc = self.npcs.get(npc_id)
                if npc is None:
                    self.set_action(f"Chờ {self._npc_label(npc_id)} nhiệm vụ")
                    return True
                if (npc[0] - self.x) ** 2 + (npc[1] - self.y) ** 2 > 55 ** 2:
                    self._move_towards(*npc)
                    self.set_action(f"Đi tới {self._npc_label(npc_id)} nhiệm vụ")
                    return True
                self._send(33, struct.pack(">h", npc_id))
                self._quest_step_done = key
                self._quest_request_due = now + 5
                self.set_action(f"Nói chuyện với {self._npc_label(npc_id)}")
                return True
            if title.startswith(("tiêu diệt", "diệt ", "đánh ", "đánh bại ", "hạ ", "giết ")):
                matches = self._match_quest_mobs(title)
                if matches:
                    self._quest_target_templates = matches
                    goal = self._best_quest_map(matches)
                    if goal is None:
                        self.set_action(f"Chưa tìm được tuyến tới map có quái nhiệm vụ: {title[:80]}")
                        return True
                    if goal != self.map_id:
                        return self._travel_to(goal, now)
                else:
                    self.set_action(f"Chưa nhận diện được loại quái trong nhiệm vụ: {title[:80]}")
                    return True
            elif title.startswith(("tìm ", "thu thập ")):
                self.set_action(f"Nhiệm vụ tìm kiếm chưa có luật tự động: {title[:80]}")
                return True
            return False
        key = f"{task['task_id']}:{index}"
        if self._quest_step_done == key and now < self._quest_request_due:
            self.set_action(f"Chờ server xác nhận nhiệm vụ NPC {npc_id}")
            return True
        npc = self.npcs.get(npc_id)
        if npc is None:
            self.set_action(f"Chờ {self._npc_label(npc_id)} nhiệm vụ")
            return True
        if (npc[0] - self.x) ** 2 + (npc[1] - self.y) ** 2 > 55 ** 2:
            self._move_towards(*npc)
            self.set_action(f"Đi tới {self._npc_label(npc_id)} nhiệm vụ")
            return True
        self._send(33, struct.pack(">h", npc_id))
        self._quest_step_done = key
        self._quest_request_due = now + 5
        self.set_action(f"Nói chuyện với {self._npc_label(npc_id)}")
        return True

    def _best_quest_map(self, target_templates: set[int]) -> int | None:
        """Prefer a nearby, survivable quest mob over a higher-level spawn."""
        candidates: list[tuple[tuple[int, int, int, int], int]] = []
        blocked = set(self._travel_blocked)
        level_limit = ROUTES.player_level(self.power) + 2
        hp_limit = max(250, self.damage * 25)
        for map_id, spawns in ROUTES.map_mobs.items():
            matching = [(template, level) for template, level, _ in spawns
                        if template in target_templates]
            if not matching:
                continue
            path = MOVEMENT.plan(self.map_id, map_id, blocked, gender=self.gender)
            if path is None:
                continue
            viable = any(level <= level_limit and ROUTES.mob_hp.get(template, 0) <= hp_limit
                         for template, level in matching)
            score = (int(viable), -len(path), -min(level for _, level in matching), -map_id)
            candidates.append((score, map_id))
        return max(candidates, default=(None, None), key=lambda candidate: candidate[0])[1]

    @staticmethod
    def _match_quest_mobs(title: str) -> set[int]:
        normalized_title = title.casefold()
        matches = [(template, name.casefold()) for template, name in ROUTES.mob_names.items()
                   if name and name.casefold() in normalized_title]
        return {template for template, name in matches
                if not any(name != other and name in other and other in normalized_title
                           for _, other in matches)}

    def _planet_index(self) -> int:
        """Infer the active planet from the character's actual map, not race."""
        for map_id in (self.home_map, self.map_id):
            for planet, maps in enumerate(PLANET_MAPS):
                if map_id in maps:
                    return planet
        return self.gender if self.gender in (0, 1, 2) else self.config.gender

    def _quest_planet(self, target: int, now: float) -> bool:
        """Keep challenge-quest farming on its target planet."""
        if self.map_id in PLANET_MAPS[target]:
            if self._quest_step_done.startswith("planet:"):
                self._quest_step_done = ""
                self._quest_request_due = 0
            return False
        return self._travel_to(24 + target, now)

    def _block_travel_step(self, now: float, reason: str) -> None:
        edge = self._travel_step
        if edge:
            self._travel_blocked[edge] = now + 30
        self._travel_step = None
        self._travel_phase = ""
        self._travel_npc = self._travel_menu = -1
        self._travel_attempts = 0
        self.set_action(reason + "; thử tuyến khác")

    def _travel_to(self, goal: int, now: float, allow_spaceships: bool = True) -> bool:
        if goal == self.map_id:
            self._travel_goal = goal
            self._travel_step = None
            self._travel_attempts = 0
            self._travel_phase = ""
            self._travel_npc = self._travel_menu = -1
            return False

        if self._travel_goal != goal:
            self._travel_goal = goal
            self._travel_step = None
            self._travel_attempts = 0
            self._travel_blocked.clear()
            self._travel_phase = ""
            self._travel_npc = self._travel_menu = -1
        self._travel_blocked = {edge: expiry for edge, expiry in self._travel_blocked.items()
                                if expiry > now}
        blocked = set(self._travel_blocked)
        step = MOVEMENT.next_step(self.map_id, goal, blocked, self.gender, allow_spaceships)
        if step is None:
            self.set_action(f"Chưa có tuyến hợp lệ từ {self._map_label(self.map_id)} tới {self._map_label(goal)}; đang chờ thử lại")
            self._travel_next = now + 10
            return True

        edge = (step["from_map"], step["go_map"], step["kind"])
        if edge != self._travel_step:
            self._travel_step = edge
            self._travel_attempts = 0
            self._travel_phase = ""
            self._travel_npc = step.get("npc_id", -1)
            self._travel_menu = step.get("menu", -1)
            self._travel_progress_at = now
            self._travel_last_distance = 0

        if step["kind"] == "spaceship":
            npc_id = step["npc_id"]
            npc = self.npcs.get(npc_id)
            if npc is None:
                self.set_action(f"Chờ {self._npc_label(npc_id)} tại trạm tàu {self._map_label(self.map_id)}")
                return True
            if (npc[0] - self.x) ** 2 + (npc[1] - self.y) ** 2 > 55 ** 2:
                self._move_towards(*npc)
                self.set_action(f"Đi tới {self._npc_label(npc_id)} để sang {self._map_label(step['go_map'])}")
                return True
            if self._travel_phase == "menu":
                if now < self._travel_next:
                    self.set_action(f"Chờ xác nhận menu tàu tới {self._map_label(step['go_map'])}")
                    return True
                self._block_travel_step(now, f"NPC {self._npc_label(npc_id)} không mở menu tàu")
                return True
            if self._travel_phase == "wait":
                if now < self._travel_next:
                    self.set_action(f"Chờ tàu tới {self._map_label(step['go_map'])}")
                    return True
                self._travel_attempts += 1
                if self._travel_attempts >= 2:
                    self._block_travel_step(now, f"Tàu không chuyển map tới {self._map_label(step['go_map'])}")
                    return True
            self._send(33, struct.pack(">h", npc_id))
            self._travel_phase = "menu"
            self._travel_next = now + 5
            self.set_action(f"Xin menu tàu từ {self._map_label(self.map_id)} tới {self._map_label(step['go_map'])}")
            return True

        live = next((wp for wp in self.waypoints
                     if tuple(wp["bounds"]) == tuple(step["bounds"])), None)
        if live is None:
            self._travel_blocked[edge] = now + 30
            self._travel_step = None
            self.set_action(f"Không thấy cổng từ {self._map_label(self.map_id)} → {self._map_label(step['go_map'])}; đổi tuyến")
            return True

        if self._travel_goal != goal or self._travel_map != self.map_id:
            self._travel_map = self.map_id
            self._travel_attempts = 0
            self._travel_next = 0
        x1, y1, x2, y2 = live["bounds"]
        x, y = (x1 + x2) // 2, (y1 + y2) // 2
        if abs(x - self.x) > 12 or abs(y - self.y) > 12:
            distance = (x - self.x) ** 2 + (y - self.y) ** 2
            if distance < self._travel_last_distance:
                self._travel_last_distance = distance
                self._travel_progress_at = now
            elif now - self._travel_progress_at >= 12:
                self._travel_blocked[edge] = now + 30
                self._travel_step = None
                self.set_action(f"Không tiến được tới cổng sang {self._map_label(step['go_map'])}; thử đường khác")
                return True
            if not self._travel_last_distance:
                self._travel_last_distance = distance
            self._move_towards(x, y)
            self.set_action(f"Đang đi tới cổng sang {self._map_label(step['go_map'])}")
            return True
        if now >= self._travel_next and self._travel_attempts < 3:
            self._send(-23)
            self._travel_attempts += 1
            self._travel_next = now + 5
            self.set_action(f"Đang qua cổng tới {self._map_label(step['go_map'])} (lần {self._travel_attempts})")
        elif self._travel_attempts >= 3 and now >= self._travel_next:
            self._travel_blocked[edge] = now + 30
            self._travel_step = None
            self._travel_attempts = 0
            self.set_action(f"Cổng tới {self._map_label(step['go_map'])} không phản hồi; thử đường khác")
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

    def remove_all(self) -> int:
        with self._lock:
            bots = list(self._bots.values())
            self._bots.clear()
            try:
                self._save()
            except Exception:
                self._bots.update((bot.id, bot) for bot in bots)
                raise
        for bot in bots:
            bot.close()
        return len(bots)

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
        MODEL_CLIENT.stop()
