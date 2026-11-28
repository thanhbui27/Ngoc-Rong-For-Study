"""Regression checks for linking a newly captured server by sprite frames."""

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import auto_mapping


class AutoMappingTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        (self.root / "decoded").mkdir()
        self.parts = [{"id": index, "type": 3, "frames": [[index, 0, 0]]}
                      for index in range(40)]
        self.source = []
        for key, kind, image in (("head", 0, 101), ("body", 1, 102), ("leg", 2, 103)):
            part = {"type": kind, "frames": [[image, 0, 0]]}
            self.parts[30 + kind] = {"id": 30 + kind, **part}
            self.source.append([10 + kind, auto_mapping.fingerprint(part)])
        self.item = {"id": 77, "type": 5, "gender": 0, "name": "Test costume",
                     "icon_id": 999, "part_id": -1}

    def run_link(self, reference_icon=None):
        (self.root / "decoded" / "items.json").write_text(
            json.dumps({"items": [self.item]}), encoding="utf-8")
        (self.root / "decoded" / "part.json").write_text(
            json.dumps(self.parts), encoding="utf-8")
        reference = [{**self.item, "id": 12,
                      "icon_id": reference_icon if reference_icon is not None else self.item["icon_id"],
                      **dict(zip(auto_mapping.KEYS, self.source))}]
        reference_file = self.root / "reference.json"
        reference_file.write_text(json.dumps(reference), encoding="utf-8")
        with patch.object(auto_mapping, "REFERENCE", reference_file), \
             patch.object(auto_mapping, "for_clone", return_value={"costume": {}, "mini_pet": {}}):
            return auto_mapping.link(self.root)

    def test_matches_renumbered_parts_and_keeps_manual_mapping(self):
        self.assertEqual(self.run_link()["costume"], 1)
        path = self.root / "mappings" / "costume-parts.json"
        self.assertEqual(json.loads(path.read_text(encoding="utf-8"))["77"],
                         {"head": 30, "body": 31, "leg": 32})
        path.write_text(json.dumps({"77": {"head": 30, "body": -1, "leg": -1}}),
                        encoding="utf-8")
        self.assertEqual(self.run_link()["costume"], 0)
        self.assertEqual(json.loads(path.read_text(encoding="utf-8"))["77"],
                         {"head": 30, "body": -1, "leg": -1})

    def test_ambiguous_part_sets_remain_unmapped(self):
        for kind in range(3):
            self.parts[20 + kind] = {**self.parts[30 + kind], "id": 20 + kind}
        self.assertEqual(self.run_link()["costume"], 0)
        self.assertFalse((self.root / "mappings" / "costume-parts.json").exists())

    def test_changed_icon_still_links_unique_complete_costume(self):
        self.assertEqual(self.run_link(reference_icon=998)["costume"], 1)

    def test_changed_icon_requires_all_three_parts(self):
        self.parts[32]["frames"] = [[888, 0, 0]]
        self.assertEqual(self.run_link(reference_icon=998)["costume"], 0)

    def test_unknown_costume_uses_only_explicit_template_head(self):
        self.item["name"] = "Unknown costume"
        self.item["part_id"] = 30
        self.parts[31]["frames"] = [[888, 0, 0]]
        self.parts[32]["frames"] = [[889, 0, 0]]
        self.assertEqual(self.run_link(reference_icon=998)["costume"], 1)
        path = self.root / "mappings" / "costume-parts.json"
        self.assertEqual(json.loads(path.read_text(encoding="utf-8"))["77"],
                         {"head": 30, "body": -1, "leg": -1})


if __name__ == "__main__":
    unittest.main()
