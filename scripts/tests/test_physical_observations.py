#!/usr/bin/env python3
"""Literal wire fixtures for physical comparisons; no guest or physical reads."""
import base64
from copy import deepcopy
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
HELPER = ROOT / "scripts/application-tests/physical_observations.py"
EVIDENCE = Path(tempfile.mkdtemp(prefix="stability-physical-tests-", dir=os.environ.get("TMPDIR")))
print("PHYSICAL_TEST_EVIDENCE " + str(EVIDENCE), flush=True)
(EVIDENCE / "source").mkdir()
inputs = []
for source in (Path(__file__).resolve(), HELPER):
    raw = source.read_bytes()
    retained = EVIDENCE / "source" / source.name
    retained.write_bytes(raw)
    inputs.append({"path": str(source), "retained": str(retained), "size": len(raw),
                   "sha256": hashlib.sha256(raw).hexdigest()})
(EVIDENCE / "inputs.json").write_text(json.dumps({
    "source_inputs": inputs, "python": sys.version, "executable": sys.executable,
    "argv": sys.argv, "cwd": os.getcwd(), "TMPDIR": os.environ.get("TMPDIR"),
    "application_acceptance": False, "physical_reads": False,
}, indent=2) + "\n")

# Import the exact retained bytes. A later working-tree change cannot silently
# substitute a different comparator for this invocation's saved source identity.
SPEC = importlib.util.spec_from_file_location("physical_observations", EVIDENCE / "source" / HELPER.name)
physical = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(physical)

# Independently transcribed little-endian C/Rust wire fixtures. These never use
# comparator constants, schemas, packers, decoders or generated expected output.
REQUEST_PACKET = bytes.fromhex(
    "0000000000000000 0400000000000000 0000000000000000 0000000000000000 "
    "d300000000000000 0000000000000000 3301000000000000 0100000000000000 "
    "0000000000000000 0000000000000000 0050341200000000 1000000000000000 "
    "4433221100000000 8877665500000000 ccbbaa9900000000 0040000000000000"
)
REQUEST = {"cpu": 0, "pid": 211, "requester": 307, "target": 0, "number": 0,
           "response": 16384, "arguments": [0, 305418240, 16, 287454020, 1432778632, 2578103244]}
WAKE_PACKET = bytes.fromhex(
    "0000000000000000 1400000000000000 0000000000000000 3301000000000000 "
    "0000000000000000 0000000000000000 0000000000000000 0000000000000000 "
    "0000000000000000 0000000000000000 0000000000000000 0000000000000000 "
    "0000000000000000 0000000000000000 0000000000000000 0000000000000000"
)
QUEUE_HEADER = bytes.fromhex(
    "01000000 f701 8000 7f000000 00000000 "
    "0000000000000000 0000000000000000 0000000000000000 803f000000000000 "
    "11000000 00000000 00000000 00000000"
)
BLOCKED = bytes.fromhex(
    "deadbeef67452301 0000000000000000 0200000000000000 "
    "f0debc9a78563412 efcdab8967452301"
)
TERMINAL = bytes.fromhex(
    "deadbeefa5010000 0000000000000000 0100000000000000 "
    "1000000000000000 efcdab8967452301"
)


def replace_word(raw, offset, width, value):
    changed = bytearray(raw)
    changed[offset:offset + width] = value.to_bytes(width, "little")
    return bytes(changed)


def ring(read, published, reserved, *, port=503, slots=()):
    # Slots are physical slot numbers chosen explicitly by each test. No
    # production retention formula is used to construct these fixtures.
    raw = bytearray(QUEUE_HEADER + bytes(16320))
    raw[4:6] = port.to_bytes(2, "little")
    for offset, value in ((16, read), (24, published), (32, reserved)):
        raw[offset:offset + 8] = value.to_bytes(8, "little")
    for slot, packet in slots:
        if not (0 <= slot < 127 and len(packet) == 128):
            raise AssertionError("invalid literal fixture slot")
        start = 64 + slot * 128
        raw[start:start + 128] = packet
    return bytes(raw)


