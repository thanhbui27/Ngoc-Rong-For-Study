import socket
import struct
import tempfile
import threading
import time
import unittest
import json
import os
import urllib.request
from pathlib import Path
from unittest.mock import Mock, patch

import app
import bot
from app import Handler, LocalServer, valid_batch, valid_config, valid_config_update
from bot import BotConfig, BotManager, BotRunner
from protocol import ItemMap, Mob, Reader, Wire, java_utf, parse_map, parse_shop
from routes import Routes
from storage import ConfigStore


def packet(sock, command, payload, keyed=True):
    # The current Java server uses the one-byte key 0.
    sock.sendall(struct.pack(">bH", command, len(payload)) + payload)


def read_client(sock):
    head = sock.recv(3)
    while len(head) < 3:
        head += sock.recv(3 - len(head))
    command, size = struct.unpack(">bH", head)
    payload = b""
    while len(payload) < size:
        payload += sock.recv(size - len(payload))
    return command, payload


def map_payload():
    data = bytearray()
    data += bytes([1, 0, 0, 0, 0]) + java_utf("Test map") + bytes([0])
    data += struct.pack(">hh", 100, 200)
    data += bytes([0])  # waypoints
    data += bytes([1])  # one mob
    data += bytes([0] * 5) + bytes([1, 0])
    data += struct.pack(">iBi", 100, 1, 100)
    data += struct.pack(">hhBBB", 120, 200, 5, 0, 0)
    data += bytes([0, 0, 0])  # players, NPCs, items
    return bytes(data)


def stats_payload():
    return (struct.pack(">iiiiiii", 100, 100, 10, 100, 100, 100, 100)
            + bytes([10, 20, 20, 1]) + struct.pack(">iiBqhhB", 10, 0, 0, 0, 100, 0, 0))


