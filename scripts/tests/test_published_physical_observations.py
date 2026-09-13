#!/usr/bin/env python3
"""Independent literal bytes; retains every attempt; no guest or physical reads."""
import base64
import hashlib
import importlib.util
import itertools
import json
import os
from pathlib import Path
import sys
import tempfile
import traceback
import unittest


ROOT = Path(__file__).resolve().parents[2]
HELPER = ROOT / "scripts/application-tests/published_physical_observations.py"
BASE = HELPER.with_name("physical_observations.py")
EVIDENCE = Path(tempfile.mkdtemp(prefix="stability-published-physical-tests-",
                               dir=os.environ.get("TMPDIR")))
print("PUBLISHED_PHYSICAL_TEST_EVIDENCE " + str(EVIDENCE), flush=True)
(EVIDENCE / "source").mkdir()
inputs = []
for source in (Path(__file__).resolve(), HELPER, BASE):
    raw = source.read_bytes()
    saved = EVIDENCE / "source" / source.name
    saved.write_bytes(raw)
    inputs.append({"path": str(source), "retained": str(saved), "size": len(raw),
                   "sha256": hashlib.sha256(raw).hexdigest()})
(EVIDENCE / "inputs.json").write_text(json.dumps({
    "source_inputs": inputs, "python": sys.version, "executable": sys.executable,
    "argv": sys.argv, "cwd": os.getcwd(), "TMPDIR": os.environ.get("TMPDIR"),
    "application_acceptance": False, "physical_reads": False,
}, indent=2) + "\n")
SPEC = importlib.util.spec_from_file_location("published_physical_observations",
                                            EVIDENCE / "source" / HELPER.name)
published = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(published)

# Literal x86_64 wire bytes, independently transcribed from reviewed wire
# layouts. The fixtures do not use subject constants, packers or expected output.
BLOCKED = bytes.fromhex(
    "deadbeef67452301 0000000000000000 0200000000000000 "
    "f0debc9a78563412 efcdab8967452301")
PREPARED = bytes.fromhex(
    "deadbeefa5010000 0000000000000000 0100000000000000 "
    "1000000000000000 efcdab8967452301")
WAKE = bytes.fromhex(
    "0000000000000000 1400000000000000 0000000000000000 3301000000000000 "
    "0000000000000000 0000000000000000 0000000000000000 0000000000000000 "
    "0000000000000000 0000000000000000 0000000000000000 0000000000000000 "
    "0000000000000000 0000000000000000 0000000000000000 0000000000000000")
HEADER = bytes.fromhex(
    "01000000 f501 8000 7f000000 00000000 "
    "0000000000000000 0000000000000000 0000000000000000 803f000000000000 "
    "11000000 00000000 00000000 00000000")


def word(raw, offset, width, value):
    changed = bytearray(raw)
    changed[offset:offset + width] = value.to_bytes(width, "little")
    return bytes(changed)


def flip(raw, offset):
    changed = bytearray(raw)
    changed[offset] ^= 1
    return bytes(changed)


def ring(read, published_count, reserved, *, slots=()):
    raw = bytearray(HEADER + bytes(16320))
    for offset, value in ((16, read), (24, published_count), (32, reserved)):
        raw[offset:offset + 8] = value.to_bytes(8, "little")
    # Each test supplies explicit physical slots; this builder does not derive
    # slot retention or choose logical publication intervals for the subject.
    for slot, packet in slots:
        if not (0 <= slot < 127 and len(packet) == 128):
            raise AssertionError("invalid literal fixture slot")
        raw[64 + slot * 128:64 + (slot + 1) * 128] = packet
    return bytes(raw)


