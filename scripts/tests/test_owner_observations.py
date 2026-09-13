#!/usr/bin/env python3
"""Synthetic parser rejection tests; these do not exercise native/guest code."""
import base64
from copy import deepcopy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

MODULE = Path(__file__).resolve().parents[1] / "application-tests/owner_observations.py"
spec = importlib.util.spec_from_file_location("owner_observations", MODULE)
owner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(owner)

# Deliberately literal producer-shaped records, independent of parser tables.
SELECTION = "Selection { os: 0, generation: 4, pid: 101, cpu: 1, requester: 101, application: 7, worker: 12, delivery: 13, ledger_serial: 17, ledger_index: 5, response: 4096, response_end: 4136 }"
KEY = "StabilityRetKey { os: 0, generation: 4, pid: 101, tid: 102, worker: 12, delivery: 13 }"
RPC = 'Rpc { token: 7, os: 0, cpu: 1, pid: 101, message: 4, reply: 5, argument: 0, phase: "reserved", result: None, waiter: false, unscheduled_deleted: false, retirement_query: false }'
APP = "App { index: 3, token: 7, pid: 101, owner_slot: 0, prepare: None, schedule: None, retirement: None, retirement_after: 0, procfs: Some(Process { token: 7, pid: 101, cpu: 1, live: true, published: true, main_seen: true, tids: 2 }), scheduled: true, needs_cleanup: false, closed: false, quarantined: false }"
DELIVERY = 'Delivery { serial: 13, phase: "delivered", phase_worker: Some((12, 102)), pid: 101, cpu: 1, requester: 101, target: 0, number: 0, response: 4096, arguments: [0, 8192, 16, 0, 0, 0] }'
CLAIM = "Some(Claim { os: 0, generation: 4, response: Tag { index: 5, serial: Some(17), physical: 4096, end: 4136 }, payload: Some(Tag { index: 5, serial: Some(18), physical: 8192, end: 8208 }) })"
MAILBOX = "Some(Mailbox { call_slots: 64, worker_slots: 64, closed: false, quarantined: false, completion_cursor: 0 })"


def counts(address, release, payload=1):
    return {"address_calls": address, "payload_calls": payload, "payload_bytes": 16 * payload, "release_calls": release, "released": bool(release), "after_release_calls": 0, "duplicate_release": 0}


def snapshot(sequence, phase, counters):
    def line(kind, payload):
        return f"STABILITY_OWNER_{kind} version=1 sequence={sequence} {payload}"
    lines = [
        line("BEGIN", f"phase={phase} selection={SELECTION} sampling=independent_domains"),
        line("RUNTIME", "os=0 generation=4 runtime_owner=ffff1234 runtime_error=0 metadata_pending=0 procfs_pending=0 zero_pending=0 completed=3 rejected=0 zeroed=1"),
        line("DOMAIN", "domain=applications os=0 generation=4 transport_error=0 slots=64 total=1 emitted=1 complete=true release_token=6"),
        line("APP", "ordinal=0 row=" + APP),
        line("RPC", "application=7 role=cleanup row=" + RPC),
        line("IMAGE", "application=7 row=None"),
        line("RPC", "application=7 role=schedule row=None"),
        line("RPC", "application=7 role=retirement row=None"),
        line("DOMAIN", "domain=mailbox application=Some(7) release_token=6 state=" + MAILBOX + " calls_total=1 calls_emitted=1 workers_total=1 workers_emitted=1 claims_known=true complete=true"),
        line("DELIVERY", "application=Some(7) ordinal=0 row=" + DELIVERY),
        line("CALL", "application=Some(7) ordinal=0 slot=2 owner=" + CLAIM + " response=true completion=false completion_response=false completion_wake=false worker=Some((12, 102)) cancelled=false kernel=false service=false transferred=false publication_since=None"),
        line("WORKER", "application=Some(7) ordinal=0 row=Worker { index: 4, handle: 12, tid: 102, delivery: Some(13), completed: None }"),
        line("DOMAIN", "domain=mailbox application=None release_token=6 state=" + MAILBOX + " calls_total=0 calls_emitted=0 workers_total=0 workers_emitted=0 claims_known=true complete=true"),
        line("DOMAIN", "domain=pagers slots=4096 total=1 emitted=1 complete=true linux_file_refcount=not_observed"),
        line("PAGER", "ordinal=0 row=Pager { index: 2, token: 8, references: 1, readable_owner: 4567, writable_owner: Some(4567) }"),
    ]
    for name in ("fixed", "requests", "responses", "payloads", "snoops", "procfs", "zeroing"):
        occupied = name in ("fixed", "responses", "payloads")
        slots = 4096 if name in ("requests", "responses", "payloads") else int(occupied)
        lines.append(line("DOMAIN", f"domain=ledger class={name} os=0 generation=4 last_serial=20 slots={slots} total={int(occupied)} emitted={int(occupied)} complete=true"))
        if occupied:
            row = {"fixed": "Tag { index: 0, serial: None, physical: 1024, end: 2048 }", "responses": "Tag { index: 5, serial: Some(17), physical: 4096, end: 4136 }", "payloads": "Tag { index: 5, serial: Some(18), physical: 8192, end: 8208 }"}[name]
            lines.append(line("TAG", f"class={name} ordinal=0 row={row}"))
    values = " ".join(f"{key}={str(value).lower()}" for key, value in counters.items())
    lines.append(line("COUNTERS", "selected_ledger_serial=Some(17) " + values + " sampling=independent_atomics"))
    lines.append(line("END", "complete=true counters_valid=true result=COMPLETE_SNAPSHOT"))
    return lines


