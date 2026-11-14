#!/usr/bin/env python3
"""Offline stale-instruction reconciliation; temporary campaign directories only."""
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import os_goal_instructions as instructions


HOLD_ID = "20261017T021032370649Z-e1d9b3466e7c4dcfb8838159453e3bf2"
OTHER_ID = "20261017T022504821606Z-b204371bdb0f45fdb86cba68c3b3d37c"
# Preserve whitespace and trailing newline: bindings cover JSON bytes, not text.
RAW = ('{ "id": "' + HOLD_ID + '", "text": "Preparation hold" }\n').encode()
SHA = hashlib.sha256(RAW).hexdigest()
NOTE = hashlib.sha256(b"explicit startup reconciliation").hexdigest()
NEXT_NOTE = hashlib.sha256(b"later startup reconciliation").hexdigest()


class ReconciliationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.control = self.base / "instructions"
        self.pending = self.control / "pending"
        self.pending.mkdir(parents=True)
        self.original = self.pending / (HOLD_ID + ".json")
        self.original.write_bytes(RAW)
        self.binding = [{"id": HOLD_ID, "sha256": SHA}]

    def run_reconcile(self, execute=False, note=NOTE, bindings=None):
        return instructions.reconcile_instructions(
            self.base, self.binding if bindings is None else bindings, note, execute=execute)

    def snapshot(self):
        return {str(p.relative_to(self.base)): p.read_bytes()
                for p in self.base.rglob("*") if p.is_file()}

    def test_default_is_read_only(self):
        before = self.snapshot()
        self.assertEqual(self.run_reconcile()[0]["status"], "would_supersede")
        self.assertEqual(self.snapshot(), before)
        self.assertEqual(sorted(p.name for p in self.control.iterdir()), ["pending"])

    def test_exact_raw_bytes_are_preserved_and_receipt_is_durable(self):
        inode = self.original.stat().st_ino
        with patch.object(instructions.os, "fsync", wraps=os.fsync) as sync:
            result = self.run_reconcile(execute=True)[0]
        archived = self.control / "superseded" / self.original.name
        receipt = self.control / "reconciliation" / self.original.name
        self.assertFalse(self.original.exists())
        self.assertEqual(archived.read_bytes(), RAW)
        self.assertEqual(archived.stat().st_ino, inode)
        self.assertEqual(json.loads(receipt.read_bytes()), result)
        self.assertEqual(result["sha256"], SHA)
        self.assertEqual(result["startup_instruction_sha256"], NOTE)
        self.assertEqual(result["status"], "superseded")
        self.assertIsInstance(result["timestamp"], str)
        self.assertGreaterEqual(sync.call_count, 6)

    def test_replay_is_idempotent_and_preserves_different_historical_note(self):
        first = self.run_reconcile(execute=True)
        before = self.snapshot()
        self.assertEqual(self.run_reconcile(execute=True), first)
        later = self.run_reconcile(execute=True, note=NEXT_NOTE)[0]
        self.assertEqual(later["startup_instruction_sha256"], NOTE)
        self.assertEqual(later["requested_startup_instruction_sha256"], NEXT_NOTE)
        self.assertTrue(later["historical_supersession"])
        self.assertEqual(self.snapshot(), before)

    def test_crash_after_move_before_receipt_is_replayed(self):
        with patch.object(instructions, "_write_receipt", side_effect=OSError("simulated crash")):
            with self.assertRaises(OSError):
                self.run_reconcile(execute=True)
        self.assertFalse(self.original.exists())
        self.assertEqual((self.control / "superseded" / self.original.name).read_bytes(), RAW)
        self.assertEqual(self.run_reconcile(execute=True)[0]["status"], "superseded")

    def test_crash_after_link_before_unlink_is_replayed(self):
        archived = self.control / "superseded"
        archived.mkdir()
        os.link(self.original, archived / self.original.name)
        self.assertEqual(self.run_reconcile(execute=True)[0]["status"], "superseded")
        self.assertFalse(self.original.exists())
        self.assertEqual((archived / self.original.name).read_bytes(), RAW)

    def test_receipt_is_published_only_after_fully_written(self):
        with patch.object(instructions.os, "write", side_effect=OSError("simulated crash")):
            with self.assertRaises(OSError):
                self.run_reconcile(execute=True)
        self.assertFalse((self.control / "reconciliation" / self.original.name).exists())
        self.assertEqual(self.run_reconcile(execute=True)[0]["status"], "superseded")

    def test_unknown_pending_blocks_before_any_mutation(self):
        (self.pending / (OTHER_ID + ".json")).write_bytes(b"unknown")
        before = self.snapshot()
        with self.assertRaisesRegex(ValueError, "Unexpected pending"):
            self.run_reconcile(execute=True)
        self.assertEqual(self.snapshot(), before)

    def test_hash_covers_raw_json_not_same_instruction_text(self):
        self.original.write_text(json.dumps(json.loads(RAW)))
        with self.assertRaisesRegex(ValueError, "hash mismatch"):
            self.run_reconcile(execute=True)
        self.assertTrue(self.original.exists())

    def test_sending_blocks_without_reading_entry(self):
        sending = self.control / "sending"
        sending.mkdir()
        os.mkfifo(sending / "uncertain.json")
        with self.assertRaisesRegex(ValueError, "uncertain"):
            self.run_reconcile(execute=True)
        self.assertTrue(self.original.exists())

    def test_delivered_is_noop_without_reading_or_recreating_original(self):
        self.original.unlink()
        delivered = self.control / "delivered"
        delivered.mkdir()
        stored = delivered / self.original.name
        stored.write_bytes(b"delivered receipt differs from original pending bytes")
        before = self.snapshot()
        with patch.object(instructions, "_read", wraps=instructions._read) as read:
            self.assertEqual(self.run_reconcile(execute=True)[0]["status"], "already_delivered")
        self.assertEqual(self.snapshot(), before)
        self.assertFalse((self.control / "superseded").exists())
        # The delivered descriptor is never passed to a file-content read.
        self.assertEqual(read.call_count, 3)

    def test_missing_original_is_reported_without_mutation(self):
        self.original.unlink()
        before = self.snapshot()
        self.assertEqual(self.run_reconcile(execute=True)[0]["status"], "not_present")
        self.assertEqual(self.snapshot(), before)

    def test_symlink_and_fifo_pending_refused(self):
        self.original.unlink()
        for kind in ("symlink", "fifo"):
            with self.subTest(kind=kind):
                if kind == "symlink":
                    self.original.symlink_to(self.base / "do-not-read")
                else:
                    os.mkfifo(self.original)
                with self.assertRaisesRegex(ValueError, "regular file"):
                    self.run_reconcile(execute=True)
                self.original.unlink()

    def test_symlink_queue_directory_refused(self):
        other = self.base / "other"
        self.pending.rename(other)
        self.pending.symlink_to(other, target_is_directory=True)
        with self.assertRaisesRegex(ValueError, "Unsafe instruction directory"):
            self.run_reconcile(execute=True)
        self.assertEqual((other / self.original.name).read_bytes(), RAW)

    def test_traversal_invalid_hash_and_duplicates_refused(self):
        for bindings in ([{"id": "../escape", "sha256": SHA}],
                         [{"id": HOLD_ID, "sha256": "bad"}], self.binding * 2):
            with self.subTest(bindings=bindings):
                with self.assertRaises(ValueError):
                    self.run_reconcile(execute=True, bindings=bindings)
        with self.assertRaises(ValueError):
            self.run_reconcile(execute=True, note="bad")

    def test_oversized_regular_file_refused(self):
        self.original.write_bytes(b"x" * (instructions._MAX_BYTES + 1))
        with self.assertRaisesRegex(ValueError, "bounded byte limit"):
            self.run_reconcile(execute=True)

    def test_corrupt_archived_bytes_or_receipt_blocks(self):
        self.run_reconcile(execute=True)
        archive = self.control / "superseded" / self.original.name
        archive.write_bytes(b"tampered")
        with self.assertRaisesRegex(ValueError, "hash mismatch"):
            self.run_reconcile(execute=True)
        archive.write_bytes(RAW)
        receipt = self.control / "reconciliation" / self.original.name
        receipt.write_bytes(b"{}")
        with self.assertRaisesRegex(ValueError, "Invalid reconciliation receipt"):
            self.run_reconcile(execute=True)

    def test_unknown_non_json_pending_and_entry_limit_refused(self):
        (self.pending / "unknown.txt").write_bytes(b"unknown")
        with self.assertRaisesRegex(ValueError, "Unexpected pending"):
            self.run_reconcile(execute=True)
        with patch.object(instructions, "_MAX_ENTRIES", 1):
            with self.assertRaisesRegex(ValueError, "bounded entry limit"):
                self.run_reconcile(execute=True)


if __name__ == "__main__":
    unittest.main()
