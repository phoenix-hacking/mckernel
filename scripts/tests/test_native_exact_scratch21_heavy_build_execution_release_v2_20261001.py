#!/usr/bin/env python3
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

PATH = Path(__file__).parents[2] / "docs/verification/evidence/native-exact-scratch21-heavy-build-execution-release-v2-20261001.py"
SPEC = importlib.util.spec_from_file_location("scratch21_release_v2", PATH)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class ReleaseTests(unittest.TestCase):
    def test_exact_derivation(self):
        prepared = json.loads(MODULE.PREP.read_text())
        derived, raw = MODULE.derive(prepared)
        self.assertEqual(MODULE.sha(raw), MODULE.DERIVED_SHA256)
        self.assertFalse(derived["preparation_only"])
        self.assertTrue(derived["execution_released"])
        self.assertTrue(derived["executable"])
        self.assertFalse(derived["release_required"])
        changed = {key for key in prepared if prepared[key] != derived[key]}
        self.assertEqual(changed, {"preparation_only", "execution_released", "executable", "release_required"})

    def test_wrong_prepared_flags_refuse(self):
        prepared = json.loads(MODULE.PREP.read_text())
        prepared["executable"] = True
        with self.assertRaises(MODULE.Refusal):
            MODULE.derive(prepared)

    def test_publish_is_exclusive(self):
        with tempfile.TemporaryDirectory() as temp:
            target = Path(temp) / "request.json"
            raw = b"{}\n"
            MODULE.publish(target, raw)
            with self.assertRaises(FileExistsError):
                MODULE.publish(target, raw)

    def test_execution_uses_outer_wrapper_and_root_lock(self):
        source = PATH.read_text()
        self.assertIn("acquire_development_lock()", source)
        self.assertIn("str(WRAPPER), str(EXECUTION)", source)
        self.assertNotIn("str(CANDIDATE / \"scripts/native_rust_exact_build_container_owner.py\")", source)
        self.assertIn("cleanup_separately_required", source)
        self.assertIn("terminal_container_retained", source)


if __name__ == "__main__":
    unittest.main()