def fixture(mode="hard-prepublication"):
    recovery = mode == "recovery-before-deadline"
    phases = ["BlockedRead", "AcceptedReturn"] + (["Recovery", "AfterEightHello"] if recovery else ["Terminal", "TerminalPlusFive"])
    released = recovery or mode == "postpublication-notify"
    vectors = [counts(0, 0, 0), counts(1, 0), counts(2 if released else 1, int(released)), counts(2 if released else 1, int(released))]
    ret = [f"STABILITY_RET_SELECTED version=1 key={KEY} valid=true mono_ns=1000000000", f"STABILITY_RET_ENTER version=1 key={KEY} value=16 cpu=1 duplicate=false mono_ns=3000000000", f"STABILITY_RET_LEAVE version=1 key={KEY} errno=-5 accepted=1 duplicate=false mono_ns=4000000000"]
    lines = ["ordinary kernel noise", ret[0]]
    for index, (phase, vector) in enumerate(zip(phases, vectors), 1):
        lines.extend(snapshot(index, phase, vector))
        if index == 1:
            lines.extend(ret[1:])
    contract = {"schema_version": 1, "observer_version": 1, "mode": mode, "expected_counters": dict(zip(phases, vectors)), "ret": {"errno": -5, "accepted": 1, "value": 16, "maximum_elapsed_ns": 15_000_000_000}}
    timing = {"schema_version": 1, "clock": "host_kernel_monotonic", "phases": dict(zip(phases, [{"begin_ns": 1_000_000_001, "end_ns": 2_000_000_000}, {"begin_ns": 4_000_000_000, "end_ns": 4_500_000_000}, {"begin_ns": 5_000_000_000, "end_ns": 6_000_000_000}, {"begin_ns": 11_000_000_000, "end_ns": 12_000_000_000}]))}
    return ("\n".join(lines) + "\n").encode(), contract, timing


