"""Check real F06 metadata reuse without compiling or admitting a kernel.

The byte references come from the canonical 70c187c7 producer with its exact
source/profile/binding. Only temporary output/source paths are normalized.
"""

import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]
PRODUCER = ROOT / "scripts/derive_f06_origin.py"
PROFILE = ROOT / "scripts/f06_origin_command_profile.json"
SOURCE = ROOT / "arch/x86_64/kernel/syscall.c"
BINDING = ROOT / "scripts/f06_origin_source_binding.json"
ORIGIN = "/src/arch/x86_64/kernel/syscall.c"
OLD_MTIME_NS = 1_600_000_000_123_456_789
EXPECTED_DIGESTS = {
    "ORIGIN-BINDING.json": "6bc04ebf4dbab7de5e801cac044a46f68a3acdb58ee2d2f6e14de8008eafa5d2",
    "f06_clone_cpuid_metadata.rs": "71e4b0ab7f5ca612e4cd06bf2150e2e6b7b5e3e39717e466cfb626b1ce249a48",
    "f06_rt_sigreturn_origin.cmake": "717d5b0f8182ef07499c5719f3065b2915a8db52dfcca9d6cb1519d36e7c232e",
    "f06_rt_sigreturn_origin.h": "aeece54c3b6f01c326fff3eb925b89b88acd3b198b0047393c8c9c0d78f74ded",
    "f06_signal_metadata.json": "f4b74627879a40571a9ebeb8a2eed177fab0a984ee78720a4d7d16f24fb3e7dd",
    "f06_signal_metadata.rs": "0da870f9f48a4500f57d593a776a5f7d38b03d37cd1abd78baf4a27f8520fd58",
    "rust-environment.json": "0bf51e6a2a3c1d8e32f7ac43c897f82d83cd9090f6c1cf5cfcfd940c742d5c1b",
}


def snapshot(output):
    result = {}
    for path in output.iterdir():
        stat = path.stat()
        result[path.name] = (path.read_bytes(), stat.st_mtime_ns, stat.st_dev, stat.st_ino)
    return result


def retain_old_mtimes(output):
    # Make a rewrite observable without sleeping or depending on clock precision.
    for path in output.iterdir():
        os.utime(path, ns=(OLD_MTIME_NS, OLD_MTIME_NS))


class M14MetadataReuseTests(unittest.TestCase):
    def run_producer(self, output, *, profile=PROFILE, source=SOURCE, binding=BINDING):
        return subprocess.run([
            sys.executable, "-B", str(PRODUCER), "--profile", str(profile),
            "--source", str(source), "--source-binding", str(binding),
            "--output", str(output),
        ], capture_output=True, text=True, timeout=15)

    def generate(self, output):
        result = self.run_producer(output)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def assert_canonical_bytes(self, output):
        actual = {}
        for path in output.iterdir():
            data = path.read_bytes().replace(str(output).encode(), b"<OUTPUT>")
            data = data.replace(str(SOURCE).encode(), b"<SOURCE>")
            actual[path.name] = hashlib.sha256(data).hexdigest()
        self.assertEqual(actual, EXPECTED_DIGESTS)

    def test_identical_generation_preserves_all_bytes_mtimes_and_inodes(self):
        with tempfile.TemporaryDirectory(prefix="m14-metadata-reuse-") as temporary:
            output = Path(temporary) / "output"
            self.generate(output)
            self.assert_canonical_bytes(output)
            retain_old_mtimes(output)
            before = snapshot(output)
            for _ in range(2):
                self.generate(output)
                self.assertEqual(snapshot(output), before)

    def test_changed_or_missing_outputs_are_repaired_at_their_own_scope(self):
        with tempfile.TemporaryDirectory(prefix="m14-metadata-repair-") as temporary:
            output = Path(temporary) / "output"
            self.generate(output)
            retain_old_mtimes(output)
            before = snapshot(output)
            changed = {"f06_rt_sigreturn_origin.cmake", "f06_signal_metadata.rs"}
            missing = "ORIGIN-BINDING.json"
            for name in changed:
                (output / name).write_bytes(before[name][0] + b"stale metadata\n")
                os.utime(output / name, ns=(OLD_MTIME_NS, OLD_MTIME_NS))
            (output / missing).unlink()
            self.generate(output)
            self.assert_canonical_bytes(output)
            after = snapshot(output)
            for name in EXPECTED_DIGESTS:
                if name in changed or name == missing:
                    self.assertEqual(after[name][0], before[name][0])
                    self.assertGreater(after[name][1], before[name][1])
                    if name in changed:
                        self.assertEqual(after[name][2:], before[name][2:])
                else:
                    self.assertEqual(after[name], before[name])

    def test_rejected_source_profile_and_binding_leave_outputs_intact(self):
        with tempfile.TemporaryDirectory(prefix="m14-metadata-rejection-") as temporary:
            root = Path(temporary)
            output = root / "output"
            self.generate(output)
            retain_old_mtimes(output)
            before = snapshot(output)
            for field, original, reason in (
                ("source", SOURCE, "exact proposed architecture source bytes required"),
                ("profile", PROFILE, "unqualified SDK profile bytes"),
                ("binding", BINDING, "unreviewed source binding bytes"),
            ):
                with self.subTest(field=field):
                    altered = root / ("changed-" + original.name)
                    altered.write_bytes(original.read_bytes() + b"\n")
                    result = self.run_producer(output, **{field: altered})
                    self.assertNotEqual(result.returncode, 0)
                    self.assertIn(reason, result.stderr)
                    self.assertEqual(snapshot(output), before)

    def test_changed_signal_lines_update_only_signal_metadata(self):
        spec = importlib.util.spec_from_file_location(
            "m14_reuse_signal_metadata", ROOT / "scripts/derive_f06_signal_metadata.py")
        signal = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(signal)
        with tempfile.TemporaryDirectory(prefix="m14-signal-metadata-change-") as temporary:
            root = Path(temporary)
            output = root / "output"
            self.generate(output)
            retain_old_mtimes(output)
            before = snapshot(output)
            original_fields = json.loads(before["f06_signal_metadata.json"][0])["sites"]
            text = SOURCE.read_text()
            signature = "int\ndo_signal("
            self.assertEqual(text.count(signature), 1)
            altered = root / "changed-syscall.c"
            altered.write_text(text.replace(signature, "\n" + signature, 1))
            # Exercise changed input in the existing metadata helper. The public
            # producer still rejects unbound source, as tested separately above.
            signal.write_signal_metadata(altered, ORIGIN, output)
            after = snapshot(output)
            receipt = json.loads(after["f06_signal_metadata.json"][0])
            self.assertEqual(receipt["sites"],
                             {name: value + 1 for name, value in original_fields.items()})
            self.assertEqual(receipt["source_sha256"],
                             hashlib.sha256(altered.read_bytes()).hexdigest())
            for name in EXPECTED_DIGESTS:
                if name in {"f06_signal_metadata.rs", "f06_signal_metadata.json"}:
                    self.assertNotEqual(after[name][0], before[name][0])
                    self.assertGreater(after[name][1], before[name][1])
                    self.assertEqual(after[name][2:], before[name][2:])
                else:
                    self.assertEqual(after[name], before[name])
            retain_old_mtimes(output)
            reused = snapshot(output)
            signal.write_signal_metadata(altered, ORIGIN, output)
            self.assertEqual(snapshot(output), reused)


if __name__ == "__main__":
    unittest.main()
