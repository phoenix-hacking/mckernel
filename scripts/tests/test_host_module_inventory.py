#!/usr/bin/env python3
"""Focused regression tests for the frozen host-module inventory."""

from __future__ import annotations

import json
import sys
import unittest
from collections import Counter
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import host_module_inventory as inventory  # noqa: E402


class IntegerParserTests(unittest.TestCase):
    def test_c_integer_syntax_used_by_the_legacy_headers(self) -> None:
        self.assertEqual(inventory.parse_c_integer("0x112900UL"), 0x112900)
        self.assertEqual(inventory.parse_c_integer("(1U << 8) | 3ULL"), 0x103)
        self.assertEqual(inventory.parse_c_integer("BASE + 1", {"BASE": 41}), 42)
        self.assertEqual(inventory.parse_c_integer("7 / 2"), 3)


class ConditionalFilterTests(unittest.TestCase):
    def test_named_guards_preserve_only_the_active_branch_and_line_count(self) -> None:
        source = """before
#ifdef ENABLED
enabled
#else
disabled
#endif
#ifndef ENABLED
also_disabled
#endif
after
"""
        filtered = inventory.filter_simple_cpp(source, {"ENABLED"})
        self.assertIn("enabled\n", filtered)
        self.assertNotIn("disabled\n", filtered)
        self.assertNotIn("also_disabled\n", filtered)
        self.assertIn("after\n", filtered)
        self.assertEqual(filtered.count("\n"), source.count("\n"))


class FrozenInventoryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        golden_path = REPO_ROOT / inventory.DEFAULT_OUTPUT
        cls.golden = json.loads(golden_path.read_text(encoding="utf-8"))

    def test_active_source_languages_are_exact(self) -> None:
        modules = inventory.module_source_entries(REPO_ROOT)
        counts = {
            module: Counter(entry.language for entry in entries)
            for module, entries in modules.items()
        }
        self.assertEqual(counts["ihk"], Counter(c=7))
        self.assertEqual(counts["ihk_smp_x86_64"], Counter(c=2, assembly=2))
        self.assertEqual(counts["mcctrl"], Counter(c=6, rust=1))

    def test_binary_capture_and_cross_capture_remain_locked(self) -> None:
        digest = inventory.validate_locked_binary_capture(
            self.golden["binary_capture"]
        )
        self.assertEqual(digest, inventory.BINARY_CAPTURE_SHA256)
        inventory.validate_cross_capture(self.golden)


if __name__ == "__main__":
    unittest.main()