class OwnerObservationsTests(unittest.TestCase):
    def reject(self, raw):
        with self.assertRaises(owner.ObservationError):
            owner.parse_observations(raw)

    def test_complete_literal_fixture_all_modes_retains_exact_bytes_without_acceptance(self):
        for mode in owner.MODES:
            with self.subTest(mode=mode):
                raw, contract, timing = fixture(mode)
                parsed = owner.parse_observations(raw)
                result = owner.validate_run(parsed, contract, timing)
                self.assertEqual(result["status"], "OBSERVATIONS_MATCH_FROZEN_CONTRACT")
                self.assertIs(result["application_acceptance"], False)
                self.assertIs(result["external_acceptance_evidence_complete"], False)
                self.assertEqual(base64.b64decode(parsed["raw"]["base64"]), raw)
                self.assertEqual(parsed["raw"]["sha256"], hashlib.sha256(raw).hexdigest())
                self.assertEqual(parsed["ret"]["errno"], -5)
                self.assertEqual(parsed["ret"]["accepted"], 1)
                self.assertEqual(parsed["ret"]["key"]["tid"], 102)

    def test_documented_prefixes_and_crlf(self):
        raw, _, _ = fixture()
        for prefix in (b"", b"[   12.345678] ", b"<6>[12.345] ", b"<6>"):
            with self.subTest(prefix=prefix):
                decorated = b"\r\n".join(prefix + line for line in raw.splitlines()) + b"\r\n"
                self.assertEqual(len(owner.parse_observations(decorated)["snapshots"]), 4)

    def test_versions_unknown_fields_literal_injection_and_type_drift(self):
        raw, _, _ = fixture()
        changes = [(b"version=1", b"version=2"), (b"version=1", b"version=true"), (b"phase=BlockedRead", b"phase=Unknown"), (b"sampling=independent_domains", b"sampling=independent_domains extra=1"), (b"pid: 101", b"pid: 2147483648"), (b"generation: 4", b"generation: 18446744073709551616"), (b"generation: 4", b"generation: -1"), (b"generation: 4", b"generation: 04"), (b"runtime_error=0", b"runtime_error=-0"), (b"runtime_owner=ffff1234", b"runtime_owner=0xffff1234"), (b"owner=Some(Claim", b"owner=Some(Evil"), (b"serial: Some(17)", b"serial: Some(__import__('os'))"), (b'phase: "delivered"', b'phase: "delivered\\n"'), (b"[0, 8192, 16, 0, 0, 0]", b"[0, 8192, 16, 0, 0]"), (b"Some((12, 102))", b"Some((12, 102, 1))"), (b"valid=true", b"valid=1")]
        for old, new in changes:
            with self.subTest(new=new):
                self.reject(raw.replace(old, new, 1))

    def test_missing_or_duplicate_every_owner_record_class(self):
        raw, _, _ = fixture()
        lines = raw.splitlines(keepends=True)
        for kind in (b"BEGIN", b"RUNTIME", b"DOMAIN", b"APP", b"RPC", b"IMAGE", b"DELIVERY", b"CALL", b"WORKER", b"PAGER", b"TAG", b"COUNTERS", b"END"):
            index = next(i for i, line in enumerate(lines) if b"STABILITY_OWNER_" + kind + b" " in line)
            with self.subTest(kind=kind, action="missing"):
                self.reject(b"".join(lines[:index] + lines[index + 1:]))
            with self.subTest(kind=kind, action="duplicate"):
                self.reject(b"".join(lines[:index] + [lines[index]] + lines[index:]))

    def test_missing_duplicate_reordered_or_cross_identity_ret(self):
        raw, _, _ = fixture()
        lines = raw.splitlines(keepends=True)
        for kind in (b"SELECTED", b"ENTER", b"LEAVE"):
            index = next(i for i, line in enumerate(lines) if b"STABILITY_RET_" + kind in line)
            for mutated in (lines[:index] + lines[index + 1:], lines[:index] + [lines[index]] + lines[index:]):
                self.reject(b"".join(mutated))
        for old, new in [(b"tid: 102", b"tid: 103"), (b"valid=true", b"valid=false"), (b"duplicate=false", b"duplicate=true"), (b"mono_ns=4000000000", b"mono_ns=2000000000"), (b"mono_ns=4000000000", b"mono_ns=9223372036854775808")]:
            with self.subTest(new=new):
                self.reject(raw.replace(old, new, 1))

    def test_overflow_counts_ordinals_missing_claim_and_domains(self):
        raw, _, _ = fixture()
        changes = [(b"slots=64 total=1 emitted=1", b"slots=64 total=9 emitted=1"), (b"slots=64 total=1 emitted=1", b"slots=0 total=1 emitted=1"), (b"ordinal=0 row=App", b"ordinal=1 row=App"), (b"index: 3, token: 7", b"index: 64, token: 7"), (b"calls_total=1 calls_emitted=1", b"calls_total=2 calls_emitted=1"), (b"claims_known=true", b"claims_known=false"), (b"complete=true", b"complete=false"), (b"class=snoops", b"class=responses"), (b"last_serial=20", b"last_serial=16"), (b"selected_ledger_serial=Some(17)", b"selected_ledger_serial=None"), (b"selected_ledger_serial=Some(17)", b"selected_ledger_serial=Some(18)"), (b"after_release_calls=0", b"after_release_calls=1"), (b"duplicate_release=0", b"duplicate_release=1"), (b"address_calls=0", b"address_calls=18446744073709551615"), (b"Some(7) release_token=6", b"Some(8) release_token=6"), (b"domain=mailbox application=None", b"domain=mailbox application=Some(7)"), (CLAIM.encode(), b"None")]
        for old, new in changes:
            with self.subTest(new=new):
                self.reject(raw.replace(old, new) if old == b"last_serial=20" else raw.replace(old, new, 1))

    def test_selected_read_worker_and_original_serial_required(self):
        raw, _, _ = fixture()
        for old, new in [(b'phase: "delivered"', b'phase: "returning"'), (b"number: 0", b"number: 1"), (b"arguments: [0, 8192, 16", b"arguments: [1, 8192, 16"), (b"arguments: [0, 8192, 16", b"arguments: [0, 8192, 15"), (b"worker=Some((12, 102))", b"worker=Some((13, 102))"), (b"serial: Some(17), physical: 4096", b"serial: Some(18), physical: 4096"), (b"response=true completion=false", b"response=false completion=true")]:
            with self.subTest(new=new):
                self.reject(raw.replace(old, new, 1))

    def test_complete_image_some_and_negative_rpc_result(self):
        raw, _, _ = fixture()
        image = "Some(Image { exchange: " + RPC.replace("result: None", "result: Some(-5)") + ", result: Some(-5), thread: 10, page_table: 4096, buffers_retained: true, descriptor: Some(8192), args: Some(12288), envs: None })"
        parsed = owner.parse_observations(raw.replace(b"application=7 row=None", ("application=7 row=" + image).encode(), 1))
        row = next(r["row"] for r in parsed["snapshots"][0]["records"] if r["kind"] == "IMAGE")
        self.assertEqual(row["exchange"]["result"], -5)
        self.assertIsNone(row["envs"])

    def test_truncated_overlong_nonascii_unknown_and_nested_markers(self):
        raw, _, _ = fixture()
        for mutated in (raw[:-1], raw[:-30] + b"\n", b"x" * (owner.MAX_LINE + 1) + b"\n" + raw, raw.replace(b"version=1", b"version=1\x00", 1), raw.replace(b"version=1", b"version=1\xff", 1), raw.replace(b"STABILITY_OWNER_BEGIN", b"STABILITY_OWNER_UNKNOWN", 1), b"unrecognized prefix " + raw[raw.index(b"STABILITY_RET_SELECTED"):], raw + b"STABILITY_OWNER_BEG\n"):
            self.reject(mutated)

    def test_counter_decrease_cannot_hide_in_next_phase(self):
        raw, _, _ = fixture()
        mutated = raw.replace(b"sequence=4 selected_ledger_serial=Some(17) address_calls=1", b"sequence=4 selected_ledger_serial=Some(17) address_calls=0")
        self.reject(mutated)

    def test_terminal_comparison_uses_actual_inventory_not_last_serial(self):
        raw, contract, timing = fixture()
        # Ledger removal does not advance last_serial; all counts stay valid.
        lines = raw.splitlines(keepends=True)
        for i, line in enumerate(lines):
            if b"sequence=4 class=responses ordinal=0" in line:
                lines[i] = line.replace(b"physical: 4096, end: 4136", b"physical: 20480, end: 20520")
        parsed = owner.parse_observations(b"".join(lines))
        with self.assertRaisesRegex(owner.ObservationError, "inventories changed"):
            owner.validate_run(parsed, contract, timing)

    def test_frozen_mode_counters_ret_result_deadline_and_phase_spacing(self):
        raw, contract, timing = fixture()
        parsed = owner.parse_observations(raw)
        mutations = [lambda c, t: c.update(schema_version=True), lambda c, t: c.update(mode="automatic"), lambda c, t: c["expected_counters"]["AcceptedReturn"].update(address_calls=9), lambda c, t: c["expected_counters"]["AcceptedReturn"].update(payload_bytes=15), lambda c, t: c["expected_counters"]["BlockedRead"].update(payload_calls=False), lambda c, t: c["ret"].update(errno=0), lambda c, t: c["ret"].update(accepted=0), lambda c, t: c["ret"].update(maximum_elapsed_ns=999_999_999), lambda c, t: c["ret"].update(maximum_elapsed_ns=15_000_000_001), lambda c, t: t["phases"]["TerminalPlusFive"].update(begin_ns=10_999_999_999), lambda c, t: t["phases"]["BlockedRead"].update(end_ns=3_500_000_000), lambda c, t: t.update(clock="wall_clock"), lambda c, t: t["phases"].pop("Terminal")]
        for mutate in mutations:
            c, t = deepcopy(contract), deepcopy(timing)
            mutate(c, t)
            with self.assertRaises(owner.ObservationError):
                owner.validate_run(parsed, c, t)

    def test_tampered_parsed_result_is_rejected(self):
        raw, contract, timing = fixture()
        parsed = owner.parse_observations(raw)
        parsed["ret"]["errno"] = 0
        with self.assertRaisesRegex(owner.ObservationError, "retained bytes"):
            owner.validate_run(parsed, contract, timing)

    def test_bool_integer_alias_cannot_change_reparsed_evidence(self):
        raw, contract, timing = fixture()
        for path, replacement in [(('schema_version',), True), (('ret', 'accepted'), True), (('ret', 'key', 'os'), False), (('application_acceptance',), 0)]:
            parsed = owner.parse_observations(raw)
            container = parsed
            for key in path[:-1]:
                container = container[key]
            container[path[-1]] = replacement
            with self.subTest(path=path), self.assertRaisesRegex(owner.ObservationError, "retained bytes"):
                owner.validate_run(parsed, contract, timing)

    def test_base64_is_bounded_before_decoding(self):
        raw, contract, timing = fixture()
        parsed = owner.parse_observations(raw)
        for encoded in (b"AAAA", None, 1, "A" * 17):
            parsed["raw"]["base64"] = encoded
            with mock.patch.object(owner, "MAX_BYTES", 12), mock.patch.object(owner.base64, "b64decode", side_effect=AssertionError("must not decode")) as decode:
                with self.assertRaisesRegex(owner.ObservationError, "base64 type/encoded-size"):
                    owner.validate_run(parsed, contract, timing)
                decode.assert_not_called()

    def test_selected_worker_inventory_and_ret_cpu_are_bound(self):
        raw, _, _ = fixture()
        for old, new in [(b"index: 4, handle: 12", b"index: 4, handle: 14"), (b"handle: 12, tid: 102", b"handle: 12, tid: 103"), (b"tid: 102, delivery: Some(13)", b"tid: 102, delivery: Some(14)"), (b"completed: None", b"completed: Some(13)"), (b"value=16 cpu=1", b"value=16 cpu=2")]:
            with self.subTest(new=new):
                self.reject(raw.replace(old, new, 1))
        # Production reserve() deliberately retains the preceding completion.
        parsed = owner.parse_observations(raw.replace(b"completed: None", b"completed: Some(9)"))
        worker = next(r["row"] for r in parsed["snapshots"][0]["records"] if r["kind"] == "WORKER")
        self.assertEqual(worker["completed"], 9)

    def test_bounded_file_inputs_symlinks_fifo_and_duplicate_json(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            regular = root / "regular"
            regular.write_bytes(b"1234")
            self.assertEqual(owner.read_artifact(regular, 4)[0], b"1234")
            with self.assertRaises(owner.ObservationError):
                owner.read_artifact(regular, 3)
            link = root / "link"
            link.symlink_to(regular)
            with self.assertRaises(OSError):
                owner.read_artifact(link)
            fifo = root / "fifo"
            os.mkfifo(fifo)
            with self.assertRaises(owner.ObservationError):
                owner.read_artifact(fifo)
        with self.assertRaises(owner.ObservationError):
            owner.load_json(b'{"version":1,"version":2}')
        with self.assertRaises(owner.ObservationError):
            owner.load_json(b'{"version":NaN}')

    def test_cli_retains_rejected_capture_and_creates_immutable_result(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            raw, _, _ = fixture()
            raw = raw[:-1]
            log, output = root / "serial.log", root / "result.json"
            log.write_bytes(raw)
            run = subprocess.run([sys.executable, str(MODULE), "--log", str(log), "--output", str(output)], stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=5)
            self.assertEqual(run.returncode, 1)
            result = json.loads(output.read_text())
            self.assertEqual(result["status"], "REJECTED_OBSERVATIONS")
            self.assertEqual(base64.b64decode(result["raw"]["base64"]), raw)
            original = output.read_bytes()
            again = subprocess.run([sys.executable, str(MODULE), "--log", str(log), "--output", str(output)], stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=5)
            self.assertNotEqual(again.returncode, 0)
            self.assertEqual(output.read_bytes(), original)


if __name__ == "__main__":
    unittest.main()