class PublishedPhysicalTests(unittest.TestCase):
    def setUp(self):
        self.evidence = EVIDENCE / self._testMethodName
        self.evidence.mkdir()
        self.sequence = itertools.count(1)

    def call(self, label, function, *args, expected_error=False, **kwargs):
        target = self.evidence / f"{next(self.sequence):03d}-{label}"
        target.mkdir()

        def encode(value, name):
            if type(value) in (bytes, bytearray):
                raw = bytes(value)
                path = target / (name + ".bin")
                path.write_bytes(raw)
                return {"type": type(value).__name__, "path": path.name,
                        "size": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}
            if type(value) in (list, tuple):
                return {"type": type(value).__name__, "items": [
                    encode(item, name + "-" + str(index)) for index, item in enumerate(value)]}
            if type(value) is dict:
                return {"type": "dict", "items": [[encode(key, name + f"-k{index}"),
                    encode(item, name + f"-v{index}")] for index, (key, item) in enumerate(value.items())]}
            return {"type": type(value).__name__, "value": value}

        (target / "invocation.json").write_text(json.dumps({
            "function": function.__name__, "args": encode(args, "args"),
            "kwargs": encode(kwargs, "kwargs"),
            "expected_outcome": "PhysicalObservationError" if expected_error else "return",
            "application_acceptance": False,
        }, indent=2) + "\n")
        try:
            result = function(*args, **kwargs)
        except BaseException as error:
            (target / "outcome.json").write_text(json.dumps({
                "outcome": "raised", "type": type(error).__name__, "message": str(error),
                "traceback": traceback.format_exc(limit=12), "application_acceptance": False,
            }, indent=2) + "\n")
            raise
        (target / "outcome.json").write_text(json.dumps({
            "outcome": "returned", "result": result, "application_acceptance": False,
        }, indent=2) + "\n")
        return result

    def reject(self, label, function, *args, **kwargs):
        with self.assertRaises(published.PhysicalObservationError):
            self.call(label, function, *args, expected_error=True, **kwargs)

    def check_scope(self, result):
        self.assertEqual(result["status"], "PHYSICAL_BYTES_MATCH_ONLY")
        for key in ("application_acceptance", "transport_acceptance", "production_gate_credit",
                    "physical_reads_performed"):
            self.assertIs(result[key], False)

    def test_literal_prepared_response_and_input_identities(self):
        result = self.call("prepared", published.compare_prepared_response,
                           BLOCKED, PREPARED, worker_tid=421)
        self.check_scope(result)
        self.assertEqual(result["allowed_write_spans"], [[4, 8], [16, 24], [24, 32]])
        self.assertEqual(result["worker_tid"], 421)
        self.assertIs(result["phase_labels_are_caller_claims"], True)
        for label, expected in (("BlockedRead", BLOCKED), ("AcceptedReturn", PREPARED)):
            self.assertEqual(base64.b64decode(result["raw"][label]["base64"]), expected)
            self.assertEqual(result["raw"][label]["sha256"], hashlib.sha256(expected).hexdigest())
        self.assertEqual(base64.b64decode(result["expected_prepublication_prefix"]["base64"]), PREPARED)

    def test_opaque_first_word_and_tail_are_preserved_not_initialized(self):
        blocked = word(word(BLOCKED, 0, 4, 0x76543210), 32, 8, 0x1020304050607080)
        prepared = word(word(PREPARED, 0, 4, 0x76543210), 32, 8, 0x1020304050607080)
        result = self.call("different-opaque", published.compare_prepared_response,
                           blocked, prepared, worker_tid=421)
        self.check_scope(result)
        for tid in (1, 2147483647):
            changed = word(PREPARED, 4, 4, tid)
            self.call("worker-boundary-" + str(tid), published.compare_prepared_response,
                      BLOCKED, changed, worker_tid=tid)

    def test_every_forbidden_response_byte_rejected(self):
        for offset in list(range(0, 4)) + list(range(8, 16)) + list(range(32, 40)):
            with self.subTest(offset=offset):
                self.reject("forbidden-" + str(offset), published.compare_prepared_response,
                            BLOCKED, flip(PREPARED, offset), worker_tid=421)

    def test_every_required_prepared_byte_rejected_when_wrong(self):
        for offset in list(range(4, 8)) + list(range(16, 32)):
            with self.subTest(offset=offset):
                self.reject("required-" + str(offset), published.compare_prepared_response,
                            BLOCKED, flip(PREPARED, offset), worker_tid=421)

    def test_blocked_status_and_wake_prerequisites(self):
        for offset, value in ((8, 1), (8, 2), (16, 0), (16, 1), (16, 3)):
            self.reject(f"blocked-{offset}-{value}", published.compare_prepared_response,
                        word(BLOCKED, offset, 8, value), PREPARED, worker_tid=421)
        self.reject("published-response-forbidden", published.compare_prepared_response,
                    BLOCKED, word(PREPARED, 8, 8, 1), worker_tid=421)

    def test_response_strict_types_sizes_and_worker(self):
        for index, bad in enumerate((None, [], "x" * 40, bytearray(BLOCKED), BLOCKED[:-1], BLOCKED + b"x")):
            self.reject("blocked-type-" + str(index), published.compare_prepared_response,
                        bad, PREPARED, worker_tid=421)
            self.reject("accepted-type-" + str(index), published.compare_prepared_response,
                        BLOCKED, bad, worker_tid=421)
        for index, bad in enumerate((True, False, 421.0, "421", None, 0, -1, 2147483648)):
            self.reject("worker-type-" + str(index), published.compare_prepared_response,
                        BLOCKED, PREPARED, worker_tid=bad)

    def test_exactly_one_wake_at_each_interval_position(self):
        before = ring(5, 5, 5)
        for slot in (5, 6, 7):
            after = ring(8, 8, 8, slots=[(slot, WAKE)])
            result = self.call("slot-" + str(slot), published.one_new_requester_wake,
                               before, after, 307)
            self.check_scope(result)
            self.assertEqual((result["checked_publication_begin"], result["checked_publication_end"]), (5, 8))
            self.assertEqual((result["match"]["sequence"], result["match"]["slot"], result["match"]["offset"]),
                             (slot, slot, 64 + slot * 128))
            self.assertEqual(base64.b64decode(result["match"]["packet"]["base64"]), WAKE)
            self.assertEqual(result["after"]["raw"]["sha256"], hashlib.sha256(after).hexdigest())
            self.assertEqual(result["before"]["raw"]["sha256"], hashlib.sha256(before).hexdigest())
            self.assertIs(result["complete_ring_equivalence_proved"], False)

    def test_physical_slot_wrap_preserves_sequence(self):
        result = self.call("sequence-127-slot-0", published.one_new_requester_wake,
                           ring(126, 126, 126), ring(129, 129, 129, slots=[(0, WAKE)]), 307)
        self.assertEqual((result["match"]["sequence"], result["match"]["slot"], result["match"]["offset"]),
                         (127, 0, 64))

    def test_published_wake_counts_whether_consumed_or_pending(self):
        for read in (5, 6):
            result = self.call("read-" + str(read), published.one_new_requester_wake,
                               ring(5, 5, 5), ring(read, 6, 6, slots=[(5, WAKE)]), 307)
            self.assertEqual(result["new_matching_wakes"], 1)

    def test_old_unpublished_unrelated_and_wrong_union_do_not_count(self):
        other_tid = word(WAKE, 24, 4, 308)
        wrong_pid = word(word(WAKE, 24, 4, 0), 32, 4, 307)
        wrong_target = word(word(WAKE, 24, 4, 0), 52, 4, 307)
        wrong_message = word(WAKE, 8, 4, 0x13)
        after = ring(5, 10, 11, slots=[(4, WAKE), (5, other_tid), (6, wrong_pid),
                    (7, WAKE), (8, wrong_target), (9, wrong_message), (10, WAKE)])
        result = self.call("only-sequence-7", published.one_new_requester_wake,
                           ring(5, 5, 5, slots=[(4, WAKE)]), after, 307)
        self.assertEqual(result["match"]["sequence"], 7)

    def test_missing_wake_empty_old_and_reserved_only_rejected(self):
        before = ring(5, 5, 5)
        for label, after in (("empty", before), ("old", ring(6, 6, 6, slots=[(4, WAKE)])),
                             ("reserved", ring(5, 5, 6, slots=[(5, WAKE)])),
                             ("other-tid", ring(6, 6, 6, slots=[(5, word(WAKE, 24, 4, 308))]))):
            self.reject(label, published.one_new_requester_wake, before, after, 307)

    def test_duplicate_wakes_at_edges_and_wrap_rejected(self):
        self.reject("both-edges", published.one_new_requester_wake,
                    ring(5, 5, 5), ring(8, 8, 8, slots=[(5, WAKE), (7, WAKE)]), 307)
        self.reject("wrapped-duplicate", published.one_new_requester_wake,
                    ring(126, 126, 126), ring(129, 129, 129, slots=[(126, WAKE), (0, WAKE)]), 307)

    def test_complete_retention_boundary_and_prepublication_overwrite(self):
        before = ring(0, 0, 0)
        oldest = ring(1, 127, 127, slots=[(0, WAKE)])
        result = self.call("127-retained-publications", published.one_new_requester_wake,
                           before, oldest, 307)
        self.assertEqual(result["match"]["sequence"], 0)
        self.assertEqual(result["checked_publication_end"], 127)
        self.reject("128-publications", published.one_new_requester_wake,
                    before, ring(2, 128, 128, slots=[(1, WAKE)]), 307)
        self.reject("reserved-overwrite-before-publication", published.one_new_requester_wake,
                    before, ring(2, 127, 128, slots=[(1, WAKE)]), 307)

    def test_invalid_queue_geometry_counters_and_saturation_rejected(self):
        before, after = ring(5, 5, 5), ring(6, 6, 6, slots=[(5, WAKE)])
        for offset, width, value in ((0, 4, 2), (4, 2, 503), (6, 2, 64), (8, 4, 128),
                                     (40, 8, 16384), (16, 8, 7), (24, 8, 7)):
            self.reject(f"geometry-{offset}", published.one_new_requester_wake,
                        before, word(after, offset, width, value), 307)
        self.reject("saturated", published.one_new_requester_wake,
                    ring(0, 0, 0), ring(0, 127, 127, slots=[(0, WAKE)]), 307)
        maximum = 18446744073709551615
        self.reject("counter-wrap-boundary", published.one_new_requester_wake,
                    before, ring(maximum, maximum, maximum), 307)

    def test_queue_identity_changes_and_decreasing_counters_rejected(self):
        before, after = ring(5, 5, 5), ring(6, 6, 6, slots=[(5, WAKE)])
        for offset in (12, 48, 52, 56, 60):
            self.reject("metadata-" + str(offset), published.one_new_requester_wake,
                        before, flip(after, offset), 307)
        for label, first, last in (
                ("read", ring(6, 6, 6), ring(5, 7, 7, slots=[(6, WAKE)])),
                ("published", ring(5, 7, 7), ring(5, 6, 7, slots=[(5, WAKE)])),
                ("reserved", ring(5, 5, 7), ring(5, 6, 6, slots=[(5, WAKE)]))):
            self.reject(label, published.one_new_requester_wake, first, last, 307)

    def test_requester_and_queue_strict_type_bounds(self):
        before, after = ring(5, 5, 5), ring(6, 6, 6, slots=[(5, WAKE)])
        for index, bad in enumerate((True, False, 307.0, "307", None, 0, -1, 2147483648)):
            self.reject("requester-" + str(index), published.one_new_requester_wake, before, after, bad)
        for index, bad in enumerate((None, [], "x" * 16384, bytearray(after), after[:-1], after + b"x")):
            self.reject("before-" + str(index), published.one_new_requester_wake, bad, after, 307)
            self.reject("after-" + str(index), published.one_new_requester_wake, before, bad, 307)
        for tid in (1, 2147483647):
            self.call("requester-boundary-" + str(tid), published.one_new_requester_wake,
                      before, ring(6, 6, 6, slots=[(5, word(WAKE, 24, 4, tid))]), tid)

    def test_quiet_interval_requires_zero_additional_selected_wakes(self):
        terminal = ring(6, 6, 6, slots=[(5, WAKE)])
        quiet = ring(7, 7, 7, slots=[(5, WAKE), (6, word(WAKE, 24, 4, 308))])
        result = self.call("quiet-other-requester", published.base.no_new_requester_wake,
                           terminal, quiet, 307)
        self.assertEqual(result["new_matching_wakes"], 0)
        self.reject("quiet-selected-duplicate", published.base.no_new_requester_wake,
                    terminal, ring(7, 7, 7, slots=[(5, WAKE), (6, WAKE)]), 307)

    def test_separate_phase_comparisons_never_grant_acceptance(self):
        blocked_queue = ring(5, 5, 5)
        accepted_queue = ring(6, 6, 6, slots=[(5, word(WAKE, 24, 4, 308))])
        terminal_queue = ring(7, 7, 7, slots=[(5, word(WAKE, 24, 4, 308)), (6, WAKE)])
        response = self.call("prepared", published.compare_prepared_response,
                             BLOCKED, PREPARED, worker_tid=421)
        no_early = self.call("no-prepared-wake", published.base.no_new_requester_wake,
                             blocked_queue, accepted_queue, 307)
        one = self.call("one-through-terminal", published.one_new_requester_wake,
                        blocked_queue, terminal_queue, 307)
        quiet = self.call("none-after-terminal", published.base.no_new_requester_wake,
                          terminal_queue, terminal_queue, 307)
        self.check_scope(response)
        self.check_scope(one)
        self.assertEqual((no_early["new_matching_wakes"], one["new_matching_wakes"],
                          quiet["new_matching_wakes"]), (0, 1, 0))


if __name__ == "__main__":
    unittest.main()
