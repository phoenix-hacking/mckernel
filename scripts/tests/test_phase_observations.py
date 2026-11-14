#!/usr/bin/env python3
"""Synthetic native-prefix/phase/fault records; never a guest acceptance test."""
import base64
from copy import deepcopy
import hashlib
import importlib.util
import itertools
import json
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


phase = load("phase_observations", ROOT / "scripts/application-tests/phase_observations.py")
literal = load("literal_owner_fixture", Path(__file__).with_name("test_owner_observations.py"))
EVIDENCE = Path(tempfile.mkdtemp(prefix="stability-phase-parser-tests-"))
SEQUENCE = itertools.count(1)
print("PHASE_TEST_EVIDENCE " + str(EVIDENCE), flush=True)


def keep(raw, label):
    path = EVIDENCE / f"{next(SEQUENCE):04d}-{label}.bin"
    path.write_bytes(raw)
    return raw


def fixture(mode="prepublish-hard", *, barrier=0, timer=3):
    number = phase.MODES[mode]
    owner_mode = phase.OWNER_MODES[number]
    _, contract, _ = literal.fixture(owner_mode)
    contract["ret"]["errno"] = 0 if number == 3 else -71
    names = list(contract["expected_counters"])
    since = 3_500_000_000
    terminal = 10_000_000_000 if number == 4 else 7_000_000_000
    ret_leave = 9_000_000_000 if number == 4 else 6_000_000_000
    intervals = [(1_000_000_000, 1_200_000_000), (3_200_000_000, 3_400_000_000),
                 (terminal, terminal + 200_000_000), (terminal + 6_000_000_000, terminal + 6_200_000_000)]
    attempts = {1: 1, 2: 2, 3: 5, 4: 8}[number]
    published, notification, sends = int(number in (2, 3)), int(number == 2), 2 if number in (2, 3) else 0
    lines = [f"STABILITY_RET_SELECTED version=1 key={literal.KEY} valid=true mono_ns=500000000"]
    for index, (name, (begin, end)) in enumerate(zip(names, intervals), 1):
        if index == 2:
            lines.append(f"STABILITY_RET_ENTER version=1 key={literal.KEY} value=16 cpu=1 duplicate=false mono_ns=3000000000")
        if index == 3:
            lines.append(f"STABILITY_FAULT_SELECTED version=1 mode={number} selection={literal.SELECTION} buffer=2000 bytes=16 mono_ns={since}")
            if number == 1:
                lines.append(f"STABILITY_FAULT_PREPUBLICATION version=1 errno=-5 attempts=1 mono_ns={since}")
            if number in (2, 3):
                start = 5_500_000_000 if number == 3 else 3_510_000_000
                lines += [f"STABILITY_FAULT_REAL_SEND version=1 mode={number} attempt=1 errno=-11 begin_ns={start} end_ns={start + 10_000_000}",
                          f"STABILITY_FAULT_REAL_SEND version=1 mode={number} attempt=2 errno=0 begin_ns={start + 20_000_000} end_ns={start + 30_000_000}",
                          f"STABILITY_FAULT_{'RECOVERED' if number == 3 else 'PUBLISHED'} version=1 mode={number} attempts={attempts} mono_ns={start + 40_000_000}"]
                if number == 2:
                    lines.append(f"STABILITY_FAULT_NOTIFICATION version=1 errno=-5 published=1 mono_ns={start + 50_000_000}")
            lines.append(f"STABILITY_RET_LEAVE version=1 key={literal.KEY} errno={contract['ret']['errno']} accepted=1 duplicate=false mono_ns={ret_leave}")
        lines.append(f"STABILITY_PHASE_SNAPSHOT_BEGIN version=1 phase_sequence={index} phase={name} nonce_low=0000000000001234 nonce_high=000000000000abcd mono_ns={begin} sampling=independent_domains")
        rows = literal.snapshot(index, name, contract["expected_counters"][name])
        if index >= 2:
            timer_text = "None" if timer is None else f"Some({timer})"
            rows = [row.replace('phase: "delivered"', 'phase: "returning"')
                    .replace("response=true completion=false completion_response=false completion_wake=false",
                             "response=false completion=true completion_response=true completion_wake=true")
                    .replace("publication_since=None", "publication_since=" + timer_text) for row in rows]
        if index >= 3:
            if number != 3:
                error = -110 if number == 4 else -5
                rows = [row.replace("runtime_error=0", f"runtime_error={error}")
                        .replace("transport_error=0", f"transport_error={error}")
                        .replace("needs_cleanup: false", "needs_cleanup: true")
                        .replace("quarantined: false", "quarantined: true") for row in rows]
                rows = [row.replace("closed: false, quarantined: true", "closed: true, quarantined: true") for row in rows]
            if number in (2, 3):
                rows = [row for row in rows if not any("STABILITY_OWNER_" + kind + " " in row for kind in ("DELIVERY", "CALL", "WORKER"))
                        and not ("STABILITY_OWNER_TAG " in row and ("class=responses " in row or "class=payloads " in row))]
                rows = [row.replace("calls_total=1 calls_emitted=1 workers_total=1 workers_emitted=1", "calls_total=0 calls_emitted=0 workers_total=0 workers_emitted=0")
                        .replace("last_serial=20 slots=4096 total=1 emitted=1", "last_serial=20 slots=4096 total=0 emitted=0") for row in rows]
            if number == 3:
                rows = [row for row in rows if not any("STABILITY_OWNER_" + kind + " " in row for kind in ("APP", "RPC", "IMAGE"))
                        and "domain=mailbox application=Some(7) " not in row]
                rows = [row.replace("slots=64 total=1 emitted=1", "slots=64 total=0 emitted=0") for row in rows]
        lines.extend(rows)
        tail = index >= 3
        lines.append(f"STABILITY_FAULT_COUNTS version=1 mode={number} attempts={attempts if tail else 0} barrier_attempts={barrier if index >= 2 else 0} published={published if tail else 0} notification_failures={notification if tail else 0} real_sends={sends if tail else 0} since_ns={since if tail else 0} mono_ns={begin + 100_000_000}")
        lines.append(f"STABILITY_PHASE_SNAPSHOT_END version=1 phase_sequence={index} errno=0 mono_ns={end} barrier_calls={barrier if index >= 2 else 0} verification_errno=0")
    raw = ("\n".join(("mcctrl: " if "STABILITY_RET_" in line else "ihk_smp_x86_64: ") + line for line in lines) + "\n").encode()
    keep(raw, "fixture-" + mode)
    (EVIDENCE / f"{next(SEQUENCE):04d}-contract.json").write_text(json.dumps(contract, indent=2) + "\n")
    return raw, contract