class PhysicalTests(unittest.TestCase):
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

        invocation = {"function": function.__name__, "args": encode(args, "args"),
                      "kwargs": encode(kwargs, "kwargs"),
                      "expected_outcome": "PhysicalObservationError" if expected_error else "return",
                      "application_acceptance": False}
        (target / "invocation.json").write_text(json.dumps(invocation, indent=2) + "\n")
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
        with self.assertRaises(physical.PhysicalObservationError):
            self.call(label, function, *args, expected_error=True, **kwargs)

    def test_literal_packet_fields_and_retained_bytes(self):
        decoded = self.call("literal-decode", physical.decode_request, REQUEST_PACKET)
        self.assertEqual(decoded, REQUEST)
        raw = ring(1, 1, 1, slots=[(0, REQUEST_PACKET)])
        result = self.call("first-consumed", physical.locate_consumed_request, raw, REQUEST)
        self.assertEqual((result["match"]["sequence"], result["match"]["slot"], result["match"]["offset"]), (0, 0, 64))
        self.assertEqual(base64.b64decode(result["match"]["packet"]["base64"]), REQUEST_PACKET)
        self.assertEqual(base64.b64decode(result["queue"]["raw"]["base64"]), raw)
        self.assertEqual(result["queue"]["raw"]["sha256"], hashlib.sha256(raw).hexdigest())

    def test_retained_consumed_lower_boundary_uses_reservation_before_copy(self):
        # Sequence0 is still safe at next reservation127, even though the126
        # outstanding slots form a legal full ring. Reservation127 makes next
        # reservation128 and invalidates old slot0 before the new copy publishes.
        before_reuse = ring(1, 127, 127, slots=[(0, REQUEST_PACKET)])
        result = self.call("oldest-safe", physical.locate_consumed_request, before_reuse, REQUEST)
        self.assertEqual(result["match"]["sequence"], 0)
        reserved_reuse = ring(2, 127, 128, slots=[(0, REQUEST_PACKET)])
        self.reject("reserved-stale-slot", physical.locate_consumed_request, reserved_reuse, REQUEST)

    def test_consumed_upper_boundary_and_physical_slot_wrap(self):
        wrapped = ring(128, 128, 128, slots=[(0, REQUEST_PACKET)])
        result = self.call("wrapped-last-consumed", physical.locate_consumed_request, wrapped, REQUEST)
        self.assertEqual((result["match"]["sequence"], result["match"]["slot"], result["match"]["offset"]), (127, 0, 64))
        for label, raw in (("published-not-consumed", ring(5, 6, 6, slots=[(5, REQUEST_PACKET)])),
                           ("reserved-not-published", ring(5, 5, 6, slots=[(5, REQUEST_PACKET)]))):
            self.reject(label, physical.locate_consumed_request, raw, REQUEST)

    def test_duplicate_consumed_request_is_ambiguous(self):
        raw = ring(2, 2, 2, slots=[(0, REQUEST_PACKET), (1, REQUEST_PACKET)])
        self.reject("duplicate", physical.locate_consumed_request, raw, REQUEST)

    def test_every_original_request_field_is_bound(self):
        mutations = [(8, 4, 5), (24, 4, 3), (32, 4, 212), (48, 4, 308), (52, 4, 17),
                     (56, 8, 0), (64, 8, 1), (72, 8, 1), (80, 8, 305422336), (88, 8, 15),
                     (96, 8, 287454021), (104, 8, 1432778633), (112, 8, 2578103245), (120, 8, 20480)]
        for offset, width, value in mutations:
            with self.subTest(offset=offset):
                packet = replace_word(REQUEST_PACKET, offset, width, value)
                self.assertNotEqual(packet, REQUEST_PACKET)
                self.reject("field-" + str(offset), physical.locate_consumed_request,
                            ring(1, 1, 1, slots=[(0, packet)]), REQUEST)

    def test_original_request_types_schema_and_response_overflow(self):
        invalid = []
        for field, value in (("cpu", False), ("number", False), ("pid", True),
                             ("response", (1 << 64) - 40), ("response", 16385)):
            changed = deepcopy(REQUEST); changed[field] = value; invalid.append(changed)
        for arguments in (tuple(REQUEST["arguments"]), REQUEST["arguments"][:-1],
                          [False] + REQUEST["arguments"][1:]):
            changed = deepcopy(REQUEST); changed["arguments"] = arguments; invalid.append(changed)
        changed = deepcopy(REQUEST); del changed["target"]; invalid.append(changed)
        changed = deepcopy(REQUEST); changed["extra"] = 0; invalid.append(changed)
        raw = ring(1, 1, 1, slots=[(0, REQUEST_PACKET)])
        for index, changed in enumerate(invalid):
            with self.subTest(index=index):
                self.reject("schema-" + str(index), physical.locate_consumed_request, raw, changed)

    def test_queue_geometry_counter_order_wrap_and_byte_bounds(self):
        good = ring(1, 1, 1)
        invalid = [good[:-1], good + b"\0", bytearray(good),
                   replace_word(good, 0, 4, 2), replace_word(good, 4, 2, 501),
                   replace_word(good, 6, 2, 64), replace_word(good, 8, 4, 126),
                   replace_word(good, 40, 8, 16255), ring(2, 1, 2), ring(1, 3, 2),
                   ring(0, 127, 127), ring((1 << 64) - 1, (1 << 64) - 1, (1 << 64) - 1),
                   ring((1 << 64) - 2, 1, 1)]
        for index, raw in enumerate(invalid):
            with self.subTest(index=index):
                self.reject("queue-" + str(index), physical.queue, raw, 503)
        self.reject("port-type", physical.queue, good, True)

    def test_legal_full126_queue_is_accepted_without_physical_credit(self):
        result = self.call("full126", physical.queue, ring(10, 135, 136), 503)
        self.assertEqual((result["read"], result["published"], result["reserved"]), (10, 135, 136))
        self.assertNotIn("application_acceptance", result)
        self.assertNotIn("physical_full_ring_proved", result)

    def test_new_wake_interval_ignores_old_unrelated_and_unpublished_packets(self):
        other_tid = replace_word(WAKE_PACKET, 24, 4, 308)
        other_message = replace_word(WAKE_PACKET, 8, 4, 49)
        before = ring(4, 4, 4, port=501, slots=[(3, WAKE_PACKET)])
        after = ring(6, 6, 7, port=501, slots=[(3, WAKE_PACKET), (4, other_tid),
                                             (5, other_message), (6, WAKE_PACKET)])
        result = self.call("unrelated", physical.no_new_requester_wake, before, after, 307)
        self.assertEqual((result["checked_publication_begin"], result["checked_publication_end"], result["new_matching_wakes"]), (4, 6, 0))
        # Request.target is at52, but a WAKE's requester is at24. Putting307
        # only in the request-shaped location must not fabricate a selected wake.
        wrong_union = replace_word(replace_word(WAKE_PACKET, 24, 4, 0), 52, 4, 307)
        self.call("wrong-union-location", physical.no_new_requester_wake,
                  ring(4, 4, 4, port=501), ring(5, 5, 5, port=501, slots=[(4, wrong_union)]), 307)

    def test_selected_wake_at_both_interval_edges_and_wrapped_slot_is_rejected(self):
        for slot in (4, 5):
            self.reject("new-wake-" + str(slot), physical.no_new_requester_wake,
                        ring(4, 4, 4, port=501), ring(6, 6, 6, port=501, slots=[(slot, WAKE_PACKET)]), 307)
        self.reject("wrapped-new-wake", physical.no_new_requester_wake,
                    ring(127, 127, 127, port=501), ring(128, 128, 128, port=501, slots=[(0, WAKE_PACKET)]), 307)

    def test_publication_retention_boundary_and_overwritten_interval(self):
        before = ring(0, 0, 0, port=501)
        result = self.call("all127-retained", physical.no_new_requester_wake,
                           before, ring(127, 127, 127, port=501), 307)
        self.assertEqual(result["checked_publication_end"], 127)
        self.reject("oldest-published-overwritten", physical.no_new_requester_wake,
                    before, ring(128, 128, 128, port=501), 307)
        self.reject("oldest-reserved-before-copy", physical.no_new_requester_wake,
                    before, ring(127, 127, 128, port=501), 307)
        result = self.call("retention-start-one", physical.no_new_requester_wake,
                           ring(1, 1, 1, port=501), ring(128, 128, 128, port=501), 307)
        self.assertEqual((result["checked_publication_begin"], result["checked_publication_end"]), (1, 128))
        self.reject("oldest-retained-wake", physical.no_new_requester_wake,
                    ring(1, 1, 1, port=501), ring(128, 128, 128, port=501, slots=[(1, WAKE_PACKET)]), 307)

    def test_outbound_metadata_counter_decrease_and_requester_type(self):
        before, after = ring(4, 4, 4, port=501), ring(5, 5, 5, port=501)
        self.reject("channel-changed", physical.no_new_requester_wake,
                    before, replace_word(after, 48, 4, 18), 307)
        self.reject("counter-decrease", physical.no_new_requester_wake,
                    before, ring(3, 3, 3, port=501), 307)
        self.reject("requester-bool", physical.no_new_requester_wake, before, after, True)

    def test_literal_hard_response_preserves_opaque_bytes_without_acceptance(self):
        result = self.call("literal-response", physical.compare_hard_response,
                           BLOCKED, TERMINAL, TERMINAL, worker_tid=421)
        self.assertEqual(base64.b64decode(result["expected_prepublication_prefix"]["base64"]), TERMINAL)
        self.assertEqual(base64.b64decode(result["raw"]["BlockedRead"]["base64"]), BLOCKED)
        self.assertIs(result["application_acceptance"], False)
        self.assertIs(result["production_gate_credit"], False)
        self.assertIs(result["accepted_return_physically_observed"], False)
        # An opaque firstword of -1 is also legal and must simply survive.
        blocked = b"\xff" * 4 + BLOCKED[4:]
        terminal = b"\xff" * 4 + TERMINAL[4:]
        self.call("opaque-negative-firstword", physical.compare_hard_response,
                  blocked, terminal, terminal, worker_tid=421)

    def test_forbidden_response_writes_and_wrong_prepared_values(self):
        for offset in list(range(0, 4)) + list(range(8, 16)) + list(range(32, 40)):
            with self.subTest(offset=offset):
                changed = bytearray(TERMINAL); changed[offset] ^= 1; changed = bytes(changed)
                self.reject("forbidden-byte-" + str(offset), physical.compare_hard_response,
                            BLOCKED, changed, changed, worker_tid=421)
        for offset, width, value in ((4, 4, 422), (16, 8, 2), (24, 8, 15)):
            changed = replace_word(TERMINAL, offset, width, value)
            self.reject("prepared-field-" + str(offset), physical.compare_hard_response,
                        BLOCKED, changed, changed, worker_tid=421)

    def test_quiet_snapshot_must_be_byte_identical(self):
        for offset in (0, 4, 8, 16, 24, 32, 39):
            changed = bytearray(TERMINAL); changed[offset] ^= 1
            self.reject("quiet-byte-" + str(offset), physical.compare_hard_response,
                        BLOCKED, TERMINAL, bytes(changed), worker_tid=421)

    def test_blocked_status_wake_response_length_and_worker_type(self):
        for offset, width, value in ((8, 8, 1), (16, 8, 0), (16, 8, 1)):
            self.reject("blocked-field-" + str(offset) + "-" + str(value), physical.compare_hard_response,
                        replace_word(BLOCKED, offset, width, value), TERMINAL, TERMINAL, worker_tid=421)
        for index, bad in enumerate((BLOCKED[:-1], BLOCKED + bytes(8), bytearray(BLOCKED))):
            self.reject("bad-prefix-" + str(index), physical.compare_hard_response,
                        bad, TERMINAL, TERMINAL, worker_tid=421)
        for index, tid in enumerate((0, -1, True, 1.0, 1 << 31)):
            self.reject("bad-tid-" + str(index), physical.compare_hard_response,
                        BLOCKED, TERMINAL, TERMINAL, worker_tid=tid)


if __name__ == "__main__":
    unittest.main()