class ProtocolTests(unittest.TestCase):
    def test_ai_history_is_exposed_only_in_bot_detail(self):
        with tempfile.TemporaryDirectory() as directory, \
                patch.object(bot, "LOG_DIR", Path(directory)), \
                patch.object(bot.ai_memory, "ROOT", Path(directory) / "memory"):
            runner = BotRunner(BotConfig("AI", "testuser", "testpass", mode="ai"))
            try:
                bot.ai_memory.append(runner.id, "goal:farm", "Cần luyện sức mạnh", "Đã đổi mục tiêu chơi")
                self.assertNotIn("ai_history", runner.snapshot())
                history = runner.snapshot(include_logs=True)["ai_history"]
                self.assertEqual(history[0]["choice"], "goal:farm")
                self.assertEqual(history[0]["outcome"], "Đã đổi mục tiêu chơi")
                self.assertIn("at", history[0])
            finally:
                runner.close()

    def test_local_model_stops_after_last_ai_bot_stops(self):
        with tempfile.TemporaryDirectory() as directory, \
                patch.object(bot, "LOG_DIR", Path(directory) / "logs"), \
                patch.object(bot.MODEL_CLIENT, "stop") as stop_model:
            manager = BotManager(ConfigStore(Path(directory) / "state" / "bots.dat"))
            first, second = manager.create_many([
                BotConfig("AI 1", "testuser1", "testpass", mode="ai"),
                BotConfig("AI 2", "testuser2", "testpass", mode="ai"),
            ])
            try:
                for runner in (first, second):
                    runner._stop.clear()
                    runner.status = "running"
                first.stop()
                stop_model.assert_not_called()
                second.stop()
                stop_model.assert_called_once()
            finally:
                manager.close()

    def test_switching_last_bot_out_of_ai_mode_stops_model(self):
        with tempfile.TemporaryDirectory() as directory, \
                patch.object(bot, "LOG_DIR", Path(directory) / "logs"), \
                patch.object(bot.MODEL_CLIENT, "stop") as stop_model:
            manager = BotManager(ConfigStore(Path(directory) / "state" / "bots.dat"))
            runner = manager.create(BotConfig("AI", "testuser", "testpass", mode="ai"))
            try:
                runner._stop.clear()
                runner.status = "running"
                manager.update_config(runner.id, valid_config_update(runner.config, {"mode": "auto"}))
                stop_model.assert_called_once()
            finally:
                manager.close()

    def test_shop_packet_with_item_options_keeps_following_items_aligned(self):
        payload = bytearray([0, 1]) + java_utf("Trang bị") + bytes([2])
        payload += struct.pack(">HiiBHHBB", 21, 700, 0, 1, 50, 5, 0, 0)
        payload += struct.pack(">HiiBBB", 212, 100, 0, 0, 0, 0)
        self.assertEqual(parse_shop(bytes(payload)), {
            21: {"gold": 700, "gems": 0, "options": [{"id": 50, "param": 5}]},
            212: {"gold": 100, "gems": 0, "options": []},
        })

    def test_first_quest_moves_opens_chest_and_harvests(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(bot, "LOG_DIR", Path(directory)):
            runner = BotRunner(BotConfig("Quest", "testuser", "testpass"))
            runner._send = Mock()
            try:
                runner.map_id, runner.x, runner.y = 39, 100, 384
                runner.task = {"task_id": 0, "index": 0, "steps": [{"map_id": -1, "npc_id": -1}]}
                self.assertTrue(runner._quest(10))
                self.assertEqual(runner._send.call_args.args[0], -7)
                self.assertIn("mũi tên", runner.action)

                runner.map_id, runner.x, runner.y = 21, 100, 100
                runner.npcs = {3: (100, 100), 4: (120, 100), 0: (100, 100)}
                runner.task = {"task_id": 0, "index": 3, "steps": [{}] * 3 + [{"map_id": 21, "npc_id": 3}]}
                self.assertTrue(runner._quest(11))
                runner._send.assert_called_with(33, struct.pack(">h", 3))
                box = bytes([0, 1]) + struct.pack(">hi", 12, 1) + java_utf("") + java_utf("") + bytes([0])
                runner._packet(-35, box)
                self.assertTrue(runner._quest(15))
                runner._send.assert_called_with(-40, bytes([0, 0]))

                runner.task = {"task_id": 0, "index": 4, "steps": [{}] * 4 + [{"map_id": 21, "npc_id": 4}]}
                runner._quest_request_due = 0
                self.assertTrue(runner._quest(16))
                runner._send.assert_called_with(-34, bytes([1]))
                runner._packet(-34, bytes([1]) + java_utf("Thu\nhoạch"))
                self.assertTrue(runner._quest(17))
                runner._send.assert_called_with(22, bytes([0, 0]))

                runner.task = {"task_id": 0, "index": 5, "steps": [{}] * 5 + [{"map_id": 21, "npc_id": 0}]}
                self.assertTrue(runner._quest(18))
                runner._send.assert_called_with(33, struct.pack(">h", 0))
            finally:
                runner.close()

    def test_training_quest_targets_moc_nhan(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(bot, "LOG_DIR", Path(directory)):
            runner = BotRunner(BotConfig("Quest", "testuser", "testpass"))
            try:
                runner.map_id = 21
                runner.task = {"task_id": 1, "index": 0,
                               "steps": [{"map_id": -1, "npc_id": -1, "title": "Đánh ngã 5 mộc nhân"}]}
                runner._quest(10)
                self.assertIn(0, runner._quest_target_templates)
            finally:
                runner.close()

    def test_quest_mob_search_includes_cross_planet_spaceship_route(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(bot, "LOG_DIR", Path(directory)):
            runner = BotRunner(BotConfig("Quest", "testuser", "testpass", gender=0))
            try:
                runner._send = Mock()
                runner.map_id = 5  # Earth Guru; the next guild quest target is Namek.
                runner.waypoints = bot.ROUTES.maps[5]
                runner.task = {"task_id": 13, "index": 1,
                               "steps": [{"map_id": -1, "npc_id": -1, "title": "Tiêu diệt Heo rừng"},
                                         {"map_id": -1, "npc_id": -1,
                                          "title": "Tiêu diệt Heo da xanh"}]}
                goal = runner._best_quest_map({17})
                self.assertEqual(goal, 31)
                self.assertEqual(runner._match_quest_mobs("tiêu diệt heo da xanh"), {17})
                self.assertIn("spaceship", {step["kind"]
                                            for step in bot.MOVEMENT.plan(5, goal, gender=0)})
                self.assertTrue(runner._quest(time.monotonic()))
                self.assertIn("Rừng xương (ID: 4)", runner.action)
            finally:
                runner.close()

    def test_quest_recognizes_defeat_objective_and_selects_target_mob(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(bot, "LOG_DIR", Path(directory)):
            runner = BotRunner(BotConfig("Quest", "testuser", "testpass", gender=2))
            try:
                runner.gender = 2
                runner._send = Mock()
                runner.map_id = 17
                runner.task = {"task_id": 7, "index": 1,
                               "steps": [{"map_id": -1, "npc_id": -1, "title": "power"},
                                         {"map_id": 17, "npc_id": -1,
                                          "title": "Đánh bại 20 con quỷ bay"}]}
                with patch.object(runner, "_best_quest_map", return_value=17):
                    self.assertFalse(runner._quest(time.monotonic()))
                self.assertEqual(runner._quest_target_templates, {9})
            finally:
                runner.close()

    def test_quest_map_prefers_nearby_survivable_mob(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(bot, "LOG_DIR", Path(directory)):
            runner = BotRunner(BotConfig("Quest", "testuser", "testpass"))
            try:
                runner.map_id, runner.power, runner.damage = 1, 0, 10
                with patch.object(bot.ROUTES, "map_mobs", {1: [(9, 1, 50)], 17: [(9, 9, 200)]}):
                    self.assertEqual(runner._best_quest_map({9}), 1)
            finally:
                runner.close()

    def test_mentor_quest_travels_to_npc_map_before_talking(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(bot, "LOG_DIR", Path(directory)):
            runner = BotRunner(BotConfig("Quest", "testuser", "testpass", gender=1))
            try:
                runner.gender, runner.map_id = 1, 8
                runner.task = {"task_id": 11, "index": 0,
                               "steps": [{"map_id": -1, "npc_id": -1, "title": "Tìm trưởng lão Guru"}]}
                with patch.object(runner, "_travel_to", return_value=True) as travel:
                    self.assertTrue(runner._quest(10))
                    travel.assert_called_once_with(13, 10)
            finally:
                runner.close()

    def test_cat_quest_finds_bo_mong_then_climbs_karin_tower(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(bot, "LOG_DIR", Path(directory)):
            runner = BotRunner(BotConfig("Quest", "testuser", "testpass"))
            try:
                runner._send = Mock()
                runner.task = {"task_id": 9, "index": 0,
                               "steps": [{"map_id": -1, "npc_id": -1,
                                          "title": "Nói chuyện với Bò Mộng"},
                                         {"map_id": -1, "npc_id": -1, "title": "Đụng độ Tàu Pảy Pảy"},
                                         {"map_id": -1, "npc_id": -1, "title": "Bỏ chạy lên tháp Karin"}]}
                runner.map_id = 1
                with patch.object(runner, "_travel_to", return_value=True) as travel:
                    self.assertTrue(runner._quest(10))
                    travel.assert_called_once_with(47, 10)
                runner.map_id = 47
                runner.npcs = {17: (100, 100)}
                runner.x = runner.y = 100
                self.assertTrue(runner._quest(11))
                runner._send.assert_called_with(33, struct.pack(">h", 17))
                runner.task["index"] = 2
                with patch.object(runner, "_travel_to", return_value=True) as travel:
                    self.assertTrue(runner._quest(12))
                    travel.assert_called_once_with(46, 12)
            finally:
                runner.close()

    def test_travel_status_shows_map_name_and_id(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(bot, "LOG_DIR", Path(directory)):
            runner = BotRunner(BotConfig("Quest", "testuser", "testpass"))
            try:
                runner.map_id = 1
                runner.map_name = "Đồi hoa cúc"
                runner.x, runner.y = 100, 336
                runner.waypoints = bot.ROUTES.maps[1]
                runner._send = Mock()
                self.assertTrue(runner._travel_to(47, 10))
                self.assertEqual(runner.action, "Đang đi tới cổng sang Rừng Karin (ID: 47)")
                self.assertEqual(runner._map_label(46), "Tháp Karin (ID: 46)")
                self.assertEqual(runner._map_label(9999), "Map (ID: 9999)")
            finally:
                runner.close()

    def test_quest_bot_collects_drops_and_resumes_target_mob(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(bot, "LOG_DIR", Path(directory)):
            runner = BotRunner(BotConfig("Quest", "testuser", "testpass", stat="off"))
            try:
                runner._ready = True
                runner.status = "running"
                runner.map_id = 1
                runner.hp = runner.max_hp = 100
                runner.power = 3000
                runner.damage = 10
                runner.x = runner.y = 100
                runner.task = {"task_id": 13, "index": 1,
                               "steps": [{}, {"map_id": -1, "npc_id": -1,
                                              "title": "Tiêu diệt Heo da xanh"}]}
                runner.mobs = {0: Mob(0, 17, 2, 100, 100, 200, 200, 5, 0)}
                runner.items = {7: ItemMap(7, 100, 100, 100, -1)}
                sent = []
                runner._send = lambda command, payload=b"": sent.append((command, payload))
                with patch.object(runner, "_best_quest_map", return_value=1):
                    runner._tick()
                self.assertEqual(sent[-1], (-20, struct.pack(">H", 7)))

                runner.items.clear()
                runner._next_action = 0
                with patch.object(runner, "_best_quest_map", return_value=1):
                    runner._tick()
                self.assertEqual(sent[-1], (54, b"\x00"))

                runner._next_action = 0
                runner.task = {"task_id": 2, "index": 0,
                               "steps": [{"map_id": -1, "npc_id": -1, "title": "Tìm đùi gà"}]}
                runner.mobs = {0: Mob(0, 1, 2, 100, 100, 200, 200, 5, 0)}
                runner.items[7] = ItemMap(7, 100, 100, 100, -1)
                runner.items[8] = ItemMap(8, 73, 100, 100, -1)
                runner._tick()
                self.assertEqual(sent[-1], (-20, struct.pack(">H", 8)))

                runner.items.pop(8)
                runner._next_action = 0
                runner._tick()
                self.assertEqual(sent[-1], (-20, struct.pack(">H", 7)))
            finally:
                runner.close()

    def test_skip_quest_returns_home_and_waits_for_server_task(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(bot, "LOG_DIR", Path(directory)):
            runner = BotRunner(BotConfig("Quest", "testuser", "testpass", stat="off"))
            try:
                runner._ready = True
                runner.status = "running"
                runner.hp = runner.max_hp = 100
                runner.map_id = 47
                runner.task = {"task_id": 9, "index": 2, "steps": [{}, {}, {}]}
                runner._send = Mock()
                runner.request_skip_quest()
                runner._tick()
                runner._send.assert_called_with(-15)
                runner.map_id = 21
                runner._next_action = 0
                runner._tick()
                runner._send.assert_called_with(126)
                runner.task = {"task_id": 10, "index": 0, "steps": [{}]}
                runner._next_action = 0
                runner._tick()
                self.assertIsNone(runner._skip_quest_id)
            finally:
                runner.close()

    def test_karin_quest_opens_duel_and_attacks_own_boss(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(bot, "LOG_DIR", Path(directory)):
            runner = BotRunner(BotConfig("Karin", "testuser", "testpass"))
            runner._send = Mock()
            try:
                runner.map_id, runner.x, runner.y = 46, 100, 100
                runner.player_id = 123
                runner.npcs = {18: (100, 100)}
                runner.task = {"task_id": 10, "index": 0, "steps": [
                    {"map_id": 46, "npc_id": -1, "title": "Đánh thắng Thần mèo"}]}
                self.assertTrue(runner._quest(10))
                runner._send.assert_called_with(33, struct.pack(">h", 18))
                menu = (struct.pack(">h", 18) + java_utf("Thần Mèo") + bytes([4])
                        + b"".join(java_utf(option) for option in
                                   ("Tập tự động", "Nhiệm vụ", "Tập luyện", "Thách đấu\nThần Mèo")))
                runner._packet(32, menu)
                runner._send.assert_called_with(32, struct.pack(">hb", 18, 3))
                confirm = (struct.pack(">h", 18) + java_utf("Thách đấu") + bytes([2])
                           + java_utf("Đồng ý\ngiao đấu") + java_utf("Không đồng ý"))
                runner._packet(32, confirm)
                runner._send.assert_called_with(32, struct.pack(">hb", 18, 0))
                boss_id = -351126
                self.assertEqual(runner._karin_boss_id, boss_id)
                self.assertEqual(runner._karin_boss_pos, (420, 408))
                boss = (bytes([7]) + struct.pack(">i", boss_id) + bytes(11) + java_utf("Karin")
                        + struct.pack(">ii", 500, 500) + bytes(6) + struct.pack(">hh", 100, 100))
                runner._packet(-30, boss)
                self.assertEqual(runner._karin_boss_id, boss_id)
                self.assertTrue(runner._quest(20))
                runner._send.assert_called_with(-60, struct.pack(">i", boss_id))
            finally:
                runner.close()

    def test_tau_quest_trains_when_weak_and_attacks_when_ready(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(bot, "LOG_DIR", Path(directory)):
            runner = BotRunner(BotConfig("Tau", "testuser", "testpass"))
            runner._send = Mock()
            try:
                runner.player_id = 49
                runner.task = {"task_id": 10, "index": 1, "steps": [
                    {}, {"map_id": 0, "npc_id": -1, "title": "Tiêu diệt Tàu Pảy Pảy"}]}
                runner.map_id = 46
                runner.damage, runner.max_hp = 24, 1048
                self.assertTrue(runner._quest(10))
                runner._send.assert_called_with(-15)
                runner.map_id = 21
                self.assertFalse(runner._quest(11))
                runner.map_id, runner.x, runner.y = 47, 775, 300
                runner.damage, runner.max_hp = 500, 4000
                self.assertTrue(runner._quest(12))
                runner._send.assert_called_with(-60, struct.pack(">i", -10251052))
            finally:
                runner.close()

    def test_farm_mode_does_not_follow_quest(self):
        config = valid_config({"name": "Farm", "username": "testuser", "password": "testpass",
                               "mode": "farm"})
        self.assertEqual(config.mode, "farm")
        with tempfile.TemporaryDirectory() as directory, patch.object(bot, "LOG_DIR", Path(directory)):
            runner = BotRunner(config)
            try:
                runner._ready = True
                runner.status = "running"
                runner.map_id = 1
                runner.hp = runner.max_hp = 100
                runner.task = {"task_id": 9, "index": 2, "steps": [{}, {}, {}]}
                runner._send = Mock()
                with patch.object(runner, "_quest") as quest:
                    runner._tick()
                    quest.assert_not_called()
            finally:
                runner.close()

    def test_ai_only_offers_affordable_usable_gear_and_skill_books(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(bot, "LOG_DIR", Path(directory)):
            runner = BotRunner(BotConfig("AI", "testuser", "testpass", mode="ai"))
            try:
                runner.gender = 0
                runner.power = 10000
                runner.gold = 1000
                runner.gems = 10
                runner.mp = 100
                runner.learned_skill_ids = {0}
                runner.bag_slots = {94: 2}
                runner.bag = {94: 1}
                runner.shop = {
                    21: {"gold": 700, "gems": 0, "options": []},
                    24: {"gold": 15000, "gems": 0, "options": []},
                    79: {"gold": 0, "gems": 5, "options": []},
                }
                choices = {entry["id"] for entry in runner._ai_choices(10)}
                self.assertIn("learn:94", choices)
                self.assertIn("buy:21", choices)
                self.assertNotIn("buy:24", choices)
                self.assertNotIn("buy:79", choices)
                runner._send = Mock()
                self.assertTrue(runner._ai_apply({"choice": "learn:94", "reason": "học chưởng"}, 10))
                runner._send.assert_called_with(-43, bytes([0, 1, 2]))
                runner._subcommand(bytes([23]) + struct.pack(">H", 7))
                self.assertIn(7, runner.learned_skill_ids)
                self.assertNotIn("learn:94", {entry["id"] for entry in runner._ai_choices(20)})
            finally:
                runner.close()

    def test_ai_sets_own_farming_goal_and_stat_focus(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(bot, "LOG_DIR", Path(directory)):
            runner = BotRunner(BotConfig("AI", "testuser", "testpass", mode="ai"))
            try:
                runner._ready = True
                runner.status = "running"
                runner.hp = runner.max_hp = 100
                runner.map_id = 1
                runner.power = 3000
                runner.potential = 1000
                runner.base_damage = 10
                runner.task = {"task_id": 9, "index": 2, "steps": [{}, {}, {}]}
                runner._send = Mock()
                now = time.monotonic()
                self.assertTrue(runner._ai_apply({"choice": "goal:farm", "reason": "cần luyện"}, now))
                self.assertEqual(runner._ai_goal, "farm")
                self.assertNotIn("goal:quest", {entry["id"] for entry in runner._ai_choices(now + 60)})
                self.assertTrue(runner._ai_apply({"choice": "stat:attack", "reason": "tăng sát thương"}, now))
                self.assertEqual(runner._ai_stat_focus, "attack")
                with patch.object(runner, "_ai_tick", return_value=False), patch.object(runner, "_quest") as quest:
                    runner._tick()
                    quest.assert_not_called()
                runner._send.assert_any_call(-30, bytes([16, 2]) + struct.pack(">h", 1))
                runner._ai_next = now + 999
                runner._ai_tick(now + 301)
                self.assertEqual(runner._ai_goal, "quest")
            finally:
                runner.close()

    def test_starter_gear_is_bought_and_equipped_from_own_village(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(bot, "LOG_DIR", Path(directory)):
            runner = BotRunner(BotConfig("Gear", "testuser", "testpass"))
            try:
                runner._send = Mock()
                runner.map_id, runner.gender, runner.gold = 0, 0, 10000
                runner.x = runner.y = 100
                runner.npcs = {7: (100, 100)}
                self.assertTrue(runner._supply(10))
                runner._send.assert_called_with(33, struct.pack(">h", 7))
                self.assertTrue(runner._supply(11))
                runner.shop = {21: {"gold": 700, "gems": 0}}
                self.assertTrue(runner._supply(12))
                self.assertTrue(runner._supply(20))
                runner._send.assert_called_with(6, bytes([0]) + struct.pack(">h", 21))
                runner.bag, runner.bag_slots = {21: 1}, {21: 3}
                self.assertTrue(runner._equip_starter_gear(21))
                runner._send.assert_called_with(-40, bytes([4, 3]))
            finally:
                runner.close()

    def test_server_route_refusal_blocks_current_travel_edge(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(bot, "LOG_DIR", Path(directory)):
            runner = BotRunner(BotConfig("Quest", "testuser", "testpass"))
            try:
                runner._travel_step = (24, 17, "spaceship")
                runner._travel_phase = "menu"
                runner._packet(-25, java_utf("Bạn không thể đến khu vực này"))
                self.assertIsNone(runner._travel_step)
                self.assertIn((24, 17, "spaceship"), runner._travel_blocked)
                self.assertIn("bị server từ chối", runner.action)
            finally:
                runner.close()

    def test_rescue_quest_uses_return_home_while_transport_is_locked(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(bot, "LOG_DIR", Path(directory)):
            runner = BotRunner(BotConfig("Quest", "testuser", "testpass", gender=2))
            try:
                runner._send = Mock()
                runner.map_id = 24
                runner.task = {"task_id": 7, "index": 1,
                               "steps": [{"map_id": -1, "npc_id": -1},
                                         {"map_id": 17, "npc_id": -1,
                                          "title": "Đánh bại 20 con quỷ bay"}]}
                self.assertTrue(runner._quest(time.monotonic()))
                runner._send.assert_called_once_with(-15)
                self.assertIn("tàu", runner.action)
            finally:
                runner.close()

    def test_character_faction_is_saved_and_sent_to_server(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(bot, "LOG_DIR", Path(directory)):
            for gender, hair in ((0, 64), (1, 9), (2, 6)):
                config = valid_config({"name": "Faction", "username": "testuser",
                                       "password": "testpass", "gender": gender,
                                       "auto_register": False})
                runner = BotRunner(config)
                runner._send = Mock()
                runner._auth_phase = "login"
                runner._packet(2, b"")
                command, payload = runner._send.call_args.args
                reader = Reader(payload)
                self.assertEqual((command, reader.u8()), (-28, 2))
                self.assertLessEqual(5, len(reader.utf()))
                self.assertEqual((reader.u8(), reader.u8()), (gender, hair))
                runner.close()
            self.assertEqual(valid_batch({"name_prefix": "bot", "username_prefix": "abc",
                                          "start_number": 10, "count": 2,
                                          "password": "testpass", "gender": 2})[1].gender, 2)

    def test_reconnects_after_socket_closes(self):
        listener = socket.socket()
        listener.bind(("127.0.0.1", 0))
        listener.listen(2)
        listener.settimeout(6)
        with tempfile.TemporaryDirectory() as directory, patch.object(bot, "LOG_DIR", Path(directory)):
            runner = BotRunner(BotConfig("Retry", "testuser", "testpass", "127.0.0.1",
                                         listener.getsockname()[1], auto_register=False))
            try:
                runner.start()
                first, _ = listener.accept()
                self.assertEqual(read_client(first)[0], -27)
                first.close()
                second, _ = listener.accept()
                with second:
                    self.assertEqual(read_client(second)[0], -27)
                    self.assertGreaterEqual(runner._reconnect_attempt, 1)
                    self.assertTrue(any("Mất kết nối" in event["message"] for event in runner.logs))
            finally:
                runner.close()
                listener.close()

    def test_low_ki_returns_home_harvests_and_resumes(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(bot, "LOG_DIR", Path(directory)):
            runner = BotRunner(BotConfig("Recovery", "testuser", "testpass"))
            runner._send = Mock()
            runner.max_mp, runner.mp, runner.map_id, runner.gender = 100, 0, 1, 0
            self.assertTrue(runner._recover(10))
            runner._send.assert_called_with(-15)
            self.assertIn("về nhà", runner.action)

            runner.map_id = 21
            self.assertTrue(runner._recover(15))
            runner._send.assert_called_with(-34, bytes([2]))
            tree = (bytes([0]) + struct.pack(">h", 1) + java_utf("Đậu thần")
                    + struct.pack(">hhBh", 100, 200, 1, 3)
                    + struct.pack(">h", 5) + java_utf("Cây đậu") + struct.pack(">i", 30))
            runner._packet(-34, tree)
            self.assertEqual((runner._tree_peas, runner._tree_seconds), (3, 30))
            self.assertTrue(runner._recover(18))
            runner._send.assert_called_with(-34, bytes([1]))
            runner._packet(-34, bytes([1]) + java_utf("Thu\nhoạch"))
            self.assertTrue(runner._recover(20))
            runner._send.assert_called_with(22, bytes([0, 0]))
            runner.bag, runner.bag_slots = {13: 3}, {13: 2}
            self.assertTrue(runner._recover(23))
            runner._send.assert_called_with(-43, bytes([0, 1, 2]))
            runner.mp = 80
            self.assertFalse(runner._recover(25))
            self.assertFalse(runner._recovering)
            runner.close()

    def test_batch_names_and_saved_bots_survive_restart(self):
        raw = {"name_prefix": "bot", "username_prefix": "abc", "start_number": 123,
               "count": 3, "password": "secret123", "auto_register": True, "gender": 2}
        configs = valid_batch(raw)
        self.assertEqual([config.username for config in configs], ["abc123", "abc124", "abc125"])
        with tempfile.TemporaryDirectory() as directory, patch.object(bot, "LOG_DIR", Path(directory) / "logs"):
            store = ConfigStore(Path(directory) / "state" / "bots.dat")
            manager = BotManager(store)
            created = manager.create_many(configs)
            ids = [item.id for item in created]
            self.assertEqual(len(ids), 3)
            if os.name == "nt":
                self.assertNotIn(b"secret123", store.path.read_bytes())
            manager.close()
            restored = BotManager(store)
            self.assertEqual([item["id"] for item in restored.all()], ids)
            self.assertTrue(all(item["status"] == "stopped" for item in restored.all()))
            self.assertEqual(restored.get(ids[0]).config.password, "secret123")
            self.assertEqual(restored.get(ids[0]).config.gender, 2)
            updated = valid_config_update(restored.get(ids[1]).config,
                                          {"stat": "attack", "gender": "1", "trade_partner": "123",
                                           "shop_npc": "7", "shop_item": "457",
                                           "shop_min": "1", "shop_target": "10"})
            restored.update_config(ids[1], updated)
            restored.remove(ids[0])
            restored.close()
            again = BotManager(store)
            self.assertEqual(len(again.all()), 2)
            self.assertEqual(again.get(ids[1]).config.trade_partner, 123)
            self.assertEqual(again.get(ids[1]).config.stat, "attack")
            self.assertEqual(again.get(ids[1]).config.gender, 1)
            again.close()

    def test_batch_http_endpoint_creates_saved_bots(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(bot, "LOG_DIR", Path(directory) / "logs"):
            manager = BotManager(ConfigStore(Path(directory) / "state" / "bots.dat"))
            with patch.object(app, "MANAGER", manager):
                server = LocalServer(("127.0.0.1", 0), Handler)
                thread = threading.Thread(target=server.serve_forever, daemon=True)
                thread.start()
                try:
                    payload = {"name_prefix": "bot", "username_prefix": "abc", "start_number": 7,
                               "count": 2, "password": "secret123", "host": "127.0.0.1", "port": 1,
                               "auto_register": True}
                    request = urllib.request.Request(
                        f"http://127.0.0.1:{server.server_port}/api/bots/batch",
                        data=json.dumps(payload).encode(), headers={"Content-Type": "application/json"}, method="POST")
                    with urllib.request.urlopen(request, timeout=5) as response:
                        created = json.load(response)
                    self.assertEqual([item["username"] for item in created], ["abc7", "abc8"])
                    self.assertEqual(len(manager.all()), 2)
                    update = urllib.request.Request(
                        f"http://127.0.0.1:{server.server_port}/api/bots/{created[0]['id']}/config",
                        data=json.dumps({"stat": "attack", "trade_partner": 123}).encode(),
                        headers={"Content-Type": "application/json"}, method="POST")
                    with urllib.request.urlopen(update, timeout=5) as response:
                        changed = json.load(response)
                    self.assertEqual((changed["stat"], changed["trade_partner"]), ("attack", 123))
                finally:
                    server.shutdown()
                    server.server_close()
                    manager.close()
                    thread.join(timeout=3)

    def test_registration_credentials_are_validated_before_start(self):
        with self.assertRaisesRegex(ValueError, "mật khẩu 5–18"):
            valid_config({"name": "Test", "username": "abc12", "password": "1234", "auto_register": True})
        config = valid_config({"name": "Test", "username": "abc12", "password": "12345", "auto_register": True})
        self.assertTrue(config.auto_register)

    def test_map_decoder_matches_server_layout(self):
        result = parse_map(map_payload())
        self.assertEqual((result["map_id"], result["x"], result["y"]), (1, 100, 200))
        self.assertEqual(result["mobs"][0].hp, 100)

    def test_session_key_and_big_packet(self):
        client, server = socket.socketpair()
        try:
            wire = Wire(client)
            packet(server, -27, bytes([1, 0]))
            command, payload = wire.read()
            self.assertEqual(command, -27)
            wire.accept_key(payload)
            wire.send(-29, b"\x02")
            self.assertEqual(read_client(server), (-29, b"\x02"))
            server.sendall(bytes([(-87) & 255, 0x84, 0x80, 0x80]) + b"test")
            self.assertEqual(wire.read(), (-87, b"test"))
        finally:
            client.close()
            server.close()

    def test_item_options_use_server_names_in_bag_box_and_worn_details(self):
        self.assertEqual(bot.ROUTES.option_names[6], "HP+#")
        item = {6: {"id": 6, "count": 1,
                    "options": [{"id": 6, "param": 33}, {"id": 263, "param": 1},
                                {"id": 264, "param": 0}, {"id": 30, "param": 0},
                                {"id": 73, "param": 0}]}}
        labels = [option["label"] for option in BotRunner._named_items(item)[6]["options"]]
        self.assertEqual(labels, ["HP+33", "Set Gohan",
                                  "(5 món +300% may mắn, +50% vàng rơi từ quái)",
                                  "Không thể giao dịch", ""])

    def test_route_graph_uses_clean_seed(self):
        routes = Routes()
        self.assertGreater(len(routes.maps), 100)
        self.assertEqual(routes.next_hop(1, 5)["go_map"], 2)
        self.assertEqual(routes.nearest_farm_map(39), 0)
        self.assertEqual(routes.mob_names[0], "Mộc nhân")
        self.assertEqual(routes.best_farm_map(39, 2000, 10), 1)
        self.assertEqual(routes.best_farm_map(0, 15000, 20), 2)

    def test_power_gain_and_target_rotation(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(bot, "LOG_DIR", Path(directory)):
            runner = BotRunner(BotConfig("Auto", "testuser", "testpass", stat="off"))
            try:
                runner._ready = True
                runner.status = "running"
                runner.map_id = 1
                runner.hp = runner.max_hp = 100
                runner.power = 3000
                runner.damage = 10
                runner.x, runner.y = 100, 100
                runner.mobs = {0: Mob(0, 1, 2, 100, 100, 200, 200, 5, 0),
                               1: Mob(1, 1, 2, 110, 100, 200, 200, 5, 0)}
                sent = []
                runner._send = lambda command, payload=b"": sent.append((command, payload))
                runner._tick()
                self.assertEqual(sent[-1], (54, b"\x00"))
                runner._packet(-12, b"\x00" + bytes(5) + b"\x00")
                runner._next_action = 0
                runner._tick()
                self.assertEqual(sent[-1], (54, b"\x01"))
                runner._packet(-3, b"\x02" + struct.pack(">i", 150))
                self.assertEqual((runner.power, runner.potential), (3150, 150))
            finally:
                runner.close()

    def test_empty_map_starts_travel_to_farm_map(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(bot, "LOG_DIR", Path(directory)):
            runner = BotRunner(BotConfig("Auto", "testuser", "testpass", stat="off"))
            runner._ready = True
            runner.status = "running"
            runner.map_id = 39
            runner.hp = 100
            runner.x, runner.y = 100, 384
            runner.waypoints = bot.ROUTES.maps[39]
            sent = []
            runner._send = lambda command, payload=b"": sent.append(command)
            try:
                runner._tick()
                self.assertEqual(sent, [-7])
                self.assertEqual(runner.action, "Đang đi tới cổng sang Nhà Gôhan (ID: 21)")
            finally:
                runner.close()

    def test_headless_bot_logs_in_and_attacks(self):
        listener = socket.socket()
        listener.bind(("127.0.0.1", 0))
        listener.listen(1)
        listener.settimeout(8)
        commands = []

        def fake_server():
            connection, _ = listener.accept()
            with connection:
                connection.settimeout(8)
                commands.append(read_client(connection)[0])
                packet(connection, -27, bytes([1, 0]) + java_utf("localhost") + struct.pack(">iB", 14445, 0), False)
                commands.append(read_client(connection)[0])
                login_command, login_payload = read_client(connection)
                commands.append(login_command)
                self.assertTrue(b"testuser" in login_payload)
                packet(connection, -28, bytes([4, 1, 1, 1, 1]))
                commands.append(read_client(connection)[0])
                packet(connection, -30, bytes([0]) + struct.pack(">iBBH", 42, 0, 0, 1) + java_utf("Tester"))
                packet(connection, -42, stats_payload())
                packet(connection, -24, map_payload())
                deadline = time.monotonic() + 6
                while time.monotonic() < deadline:
                    command, _ = read_client(connection)
                    commands.append(command)
                    if command == 54:
                        return

        server_thread = threading.Thread(target=fake_server, daemon=True)
        server_thread.start()
        with tempfile.TemporaryDirectory() as directory, patch.object(bot, "LOG_DIR", Path(directory)):
            runner = BotRunner(BotConfig("Fake", "testuser", "fakepass", "127.0.0.1", listener.getsockname()[1], stat="off", auto_register=False))
            runner.start()
            server_thread.join(timeout=8)
            runner.stop()
            self.assertFalse(server_thread.is_alive())
            self.assertIn(-27, commands)
            self.assertEqual(commands.count(-29), 2)
            self.assertIn(-38, commands)
            self.assertIn(-39, commands)
            self.assertIn(54, commands)
            self.assertEqual(runner.player_id, 42)
            runner.close()
        listener.close()

    def test_registers_missing_account_then_creates_character(self):
        listener = socket.socket()
        listener.bind(("127.0.0.1", 0))
        listener.listen(1)
        listener.settimeout(8)
        received = []

        def fake_server():
            connection, _ = listener.accept()
            with connection:
                connection.settimeout(8)
                received.append(read_client(connection)[0])
                packet(connection, -27, bytes([1, 0]) + java_utf("localhost") + struct.pack(">iB", 14445, 0))
                received.append(read_client(connection)[0])
                command, payload = read_client(connection)
                received.append(command)
                reader = Reader(payload)
                received.append([reader.utf() for _ in range(9)])
                packet(connection, -26, java_utf("Đăng ký thành công. Hãy quay lại màn hình đăng nhập để chơi."))
                received.append(read_client(connection)[0])
                packet(connection, -28, bytes([4, 1, 1, 1, 1]))
                received.append(read_client(connection)[0])
                packet(connection, 2, b"")
                command, payload = read_client(connection)
                received.append(command)
                reader = Reader(payload)
                received.append((reader.u8(), reader.utf(), reader.u8(), reader.u8()))

        server_thread = threading.Thread(target=fake_server, daemon=True)
        server_thread.start()
        with tempfile.TemporaryDirectory() as directory, patch.object(bot, "LOG_DIR", Path(directory)):
            runner = BotRunner(BotConfig("New", "newuser", "newpass", "127.0.0.1", listener.getsockname()[1]))
            runner.start()
            server_thread.join(timeout=8)
            runner.stop()
            self.assertFalse(server_thread.is_alive())
            self.assertEqual(received[2], 42)
            self.assertEqual(received[3], [""] * 7 + ["newuser", "newpass"])
            self.assertEqual(received[4:6], [-29, -38])
            self.assertEqual(received[6], -28)
            self.assertEqual(received[7][0], 2)
            self.assertEqual(received[7][2:], (0, 64))
            self.assertLessEqual(5, len(received[7][1]))
            self.assertLessEqual(len(received[7][1]), 10)
            runner.close()
        listener.close()

    def test_existing_account_stops_after_registration_rejection(self):
        listener = socket.socket()
        listener.bind(("127.0.0.1", 0))
        listener.listen(1)
        listener.settimeout(8)
        commands = []

        def fake_server():
            connection, _ = listener.accept()
            with connection:
                connection.settimeout(8)
                commands.append(read_client(connection)[0])
                packet(connection, -27, bytes([1, 0]) + java_utf("localhost") + struct.pack(">iB", 14445, 0))
                commands.append(read_client(connection)[0])
                commands.append(read_client(connection)[0])
                packet(connection, -26, java_utf("Tài khoản đã tồn tại"))
                commands.append(read_client(connection)[0])
                packet(connection, -26, java_utf("Thông tin tài khoản hoặc mật khẩu không chính xác"))

        server_thread = threading.Thread(target=fake_server, daemon=True)
        server_thread.start()
        with tempfile.TemporaryDirectory() as directory, patch.object(bot, "LOG_DIR", Path(directory)):
            runner = BotRunner(BotConfig("Existing", "olduser", "wrongpass", "127.0.0.1", listener.getsockname()[1]))
            runner.start()
            server_thread.join(timeout=8)
            deadline = time.monotonic() + 3
            while runner.status != "error" and time.monotonic() < deadline:
                time.sleep(0.02)
            self.assertEqual(runner.status, "error")
            self.assertIn("mật khẩu không đúng", runner.error)
            self.assertEqual(commands, [-27, -29, 42, -29])
            runner.close()
        listener.close()

    def test_missing_quest_npc_is_reported_instead_of_skipped(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(bot, "LOG_DIR", Path(directory)):
            runner = BotRunner(BotConfig("Auto", "testuser", "testpass"))
            try:
                runner.map_id = 1
                runner.task = {"task_id": 1, "index": 0, "steps": [{"map_id": 1, "npc_id": 2}]}
                runner._quest_step_done = "1:0"
                self.assertTrue(runner._quest(time.monotonic()))
                self.assertIn("Chờ", runner.action)
                self.assertIn("nhiệm vụ", runner.action)
            finally:
                runner.close()


if __name__ == "__main__":
    unittest.main()