class PhaseTests(unittest.TestCase):
    def validate(self, raw, contract, mode="prepublish-hard"):
        keep(raw, "checked")
        return phase.validate_capture(raw, mode=mode, nonce_low=0x1234, nonce_high=0xabcd, owner_contract=contract)

    def reject(self, raw, contract, mode="prepublish-hard"):
        with self.assertRaises(phase.ObservationError):
            self.validate(raw, contract, mode)

    def test_all_four_frozen_modes_preserve_original_and_canonical_bytes_without_acceptance(self):
        for mode in phase.MODES:
            with self.subTest(mode=mode):
                raw, contract = fixture(mode)
                result = self.validate(raw, contract, mode)
                self.assertEqual(result["status"], "NATIVE_METADATA_MATCH_ONLY")
                self.assertIs(result["application_acceptance"], False)
                self.assertIs(result["external_acceptance_evidence_complete"], False)
                self.assertIs(result["physical_accepted_return_capture_verified"], False)
                self.assertIs(result["physical_full_ring_verified"], False)
                parsed = result["phase_observations"]
                self.assertEqual(base64.b64decode(parsed["raw"]["base64"]), raw)
                canonical, mapping = phase.canonicalize_capture(raw)
                self.assertEqual(parsed["canonicalization"]["sha256"], hashlib.sha256(canonical).hexdigest())
                self.assertEqual(len(mapping), len(raw.splitlines()))

    def test_complete_blocked_prefix_does_not_require_future_ret(self):
        raw, _ = fixture()
        prefix = raw.split(b"mcctrl: STABILITY_RET_ENTER", 1)[0]
        parsed = phase.parse_envelopes(prefix, mode="prepublish-hard", nonce_low=0x1234, nonce_high=0xabcd)
        self.assertEqual(len(parsed["snapshots"]), 1)
        self.assertEqual(parsed["snapshots"][0]["owner"]["phase"], "BlockedRead")

    def test_prefix_ret_and_fault_line_positions_are_consistent_before_full_validation(self):
        raw, contract = fixture()
        prefix = raw.split(b"mcctrl: STABILITY_RET_ENTER", 1)[0]
        selected = prefix.splitlines(keepends=True)[0]
        for changed in (selected + prefix, prefix[len(selected):],
                        prefix.replace(b"valid=true", b"valid=false"),
                        prefix.replace(b"mono_ns=500000000", b"mono_ns=1300000000")):
            keep(changed, "invalid-prefix")
            with self.assertRaises(phase.ObservationError):
                phase.parse_envelopes(changed, mode="prepublish-hard", nonce_low=0x1234, nonce_high=0xabcd)
        rows = raw.splitlines(keepends=True)
        fault_index = next(i for i, row in enumerate(rows) if b"STABILITY_FAULT_SELECTED " in row)
        fault = rows[fault_index]
        without_fault = rows[:fault_index] + rows[fault_index + 1:]
        self.reject(fault + b"".join(without_fault), contract)
        self.reject(b"".join(without_fault) + fault, contract)

    def test_returning_worker_identity_and_retained_timer_cannot_change(self):
        raw, contract = fixture()
        rows = raw.splitlines(keepends=True)
        worker = next(i for i, row in enumerate(rows) if b"STABILITY_OWNER_WORKER version=1 sequence=2 " in row)
        for old, new in ((b"tid: 102", b"tid: 103"), (b"delivery: Some(13)", b"delivery: Some(14)"),
                         (b"completed: None", b"completed: Some(13)")):
            changed = list(rows)
            changed[worker] = changed[worker].replace(old, new)
            self.assertNotEqual(changed[worker], rows[worker])
            self.reject(b"".join(changed), contract)
        changed = [row.replace(b"publication_since=Some(3)", b"publication_since=Some(4)")
                   if b"STABILITY_OWNER_CALL version=1 sequence=3 " in row or b"STABILITY_OWNER_CALL version=1 sequence=4 " in row else row for row in rows]
        self.reject(b"".join(changed), contract)

    def test_original_selected_request_target_and_all_arguments_remain_immutable(self):
        raw, contract = fixture()
        rows = raw.splitlines(keepends=True)
        for sequences in ((2,), (3, 4)):
            for old, new in ((b"[0, 8192, 16, 0, 0, 0]", b"[0, 12288, 16, 0, 0, 0]"),
                             (b"[0, 8192, 16, 0, 0, 0]", b"[0, 8192, 16, 1, 0, 0]"),
                             (b"target: 0", b"target: 7")):
                with self.subTest(sequences=sequences, replacement=new):
                    changed = [row.replace(old, new) if any(
                        f"STABILITY_OWNER_DELIVERY version=1 sequence={sequence} ".encode() in row
                        for sequence in sequences) else row for row in rows]
                    self.assertNotEqual(changed, rows)
                    self.reject(b"".join(changed), contract)

    def test_zero_barrier_and_unobserved_recovery_timer_remain_distinct(self):
        raw, contract = fixture("recoverable-backpressure", timer=None)
        result = self.validate(raw, contract, "recoverable-backpressure")
        self.assertEqual(result["status"], "METADATA_MATCH_WITH_MISSING_TIMER")
        self.assertIsNone(result["publication_timer_seconds"])
        self.assertIn("observed_original_production_publication_timer", result["missing_external_gates"])
        raw, contract = fixture(barrier=2)
        self.assertEqual(self.validate(raw, contract)["status"], "NATIVE_METADATA_MATCH_ONLY")

    def test_exact_crate_prefixes_and_documented_timestamp_forms(self):
        raw, contract = fixture()
        for prefix in (b"[   12.345678] ", b"<6>[12.345] ", b"<6>"):
            native = b"\r\n".join(prefix + row for row in raw.splitlines()) + b"\r\n"
            self.validate(native, contract)
        for old, new in [(b"ihk_smp_x86_64: ", b"evil: "), (b"mcctrl: STABILITY_RET", b"ihk_smp_x86_64: STABILITY_RET"),
                         (b"ihk_smp_x86_64: STABILITY_OWNER", b"mcctrl: STABILITY_OWNER"), (b"ihk_smp_x86_64: ", b"")]:
            self.reject(raw.replace(old, new, 1), contract)

    def test_versions_nonces_unknown_fields_and_literal_types(self):
        raw, contract = fixture()
        for old, new in [(b"PHASE_SNAPSHOT_BEGIN version=1", b"PHASE_SNAPSHOT_BEGIN version=2"),
                         (b"nonce_low=0000000000001234", b"nonce_low=0000000000001235"),
                         (b"nonce_low=0000000000001234", b"nonce_low=1234"),
                         (b"FAULT_COUNTS version=1 mode=1", b"FAULT_COUNTS version=1 mode=2"),
                         (b"attempts=0 barrier_attempts", b"attempts=true barrier_attempts"),
                         (b"sampling=independent_domains\n", b"sampling=independent_domains extra=1\n")]:
            with self.subTest(new=new): self.reject(raw.replace(old, new, 1), contract)

    def test_missing_duplicate_or_reordered_phase_owner_and_counts_records(self):
        raw, contract = fixture()
        lines = raw.splitlines(keepends=True)
        for marker in (b"PHASE_SNAPSHOT_BEGIN", b"PHASE_SNAPSHOT_END", b"FAULT_COUNTS", b"OWNER_BEGIN", b"OWNER_END"):
            index = next(i for i, row in enumerate(lines) if marker in row)
            self.reject(b"".join(lines[:index] + lines[index + 1:]), contract)
            self.reject(b"".join(lines[:index] + [lines[index]] + lines[index:]), contract)
        self.reject(raw.replace(b"phase_sequence=2 phase=AcceptedReturn", b"phase_sequence=3 phase=AcceptedReturn"), contract)

    def test_incomplete_invalid_overflow_and_decreasing_counters(self):
        raw, contract = fixture()
        for old, new in [(b"verification_errno=0", b"verification_errno=-75"),
                         (b"barrier_calls=0", b"barrier_calls=1"),
                         (b"real_sends=0", b"real_sends=33"),
                         (b"attempts=0 barrier_attempts", b"attempts=18446744073709551615 barrier_attempts"),
                         (b"counters_valid=true", b"counters_valid=false")]:
            self.reject(raw.replace(old, new, 1), contract)
        self.reject(raw + b"ihk_smp_x86_64: STABILITY_FAULT_INVALID version=1 reason=duplicate_selected_send\n", contract)

    def test_actual_callback_errors_success_count_and_intervals(self):
        raw, contract = fixture("postpublish-notify")
        for old, new in [(b"attempt=1 errno=-11", b"attempt=1 errno=0"), (b"attempt=2 errno=0", b"attempt=2 errno=-5"),
                         (b"attempt=2 errno=0", b"attempt=3 errno=0"), (b"begin_ns=3510000000", b"begin_ns=3990000000"),
                         (b"notification_failures=1", b"notification_failures=0")]:
            self.reject(raw.replace(old, new, 1), contract, "postpublish-notify")

    def test_recovery_hold_deadline_and_future_timer(self):
        raw, contract = fixture("recoverable-backpressure")
        self.reject(raw.replace(b"begin_ns=5500000000", b"begin_ns=5499999999"), contract, "recoverable-backpressure")
        self.reject(raw.replace(b"publication_since=Some(3)", b"publication_since=Some(0)"), contract, "recoverable-backpressure")
        self.reject(raw.replace(b"publication_since=Some(3)", b"publication_since=Some(18446744073709551615)"), contract, "recoverable-backpressure")

    def test_terminal_mode_errno_claim_and_quiet_inventory(self):
        raw, contract = fixture()
        self.reject(raw.replace(b"runtime_error=-5", b"runtime_error=0", 1), contract)
        self.reject(raw.replace(b"quarantined: true", b"quarantined: false", 1), contract)
        lines = raw.splitlines(keepends=True)
        index = next(i for i, row in enumerate(lines) if b"sequence=4 class=responses ordinal=0" in row)
        lines[index] = lines[index].replace(b"physical: 4096, end: 4136", b"physical: 20480, end: 20520")
        self.reject(b"".join(lines), contract)
        raw, contract = fixture("permanent-backpressure")
        self.reject(raw.replace(b"publication_since=Some(3)", b"publication_since=None"), contract, "permanent-backpressure")

    def test_ret_modes_bracket_and_caller_counter_contract_are_not_overridable(self):
        raw, contract = fixture()
        for update in ({"errno": 0}, {"accepted": 0}, {"value": 15}):
            changed = deepcopy(contract); changed["ret"].update(update)
            self.reject(raw, changed)
        self.reject(raw.replace(b"mono_ns=6000000000", b"mono_ns=3400000000", 1), contract)
        changed = deepcopy(contract)
        changed["expected_counters"]["AcceptedReturn"]["payload_bytes"] = 32
        self.reject(raw, changed)

    def test_truncation_byte_line_and_unknown_marker_bounds(self):
        raw, contract = fixture()
        for changed in (raw[:-1], raw + b"ihk_smp_x86_64: STABILITY_PHASE_UNRECOGNIZED version=1\n",
                        b"x" * (phase.owner.MAX_LINE + 1) + b"\n" + raw, raw.replace(b"version=1", b"version=1\x00", 1)):
            self.reject(changed, contract)


if __name__ == "__main__":
    unittest.main()
