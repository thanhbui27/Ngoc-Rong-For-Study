import json
import struct
import tempfile
import unittest
from unittest.mock import patch
from pathlib import Path

from extended_data import decode_asset_packet, decode_sprite, decode_templates, write_json
from extended_studio import asset_path, catalog, save_bindings, tileset


def utf(value):
    value = value.encode("utf-8")
    return struct.pack(">H", len(value)) + value


def sized(value):
    return struct.pack(">i", len(value)) + value


PNG = bytes.fromhex("89504e470d0a1a0a")


class ExtendedTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def sprite_data(self, wide=False):
        coords = struct.pack(">hh", 300, 400) if wide else bytes((3, 4))
        return bytes((1, 0)) + coords + bytes((8, 9)) + struct.pack(">hbhhbhh", 1, 1, -2, 5, 0, 1, 0)

    def test_effect_and_mob_variants_preserve_offsets_and_sequences(self):
        for kind in (0, 1, 2):
            data = self.sprite_data(kind == 2)
            result = decode_sprite(data, kind)
            self.assertEqual(result["frames"], [[{"dx": -2, "dy": 5, "sprite": 0}]])
            self.assertEqual(result["sprites"][0]["x"], 300 if kind == 2 else 3)
            packet = struct.pack(">h", 3) + sized(data) + bytes((kind,)) + sized(PNG)
            category, asset_id, value, png = decode_asset_packet(-66, packet)
            self.assertEqual((category, asset_id, value["sequence"], png), ("dynamic", "3", [0], PNG))
            mob = bytes((3, kind)) + sized(data) + sized(PNG) + bytes((1, 1, 2, 0, 0))
            self.assertEqual(decode_asset_packet(11, mob)[2]["actions"], {"0": [0, 0]})

    def test_truncated_or_unknown_frames_are_rejected(self):
        with self.assertRaises(ValueError):
            decode_sprite(self.sprite_data()[:-1])
        data = bytearray(self.sprite_data())
        data[13] = 9
        with self.assertRaises(ValueError):
            decode_sprite(bytes(data))

    def test_named_sprite_and_flag_packets(self):
        category, asset_id, value, _ = decode_asset_packet(66, utf("aura_1_0") + b"\x04" + sized(PNG))
        self.assertEqual((category, asset_id, value["frame_count"]), ("sprite", "aura_1_0", 4))
        self.assertEqual(decode_asset_packet(-63, struct.pack(">BBhh", 2, 2, 101, 102))[2]["image_ids"], [101, 102])
        with self.assertRaises(ValueError):
            decode_asset_packet(66, utf("../outside") + b"\x04" + sized(PNG))

    def test_templates_read_to_end_and_keep_npc_parts(self):
        path = self.root / "raw/updates/sub6-000.bin"
        path.parent.mkdir(parents=True)
        packet = b"\x06\x01\x01" + utf("Map") + b"\x01" + utf("NPC") + struct.pack(">hhhB", 0, 1, 2, 0)
        packet += b"\x01\x00" + utf("Mob") + struct.pack(">ibbb", 100, 1, 2, 3)
        path.write_bytes(packet)
        self.assertEqual(decode_templates(self.root), {"version": 1, "maps": 1, "npcs": 1, "mobs": 1})
        self.assertEqual(json.loads((self.root / "decoded/npc.json").read_text())[0]["leg"], 2)
        path.write_bytes(packet + b"\x00")
        with self.assertRaises(ValueError):
            decode_templates(self.root)

    def test_tileset_dollar_names_are_grouped_and_paths_confined(self):
        folder = self.root / "resources/zoom4/x4/t"
        folder.mkdir(parents=True)
        (folder / "2$1.png").write_bytes(PNG)
        (folder / "2$2.png").write_bytes(PNG)
        entries = catalog(self.root, "tileset")["entries"]
        self.assertEqual(len(entries), 1)
        self.assertEqual(len(tileset(self.root, entries[0]["id"])["tiles"]), 2)
        with self.assertRaises(ValueError):
            asset_path(self.root, "../outside.png")

    def test_item_visuals_round_trip_and_validate(self):
        write_json(self.root / "decoded/items.json", {"items": [{"id": 1}]})
        layer = {"kind": "sheet", "id": "123", "width": 32, "height": 32, "count": 3}
        result = save_bindings(self.root, 1, [layer])
        self.assertEqual(result[0]["count"], 3)
        with self.assertRaises(ValueError):
            save_bindings(self.root, 1, [{**layer, "count": 0}])
        with self.assertRaises(ValueError):
            save_bindings(self.root, 999, [])

    def test_capture_saves_raw_and_resumes_without_resource_announcement(self):
        from capture_extra import capture
        packet = struct.pack(">h", 3) + sized(self.sprite_data()) + b"\x00" + sized(PNG)
        class Socket:
            def settimeout(self, value): pass
            def close(self): pass
        class Wire:
            def send(self, command, payload):
                self.request = command, payload
            def read(self):
                return -66, packet
        with patch("capture_extra.decode_templates", return_value={}), \
             patch("capture_extra.candidates", return_value={"dynamic": [3]}), \
             patch("clone_server.connect", return_value=(Socket(), Wire(), {})) as connect:
            first = capture(self.root, "test", 1, 4, "2.3.1", 1, range(1), [])
            self.assertEqual(first["dynamic"]["saved"], 1)
            self.assertFalse(connect.call_args.kwargs["require_resources"])
            self.assertTrue((self.root / "raw/animations/zoom4/dynamic/3.bin").is_file())
            connect.reset_mock()
            second = capture(self.root, "test", 1, 4, "2.3.1", 1, range(1), [])
            self.assertEqual(second["dynamic"]["existing"], 1)
            connect.assert_not_called()

    def test_import_keeps_local_source_separate(self):
        from import_assets import import_assets
        source = self.root / "source/resources/normal"
        write_json(source / "effect_data/1.json", {"id": 1, "sprites": [{"id": 0, "x": 0, "y": 0, "w": 1, "h": 1}],
                   "frames": [[{"sprite_id": 0, "dx": -1, "dy": 2}]], "animations": [0]})
        image = source / "image/4/effect/1.png"
        image.parent.mkdir(parents=True)
        image.write_bytes(PNG)
        output = self.root / "clone"
        result = import_assets(output, source)
        self.assertEqual(result["files"]["dynamic"], 1)
        imported = json.loads((output / "decoded/animations/zoom4/reference/dynamic-1.json").read_text())
        self.assertEqual(imported["source_kind"], "local-reference")
        self.assertFalse((output / "decoded/animations/zoom4/dynamic/1.json").exists())


if __name__ == "__main__":
    unittest.main()
