import copy
import hashlib
import importlib.util
import io
import json
import os
import struct
import subprocess
import shutil
import tarfile
import tempfile
import types
import unittest
from pathlib import Path
from unittest import mock

HERE = (Path(__file__).resolve().parent /
        "fixtures/application-collector-v1/linux-sealed-v1/storage-fault-v1")
ROOT_ARCHIVE = (Path(__file__).resolve().parents[2] / "docs/verification/evidence/"
    "stability-linux-collector-root-success-20260915-2.tar.gz")
ROOT_PREFIX = ("stability-linux-sealed-root-tests-20260913-2/work/cases/"
               "stdin-devnull/inputs/")

def retained(name):
    with tarfile.open(ROOT_ARCHIVE, "r:gz") as archive:
        return archive.extractfile(ROOT_PREFIX + name).read()

def module(name):
    spec = importlib.util.spec_from_file_location("storage_fault_v2_" + name,
                                                  HERE / (name + ".py"))
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value

prepare = module("prepare")
oracle = module("oracle")
owner = module("witness_owner")
supervise = module("supervise")

class StorageFaultV2SourceTests(unittest.TestCase):
    SOURCE_SHA = "09a63a343fa8cc9f511a26693371f5ba4f55ac5ca56fcb47abdc44759830cf1f"
    COUNTS = [22, 10, 17, 22, 17, 22, 17]
    WAITS = [0, 256, 256, 256, 32000, 32000, 32000]
    PHASES = ["post-fork", "pre-fork", "pre-fork", "post-fork",
              "post-fork", "post-fork", "pre-fork"]
    HASHES = {"generated_sha256": "a" * 64,
              "header_sha256": "b" * 64, "elf_sha256": "c" * 64}
    NONCE = "d" * 32

    def setUp(self):
        self.paths = [HERE / name for name in (
            "packet.json", "prepare.py", "inject.h", "collector.patch",
            "oracle.py", "witness_owner.py", "supervise.py", "tests.md")]
        self.paths += [HERE.parent / "collector.c"]
        self.hashes = {path: hashlib.sha256(path.read_bytes()).hexdigest()
                       for path in self.paths}

    def tearDown(self):
        self.assertEqual({path: hashlib.sha256(path.read_bytes()).hexdigest()
                          for path in self.paths}, self.hashes)

    def test_packet_source_and_exact_generated_diff(self):
        record = prepare.packet((HERE / "packet.json").resolve())
        self.assertEqual([case["selector"] for case in record["cases"]],
                         list(range(7)))
        self.assertEqual([case["witness_packets"] for case in record["cases"]],
                         self.COUNTS)
        self.assertTrue(all(count < 32 for count in self.COUNTS))
        raw = prepare.read(prepare.SOURCE)
        self.assertEqual(hashlib.sha256(raw).hexdigest(), self.SOURCE_SHA)
        generated = prepare.generate(raw)
        patch = prepare.diff(raw, generated)
        self.assertEqual(patch, (HERE / "collector.patch").read_bytes())
        self.assertEqual(generated.count(b'#include "storage-fault-v1/inject.h"'), 1)
        for token, count in {
            b"sf_open(SF_EVENTS_CREATE": 1,
            b"sf_write(SF_REQUEST": 1,
            b"sf_sync(SF_REQUEST_SYNC": 1,
            b"sf_open(SF_REPORT_CREATE": 1,
            b"sf_flush(fd, f)": 1,
            b"sf_sync(SF_REPORT_SYNC": 1,
            b"sf_observe_reap": 1,
            b"sf_observe_eof": 1,
            b"sf_observe_cleanup_ready": 1,
            b"sf_observe_cleanup_final": 1,
            b"sf_startup()": 1,
            b"sf_child_close()": 1,
        }.items():
            self.assertEqual(generated.count(token), count, token)
        self.assertNotIn(b"#define open", generated)
        self.assertNotIn(b"#define write", generated)
        self.assertNotIn(b"#define fsync", generated)
        with self.assertRaisesRegex(ValueError, "collector hash"):
            prepare.generate(raw + b"\n")

    def test_header_protocol_and_target_only_contract(self):
        header = (HERE / "inject.h").read_text()
        for token in (
            "M02_STORAGE_FAULT_TEST_ONLY != 1", "M02_STORAGE_FAULT_CASE > 6",
            "SF_WITNESS_FD 198", "SF_PACKET_MAX 4096", "SF_PACKET_LIMIT 32",
            '"RELEASE %s\\n"', '"ACK %s %u\\n"', "packet_sequence",
            "deadline - now", "sf_sequence = 1",
            "sf_acquisition_next", "sf_open_stat_valid", "SOCK_SEQPACKET",
            "sf_observe_reap", "sf_observe_eof", "sf_observe_cleanup_ready",
            "sf_observe_cleanup_final", "sf_observe_setup", "sf_transport_failed"):
            self.assertIn(token, header)
        self.assertEqual(header.count("static int sf_open("), 1)
        self.assertEqual(header.count("static ssize_t sf_write("), 1)
        self.assertEqual(header.count("static int sf_sync("), 1)
        self.assertEqual(header.count("static int sf_flush("), 1)
        self.assertNotIn("#define open", header)
        self.assertNotIn("#define write", header)
        self.assertNotIn("#define fsync", header)

    def test_prepare_fresh_root_durability_and_stable_rejection(self):
        unexpected = RuntimeError("execution forbidden")
        with tempfile.TemporaryDirectory() as temporary, \
             mock.patch.object(subprocess, "run", side_effect=unexpected) as run_call, \
             mock.patch.object(subprocess, "Popen", side_effect=unexpected) as popen_call, \
             mock.patch.object(owner, "launch", side_effect=unexpected) as launch_call:
            root = (Path(temporary) / "attempt").resolve()
            result = prepare.prepare((HERE / "packet.json").resolve(), root)
            self.assertEqual(result["status"], "PREPARED_NOT_BUILT")
            self.assertFalse(result["backend_enabled"] or result["application_acceptance"])
            self.assertEqual(set(result["source_bindings"]),
                             {"supervisor", "owner", "oracle"})
            for name, binding in result["source_bindings"].items():
                source_path = prepare.SOURCE_PROGRAMS[name].resolve()
                self.assertEqual(binding, {"path": str(source_path),
                    "size": source_path.stat().st_size,
                    "sha256": hashlib.sha256(source_path.read_bytes()).hexdigest()})
            expected = {"source.collector.c", "storage-fault-v2-collector.c",
                        "inject.h", "generated.diff", "prepare.json"}
            self.assertEqual({path.name for path in root.iterdir()}, expected)
            before = {path.name: hashlib.sha256(path.read_bytes()).hexdigest()
                      for path in root.iterdir()}
            with self.assertRaisesRegex(FileExistsError, "attempt root exists"):
                prepare.prepare((HERE / "packet.json").resolve(), root)
            self.assertEqual({path.name: hashlib.sha256(path.read_bytes()).hexdigest()
                              for path in root.iterdir()}, before)
            run_call.assert_not_called()
            popen_call.assert_not_called()
            launch_call.assert_not_called()

    def test_prepare_parent_open_failure_closes_attempt_descriptor(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = (Path(temporary) / "attempt").resolve()
            def fake_read(path, limit=1 << 20):
                name = Path(path).name
                return b"patch" if name == "collector.patch" else \
                    b"header" if name == "inject.h" else b"source"
            record = {"cases": [{"selector": 0}]}
            with mock.patch.object(prepare, "packet", return_value=record), \
                 mock.patch.object(prepare, "read", side_effect=fake_read), \
                 mock.patch.object(prepare, "generate", return_value=b"generated"), \
                 mock.patch.object(prepare, "diff", return_value=b"patch"), \
                 mock.patch.object(prepare, "source_bindings", return_value={}), \
                 mock.patch.object(prepare, "write_complete"), \
                 mock.patch.object(prepare.os, "open",
                    side_effect=[3, OSError("parent open")]), \
                 mock.patch.object(prepare.os, "close") as close_call:
                with self.assertRaisesRegex(OSError, "parent open"):
                    prepare.prepare((HERE / "packet.json").resolve(), root)
            close_call.assert_called_once_with(3)

    def packet(self, selector, sequence, kind, phase=None, **extra):
        hashes = getattr(self, "active_hashes", self.HASHES)
        value = {"schema_version": 2, "nonce": self.NONCE,
                 "selector": selector, "sequence": sequence, "kind": kind,
                 "phase": phase or self.PHASES[selector],
                 "monotonic_ns": 1000 if kind == "READY" else 3000 + 100 * sequence,
                 "site": "startup" if kind == "READY" else "observation",
                 "object": "collector", "occurrence": 0,
                 "collector_pid": 50,
                 "collector_startticks": 60, "source_sha256": self.SOURCE_SHA,
                 "generated_sha256": hashes["generated_sha256"],
                 "header_sha256": hashes["header_sha256"],
                 "elf_sha256": hashes["elf_sha256"]}
        value.update(extra)
        return value

    def packets(self, selector, report_size=128):
        def pair(site, object_name, occurrence=1):
            return [("BEFORE", site, object_name, occurrence),
                    ("AFTER", site, object_name, occurrence)]
        e, w1, w2 = pair("events-create", "events.jsonl"), \
            pair("request-write", "request.bin"), pair("request-write", "request.bin", 2)
        eb = [("BIND", "events-create", "events.jsonl", 1)]
        a, r = pair("request-sync", "request.bin"), pair("report-create", "report.json")
        rb = [("BIND", "report-create", "report.json", 1)]
        f, s = pair("report-flush", "report.json"), pair("report-sync", "report.json")
        observations = [("REAP", "reap", "leader", 1),
            ("EOF", "pump", "stdout", 1), ("EOF", "pump", "stderr", 2),
            ("EOF", "pump", "setup", 3),
            ("CLEANUP_READY", "cleanup", "owned-tree", 1),
            ("CLEANUP_FINAL", "cleanup", "owned-tree", 1),
            ("SETUP", "setup", "collector", 1)]
        body = {0:e+eb+w1+observations+a+r+rb+f+s, 1:e+r+rb+f+s,
            2:e+eb+w1+w2+a+r+rb+f+s, 3:e+eb+w1+observations+a+r+rb+f+s,
            4:e+eb+w1+observations+a+r, 5:e+eb+w1+observations+a+r+rb+f+s,
            6:e+eb+w1+w2+a+r+rb+f+s}[selector]
        signatures = [("READY", "startup", "collector", 0)] + body
        values, request_size = [], 0
        stat_ids = {"events.jsonl": (10, 100), "request.bin": (11, 101),
                    "report.json": (12, 102)}
        def stat_value(object_name, size):
            return {"dev": 1, "ino": stat_ids[object_name][1],
                    "mode": 0o100600, "size": size}
        for kind, site, object_name, occurrence in signatures:
            phase = "pre-fork" if kind == "READY" or site in (
                "events-create", "request-write") or selector in (1, 2, 6) \
                else "post-fork"
            extra = {"site": site, "object": object_name, "occurrence": occurrence}
            if kind in ("BEFORE", "AFTER") and site in ("events-create", "report-create"):
                failed = (site == "events-create" and selector == 1) or \
                         (site == "report-create" and selector == 4)
                acquisition = 1 if site == "events-create" or selector == 1 else 2
                extra.update({"dirfd": 5, "dir_stat": {"dev": 1, "ino": 90,
                    "mode": 0o40700, "size": 0}})
                if kind == "BEFORE":
                    extra.update({"fd": None, "target_stat": None,
                        "acquisition_id": None, "return": None,
                        "errno_authoritative": False, "errno": None})
                elif failed:
                    extra.update({"fd": None, "target_stat": None,
                        "acquisition_id": None, "return": -1,
                        "errno_authoritative": True, "errno": 28})
                else:
                    fd = stat_ids[object_name][0]
                    extra.update({"fd": fd, "target_stat": stat_value(object_name, 0),
                        "acquisition_id": acquisition, "return": fd,
                        "errno_authoritative": False, "errno": None})
            elif kind == "BIND":
                acquisition = 1 if site == "events-create" or selector == 1 else 2
                fd = stat_ids[object_name][0]
                extra.update({"acquisition_id": acquisition, "old_fd": fd,
                    "old_stat": stat_value(object_name, 0), "new_fd": fd,
                    "new_stat": stat_value(object_name, 0)})
            elif site == "request-write":
                requested = 406 if occurrence == 1 else 399
                before_size = 0 if occurrence == 1 else 7
                injected = selector in (2, 6)
                result = 7 if injected and occurrence == 1 else -1 if occurrence == 2 else 406
                after_size = 7 if injected else 406
                extra.update({"fd": 11, "target_stat": stat_value("request.bin",
                    before_size if kind == "BEFORE" else after_size),
                    "acquisition_id": 0, "requested_bytes": requested,
                    "return": None if kind == "BEFORE" else result,
                    "errno_authoritative": kind == "AFTER" and result < 0,
                    "errno": 28 if kind == "AFTER" and result < 0 else None})
                if kind == "AFTER":
                    extra["actual_bytes"] = max(result, 0); request_size = after_size
            elif site in ("request-sync", "report-flush", "report-sync"):
                is_request = site == "request-sync"
                size = request_size if is_request else (0 if kind == "BEFORE" and
                    site == "report-flush" else report_size)
                failed = kind == "AFTER" and ((site == "request-sync" and selector in (3, 6)) or
                    (site == "report-sync" and selector in (5, 6)))
                extra.update({"fd": 11 if is_request else 12,
                    "target_stat": stat_value("request.bin" if is_request else "report.json", size),
                    "acquisition_id": 0 if is_request else (1 if selector == 1 else 2),
                    "return": None if kind == "BEFORE" else (-1 if failed else 0),
                    "errno_authoritative": failed, "errno": 5 if failed else None})
            elif kind == "REAP":
                extra.update({"pid": 70, "startticks": 80, "raw_wait_status": 0})
            elif kind == "EOF":
                extra["closed_fd"] = 20 + occurrence
            elif kind == "CLEANUP_READY":
                extra.update({"waitid_return": -1, "waitid_errno": 10,
                    "leader_reaped": True, "stdout_eof": True,
                    "stderr_eof": True, "setup_eof": True})
            elif kind == "CLEANUP_FINAL":
                extra.update({"cleanup_start_ns": 3500,
                    "cleanup_deadline_ns": 15000003500,
                    "cleanup_finished_ns": 3800, "cleanup_complete": True,
                    "group_pinned": True, "owned_count": 0,
                    "owned_records_omitted": 0, "first_failure": "none",
                    "first_failure_errno": 0})
            elif kind == "SETUP":
                extra.update({"setup_words": [827081537, 1, 1, 1, 0, 70, 50, 70, 70,
                    0, 0, 0, 0, 1, 0, 0o22, 1, 300, 0o20666, 1, 203,
                    0o10600, 1, 301, 0o10600, 1, 302, 1, 202, 15, 0,
                    0, 1, 1, 0, 0, 0, 1] + [0] * 10,
                    "cwd_stat": {"dev": 1, "ino": 300, "mode": 0o40700, "size": 0},
                    "stdin_stat": {"dev": 1, "ino": 203, "mode": 0o20666, "size": 0},
                    "stdout_pipe_stat": {"dev": 1, "ino": 301, "mode": 0o10600, "size": 0},
                    "stderr_pipe_stat": {"dev": 1, "ino": 302, "mode": 0o10600, "size": 0},
                    "executable_backing": {"dev": 1, "ino": 202, "mode": 0o100500, "size": 27448},
                    "executable_seals": 15, "leader_pid": 70, "leader_startticks": 80})
            values.append(self.packet(selector, len(values), kind, phase=phase, **extra))
        self.assertEqual(len(values), self.COUNTS[selector])
        return values

    def write_fixture(self, root, selector):
        root.mkdir()
        collection = root / "collection"
        collection.mkdir()
        report_status = oracle.EXPECTED[selector]
        retained_root = root / "retained-inputs"; retained_root.mkdir()
        original_request = retained("request.bin")
        selected = retained("selected-inputs.json")
        stimulus = retained("fixture")
        (retained_root / "request.bin").write_bytes(original_request)
        (retained_root / "selected-inputs.json").write_bytes(selected)
        (retained_root / "fixture").write_bytes(stimulus)
        source = root / "collector.c"; source.write_bytes(prepare.SOURCE.read_bytes())
        generated = root / "generated.c"; generated.write_bytes(b"synthetic generated source\n")
        header = root / "inject.h"; header.write_bytes((HERE / "inject.h").read_bytes())
        elf = root / "collector.elf"; elf.write_bytes(b"synthetic collector ELF\n")
        self.active_hashes = {"generated_sha256": hashlib.sha256(generated.read_bytes()).hexdigest(),
            "header_sha256": hashlib.sha256(header.read_bytes()).hexdigest(),
            "elf_sha256": hashlib.sha256(elf.read_bytes()).hexdigest()}
        post = selector in (0, 3, 4, 5)
        setup_values = ([827081537, 1, 1, 1, 0, 70, 50, 70, 70,
            0, 0, 0, 0, 1, 0, 0o22, 1, 300, 0o20666, 1, 203,
            0o10600, 1, 301, 0o10600, 1, 302, 1, 202, 15, 0,
            0, 1, 1, 0, 0, 0, 1] + [0] * 10) if post else [0] * 48
        if report_status[2] != "absent":
            def report_stat(mode=0o100600, size=0, inode=201):
                return {"device": 1, "inode": inode, "mode": mode, "uid": 0,
                    "gid": 0, "size": size, "nlink": 1, "mtime_seconds": 1,
                    "mtime_nanoseconds": 2, "ctime_seconds": 1,
                    "ctime_nanoseconds": 2}
            def sink(name=None, seen=0, stored=0, io_error=False, raw=b""):
                if name is None:
                    return None
                limits = {"request.bin": 65537, "selected-inputs.bin": 4194304,
                    "argv.nul": 65536, "env.nul": 65536, "events.jsonl": 65536,
                    "executable.verified.bin": 1048576, "stdout.bin": 65536,
                    "stderr.bin": 65536, "setup.bin": 768}
                return {"attempted_name": name, "created": True,
                    "fd_available": True, "creation_errno": 0, "fd_errno": 0,
                    "path": name, "limit_bytes": limits[name],
                    "seen_bytes": seen, "stored_bytes": stored,
                    "truncated": False, "io_error": io_error,
                    "sha256": hashlib.sha256(raw).hexdigest()}
            def failed_sink(name, error):
                return {"attempted_name": name, "created": False,
                    "fd_available": False, "creation_errno": error,
                    "fd_errno": 0, "path": None, "limit_bytes": 65536,
                    "seen_bytes": 0, "stored_bytes": 0, "truncated": False,
                    "io_error": False, "sha256": None}
            def source_record(opened):
                return {"opened": opened, "stable": opened, "verified": opened,
                    "source_before": report_stat(mode=0o100755,
                        size=len(stimulus), inode=201) if opened else None,
                    "source_after": report_stat(mode=0o100755,
                        size=len(stimulus), inode=201) if opened else None,
                    "sealed_backing": report_stat(mode=0o100500,
                        size=len(stimulus), inode=202) if opened else None,
                    # json_source() leaves an unopened source entirely empty;
                    # DEVNULL is opened for use but is not a sealed source.
                    "requested_memfd_flags": 3,
                    "seals": 15 if opened else 0,
                    "artifact": sink("executable.verified.bin", len(stimulus),
                        len(stimulus), False, stimulus) if opened else None}
            request_valid = selector not in (1, 2, 6)
            request_bytes = oracle.PREFIX if selector in (2, 6) else original_request
            request_sink = None if selector == 1 else sink("request.bin", 406,
                len(request_bytes), selector in (2, 6), request_bytes)
            artifacts = [request_sink, sink("selected-inputs.bin") if request_valid else None,
                sink("argv.nul") if request_valid else None,
                sink("env.nul") if request_valid else None,
                failed_sink("events.jsonl", 28) if selector == 1
                    else sink("events.jsonl"),
                sink("executable.verified.bin", len(stimulus), len(stimulus),
                    False, stimulus) if post else None, None,
                sink("stdout.bin") if post else None,
                sink("stderr.bin") if post else None,
                sink("setup.bin") if post else None]
            desired = None if not request_valid else {"role": 1,
                "request_profile": 1, "uid": 0, "gid": 0, "group": 0,
                "umask": 18, "argc": 2, "envc": 0, "stdin_mode": 0,
                "case_id_hex": "696e6672617374727563747572652e636f6c6c6563746f72",
                "source_selector_hex": "2f776f726b2f63617365732f737464696e2d6465766e756c6c2f696e707574732f66697874757265",
                "cwd_hex": "2f776f726b2f63617365732f737464696e2d6465766e756c6c2f637764",
                "stdin_selector_hex": "2f6465762f6e756c6c",
                "attempt_id_hex": "b9e7824e46f727250a6a80c8fcfc9359",
                "selected_inputs_sha256": oracle.SELECTED_SHA}
            report = {"schema_version": 1,
                "kind": "linux-sealed-infrastructure-collection",
                "collector_mode": "linux-sealed-infrastructure-v1",
                "status": report_status[3], "first_failure": report_status[4],
                "first_failure_errno": report_status[5],
                "application_acceptance": False, "transport_acceptance": False,
                "backend_enabled": False, "collector_pid": 50,
                "request_valid": request_valid, "child_created": post,
                "linux_child": {"pid": 70, "identity_observed": True,
                    "ppid": 50, "pgid_at_observation": 70,
                    "sid_at_observation": 70, "startticks": 80,
                    "kill_sent": False, "reaped": True, "raw_wait_status": 0,
                    "wait": {"exited": True, "signaled": False,
                        "exit_code": 0, "signal": None, "core_dumped": False}}
                    if post else None,
                "cleanup_start_ns": 3500 if post else 0,
                "cleanup_deadline_ns": 15000003500 if post else 0,
                "cleanup_finished_ns": 3800 if post else 0,
                "cleanup_complete": post, "group_identity_pinned": post,
                "owned_records_omitted": 0, "owned_children": [],
                "streams": {"stdout_eof": selector in (0, 3, 4, 5),
                    "stderr_eof": selector in (0, 3, 4, 5),
                    "setup_eof": selector in (0, 3, 4, 5)}}
            report.update({"first_failure_monotonic_ns": 0 if report_status[4] == "none"
                else 3950 if selector == 3 else 2300,
                "pathname_execution": False, "loader_closure_verified": False,
                "native_payload": None, "collector_uid": 0,
                "collector_euid": 0, "collector_interruption_signal": 0,
                "desired": desired,
                "configured_execution_mechanism": "execveat-AT_EMPTY_PATH-sealed-memfd",
                "setup_ready_record": selector in (0, 3, 4, 5),
                "setup_error_record": False,
                "setup_validated": selector in (0, 3, 4, 5),
                "setup_words": setup_values,
                "post_exec_backing_observed": post,
                "post_exec_observed_monotonic_ns": 2700 if post else 0,
                "post_exec_backing": report_stat(mode=0o100500,
                    size=len(stimulus), inode=202) if post else None,
                "subsequent_proc_exe_link_sample": None,
                "preparation_start_ns": 2110,
                "preparation_deadline_ns": 120000002110,
                "process_start_ns": 2600 if post else 0,
                "process_deadline_ns": 10000002600 if post else 0,
                "completion_observed_ns": 3400 if post else 0,
                "executable": source_record(post), "stdin": source_record(False),
                "devnull_identity": report_stat(mode=0o20666, inode=203)
                    if post else None, "artifacts": artifacts})
            (collection / "report.json").write_text(
                json.dumps(report, sort_keys=True, separators=(",", ":")))
        request = oracle.PREFIX if selector in (2, 6) else original_request
        if selector != 1: (collection / "request.bin").write_bytes(request)
        if selector != 1:
            event_values = [{"monotonic_ns": 2200, "event": "collector-start", "pid": 50}]
            if post:
                event_values += [
                    {"monotonic_ns": 2600, "event": "child-created", "pid": 70,
                     "startticks": 80},
                    {"monotonic_ns": 2700, "event": "observed-sealed-exe", "pid": 70},
                    {"monotonic_ns": 3400, "event": "leader-waitable", "pid": 70},
                    {"monotonic_ns": 3600, "event": "owned-group-kill-attempt",
                     "pgid": 70, "leader_startticks": 80},
                    {"monotonic_ns": 3700, "event": "actual-reap", "pid": 70,
                     "raw_wait_status": 0}]
            event_values.append({"monotonic_ns": 3900 if post else 2400,
                "event": "collector-finish",
                "first_failure": "artifact-write" if selector in (2, 6) else "none"})
            (collection / "events.jsonl").write_bytes(b"".join(
                json.dumps(value, sort_keys=True, separators=(",", ":")).encode() + b"\n"
                for value in event_values))
            if post:
                (collection / "selected-inputs.bin").write_bytes(selected)
                (collection / "argv.nul").write_bytes(b"literal-app\x00stdin-devnull\x00")
                (collection / "env.nul").write_bytes(b"")
                (collection / "executable.verified.bin").write_bytes(stimulus)
                (collection / "stdout.bin").write_bytes(b"DEVNULL\n" if post else b"")
                (collection / "stderr.bin").write_bytes(b"")
                (collection / "setup.bin").write_bytes(struct.pack(
                    "<" + "Q" * len(setup_values), *setup_values))
            if (collection / "report.json").exists():
                report_value = json.loads((collection / "report.json").read_text())
                for artifact in report_value["artifacts"]:
                    if artifact is None or not artifact["created"]:
                        continue
                    artifact_path = collection / artifact["path"]
                    if artifact_path.exists():
                        artifact_raw = artifact_path.read_bytes()
                        if not artifact["io_error"]:
                            artifact["seen_bytes"] = len(artifact_raw)
                        artifact["stored_bytes"] = len(artifact_raw)
                        artifact["sha256"] = hashlib.sha256(artifact_raw).hexdigest()
                (collection / "report.json").write_text(json.dumps(
                    report_value, sort_keys=True, separators=(",", ":")))
        (root / "stdout.bin").write_bytes(b"")
        (root / "stderr.bin").write_bytes(b"")
        (root / "owner-errors.jsonl").write_bytes(b"")
        def record(path, shown=None):
            if not path.exists():
                return {"path": str(shown or path), "present": False,
                        "size": None, "sha256": None}
            raw = path.read_bytes()
            return {"path": str(shown or path), "present": True,
                    "size": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}
        hashes = {"source_sha256": self.SOURCE_SHA, **self.active_hashes}
        environment = owner.effective_environment(self.NONCE, hashes)
        packet_values = self.packets(selector,
            (collection / "report.json").stat().st_size if
            (collection / "report.json").exists() else 0)
        receipts = [2000 if index == 0 else packet["monotonic_ns"] + 1
                    for index, packet in enumerate(packet_values)]
        first_postfork_receipt = next((receipts[index] for index, packet in
            enumerate(packet_values) if packet["phase"] == "post-fork"), None)
        argv = [str(elf), "--linux-sealed-infrastructure-v1",
                str(retained_root / "request.bin"),
                str(retained_root / "selected-inputs.json"), str(collection)]
        cleanup = {"complete": True, "trigger_kind": "normal-eof",
            "trigger_ns": 6000, "cleanup_start_ns": 6100,
            "cleanup_deadline_ns": 22000006000, "cleanup_finished_ns": 6600,
            "events": [{"kind": "wait", "pid": 50, "startticks": 60,
                "raw_wait_status": self.WAITS[selector], "direct": True,
                "monotonic_ns": 6200},
                {"kind": "owned-scan", "monotonic_ns": 6300, "pids": []},
                {"kind": "owned-scan", "monotonic_ns": 6400, "pids": []},
                {"kind": "echild", "monotonic_ns": 6500,
                 "return": -1, "errno": 10}],
            "adopted_reaps": [], "unresolved": []}
        owner_result = {"schema_version": 2, "kind": "OWNER_RESULT",
            "nonce": self.NONCE, "selector": selector, "argv": argv,
            "owner": {"pid": 40, "startticks": 30}, "environment": environment,
            "collector": {"pid": 50, "identity_observed": True, "ppid": 40,
                "startticks": 60, "reaped": True,
                "raw_wait_status": self.WAITS[selector]},
            "packet_count": self.COUNTS[selector], "hashes": hashes,
            "inputs": {"source": record(source), "generated_source": record(generated),
                "header": record(header), "elf": record(elf)},
            "runtime_inputs": {
                "request": {"source_path": "/original/request.bin",
                    "destination_path": str(retained_root / "request.bin"),
                    "size": 406, "sha256": oracle.REQUEST_SHA},
                "selected_inputs": {"source_path": "/original/selected-inputs.json",
                    "destination_path": str(retained_root / "selected-inputs.json"),
                    "size": 76, "sha256": oracle.SELECTED_SHA},
                "fixture": {"source_path": "/work/cases/stdin-devnull/inputs/fixture",
                    "destination_path": str(retained_root / "fixture"),
                    "size": 27448, "sha256": oracle.FIXTURE_SHA}},
            "captures": {"stdout": record(root / "stdout.bin", "stdout.bin"),
                "stderr": record(root / "stderr.bin", "stderr.bin")},
            "artifacts": {"events": record(collection / "events.jsonl"),
                "request": record(collection / "request.bin"),
                "report": record(collection / "report.json")},
            "owner_failure": None, "secondary_failures": [],
            "result_serialized_ns": 7000, "cleanup": cleanup,
            "deadlines": {"owner_start_ns": 500,
                "ready_deadline_ns": 10000000500,
                "release_send_start_ns": 2100,
                "collection_deadline_ns": 180000002100,
                "first_postfork_receipt_ns": first_postfork_receipt,
                "postfork_deadline_ns": first_postfork_receipt + 60000000000
                    if first_postfork_receipt is not None else None,
                "cleanup_trigger_ns": 6000,
                "cleanup_deadline_ns": 22000006000},
            "backend_enabled": False, "application_acceptance": False}
        (root / "owner-result.json").write_text(json.dumps(
            owner_result, sort_keys=True, separators=(",", ":")) + "\n")
        rows = [{"packet": packet, "receipt_monotonic_ns": receipts[index]}
                for index, packet in enumerate(packet_values)]
        rows.append({"packet": owner_result,
                     "receipt_monotonic_ns": 7100})
        (root / "witness.jsonl").write_bytes(b"".join(
            json.dumps(row, sort_keys=True, separators=(",", ":")).encode() + b"\n"
            for row in rows))
        (root / "owner-supervisor.stdout.bin").write_bytes(b"")
        (root / "owner-supervisor.stderr.bin").write_bytes(b"")
        def digest(filename):
            return hashlib.sha256((root / filename).read_bytes()).hexdigest()
        supervisor_result = {
            "schema_version": 1, "kind": "STORAGE_FAULT_V2_SUPERVISOR",
            "supervisor_pid": 20,
            "status": "COMPLETE", "owner_exit_code": 0, "owner_signal": None,
            "started_ns": 300, "finished_ns": 7600, "attempt_root": str(root),
            "owner_result_present": True,
            "owner_result_sha256": digest("owner-result.json"),
            "witness_present": True, "witness_sha256": digest("witness.jsonl"),
            "owner_errors_present": True,
            "owner_errors_sha256": digest("owner-errors.jsonl"),
            "owner_stdout_sha256": digest("owner-supervisor.stdout.bin"),
            "owner_stderr_sha256": digest("owner-supervisor.stderr.bin"),
            "owner_identity": {"state": "MATCHED", "pid": 40, "ppid": 20,
                "startticks": 30, "spawn_error": None},
            "owner_identity_observations": [
                {"observation": "observed", "pid": 40, "ppid": 20,
                 "startticks": 30, "monotonic_ns": 400},
                {"observation": "observed", "pid": 40, "ppid": 20,
                 "startticks": 30, "monotonic_ns": 500}],
            "owner_wait_observed": True,
            "owner_wait_deadline_ns": 220000000300,
            "cleanup_trigger_ns": 7200,
            "supervisor_cleanup_deadline_ns": 22000007200,
            "supervisor_deadline_ns": 248000000300,
            "supervisor_cleanup": {"complete": True, "unresolved": [],
                "events": [
                    {"kind": "wait", "pid": 40, "startticks": 30,
                     "raw_wait_status": 0, "direct": True,
                     "monotonic_ns": 7200},
                    {"kind": "owned-scan", "monotonic_ns": 7300, "pids": []},
                    {"kind": "owned-scan", "monotonic_ns": 7400, "pids": []},
                    {"kind": "echild", "monotonic_ns": 7500,
                     "return": -1, "errno": 10}]},
            "sigchld_default": True, "sentinel_wait_passed": True,
            "preflight_failure": None, "preflight_started_ns": 100,
            "sentinel_wait_deadline_ns": 5000000100}
        (root / "supervisor-result.json").write_text(json.dumps(
            supervisor_result, sort_keys=True, separators=(",", ":")) + "\n")

    def mutate(self, selector, mutation, message, exception=ValueError):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "case"
            self.write_fixture(root, selector)
            mutation(root)
            self.refresh_supervisor(root)
            with self.assertRaises(exception) as raised:
                oracle.validate(root, selector, 0)
            self.assertEqual(str(raised.exception), message)

    def test_oracle_seven_positive_fixtures(self):
        unexpected = RuntimeError("execution forbidden")
        with mock.patch.object(subprocess, "run", side_effect=unexpected) as run_call, \
             mock.patch.object(subprocess, "Popen", side_effect=unexpected) as popen_call, \
             mock.patch.object(owner.os, "fork", side_effect=unexpected) as fork_call:
            for selector in range(7):
                with self.subTest(selector=selector), tempfile.TemporaryDirectory() as temporary:
                    root = Path(temporary) / "case"
                    self.write_fixture(root, selector)
                    self.assertTrue(oracle.validate(root, selector, 0))
            run_call.assert_not_called()
            popen_call.assert_not_called()
            fork_call.assert_not_called()

    def test_fixture_chronology_all_seven(self):
        for selector in range(7):
            with self.subTest(selector=selector), \
                 tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary) / "case"
                self.write_fixture(root, selector)
                rows = [json.loads(line) for line in
                        (root / "witness.jsonl").read_text().splitlines()]
                owner_result = json.loads((root / "owner-result.json").read_text())
                packets = rows[:-1]
                self.assertEqual(packets[0]["packet"]["kind"], "READY")
                self.assertEqual((packets[0]["packet"]["monotonic_ns"],
                                  packets[0]["receipt_monotonic_ns"]), (1000, 2000))
                for row in packets[1:]:
                    self.assertEqual(row["receipt_monotonic_ns"],
                                     row["packet"]["monotonic_ns"] + 1)
                    self.assertGreater(row["packet"]["monotonic_ns"], 2100)
                first_post = next((row["receipt_monotonic_ns"] for row in packets
                    if row["packet"]["phase"] == "post-fork"), None)
                deadlines = owner_result["deadlines"]
                self.assertEqual(deadlines["release_send_start_ns"], 2100)
                self.assertEqual(deadlines["first_postfork_receipt_ns"], first_post)
                self.assertEqual(deadlines["postfork_deadline_ns"],
                    min(deadlines["collection_deadline_ns"], first_post + 60000000000)
                    if first_post is not None else None)
                self.assertLess(max(row["receipt_monotonic_ns"] for row in packets),
                                owner_result["cleanup"]["trigger_ns"])
                self.assertLess(owner_result["cleanup"]["cleanup_finished_ns"],
                                owner_result["result_serialized_ns"])
                self.assertLess(owner_result["result_serialized_ns"],
                                rows[-1]["receipt_monotonic_ns"])
                report_path = root / "collection/report.json"
                if report_path.exists():
                    report = json.loads(report_path.read_text())
                    self.assertGreater(report["preparation_start_ns"], 2100)
                    if report["first_failure_monotonic_ns"]:
                        self.assertGreater(report["first_failure_monotonic_ns"],
                                           report["preparation_start_ns"])
                    if report["child_created"]:
                        self.assertLess(report["process_start_ns"],
                                        report["completion_observed_ns"])
                        self.assertLessEqual(report["cleanup_start_ns"],
                                             report["cleanup_finished_ns"])
                events_path = root / "collection/events.jsonl"
                if events_path.exists():
                    times = [json.loads(line)["monotonic_ns"] for line in
                             events_path.read_text().splitlines()]
                    self.assertEqual(times, sorted(times))
                    self.assertGreater(times[0], 2100)
                    self.assertLess(times[-1], owner_result["cleanup"]["trigger_ns"])

    def test_exact_schedule_and_pre_ack_schema_for_all_selectors(self):
        for selector in range(7):
            packets = self.packets(selector)
            state = owner.PacketState(selector)
            self.assertEqual(len(packets), self.COUNTS[selector])
            for index, packet in enumerate(packets):
                owner.validate_packet_schema(packet, selector)
                owner.validate_schedule_prefix(packets[:index + 1], selector)
                state.validate(packet)
            signatures = [(packet["kind"], packet["site"], packet["object"],
                           packet["occurrence"]) for packet in packets]
            self.assertIn(signatures, oracle.schedule_variants(selector))

    def test_pre_ack_rejects_wrong_phase_null_stat_and_boolean_fd(self):
        packet = next(value for value in self.packets(0) if
                      value["kind"] == "BEFORE" and
                      value["site"] == "request-write")
        for field, replacement, message in (
                ("phase", "post-fork", "witness phase"),
                ("target_stat", None, "witness write types"),
                ("fd", True, "witness write types")):
            changed = copy.deepcopy(packet)
            changed[field] = replacement
            with self.assertRaises(ValueError) as raised:
                owner.validate_packet_schema(changed, 0)
            self.assertEqual(str(raised.exception), message)
        changed = copy.deepcopy(packet)
        changed["acquisition_id"] = False
        with self.assertRaisesRegex(ValueError, "witness write types"):
            owner.validate_packet_schema(changed, 0)

    def test_pre_ack_state_machine_exact_transitions(self):
        def rejected(selector, mutation, message):
            packets = copy.deepcopy(self.packets(selector))
            mutation(packets)
            state = owner.PacketState(selector)
            with self.assertRaisesRegex(ValueError, message):
                for index, packet in enumerate(packets):
                    owner.validate_packet_schema(packet, selector)
                    owner.validate_schedule_prefix(packets[:index + 1], selector)
                    state.validate(packet)
        rejected(0, lambda packets: next(packet for packet in packets if
            packet["kind"] == "AFTER" and packet["site"] == "request-write").
            __setitem__("actual_bytes", 405), "request write result")
        rejected(0, lambda packets: next(packet for packet in packets if
            packet["site"] == "request-sync")["target_stat"].
            __setitem__("ino", 999), "request sync result")
        rejected(0, lambda packets: next(packet for packet in packets if
            packet["kind"] == "BIND" and packet["site"] == "report-create").
            __getitem__("old_stat").__setitem__("dev", 2), "bind identity")
        rejected(0, lambda packets: next(packet for packet in packets if
            packet["kind"] == "AFTER" and packet["site"] == "report-flush").
            __getitem__("target_stat").__setitem__("size", 0), "report sync size")
        rejected(0, lambda packets: next(packet for packet in packets if
            packet["kind"] == "CLEANUP_FINAL").__setitem__("owned_count", 1),
            "collector cleanup result")

    def test_report_preflush_prefix_size_is_permitted(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "case"
            self.write_fixture(root, 0)
            report_size = (root / "collection/report.json").stat().st_size
            self.rewrite_journal(root / "witness.jsonl", lambda rows:
                next(row for row in rows if row["packet"].get("site") ==
                     "report-flush" and row["packet"].get("kind") == "BEFORE")
                    ["packet"]["target_stat"].__setitem__("size", report_size // 2))
            self.refresh_supervisor(root)
            self.assertTrue(oracle.validate(root, 0, 0))
            with tempfile.TemporaryDirectory() as invalid:
                prefork = Path(invalid) / "case"
                self.write_fixture(prefork, 2)
                self._mutate_report(prefork, "subsequent_proc_exe_link_sample", {
                    "atomic_with_backing_stat": False,
                    "observed_monotonic_ns": 1, "bytes_hex": ""})
                self.rebind_artifact(prefork, "report")
                self.refresh_supervisor(prefork)
                with self.assertRaises(ValueError):
                    oracle.validate(prefork, 2, 0)

    def test_supervisor_status_rejected_before_evidence_read(self):
        with mock.patch.object(oracle, "read",
                               side_effect=RuntimeError("read forbidden")) as reader:
            for status in (oracle._MISSING_STATUS, True, 0.0, 1, 9):
                with self.subTest(status=status), \
                     self.assertRaisesRegex(ValueError,
                                            "supervisor raw wait status"):
                    if status is oracle._MISSING_STATUS:
                        oracle.validate(Path("/missing"), 0)
                    else:
                        oracle.validate(Path("/missing"), 0, status)
            reader.assert_not_called()

    def mutate_supervisor(self, edit, message):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "case"
            self.write_fixture(root, 0)
            self.rewrite_json(root / "supervisor-result.json", edit)
            with self.assertRaises(ValueError) as raised:
                oracle.validate(root, 0, 0)
            self.assertEqual(str(raised.exception), message)

    def test_supervisor_oracle_exact_identity_deadline_and_hash_controls(self):
        for edit, message in (
                (lambda value: value.__setitem__("schema_version", 1.0),
                 "supervisor record"),
                (lambda value: value["owner_identity"].__setitem__("pid", True),
                 "supervisor owner identity"),
                (lambda value: value["owner_identity_observations"][0].
                    __setitem__("ppid", False),
                 "supervisor identity observation"),
                (lambda value: value.__setitem__("owner_wait_deadline_ns",
                    value["owner_wait_deadline_ns"] + 1),
                 "supervisor deadlines"),
                (lambda value: value.__setitem__("owner_result_sha256", "0" * 64),
                 "supervisor evidence hash"),
                (lambda value: value["supervisor_cleanup"]["events"].insert(1,
                    {"kind": "signal", "pid": 40, "startticks": None,
                     "signal": 15, "direct": True, "monotonic_ns": 7250}),
                 "supervisor cleanup signal"),
                (lambda value: value["supervisor_cleanup"].update({
                    "complete": False,
                    "unresolved": [{"kind": "identity",
                        "phase": "term-identity-1", "observation": "missing",
                        "pid": 40, "ppid": None, "startticks": None,
                        "matched": False, "monotonic_ns": 7250}]}),
                 "supervisor cleanup incomplete"),
                (lambda value: value["supervisor_cleanup"]["events"][0].
                    __setitem__("raw_wait_status", 256),
                 "supervisor direct wait"),
                (lambda value: value["supervisor_cleanup"]["events"].insert(1,
                    {"kind": "signal", "pid": 40, "startticks": 30,
                     "signal": 9, "direct_child": True,
                     "monotonic_ns": 7250}),
                 "supervisor cleanup terminal order")):
            with self.subTest(message=message):
                self.mutate_supervisor(edit, message)

    def test_oracle_rejects_unclosed_adopted_supervisor_signal(self):
        def inject(value):
            events = value["supervisor_cleanup"]["events"]
            events[1:1] = [
                {"kind": "identity", "phase": "owned-scan-1-1",
                 "observation": "observed", "pid": 99, "ppid": 20,
                 "startticks": 88, "matched": True, "monotonic_ns": 7220},
                {"kind": "identity", "phase": "owned-scan-1-2",
                 "observation": "observed", "pid": 99, "ppid": 20,
                 "startticks": 88, "matched": True, "monotonic_ns": 7230},
                {"kind": "signal", "pid": 99, "startticks": 88,
                 "signal": 9, "monotonic_ns": 7240}]
        self.mutate_supervisor(inject, "supervisor adopted signal wait")

    def test_supervisor_identity_classification_exact_states(self):
        observed = lambda pid=40, ppid=20, ticks=30, when=1: {
            "observation": "observed", "pid": pid, "ppid": ppid,
            "startticks": ticks, "monotonic_ns": when}
        missing = lambda when=1: {"observation": "missing", "pid": 40,
            "ppid": None, "startticks": None, "monotonic_ns": when}
        matched = supervise.classify_owner(40, 20,
                                           [observed(), observed(when=2)])
        self.assertEqual(matched, {"state": "MATCHED", "pid": 40,
            "ppid": 20, "startticks": 30, "spawn_error": None})
        self.assertEqual(supervise.classify_owner(40, 20,
            [observed(), observed(ticks=31, when=2)])["state"], "MISMATCH")
        self.assertEqual(supervise.classify_owner(40, 20,
            [observed(), missing(2)])["state"], "UNOBSERVED")
        self.assertEqual(supervise.classify_owner(40, 20,
            [missing(), missing(2)])["state"], "UNOBSERVED")
        for mutation in (
                lambda rows: rows[0].__setitem__("pid", True),
                lambda rows: rows[0].__setitem__("ppid", 20.0),
                lambda rows: rows[0].__setitem__("monotonic_ns", False)):
            rows = [observed(), observed(when=2)]; mutation(rows)
            with self.assertRaisesRegex(ValueError,
                                        "owner identity observation"):
                supervise.classify_owner(40, 20, rows)

    def test_supervisor_preflight_retains_wrong_sentinel_wait(self):
        with mock.patch.object(supervise.signal, "signal"), \
             mock.patch.object(supervise.signal, "getsignal",
                               return_value=supervise.signal.SIG_DFL), \
             mock.patch.object(supervise, "set_subreaper"), \
             mock.patch.object(supervise.os, "fork", return_value=77), \
             mock.patch.object(supervise, "wait_exact", return_value=1), \
             mock.patch.object(supervise.time, "monotonic_ns", return_value=10):
            with self.assertRaises(supervise.PreflightFailure) as raised:
                supervise.establish_wait_authority(1)
        failure = raised.exception
        self.assertEqual(failure.stage, "sentinel-wait")
        self.assertTrue(failure.sigchld_default)
        self.assertEqual(failure.sentinel_pid, 77)
        self.assertEqual(failure.sentinel_wait, {"kind": "wait", "pid": 77,
            "startticks": None, "raw_wait_status": 1, "direct": True,
            "monotonic_ns": 10})

    def test_supervisor_preflight_rejects_late_sentinel_wait(self):
        started = 100
        deadline = started + supervise.PREFLIGHT_NS
        for observed_ns in (deadline, deadline + 1):
            with self.subTest(observed_ns=observed_ns), \
                 mock.patch.object(supervise.signal, "signal"), \
                 mock.patch.object(supervise.signal, "getsignal",
                                   return_value=supervise.signal.SIG_DFL), \
                 mock.patch.object(supervise, "set_subreaper"), \
                 mock.patch.object(supervise.os, "fork", return_value=77), \
                 mock.patch.object(supervise, "wait_exact",
                                   return_value=73 << 8) as wait_call, \
                 mock.patch.object(supervise.time, "monotonic_ns",
                                   return_value=observed_ns):
                if observed_ns == deadline:
                    result = supervise.establish_wait_authority(started)
                    self.assertTrue(result["sentinel_wait_passed"])
                else:
                    with self.assertRaises(supervise.PreflightFailure) as raised:
                        supervise.establish_wait_authority(started)
                    self.assertEqual(raised.exception.stage, "sentinel-wait")
                    self.assertEqual(raised.exception.sentinel_wait["pid"], 77)
                    self.assertEqual(raised.exception.sentinel_wait[
                        "monotonic_ns"], observed_ns)
                wait_call.assert_called_once_with(77, deadline)

    def test_run_supervisor_rejects_owner_start_after_preflight_deadline(self):
        started = 100
        deadline = started + supervise.PREFLIGHT_NS
        sentinel_wait = {"kind": "wait", "pid": 77, "startticks": None,
            "raw_wait_status": 73 << 8, "direct": True,
            "monotonic_ns": deadline}
        authority = {"sigchld_default": True,
            "sentinel_wait_passed": True, "sentinel_pid": 77,
            "sentinel_raw_wait_status": 73 << 8,
            "sentinel_wait": sentinel_wait}
        def cleanup(pid, observations, direct_wait, supervisor_pid,
                    trigger_ns, deadline_ns, **kwargs):
            events = ([direct_wait] if direct_wait is not None else []) + [
                {"kind": "owned-scan", "monotonic_ns": trigger_ns + 1,
                 "pids": []},
                {"kind": "owned-scan", "monotonic_ns": trigger_ns + 2,
                 "pids": []},
                {"kind": "echild", "monotonic_ns": trigger_ns + 3,
                 "return": -1, "errno": 10}]
            return {"complete": True, "events": events,
                    "unresolved": []}, direct_wait
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "attempt"
            args = mock.Mock(attempt_root=root)
            with mock.patch.object(supervise, "validate_inputs"), \
                 mock.patch.object(supervise.time, "monotonic_ns",
                    side_effect=[started, deadline + 1, deadline + 4,
                                 deadline + 5]), \
                 mock.patch.object(supervise.os, "getpid", return_value=20), \
                 mock.patch.object(supervise, "establish_wait_authority",
                                   return_value=authority), \
                 mock.patch.object(supervise, "spawn_owner",
                                   side_effect=OSError(5, "late spawn")) as spawn, \
                 mock.patch.object(supervise, "cleanup_tree",
                                   side_effect=cleanup), \
                 mock.patch.object(supervise, "finish_pipes"), \
                 mock.patch.object(supervise, "ensure_attempt_root",
                    side_effect=lambda path: path.mkdir() or path), \
                 mock.patch.object(supervise, "publish_result"):
                result, status = supervise.run_supervisor(args)
            self.assertEqual(status, 125)
            self.assertEqual(result["preflight_failure"]["stage"],
                             "sentinel-wait")
            self.assertEqual(result["supervisor_cleanup"]["events"][0],
                             sentinel_wait)
            spawn.assert_not_called()
            self.assertTrue(oracle.validate_supervisor_record(result))

    def test_packet19_late_owner_start_uses_actual_trigger_not_sentinel_wait(self):
        """A passed sentinel is retained; the later rejected start samples trigger."""
        started = 100
        sentinel_deadline = started + supervise.PREFLIGHT_NS
        late_start = sentinel_deadline + 1
        sentinel_wait = {"kind": "wait", "pid": 77, "startticks": None,
            "raw_wait_status": 73 << 8, "direct": True,
            "monotonic_ns": 105}
        authority = {"sigchld_default": True, "sentinel_wait_passed": True,
            "sentinel_pid": 77, "sentinel_raw_wait_status": 73 << 8,
            "sentinel_wait": sentinel_wait}
        observed = {}
        def cleanup(pid, observations, direct_wait, supervisor_pid,
                    trigger_ns, deadline_ns, **kwargs):
            observed.update(trigger_ns=trigger_ns, deadline_ns=deadline_ns,
                            direct_wait=direct_wait)
            return {"complete": True, "events": [direct_wait,
                {"kind": "owned-scan", "monotonic_ns": trigger_ns + 1,
                 "pids": []}, {"kind": "owned-scan",
                 "monotonic_ns": trigger_ns + 2, "pids": []},
                {"kind": "echild", "monotonic_ns": trigger_ns + 3,
                 "return": -1, "errno": 10}], "unresolved": []}, direct_wait
        with tempfile.TemporaryDirectory() as temporary:
            args = mock.Mock(attempt_root=Path(temporary) / "attempt")
            with mock.patch.object(supervise, "validate_inputs"), \
                 mock.patch.object(supervise.time, "monotonic_ns",
                    side_effect=[started, late_start, late_start + 4]), \
                 mock.patch.object(supervise.os, "getpid", return_value=20), \
                 mock.patch.object(supervise, "establish_wait_authority",
                                   return_value=authority), \
                 mock.patch.object(supervise, "spawn_owner") as spawn, \
                 mock.patch.object(supervise, "cleanup_tree",
                                   side_effect=cleanup), \
                 mock.patch.object(supervise, "finish_pipes"), \
                 mock.patch.object(supervise, "ensure_attempt_root",
                    side_effect=lambda path: path.mkdir() or path), \
                 mock.patch.object(supervise, "publish_result"):
                result, status = supervise.run_supervisor(args)
        self.assertEqual(status, 125)
        self.assertEqual(result["started_ns"], started)
        self.assertEqual(result["preflight_failure"], {
            "stage": "sentinel-wait", "type": "TimeoutError",
            "message": "owner start deadline", "errno": None})
        spawn.assert_not_called()
        self.assertIs(observed["direct_wait"], sentinel_wait)
        self.assertEqual(result["supervisor_cleanup"]["events"][0], sentinel_wait)
        self.assertEqual(result["cleanup_trigger_ns"], late_start)
        self.assertEqual(observed["trigger_ns"], late_start)
        self.assertEqual(result["supervisor_cleanup_deadline_ns"],
                         late_start + supervise.CLEANUP_NS)
        self.assertEqual(observed["deadline_ns"], late_start + supervise.CLEANUP_NS)
        self.assertTrue(oracle.validate_supervisor_record(result))

    def test_packet19_null_timeout_birth_pair_is_strict_for_sentinel_and_owner(self):
        """A positive reap cannot promote a null timeout without a timed pair."""
        def cleanup(identity_pid, start, trigger=100, timeout_ns=200,
                    pair_start=210, wait_ns=230):
            pair = [{"kind": "identity", "phase": "term-identity-1",
                     "observation": "observed", "pid": identity_pid,
                     "ppid": 20, "startticks": start, "matched": True,
                     "monotonic_ns": pair_start},
                    {"kind": "identity", "phase": "term-identity-2",
                     "observation": "observed", "pid": identity_pid,
                     "ppid": 20, "startticks": start, "matched": True,
                     "monotonic_ns": pair_start + 1}]
            direct = {"kind": "wait", "pid": identity_pid,
                      "startticks": start, "raw_wait_status": 0,
                      "direct": True, "monotonic_ns": wait_ns}
            return {"complete": False, "events": pair + [direct,
                {"kind": "owned-scan", "monotonic_ns": 240, "pids": []},
                {"kind": "owned-scan", "monotonic_ns": 250, "pids": []},
                {"kind": "echild", "monotonic_ns": 260,
                 "return": -1, "errno": 10}], "unresolved": [
                {"kind": "wait-timeout", "stage": "direct",
                 "pid": identity_pid, "startticks": None,
                 "monotonic_ns": timeout_ns, "deadline_ns": 150}]}
        for label, identity, pid, original_deadline, preflight in (
                ("sentinel", {"state": "NOT_SPAWNED", "pid": None,
                    "ppid": None, "startticks": None, "spawn_error": None},
                 77, 150, "sentinel-wait"),
                ("owner", {"state": "UNOBSERVED", "pid": 40,
                    "ppid": None, "startticks": None, "spawn_error": None},
                 40, 150, None)):
            with self.subTest(path=label):
                valid = cleanup(pid, 30)
                oracle.validate_supervisor_cleanup(valid, identity, 20,
                    original_deadline, 100, 1000, 2000, 500, preflight)
                for name, mutate in (
                    ("missing-pair", lambda value: value["events"].__setitem__(
                        slice(0, 2), [])),
                    ("wrong-parent", lambda value: value["events"][0].__setitem__(
                        "ppid", 21)),
                    ("wrong-birth", lambda value: value["events"][1].__setitem__(
                        "startticks", 31)),
                    ("wrong-phase", lambda value: value["events"][1].__setitem__(
                        "phase", "owned-scan-1-2")),
                    ("pair-before-timeout", lambda value: [
                        event.__setitem__("monotonic_ns", 190 + index)
                        for index, event in enumerate(value["events"][:2])]),
                    ("pair-after-wait", lambda value: [
                        event.__setitem__("monotonic_ns", 231 + index)
                        for index, event in enumerate(value["events"][:2])]),
                    ("positive-reap-without-proof", lambda value: value["events"].__setitem__(
                        slice(0, 2), []))):
                    bad = copy.deepcopy(valid)
                    mutate(bad)
                    with self.subTest(control=name), self.assertRaises(ValueError):
                        oracle.validate_supervisor_cleanup(bad, identity, 20,
                            original_deadline, 100, 1000, 2000, 500, preflight)

    def _packet19_late_start_record(self):
        preflight_started = 100
        sentinel_deadline = preflight_started + supervise.PREFLIGHT_NS
        trigger = sentinel_deadline + 1
        wait = {"kind": "wait", "pid": 77, "startticks": None,
                "raw_wait_status": 73 << 8, "direct": True,
                "monotonic_ns": 105}
        cleanup = {"complete": True, "events": [wait,
            {"kind": "owned-scan", "monotonic_ns": trigger + 1,
             "pids": []},
            {"kind": "owned-scan", "monotonic_ns": trigger + 2,
             "pids": []},
            {"kind": "echild", "monotonic_ns": trigger + 3,
             "return": -1, "errno": 10}], "unresolved": []}
        failure = supervise.PreflightFailure("sentinel-wait",
            TimeoutError("owner start deadline"), 77, wait,
            sigchld_default=True, trigger_ns=trigger)
        identity = {"state": "NOT_SPAWNED", "pid": None, "ppid": None,
                    "startticks": None, "spawn_error": None}
        return supervise.supervisor_result(Path("/tmp/packet19-late"), 20,
            preflight_started, trigger + 4, identity, [], None, b"", b"",
            cleanup, preflight_started, sentinel_deadline, None, trigger,
            trigger + supervise.CLEANUP_NS,
            preflight_started + supervise.PREFLIGHT_TOTAL_NS, True, False,
            supervise.preflight_record(failure), False)

    def test_packet19_full_record_requires_exact_late_start_wait_and_trigger(self):
        valid = self._packet19_late_start_record()
        self.assertTrue(oracle.validate_supervisor_record(valid))

        missing = copy.deepcopy(valid)
        missing["supervisor_cleanup"]["complete"] = False
        missing["supervisor_cleanup"]["events"] = \
            missing["supervisor_cleanup"]["events"][1:]
        missing["supervisor_cleanup"]["unresolved"] = [{
            "kind": "wait-timeout", "stage": "direct", "pid": 77,
            "startticks": None,
            "monotonic_ns": missing["cleanup_trigger_ns"],
            "deadline_ns": missing["sentinel_wait_deadline_ns"]}]
        substituted = copy.deepcopy(valid)
        substituted["supervisor_cleanup"]["events"][0].update({
            "raw_wait_status": 0,
            "monotonic_ns": substituted["cleanup_trigger_ns"]})
        backdated = copy.deepcopy(valid)
        old_trigger = backdated["cleanup_trigger_ns"]
        new_trigger = backdated["supervisor_cleanup"]["events"][0]["monotonic_ns"]
        delta = old_trigger - new_trigger
        backdated["cleanup_trigger_ns"] = new_trigger
        backdated["supervisor_cleanup_deadline_ns"] -= delta
        for event in backdated["supervisor_cleanup"]["events"][1:]:
            event["monotonic_ns"] -= delta
        backdated["finished_ns"] -= delta
        for name, changed in (("missing", missing),
                              ("substituted", substituted),
                              ("backdated", backdated)):
            with self.subTest(control=name), self.assertRaises(ValueError):
                oracle.validate_supervisor_record(changed)

    def _packet19_later_birth_record(self, sentinel):
        preflight_started = 100
        sentinel_deadline = preflight_started + supervise.PREFLIGHT_NS
        if sentinel:
            pid, started = 77, preflight_started
            trigger = sentinel_deadline
            original_deadline = sentinel_deadline
            overall_deadline = preflight_started + supervise.PREFLIGHT_TOTAL_NS
            identity = {"state": "NOT_SPAWNED", "pid": None, "ppid": None,
                        "startticks": None, "spawn_error": None}
            observations = []
            failure = {"stage": "sentinel-wait", "type": "OSError",
                       "message": "[Errno 5] sentinel-wait", "errno": 5}
            owner_wait_deadline = None
            sigchld_default, sentinel_wait_passed = True, False
        else:
            pid, started = 40, 200
            original_deadline = started + supervise.OWNER_WAIT_NS
            trigger = original_deadline
            overall_deadline = started + supervise.TOTAL_NS
            identity = {"state": "UNOBSERVED", "pid": pid, "ppid": None,
                        "startticks": None, "spawn_error": None}
            observations = [
                {"observation": "missing", "pid": pid, "ppid": None,
                 "startticks": None, "monotonic_ns": started + 1},
                {"observation": "error", "pid": pid, "ppid": None,
                 "startticks": None, "monotonic_ns": started + 2}]
            failure = None
            owner_wait_deadline = original_deadline
            sigchld_default, sentinel_wait_passed = True, True
        pair_start = trigger + 10
        wait_ns = pair_start + 20
        wait = {"kind": "wait", "pid": pid, "startticks": 30,
                "raw_wait_status": 15, "direct": True,
                "monotonic_ns": wait_ns}
        cleanup = {"complete": False, "events": [
            {"kind": "identity", "phase": "term-identity-1",
             "observation": "observed", "pid": pid, "ppid": 20,
             "startticks": 30, "matched": True,
             "monotonic_ns": pair_start},
            {"kind": "identity", "phase": "term-identity-2",
             "observation": "observed", "pid": pid, "ppid": 20,
             "startticks": 30, "matched": True,
             "monotonic_ns": pair_start + 1}, wait,
            {"kind": "owned-scan", "monotonic_ns": wait_ns + 1,
             "pids": []},
            {"kind": "owned-scan", "monotonic_ns": wait_ns + 2,
             "pids": []},
            {"kind": "echild", "monotonic_ns": wait_ns + 3,
             "return": -1, "errno": 10}], "unresolved": [{
                "kind": "wait-timeout", "stage": "direct", "pid": pid,
                "startticks": None, "monotonic_ns": trigger,
                "deadline_ns": original_deadline}]}
        return supervise.supervisor_result(Path("/tmp/packet19-birth"), 20,
            started, wait_ns + 4, identity, observations,
            None if sentinel else wait, b"", b"",
            cleanup, preflight_started, sentinel_deadline,
            owner_wait_deadline, trigger, trigger + supervise.CLEANUP_NS,
            overall_deadline, sigchld_default, sentinel_wait_passed,
            failure, False)

    def test_packet19_full_record_rejects_contradiction_and_sentinel_revival(self):
        for sentinel in (True, False):
            with self.subTest(path="sentinel" if sentinel else "owner"):
                valid = self._packet19_later_birth_record(sentinel)
                self.assertTrue(oracle.validate_supervisor_record(valid))
                for field, value in (("ppid", 21), ("startticks", 31)):
                    contradicted = copy.deepcopy(valid)
                    pair = contradicted["supervisor_cleanup"]["events"]
                    observation = {"kind": "identity",
                        "phase": "kill-identity-1",
                        "observation": "observed", "pid": pair[0]["pid"],
                        "ppid": 20, "startticks": 30, "matched": False,
                        "monotonic_ns": pair[1]["monotonic_ns"] + 1}
                    observation[field] = value
                    pair.insert(2, observation)
                    with self.subTest(field=field), self.assertRaises(ValueError):
                        oracle.validate_supervisor_record(contradicted)
        revived = self._packet19_later_birth_record(True)
        timeout_ns = revived["supervisor_cleanup"]["unresolved"][0]["monotonic_ns"]
        revived["supervisor_cleanup"]["events"].insert(0, {
            "kind": "wait", "pid": 77, "startticks": None,
            "raw_wait_status": 0, "direct": False,
            "monotonic_ns": timeout_ns + 1})
        with self.assertRaises(ValueError):
            oracle.validate_supervisor_record(revived)

    def _archived_storage_oracle(self, attempt):
        evidence = Path(__file__).resolve().parents[2] / "docs/verification/evidence/"
        review_archive = evidence / (
            "stability-linux-collector-storage-fault-v2-source-review-input-"
            "20260915-%d.tar.gz" % attempt)
        if not review_archive.exists():
            review_archive = evidence / (
                "stability-linux-collector-storage-fault-v2-source-review-input-"
                "20260916-%d.tar.gz" % attempt)
        with tarfile.open(review_archive, "r:gz") as archive:
            archived = types.ModuleType("storage_oracle_archive_%d" % attempt)
            archived.__file__ = "archive-%d/oracle.py" % attempt
            source = archive.extractfile(
                "./scripts/tests/fixtures/application-collector-v1/"
                "linux-sealed-v1/storage-fault-v1/oracle.py").read()
            exec(compile(source, archived.__file__, "exec"), archived.__dict__)
        return archived

    def _archived_storage_module(self, attempt, name):
        evidence = Path(__file__).resolve().parents[2] / "docs/verification/evidence/"
        archive_path = evidence / (
            "stability-linux-collector-storage-fault-v2-source-review-input-"
            "20260916-%d.tar.gz" % attempt)
        with tarfile.open(archive_path, "r:gz") as archive:
            module = types.ModuleType("storage_%s_archive_%d" % (name, attempt))
            module.__file__ = "archive-%d/%s.py" % (attempt, name)
            source = archive.extractfile(
                "./scripts/tests/fixtures/application-collector-v1/"
                "linux-sealed-v1/storage-fault-v1/%s.py" % name).read()
            exec(compile(source, module.__file__, "exec"), module.__dict__)
        return module

    def test_review37_storage_schema_dynamic_seals_and_integer_domains(self):
        """Review37 binds dynamic pipes, complete seals, and producer ranges."""
        archive40 = Path(__file__).resolve().parents[2] / "docs/verification/evidence" / \
            "stability-linux-collector-storage-fault-v2-source-review-input-20260916-40.tar.gz"
        self.assertEqual(hashlib.sha256(archive40.read_bytes()).hexdigest(),
                         "5f43d6af69298a84c980b04aa65f66a18c7e621043767a12f69039ed444e0a30")
        old_oracle = self._archived_storage_oracle(40)
        for selector in (0, 3, 4, 5):
            with self.subTest(selector=selector), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary) / "case"
                self.write_fixture(root, selector)
                def dynamic_setup(rows):
                    packet = next(row["packet"] for row in rows
                        if row["packet"].get("kind") == "SETUP")
                    packet["stdout_pipe_stat"]["ino"] = 901
                    packet["stderr_pipe_stat"]["ino"] = 902
                    packet["setup_words"][23] = 901
                    packet["setup_words"][26] = 902
                self.rewrite_journal(root / "witness.jsonl", dynamic_setup)
                raw = list(struct.unpack("<48Q", (root / "collection/setup.bin").read_bytes()))
                raw[23], raw[26] = 901, 902
                (root / "collection/setup.bin").write_bytes(struct.pack("<48Q", *raw))
                self.assertEqual(hashlib.sha256(
                    (root / "collection/setup.bin").read_bytes()).hexdigest(),
                    "097aa90a86bce91f05d010396f18f769a597abcc28042cc406211b6df1e787fe")
                if (root / "collection/report.json").exists():
                    setup_sha = hashlib.sha256((root / "collection/setup.bin").read_bytes()).hexdigest()
                    def dynamic_report(report):
                        report["setup_words"][23] = 901
                        report["setup_words"][26] = 902
                        report["artifacts"][9]["sha256"] = setup_sha
                    self.mutate_report(root, dynamic_report)
                self.refresh_supervisor(root)
                if selector == 4:
                    legacy = root.parent / "legacy"
                    shutil.copytree(root, legacy)
                    (legacy / "collection/stdout.bin").write_bytes(b"")
                    self.make_legacy_empty(legacy, root)
                    self.assertTrue(old_oracle.validate(legacy, selector, 0))
                else:
                    with self.assertRaisesRegex(ValueError,
                                                "report setup semantics"):
                        old_oracle.validate(root, selector, 0)
                self.assertTrue(oracle.validate(root, selector, 0))

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "case"
            self.write_fixture(root, 4)
            def zero_seals(rows):
                packet = next(row["packet"] for row in rows
                    if row["packet"].get("kind") == "SETUP")
                packet["executable_seals"] = 0
                packet["setup_words"][29] = 0
            self.rewrite_journal(root / "witness.jsonl", zero_seals)
            raw = list(struct.unpack("<48Q", (root / "collection/setup.bin").read_bytes()))
            raw[29] = 0
            (root / "collection/setup.bin").write_bytes(struct.pack("<48Q", *raw))
            self.assertEqual(hashlib.sha256(
                (root / "collection/setup.bin").read_bytes()).hexdigest(),
                "f99bc86b878d64c8a3e59d1072170f97f20185c8d07d484c9dae6a16fce9ebaa")
            self.refresh_supervisor(root)
            legacy = root.parent / "legacy"
            shutil.copytree(root, legacy)
            (legacy / "collection/stdout.bin").write_bytes(b"")
            self.make_legacy_empty(legacy, root)
            self.assertTrue(old_oracle.validate(legacy, 4, 0))
            with self.assertRaises(ValueError): oracle.validate(root, 4, 0)

        mutations = (
            ("negative-dev", lambda packet: packet["stdin_stat"].__setitem__("dev", -1)),
            ("seal-overflow", lambda packet: packet.__setitem__("executable_seals", 1 << 64)),
            ("pid-overflow", lambda packet: packet.__setitem__("leader_pid", 1 << 64)),
            ("birth-overflow", lambda packet: packet.__setitem__("leader_startticks", 1 << 64)),
            ("size-overflow", lambda packet: packet["stdin_stat"].__setitem__("size", 1 << 64)),
        )
        baseline = next(packet for packet in self.packets(4)
                        if packet.get("kind") == "SETUP")
        owner.validate_packet_schema(baseline, 4)
        for name, mutation in mutations:
            candidate = copy.deepcopy(baseline)
            mutation(candidate)
            with self.subTest(pre_ack=name), self.assertRaises(ValueError):
                owner.validate_packet_schema(candidate, 4)
            with tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary) / "case"; self.write_fixture(root, 4)
                self.rewrite_journal(root / "witness.jsonl", lambda rows: mutation(
                    next(row["packet"] for row in rows if row["packet"].get("kind") == "SETUP")))
                if name == "size-overflow":
                    rows = [json.loads(line) for line in
                            (root / "witness.jsonl").read_text().splitlines()]
                    packet = next(row["packet"] for row in rows
                                  if row["packet"].get("kind") == "SETUP")
                    canonical = json.dumps(packet, sort_keys=True,
                                           separators=(",", ":")).encode()
                    self.assertEqual(hashlib.sha256(canonical).hexdigest(),
                        "93f6036387139dd02015a829ec828eff0900ff244f259ec46659fe7659781c0f")
                self.refresh_supervisor(root)
                if name == "size-overflow":
                    legacy = root.parent / "legacy"
                    shutil.copytree(root, legacy)
                    self.make_legacy_empty(legacy, root)
                    self.assertTrue(old_oracle.validate(legacy, 4, 0))
                with self.assertRaises(ValueError): oracle.validate(root, 4, 0)

    def test_review38_storage_schema_binds_executable_backing(self):
        """Archive41 accepted unbound backing mutations; current sources reject."""
        archive41 = Path(__file__).resolve().parents[2] / "docs/verification/evidence" / \
            "stability-linux-collector-storage-fault-v2-source-review-input-20260916-41.tar.gz"
        self.assertEqual(hashlib.sha256(archive41.read_bytes()).hexdigest(),
                         "b96f2107b6a2857b3995b65e626c9d8b5a47d0a9d5fd8f697489baab6779a5e0")
        old_oracle = self._archived_storage_oracle(41)
        old_owner = self._archived_storage_module(41, "witness_owner")
        for selector in (0, 3, 4, 5):
            baseline = self.packets(selector)
            setup = next(packet for packet in baseline if packet["kind"] == "SETUP")
            for label, value in (("size", 0), ("mode", 0o100600)):
                with self.subTest(selector=selector, mutation=label):
                    candidate = json.loads(json.dumps(setup))
                    candidate["executable_backing"][label] = value
                    self.assertEqual(old_owner.validate_packet_schema(candidate, selector), None)
                    with self.assertRaises(ValueError):
                        owner.validate_packet_schema(candidate, selector, 27448)
                    if selector == 4:
                        expected = {"size": "59f63e520e309b23bc4f3ebce008cd31c84bedd9835fd07498dcef51389591a1",
                                    "mode": "f0854a4c4883ecb46218b9bddd6f01234673766456e3755a117aaa627596cbb0"}
                        canonical = json.dumps(candidate, sort_keys=True,
                                               separators=(",", ":")).encode()
                        self.assertEqual(hashlib.sha256(canonical).hexdigest(),
                                         expected[label])
                    with tempfile.TemporaryDirectory() as temporary:
                        root = Path(temporary) / "case"
                        self.write_fixture(root, selector)
                        def mutate(rows):
                            packet = next(row["packet"] for row in rows if row["packet"].get("kind") == "SETUP")
                            packet["executable_backing"][label] = value
                        self.rewrite_journal(root / "witness.jsonl", mutate)
                        self.refresh_supervisor(root)
                        if selector == 4:
                            legacy = root.parent / "legacy"
                            shutil.copytree(root, legacy)
                            (legacy / "collection/stdout.bin").write_bytes(b"")
                            self.make_legacy_empty(legacy, root)
                            self.assertTrue(old_oracle.validate(legacy, selector, 0))
                        else:
                            self.assertTrue(old_oracle.validate(root, selector, 0))
                        with self.assertRaises(ValueError):
                            oracle.validate(root, selector, 0)

    def test_review39_launch_binds_runtime_fixture_size_not_collector_size(self):
        """The real launch path validates SETUP against the payload fixture."""
        archive42 = Path(__file__).resolve().parents[2] / "docs/verification/evidence" / \
            "stability-linux-collector-storage-fault-v2-source-review-input-20260916-42.tar.gz"
        self.assertEqual(hashlib.sha256(archive42.read_bytes()).hexdigest(),
                         "c6e56b1332ec8b457cd3c031a0f1833e72d5edf6ce0d9b17d5417545603181e1")
        old_owner = self._archived_storage_module(42, "witness_owner")

        class Endpoint:
            def close(self):
                pass

        class Journal:
            def __init__(self, root):
                self.records = []
            def append(self, packet, receipt_ns):
                self.records.append(packet)
            def close(self):
                pass

        class ErrorJournal(Journal):
            poisoned = False
            fd = 0
            last_monotonic_ns = 0
            def append(self, error, stage, packet=None):
                self.records.append({"type": type(error).__name__, "stage": stage})

        hashes = {"source_sha256": self.SOURCE_SHA, **self.HASHES}
        identity = {"pid": 50, "ppid": os.getpid(), "startticks": 60}
        inputs = {name: {"path": "/tmp/" + name, "present": True, "size":
                         24 if name == "elf" else 1, "sha256": hashes.get(
                             name + "_sha256", "a" * 64)} for name in
                  ("source", "generated_source", "header", "elf")}

        def run_launch(selector, setup_size):
            packets = copy.deepcopy(self.packets(selector))
            next(packet for packet in packets if packet["kind"] == "SETUP")[
                "executable_backing"]["size"] = setup_size
            with tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary) / "attempt"
                runtime = {"fixture": {"size": 27448},
                           "request": {"size": 406, "destination_path": "/tmp/request.bin"},
                           "selected_inputs": {"size": 76,
                               "destination_path": "/tmp/selected-inputs.json"}}
                def receive(_endpoint, _deadline):
                    return packets.pop(0) if packets else None
                with mock.patch.object(owner, "bind_inputs", return_value=inputs), \
                     mock.patch.object(owner, "bind_runtime_sources", return_value={}), \
                     mock.patch.object(owner, "retain_runtime_inputs", return_value=runtime), \
                     mock.patch.object(owner, "DurableJournal", Journal), \
                     mock.patch.object(owner, "OwnerErrorJournal", ErrorJournal), \
                     mock.patch.object(owner, "subreaper"), \
                     mock.patch.object(owner, "process_identity", return_value={
                         "pid": os.getpid(), "startticks": 30}), \
                     mock.patch.object(owner, "observe_identity", return_value={
                         "matched": True, "pid": 50, "ppid": os.getpid(), "startticks": 60}), \
                     mock.patch.object(owner.socket, "socketpair", return_value=(Endpoint(), Endpoint())), \
                     mock.patch.object(owner.os, "fork", return_value=50), \
                     mock.patch.object(owner, "receive", side_effect=receive), \
                     mock.patch.object(owner, "send_packet"), \
                     mock.patch.object(owner, "fsync_directory"), \
                     mock.patch.object(owner, "bounded_cleanup", return_value=({
                         "complete": True, "trigger_kind": "normal-eof", "trigger_ns": 1,
                         "cleanup_start_ns": 2, "cleanup_deadline_ns": 3,
                         "cleanup_finished_ns": 2, "events": [], "adopted_reaps": [],
                         "unresolved": []}, {"raw_wait_status": 0})), \
                     mock.patch.object(owner, "file_record", return_value={"present": True}), \
                     mock.patch.object(owner, "publish_owner_result", return_value=(True, True)):
                    return owner.launch(root, self.NONCE, selector, hashes, {}, {})

        for selector in (0, 3, 4, 5):
            with self.subTest(selector=selector, backing="valid"):
                result = run_launch(selector, 27448)
                self.assertEqual(result["cleanup"]["trigger_kind"], "normal-eof")
            with self.subTest(selector=selector, backing="collector"):
                with self.assertRaisesRegex(ValueError, "witness executable backing"):
                    run_launch(selector, 24)

        with tempfile.TemporaryDirectory() as temporary:
            fixture_root = Path(temporary) / "fixture"
            self.write_fixture(fixture_root, 4)
            setup = next(json.loads(row)["packet"] for row in
                (fixture_root / "witness.jsonl").read_text().splitlines()
                if json.loads(row)["packet"]["kind"] == "SETUP")
        self.assertIsNone(old_owner.validate_packet_schema(setup, 4,))
        mutated = copy.deepcopy(setup)
        mutated["executable_backing"]["size"] = 24
        self.assertIsNone(old_owner.validate_packet_schema(mutated, 4))
        with self.assertRaises(ValueError):
            owner.validate_packet_schema(mutated, 4, 27448)
        for size, digest in ((27448, "30cab2013a195b0291ddc845c1aeecc84b3c1f03b446e06ccdd00c67ef658d95"),
                             (24, "92d4f5d03902cfe5f0dbd372d7d6263b493b2498257c5107daf3e24cd2a03ebf")):
            candidate = copy.deepcopy(setup)
            candidate["executable_backing"]["size"] = size
            self.assertEqual(hashlib.sha256(json.dumps(candidate, sort_keys=True,
                separators=(",", ":")).encode()).hexdigest(), digest)

    def test_review40_report_source_stats_bind_runtime_and_retained_sizes(self):
        """Archive43 accepted source-size lies after all report hashes were rebound."""
        archive43 = Path(__file__).resolve().parents[2] / "docs/verification/evidence" / \
            "stability-linux-collector-storage-fault-v2-source-review-input-20260916-43.tar.gz"
        self.assertEqual(hashlib.sha256(archive43.read_bytes()).hexdigest(),
                         "5251a83bb4d2b2446c39156a7de1cbb6197e20c79e9cf23777b80f851a38da28")
        old_oracle = self._archived_storage_oracle(43)
        expected = {
            0: "1895cdf3a35cb24af8125839094f9a7595aa326af678bcfb851a98605ce4eb3d",
            3: "3d2a916fa39ca612a84f03ac27545f9b1956fa54d2a662f7d436fb0a0bc1a32d",
            5: "1895cdf3a35cb24af8125839094f9a7595aa326af678bcfb851a98605ce4eb3d",
        }
        for selector in (0, 3, 5):
            with self.subTest(selector=selector), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary) / "case"
                self.write_fixture(root, selector)
                self.assertTrue(oracle.validate(root, selector, 0))
                self.mutate_report(root, lambda report: (
                    report["executable"]["source_before"].__setitem__("size", 0),
                    report["executable"]["source_after"].__setitem__("size", 0)))
                self.refresh_supervisor(root)
                report_hash = hashlib.sha256(
                    (root / "collection/report.json").read_bytes()).hexdigest()
                self.assertEqual(report_hash, expected[selector])
                self.assertTrue(old_oracle.validate(root, selector, 0))
                with self.assertRaises(ValueError):
                    oracle.validate(root, selector, 0)

    def test_review41_source_modes_match_seal_source_and_archive44_history(self):
        """Archive44 accepted non-executable source modes; current rejects them."""
        failure = Path(__file__).resolve().parents[2] / "docs/verification" / \
            "stability-linux-collector-storage-fault-v2-source-review-failure-20260916-37.json"
        archive44 = Path(__file__).resolve().parents[2] / "docs/verification/evidence" / \
            "stability-linux-collector-storage-fault-v2-source-review-input-20260916-44.tar.gz"
        self.assertEqual(hashlib.sha256(failure.read_bytes()).hexdigest(),
                         "4495ae0738b08cd45b54639528dcc64bb78c2ff1dd3d2cdfaeef6166fee031ca")
        self.assertEqual(hashlib.sha256(archive44.read_bytes()).hexdigest(),
                         "5ddf13abf15505cc8ebbf71abfac7175603293b2dac46ee01aa3ddf952486153")
        old_oracle = self._archived_storage_oracle(44)
        expected = {
            0: "b2123ebd069e443c69666ad24c30ae4cf864035790013e10af922c23d73c8e34",
            3: "af6ffe651d59e7a8d408df0e9681a191d5231b476b67ea77288fd8995cedb911",
            5: "b2123ebd069e443c69666ad24c30ae4cf864035790013e10af922c23d73c8e34",
        }
        for selector in (0, 3, 5):
            with self.subTest(selector=selector), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary) / "case"
                self.write_fixture(root, selector)
                self.assertTrue(oracle.validate(root, selector, 0))
                self.mutate_report(root, lambda report: (
                    report["executable"]["source_before"].__setitem__("mode", 0o100644),
                    report["executable"]["source_after"].__setitem__("mode", 0o100644)))
                self.refresh_supervisor(root)
                report_hash = hashlib.sha256(
                    (root / "collection/report.json").read_bytes()).hexdigest()
                self.assertEqual(report_hash, expected[selector])
                self.assertTrue(old_oracle.validate(root, selector, 0))
                with self.assertRaisesRegex(ValueError, "report source mode"):
                    oracle.validate(root, selector, 0)

        stat_template = {"device": 1, "inode": 201, "mode": 0o100755,
                         "uid": 0, "gid": 0, "size": 27448, "nlink": 1,
                         "mtime_seconds": 1, "mtime_nanoseconds": 2,
                         "ctime_seconds": 1, "ctime_nanoseconds": 2}
        for mode in (0o100100, 0o100010, 0o100001):
            with self.subTest(accepted_mode=oct(mode)):
                with tempfile.TemporaryDirectory() as temporary:
                    root = Path(temporary) / "case"
                    self.write_fixture(root, 0)
                    self.mutate_report(root, lambda report: (
                        report["executable"]["source_before"].__setitem__("mode", mode),
                        report["executable"]["source_after"].__setitem__("mode", mode)))
                    self.refresh_supervisor(root)
                    self.assertTrue(oracle.validate(root, 0, 0))
        stdin_value = {"opened": True, "stable": True, "verified": True,
                       "source_before": dict(stat_template, mode=0o100644),
                       "source_after": dict(stat_template, mode=0o100644),
                       "sealed_backing": None, "requested_memfd_flags": 3,
                       "seals": 15, "artifact": None}
        oracle.validate_report_source(stdin_value)
        for mode in (0o104755, 0o102755):
            with self.subTest(rejected_mode=oct(mode)), \
                 self.assertRaisesRegex(ValueError, "report source mode"):
                with tempfile.TemporaryDirectory() as temporary:
                    root = Path(temporary) / "case"
                    self.write_fixture(root, 0)
                    self.mutate_report(root, lambda report: (
                        report["executable"]["source_before"].__setitem__("mode", mode),
                        report["executable"]["source_after"].__setitem__("mode", mode)))
                    self.refresh_supervisor(root)
                    oracle.validate(root, 0, 0)

    def test_review42_report_stat_abi_ranges_and_archive45_history(self):
        """Archive45 accepted an unrepresentable negative executable UID."""
        failure = Path(__file__).resolve().parents[2] / "docs/verification" / \
            "stability-linux-collector-storage-fault-v2-source-review-failure-20260916-38.json"
        archive45 = Path(__file__).resolve().parents[2] / "docs/verification/evidence" / \
            "stability-linux-collector-storage-fault-v2-source-review-input-20260916-45.tar.gz"
        self.assertEqual(hashlib.sha256(failure.read_bytes()).hexdigest(),
                         "9488b12ca9cfd21a18d607b0b407b624c6e7f60eb782b9b47811a66963bd1fd8")
        self.assertEqual(hashlib.sha256(archive45.read_bytes()).hexdigest(),
                         "ced17e4703ca50a1797ac5531d95653f0f4ad408215d0d0da4d63e2cb0ee57fb")
        old_oracle = self._archived_storage_oracle(45)
        expected = {
            0: "6c7276c75980765cca3812246132b4163b06531c1c5ef97a8092be5356b50864",
            3: "5cb173cbdd58d59d77b7f57285f59aa7ac168b2b1654d180fdcac6486196d981",
            5: "6c7276c75980765cca3812246132b4163b06531c1c5ef97a8092be5356b50864"}
        for selector in (0, 3, 5):
            with self.subTest(selector=selector), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary) / "case"
                self.write_fixture(root, selector)
                self.mutate_report(root, lambda report: (
                    report["executable"]["source_before"].__setitem__("uid", -1),
                    report["executable"]["source_after"].__setitem__("uid", -1)))
                self.refresh_supervisor(root)
                report_hash = hashlib.sha256(
                    (root / "collection/report.json").read_bytes()).hexdigest()
                self.assertEqual(report_hash, expected[selector])
                self.assertTrue(old_oracle.validate(root, selector, 0))
                with self.assertRaisesRegex(ValueError, "report stat range"):
                    oracle.validate(root, selector, 0)

        base = {"device": 1, "inode": 2, "mode": 3, "uid": 4, "gid": 5,
                "size": 6, "nlink": 7, "mtime_seconds": 8,
                "mtime_nanoseconds": 9, "ctime_seconds": 10,
                "ctime_nanoseconds": 11}
        ranges = {
            "device": (0, oracle.U64_MAX), "inode": (0, oracle.U64_MAX),
            "nlink": (0, oracle.U64_MAX), "mode": (0, (1 << 32) - 1),
            "uid": (0, (1 << 32) - 1), "gid": (0, (1 << 32) - 1),
            "size": (oracle.I64_MIN, oracle.I64_MAX),
            "mtime_seconds": (oracle.I64_MIN, oracle.I64_MAX),
            "ctime_seconds": (oracle.I64_MIN, oracle.I64_MAX),
            "mtime_nanoseconds": (0, 999999999),
            "ctime_nanoseconds": (0, 999999999)}
        for field, (low, high) in ranges.items():
            for boundary in (low, high):
                oracle.validate_report_stat(dict(base, **{field: boundary}))
            for invalid in (low - 1, high + 1):
                with self.subTest(field=field, invalid=invalid), \
                     self.assertRaisesRegex(ValueError, "report stat range"):
                    oracle.validate_report_stat(dict(base, **{field: invalid}))

    def test_review43_postfork_devnull_output_contract_archive46_history(self):
        """Archive46 accepted synthetic empty output and rebound wrong output."""
        failure = Path(__file__).resolve().parents[2] / "docs/verification" / \
            "stability-linux-collector-storage-fault-v2-source-review-failure-20260916-39.json"
        archive46 = Path(__file__).resolve().parents[2] / "docs/verification/evidence" / \
            "stability-linux-collector-storage-fault-v2-source-review-input-20260916-46.tar.gz"
        self.assertEqual(hashlib.sha256(failure.read_bytes()).hexdigest(),
                         "a9abaa2d3f0c9b9c13503f85a10aebf72aa9bf0f465e68d63a0bfa636ba9be96")
        self.assertEqual(hashlib.sha256(archive46.read_bytes()).hexdigest(),
                         "15ac775cf137503ae69c10220db13467f9fb3c49a5df650d6514573e5ce94187")
        self.assertEqual(hashlib.sha256(ROOT_ARCHIVE.read_bytes()).hexdigest(),
                         "ad7c670311f6756cf64610e1d3e0dbdcdb026f86857c8461c3295cc34c17a721")
        with tarfile.open(ROOT_ARCHIVE, "r:gz") as archive:
            stdout = archive.extractfile(ROOT_PREFIX.replace("inputs/", "collection/") +
                                         "stdout.bin").read()
            stderr = archive.extractfile(ROOT_PREFIX.replace("inputs/", "collection/") +
                                         "stderr.bin").read()
            fixture = archive.extractfile(ROOT_PREFIX + "fixture").read()
        self.assertEqual(stdout, b"DEVNULL\n")
        self.assertEqual(hashlib.sha256(stdout).hexdigest(),
                         "3e6f38dc6dd02d445e4ff7679b89658b97bafabcf93840c3865e05924fab134f")
        self.assertEqual(stderr, b"")
        self.assertIn(b"DEVNULL", fixture)
        old_oracle = self._archived_storage_oracle(46)
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "case"
            self.write_fixture(root, 4)
            self.assertTrue(oracle.validate(root, 4, 0))
            (root / "collection/stdout.bin").write_bytes(b"")
            self.assertTrue(old_oracle.validate(root, 4, 0))
            self.refresh_supervisor(root)
            with self.assertRaisesRegex(ValueError, "postfork output binding"):
                oracle.validate(root, 4, 0)
        for selector in (0, 3, 5):
            with self.subTest(selector=selector), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary) / "case"
                self.write_fixture(root, selector)
                wrong = b"WRONG\n"
                (root / "collection/stdout.bin").write_bytes(wrong)
                def rebind_stdout(report):
                    sink = report["artifacts"][7]
                    sink.update({"seen_bytes": len(wrong), "stored_bytes": len(wrong),
                                 "sha256": hashlib.sha256(wrong).hexdigest()})
                self.mutate_report(root, rebind_stdout)
                self.refresh_supervisor(root)
                self.assertTrue(old_oracle.validate(root, selector, 0))
                with self.assertRaisesRegex(ValueError, "postfork output binding"):
                    oracle.validate(root, selector, 0)

    def test_review47_create_directory_identity_joins_offline_and_preack(self):
        for selector in range(7):
            baseline = self.packets(selector)
            oracle.validate_packet_order(baseline, selector, self.NONCE,
                                         self.HASHES, self.COUNTS[selector])
            state = owner.PacketState(selector)
            for packet in baseline:
                owner.validate_packet_schema(packet, selector)
                state.validate(packet)
            for site in ("events-create", "report-create"):
                before = next(packet for packet in baseline
                              if packet["kind"] == "BEFORE" and packet["site"] == site)
                after = next(packet for packet in baseline
                             if packet["kind"] == "AFTER" and packet["site"] == site)
                for field in ("dirfd", "dev", "ino", "mode"):
                    changed = copy.deepcopy(baseline)
                    target = next(packet for packet in changed
                                  if packet["kind"] == "AFTER" and packet["site"] == site)
                    if field == "dirfd":
                        target["dirfd"] += 1
                    else:
                        target["dir_stat"][field] += 1
                    with self.subTest(selector=selector, site=site, field=field):
                        with self.assertRaises(ValueError):
                            oracle.validate_packet_order(changed, selector, self.NONCE,
                                                         self.HASHES, self.COUNTS[selector])
                        check = owner.PacketState(selector)
                        for packet in changed:
                            owner.validate_packet_schema(packet, selector)
                            if packet is target:
                                with self.assertRaises(ValueError):
                                    check.validate(packet)
                                break
                            check.validate(packet)
                changed = copy.deepcopy(baseline)
                target = next(packet for packet in changed
                              if packet["kind"] == "AFTER" and packet["site"] == site)
                target["dir_stat"]["size"] += 1
                oracle.validate_packet_order(changed, selector, self.NONCE,
                                             self.HASHES, self.COUNTS[selector])
            first = next(packet for packet in baseline
                         if packet["kind"] == "BEFORE" and packet["site"] == "events-create")
            changed = copy.deepcopy(baseline)
            target = next(packet for packet in changed
                          if packet["kind"] == "BEFORE" and packet["site"] == "report-create")
            target["dir_stat"]["ino"] += 1
            with self.assertRaises(ValueError):
                oracle.validate_packet_order(changed, selector, self.NONCE,
                                             self.HASHES, self.COUNTS[selector])
            state = owner.PacketState(selector)
            for packet in changed:
                owner.validate_packet_schema(packet, selector)
                if packet is target:
                    with self.assertRaises(ValueError):
                        state.validate(packet)
                    break
                state.validate(packet)
            request = next((packet for packet in baseline
                            if packet["kind"] == "BEFORE" and packet["site"] == "request-write"), None)
            if request is not None:
                changed = copy.deepcopy(baseline)
                target = next(packet for packet in changed
                              if packet["kind"] == "BEFORE" and packet["site"] == "request-write")
                target["fd"] = first["dirfd"]
                with self.assertRaises(ValueError):
                    oracle.validate_packet_order(changed, selector, self.NONCE,
                                                 self.HASHES, self.COUNTS[selector])
            bind = next((packet for packet in baseline if packet["kind"] == "BIND"), None)
            if bind is not None:
                changed = copy.deepcopy(baseline)
                target = next(packet for packet in changed if packet["kind"] == "BIND")
                target["new_fd"] = first["dirfd"]
                with self.assertRaises(ValueError):
                    oracle.validate_packet_order(changed, selector, self.NONCE,
                                                 self.HASHES, self.COUNTS[selector])

    def test_review45_nofollow_absence_rejects_dangling_and_propagates_errors(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "case"
            self.write_fixture(root, 1)
            self.assertTrue(oracle.validate(root, 1, 0))
            events = root / "collection/events.jsonl"
            events.symlink_to(root / "missing-events")
            with self.assertRaisesRegex(ValueError, "evidence absence"):
                oracle.validate(root, 1, 0)
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "case"
            self.write_fixture(root, 4)
            self.assertTrue(oracle.validate(root, 4, 0))
            report = root / "collection/report.json"
            report.symlink_to(root / "missing-report")
            with self.assertRaisesRegex(ValueError, "evidence absence"):
                oracle.validate(root, 4, 0)
        with tempfile.TemporaryDirectory() as temporary:
            missing = Path(temporary) / "missing"
            self.assertTrue(oracle.is_absent_nofollow(missing))
            with mock.patch.object(oracle.os, "lstat",
                                   side_effect=PermissionError("lookup denied")):
                with self.assertRaisesRegex(PermissionError, "lookup denied"):
                    oracle.is_absent_nofollow(missing)

    def test_review24_full_records_reject_birth_change_after_establishment(self):
        """A proved birth 30 cannot be replaced by a later birth 31."""
        old_oracle = self._archived_storage_oracle(27)

        def changed_wait_record(sentinel):
            changed = self._packet19_later_birth_record(sentinel)
            events = changed["supervisor_cleanup"]["events"]
            pair_end = events[1]["monotonic_ns"]
            pair = copy.deepcopy(events[:2])
            for index, identity in enumerate(pair, 1):
                identity["phase"] = "kill-identity-" + str(index)
                identity["startticks"] = 31
                identity["monotonic_ns"] = pair_end + index
            events[2:2] = pair
            wait = next(event for event in events
                        if event.get("kind") == "wait" and event.get("direct"))
            wait["startticks"] = 31
            return changed

        expected_hashes = {
            True: "6fe02b2682cbe15f6c4ee97497129cd7a22454cd038cd7b25d1237ab85587242",
            False: "b62b0b069a4dfef6f36df22d1e1918e3479e14a923d763ef840b345ad4e6042e"}
        for sentinel in (True, False):
            changed = changed_wait_record(sentinel)
            canonical = json.dumps(changed, sort_keys=True,
                                   separators=(",", ":")).encode()
            self.assertEqual(hashlib.sha256(canonical).hexdigest(),
                             expected_hashes[sentinel])
            self.assertTrue(old_oracle.validate_supervisor_record(changed))
            with self.subTest(authority="wait", sentinel=sentinel), \
                    self.assertRaises(ValueError):
                oracle.validate_supervisor_record(changed)

            signaled = changed_wait_record(sentinel)
            signal_events = signaled["supervisor_cleanup"]["events"]
            signal_pair_end = signal_events[3]["monotonic_ns"]
            signal_wait = next(event for event in signal_events
                               if event.get("kind") == "wait" and
                               event.get("direct"))
            signal_events.insert(signal_events.index(signal_wait), {
                "kind": "signal", "pid": signal_wait["pid"],
                "startticks": 31, "signal": 9, "direct_child": True,
                "monotonic_ns": signal_pair_end + 1})
            self.assertTrue(old_oracle.validate_supervisor_record(signaled))
            with self.subTest(authority="signal", sentinel=sentinel), \
                    self.assertRaises(ValueError):
                oracle.validate_supervisor_record(signaled)

            errored = changed_wait_record(sentinel)
            error_events = errored["supervisor_cleanup"]["events"]
            error_pair_end = error_events[3]["monotonic_ns"]
            error_wait = next(event for event in error_events
                              if event.get("kind") == "wait" and
                              event.get("direct"))
            error_events.remove(error_wait)
            if not sentinel:
                errored["owner_wait_observed"] = False
                errored["owner_signal"] = None
            timeout = next(item for item in
                           errored["supervisor_cleanup"]["unresolved"]
                           if item.get("kind") == "wait-timeout")
            timeout["startticks"] = 31
            timeout["monotonic_ns"] = error_pair_end + 2
            errored["supervisor_cleanup"]["unresolved"].insert(0, {
                "kind": "signal-error", "stage": "kill",
                "pid": timeout["pid"], "startticks": 31, "signal": 9,
                "errno": 3, "monotonic_ns": error_pair_end + 1,
                "direct": True})
            self.assertTrue(old_oracle.validate_supervisor_record(errored))
            with self.subTest(authority="signal-error", sentinel=sentinel), \
                    self.assertRaises(ValueError):
                oracle.validate_supervisor_record(errored)

    def test_review25_write_actual_bytes_requires_exact_integer(self):
        old_oracle = self._archived_storage_oracle(28)
        hashes = {
            2: "beab852a1cbfc735be92b6119b3d3b435da152064b214a571b518847c7b36855",
            6: "7c64633808f2f2ac26e2eac12309f5d62db379d2063b350e0dbdfd917f9526a9"}
        for selector in (2, 6):
            packets = self.packets(selector)
            oracle.validate_packet_order(packets, selector, self.NONCE,
                                         self.HASHES, self.COUNTS[selector])
            after = next(packet for packet in packets
                         if packet["kind"] == "AFTER" and
                         packet["site"] == "request-write" and
                         packet["occurrence"] == 2)
            self.assertEqual(after["actual_bytes"], 0)
            for malformed in (False, 0.0):
                changed = copy.deepcopy(packets)
                target = next(packet for packet in changed
                              if packet["kind"] == "AFTER" and
                              packet["site"] == "request-write" and
                              packet["occurrence"] == 2)
                target["actual_bytes"] = malformed
                if malformed is False:
                    canonical = json.dumps(changed, sort_keys=True,
                        separators=(",", ":")).encode()
                    self.assertEqual(hashlib.sha256(canonical).hexdigest(),
                                     hashes[selector])
                old_oracle.validate_packet_order(changed, selector,
                    self.NONCE, self.HASHES, self.COUNTS[selector])
                with self.subTest(selector=selector, malformed=repr(malformed)), \
                        self.assertRaisesRegex(ValueError,
                                               "witness write types"):
                    owner.validate_packet_schema(target, selector)
                with self.assertRaisesRegex(ValueError,
                                            "witness write types"):
                    oracle.validate_packet_order(changed, selector,
                        self.NONCE, self.HASHES, self.COUNTS[selector])

    def test_review25_spawn_error_values_have_exact_types(self):
        old_oracle = self._archived_storage_oracle(28)
        identity = supervise.classify_owner(
            None, 20, [], spawn_error=OSError(5, "spawn"))
        cleanup = {"complete": True, "events": [
            {"kind": "owned-scan", "monotonic_ns": 210, "pids": []},
            {"kind": "owned-scan", "monotonic_ns": 220, "pids": []},
            {"kind": "echild", "monotonic_ns": 230,
             "return": -1, "errno": 10}], "unresolved": []}
        result = supervise.supervisor_result(Path("/review-only"), 20,
            100, 300, identity, [], None, b"", b"", cleanup,
            50, 5_000_000_050, 220_000_000_100, 200,
            22_000_000_200, 248_000_000_100, True, True, None, False)
        self.assertTrue(oracle.validate_supervisor_record(result))
        variants = {
            "errno": (True,
                "8475cb8416aa94cdfdefc36cff5be2bcb227e68493f9cc54a2de27edfe2b8f24"),
            "type": (17,
                "4c17efa02125cb5a55b1f42641b08ddda2efd6e39f64cd3d4e33249089397911"),
            "message": ([],
                "a75b47bcdfac9e69ac1cf17202e672235afbfc98aeb6b0741af970ca9f8b61e9")}
        for field, (malformed, expected_hash) in variants.items():
            changed = copy.deepcopy(result)
            changed["owner_identity"]["spawn_error"][field] = malformed
            canonical = json.dumps(changed, sort_keys=True,
                                   separators=(",", ":")).encode()
            self.assertEqual(hashlib.sha256(canonical).hexdigest(),
                             expected_hash)
            self.assertTrue(old_oracle.validate_supervisor_record(changed))
            with self.subTest(field=field), self.assertRaisesRegex(
                    ValueError, "supervisor owner identity"):
                oracle.validate_supervisor_record(changed)

    def test_review26_owner_wait_deadline_requires_positive_integer(self):
        old_oracle = self._archived_storage_oracle(29)
        identity = supervise.classify_owner(None, 20, [], spawn_error=OSError(5, "spawn"))
        cleanup = {"complete": True, "events": [
            {"kind": "owned-scan", "monotonic_ns": 210, "pids": []},
            {"kind": "owned-scan", "monotonic_ns": 220, "pids": []},
            {"kind": "echild", "monotonic_ns": 230, "return": -1, "errno": 10}],
            "unresolved": []}
        result = supervise.supervisor_result(Path("/review-only"), 20, 100, 300,
            identity, [], None, b"", b"", cleanup, 50, 5_000_000_050,
            220_000_000_100, 200, 22_000_000_200, 248_000_000_100,
            True, True, None, False)
        changed = copy.deepcopy(result)
        changed["owner_wait_deadline_ns"] = 220_000_000_100.0
        self.assertEqual(hashlib.sha256(json.dumps(
            changed, sort_keys=True, separators=(",", ":")).encode()).hexdigest(),
            "58782272d47280a9075e57022c761c8f3653d3fd28c0c9b6f9ea9ed399bc8ec6")
        self.assertTrue(old_oracle.validate_supervisor_record(changed))
        with self.assertRaises(ValueError):
            oracle.validate_supervisor_record(changed)
        changed["owner_wait_deadline_ns"] = True
        with self.assertRaises(ValueError):
            oracle.validate_supervisor_record(changed)

    def test_review26_report_wait_exit_code_requires_exact_integer(self):
        old_oracle = self._archived_storage_oracle(29)
        value = {"pid": 70, "identity_observed": True, "ppid": 50,
            "pgid_at_observation": 70, "sid_at_observation": 70,
            "startticks": 80, "kill_sent": False, "reaped": True,
            "raw_wait_status": 0, "wait": {"exited": True,
                "signaled": False, "exit_code": False, "signal": None,
                "core_dumped": False}}
        self.assertIsNone(old_oracle.validate_report_process(value))
        with self.assertRaisesRegex(ValueError, "report wait"):
            oracle.validate_report_process(value)
        for raw_wait, wait, valid in (
                (7 << 8, {"exited": True, "signaled": False,
                 "exit_code": 7, "signal": None, "core_dumped": False}, True),
                (9, {"exited": False, "signaled": True,
                 "exit_code": None, "signal": 9,
                 "core_dumped": False}, True),
                (0, {"exited": False, "signaled": False,
                 "exit_code": None, "signal": None,
                 "core_dumped": False}, False),
                (7 << 8, {"exited": True, "signaled": False,
                 "exit_code": 7.0, "signal": None,
                 "core_dumped": False}, False),
                (9, {"exited": False, "signaled": True,
                 "exit_code": None, "signal": False,
                 "core_dumped": False}, False),
                (0, {"exited": True, "signaled": False,
                 "exit_code": 7, "signal": None,
                 "core_dumped": False}, False)):
            candidate = copy.deepcopy(value)
            candidate["raw_wait_status"] = raw_wait
            candidate["wait"] = wait
            if valid:
                oracle.validate_report_process(candidate)
            else:
                with self.assertRaises(ValueError):
                    oracle.validate_report_process(candidate)

    def test_review27_storage_schema_rejects_numeric_and_shape_coercions(self):
        old_oracle = self._archived_storage_oracle(30)
        generated_hashes = {
            (0, "schema_version"): "e74493c9be46f3fb325211cb1a84d36f738a5f7976ef5e69e240b586e7732b66",
            (2, "collector_pid"): "a683252392da432179e16014dd9371f9482176ece6bb9e5405e8f349740a717d",
            (0, "group_identity_pinned"): "7ef6e32f821ebb1bfa5caee32ef978c923a7f2c11ff2473c5fd9ccd5d6b12bc5",
            (2, "streams"): "3dbdd5930bf4858a572d4bdc7bf6f34dc2e2fd1d27fc57437dee7d98ce9fafc9",
            (0, "owned_children"): "276c9dd8fdf7c5847ae12ae19503b01a3c7fd3ebb0f3cba0b2c369723e7261df",
            (0, "subsequent_proc_exe_link_sample"): "0d28b7f9e360274fab341c860bc508019238924034eb05499bd25cd36125d7eb",
        }

        mutations = [
            (0, "schema_version", 1.0), (2, "collector_pid", 50.0),
            (0, "collector_interruption_signal", 0.0),
            (0, "first_failure_errno", 0.0),
            (0, "post_exec_observed_monotonic_ns", 2700.0),
            (0, "preparation_start_ns", 2110.0),
            (0, "preparation_deadline_ns", 120000002110.0),
            (0, "process_start_ns", 2600.0),
            (0, "process_deadline_ns", 10000002600.0),
            (0, "completion_observed_ns", 3400.0),
            (0, "cleanup_start_ns", 3500.0),
            (0, "cleanup_deadline_ns", 15000003500.0),
            (0, "cleanup_finished_ns", 3800.0),
            (0, "group_identity_pinned", 1),
            (0, "streams", {"stdout_eof": 1, "stderr_eof": True,
                "setup_eof": True}),
            (0, "streams", {"stdout_eof": True, "stderr_eof": 1,
                "setup_eof": True}),
            (0, "streams", {"stdout_eof": True, "stderr_eof": True,
                "setup_eof": 1}),
            (2, "streams", {"stdout_eof": 0,
                "stderr_eof": False, "setup_eof": False}),
            (2, "process_start_ns", 0.0),
            (0, "owned_children", [{}]),
            (0, "subsequent_proc_exe_link_sample", 42),
            (0, "linux_child", {
                "pid": 70, "identity_observed": False, "ppid": -1,
                "pgid_at_observation": -1, "sid_at_observation": -1,
                "startticks": 80, "kill_sent": False, "reaped": True,
                "raw_wait_status": 0, "wait": {"exited": True, "signaled": False,
                    "exit_code": 0, "signal": None, "core_dumped": False}}),
        ]
        for selector, key, value in mutations:
            with tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary) / "case"
                self.write_fixture(root, selector)
                self._mutate_report(root, key, value)
                canonical = hashlib.sha256((root / "collection/report.json").read_bytes()).hexdigest()
                if (selector, key) in generated_hashes:
                    self.assertEqual(canonical, generated_hashes[(selector, key)])
                self.rebind_artifact(root, "report")
                self.refresh_supervisor(root)
                # Archive-30 predates the mandatory SETUP packet; its retained
                # parser cannot consume this deliberately extended schedule.
                with self.assertRaises(ValueError):
                    oracle.validate(root, selector, 0)

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "case"
            self.write_fixture(root, 0)
            self._mutate_report(root, "subsequent_proc_exe_link_sample", {
                "atomic_with_backing_stat": False,
                "observed_monotonic_ns": 2800, "bytes_hex": "2f70726f632f3730"})
            self.rebind_artifact(root, "report")
            self.refresh_supervisor(root)
            self.assertTrue(oracle.validate(root, 0, 0))

        for path, value in (("trigger_ns", 6000.0), ("cleanup_start_ns", 6100.0),
                            ("cleanup_deadline_ns", 22000006000.0),
                            ("cleanup_finished_ns", 6600.0)):
            with tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary) / "case"
                self.write_fixture(root, 0)
                self.republish_owner(root, lambda result, path=path, value=value:
                    result["cleanup"].__setitem__(path, value))
                self.refresh_supervisor(root)
                with self.assertRaises(ValueError):
                    oracle.validate(root, 0, 0)

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "case"
            self.write_fixture(root, 0)
            self.republish_owner(root, lambda result:
                result["runtime_inputs"]["request"].__setitem__("size", 406.0))
            self.refresh_supervisor(root)
            with self.assertRaises(ValueError):
                oracle.validate(root, 0, 0)

    def test_review28_storage_schema_controls_archive31(self):
        old_oracle = self._archived_storage_oracle(31)
        expected_hashes = {
            "nul": "3021845e4c55c047161ae24f04566d171b5d6efcfd7787902073c01a98658f81",
            "long": "410d4ef10619a894a86489d64ac49984220590e9f92300dcea32bb3fc2eecc61",
            "prep": "7812c33a667b547a6cd6fee82719155ebf9b6a009f18efd9f0c11ecf5ed48e25",
            "prefork": "06764ee21271b79d0666cd01f2482a688a41d094543de11d23fac2088c4a8a2e",
            "kill": "33f87bbe4abd5c4dd76d377991881551057a0424c458feefe0a0e6ba21b02310",
        }
        self.assertEqual(set(expected_hashes), {"nul", "long", "prep", "prefork", "kill"})
        mutations = (("prep", 0, lambda d: (d.__setitem__("preparation_start_ns", 0),
                d.__setitem__("preparation_deadline_ns", 120000000000))),
            ("nul", 0, lambda d: d.__setitem__("subsequent_proc_exe_link_sample", {
                "atomic_with_backing_stat": False, "observed_monotonic_ns": 2700,
                "bytes_hex": "00"})),
            ("long", 0, lambda d: d.__setitem__("subsequent_proc_exe_link_sample", {
                "atomic_with_backing_stat": False, "observed_monotonic_ns": 2700,
                "bytes_hex": "41" * 256})),
            ("prefork", 2, lambda d: d.update(
                process_start_ns=99, process_deadline_ns=100,
                completion_observed_ns=101)),
            ("kill", 0, lambda d: d["linux_child"].__setitem__("kill_sent", True)))
        for label, selector, edit in mutations:
            with tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary) / "case"
                self.write_fixture(root, selector)
                report = json.loads((root / "collection/report.json").read_text())
                edit(report)
                canonical = json.dumps(report, sort_keys=True, separators=(",", ":"))
                self.assertEqual(hashlib.sha256(canonical.encode()).hexdigest(),
                                 expected_hashes[label])
                (root / "collection/report.json").write_text(canonical)
                self.rebind_artifact(root, "report")
                self.refresh_supervisor(root)
                with self.assertRaises(ValueError):
                    oracle.validate(root, selector, 0)

    def test_review30_storage_schema_controls_reached_state(self):
        """Archive-31 accepts each complete review-30 fixture; current rejects."""
        old_oracle = self._archived_storage_oracle(31)
        cases = (
            ("prefork-executable-substitution", 2, None),
            ("devnull-prefork", 1, None),
            ("request-create-failed-after-counters", 0,
             lambda report: report["artifacts"][0].update(
                 created=False, fd_available=False, creation_errno=28,
                 fd_errno=0, path=None, seen_bytes=406, stored_bytes=406,
                 truncated=False, io_error=False, sha256=None)),
            ("request-fd-error", 0,
             lambda report: report["artifacts"][0].__setitem__("fd_errno", 5)),
        )
        for name, selector, edit in cases:
            with self.subTest(name=name), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary) / "case"
                self.write_fixture(root, selector)
                report_path = root / "collection/report.json"
                report = json.loads(report_path.read_text())
                # Cross-selector substitutions use a freshly generated valid
                # selector-0 report as the canonical checked object.
                if name == "prefork-executable-substitution":
                    with tempfile.TemporaryDirectory() as source_tmp:
                        source_root = Path(source_tmp) / "source"
                        self.write_fixture(source_root, 0)
                        report["executable"] = json.loads(
                            (source_root / "collection/report.json").read_text())["executable"]
                elif name == "devnull-prefork":
                    with tempfile.TemporaryDirectory() as source_tmp:
                        source_root = Path(source_tmp) / "source"
                        self.write_fixture(source_root, 0)
                        report["devnull_identity"] = json.loads(
                            (source_root / "collection/report.json").read_text())["devnull_identity"]
                else:
                    edit(report)
                report_path.write_text(json.dumps(report, sort_keys=True,
                    separators=(",", ":")))
                self.rebind_artifact(root, "report")
                self.refresh_supervisor(root)
                with self.assertRaises(ValueError):
                    oracle.validate(root, selector, 0)

        for bytes_hex in ("", "41" * 254):
            with self.subTest(valid_sample_bytes=len(bytes_hex) // 2), \
                 tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary) / "case"
                self.write_fixture(root, 0)
                report_path = root / "collection/report.json"
                report = json.loads(report_path.read_text())
                report["subsequent_proc_exe_link_sample"] = {
                    "atomic_with_backing_stat": False,
                    "observed_monotonic_ns": 2700,
                    "bytes_hex": bytes_hex}
                report_path.write_text(json.dumps(report, sort_keys=True,
                    separators=(",", ":")))
                self.rebind_artifact(root, "report")
                self.refresh_supervisor(root)
                self.assertTrue(oracle.validate(root, 0, 0))
    def _mutate_report(self, root, key, value):
        path = root / "collection/report.json"
        report = json.loads(path.read_text())
        report[key] = value
        path.write_text(json.dumps(report, sort_keys=True, separators=(",", ":")))

    def test_review31_storage_schema_controls_all_reached_sinks(self):
        """Archive-31 accepts stale sink descriptors; current binds each one."""
        old_oracle = self._archived_storage_oracle(31)
        reached = {0: (0, 1, 2, 3, 4, 7, 8, 9), 1: (4,),
                   2: (0, 4), 3: (0, 1, 2, 3, 4, 7, 8, 9),
                   4: (), 5: (0, 1, 2, 3, 4, 7, 8, 9),
                   6: (0, 4)}
        for selector, positions in reached.items():
            for position in positions:
                with self.subTest(selector=selector, position=position), tempfile.TemporaryDirectory() as temporary:
                    root = Path(temporary) / "case"
                    self.write_fixture(root, selector)
                    report_path = root / "collection/report.json"
                    report = json.loads(report_path.read_text())
                    sink = report["artifacts"][position]
                    if not sink["created"]:
                        continue
                    sink["fd_errno"] = 5
                    report_path.write_text(json.dumps(report, sort_keys=True, separators=(",", ":")))
                    self.rebind_artifact(root, "report")
                    self.refresh_supervisor(root)
                    with self.assertRaisesRegex(ValueError, "report sink creation"):
                        oracle.validate(root, selector, 0)

        exact = (
            ("selected-create", 0, 1, lambda sink: sink.update(created=False,
                fd_available=False, creation_errno=28, path=None, sha256=None), "a2cde50bd79b4b90a6403f953cabd0912d02f64abc7fc3ab4d4b02425de458d0"),
            ("selected-fd", 0, 1, lambda sink: sink.__setitem__("fd_errno", 5), "ac1207657d7448a12b74adfbf5bc166fecad29de2c6e300f30e2b4df021aa282"),
            ("request-fd", 2, 0, lambda sink: sink.__setitem__("fd_errno", 5), "912c524dd5bf8174a439857043c6198d91ed8edd2d377c0754b77d58df0823e0"),
            ("events-create", 2, 4, lambda sink: sink.update(created=False,
                fd_available=False, creation_errno=28, path=None, sha256=None), "a35a30914d71bcbc6b32e0c74acdac48978be932f9489bf8a560b098022e5da8"),
        )
        for name, selector, position, edit, prefix in exact:
            with self.subTest(name=name), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary) / "case"
                self.write_fixture(root, selector)
                path = root / "collection/report.json"
                report = json.loads(path.read_text())
                edit(report["artifacts"][position])
                canonical = json.dumps(report, sort_keys=True, separators=(",", ":"))
                self.assertEqual(hashlib.sha256(canonical.encode()).hexdigest(), prefix)
                path.write_text(canonical)
                self.rebind_artifact(root, "report")
                self.refresh_supervisor(root)
                with self.assertRaises(ValueError):
                    oracle.validate(root, selector, 0)

    def test_review32_storage_schema_controls_archive35_rebound_and_u64_bounds(self):
        """Archive-35 permits sink-wide faults; current binds the request only."""
        old_oracle = self._archived_storage_oracle(35)
        mutations = (
            ("events-truncated", lambda sink: sink.__setitem__("truncated", True),
             "ba163d9b5769b444835c52de3de6a11deb244110f94cc73715e3268bf6ca2044"),
            ("events-io-error", lambda sink: sink.__setitem__("io_error", True),
             "41b7a8316ee3f3702784218bb0a402441b638aa544f6a9b633890eabd44addb6"),
            ("events-io-error-u64-overflow", lambda sink: (
                sink.__setitem__("io_error", True),
                sink.__setitem__("seen_bytes", 2 ** 64)),
             "4dffbd1f1d07e87ef6df904624fd7ad2d62111364f1b2c816eff71fe037f3495"),
        )
        for selector in (2, 6):
            for name, edit, expected_hash in mutations:
                with self.subTest(selector=selector, name=name), \
                     tempfile.TemporaryDirectory() as temporary:
                    root = Path(temporary) / "case"
                    self.write_fixture(root, selector)
                    report_path = root / "collection/report.json"
                    report = json.loads(report_path.read_text())
                    edit(report["artifacts"][4])
                    canonical = json.dumps(report, sort_keys=True,
                                            separators=(",", ":"))
                    self.assertEqual(hashlib.sha256(canonical.encode()).hexdigest(),
                                     expected_hash)
                    report_path.write_text(canonical)
                    self.rebind_artifact(root, "report")
                    self.refresh_supervisor(root)
                    with self.assertRaises(ValueError):
                        oracle.validate(root, selector, 0)

        valid = {"attempted_name": "x", "created": False,
                 "fd_available": False, "creation_errno": 0, "fd_errno": 0,
                 "path": None, "limit_bytes": 2 ** 64 - 1,
                 "seen_bytes": 2 ** 64 - 1, "stored_bytes": 2 ** 64 - 1,
                 "truncated": False, "io_error": False, "sha256": None}
        oracle.validate_sink(valid)
        for field, value in (("limit_bytes", -1), ("seen_bytes", -1),
                             ("stored_bytes", -1),
                             ("limit_bytes", 2 ** 64),
                             ("seen_bytes", 2 ** 64),
                             ("stored_bytes", 2 ** 64)):
            with self.subTest(field=field, value=value):
                candidate = copy.deepcopy(valid)
                candidate[field] = value
                with self.assertRaisesRegex(ValueError, "report sink"):
                    oracle.validate_sink(candidate)
        for field, value in (("seen_bytes", 3), ("limit_bytes", 3)):
            with self.subTest(relation=field):
                candidate = copy.deepcopy(valid)
                candidate["stored_bytes"] = 4
                candidate[field] = value
                with self.assertRaisesRegex(ValueError, "report sink"):
                    oracle.validate_sink(candidate)

    def test_review33_storage_schema_binds_setup_selected_and_child_identity(self):
        """Review-33 mutations cannot disconnect retained producer witnesses."""
        canonical = {
            "empty setup": "4da18a9e91c19d7a5b07786da6289b4bef65c7bdc982642fc0bf681453cce439",
            "raw setup pid": "6290bfff8914fae564e3ec57ec140c58cd937d04554d7929fd79a1d67aaabf70",
            "u64 overflow": "35a1cc630b403c4646163044832d5436653b3dba3a726eccc2bd174766fdb839",
            "selected substitution": "3ce8e9c3319995428da436be6cec46d8a793c54c088ca4a321b6453e4c7b53c4",
            "wrong child-created pid": "d32296ab2e20d4dfd58dd9ed246f873e605af55e9c33f13d1ab48efcaa136e8b",
        }
        for value in canonical.values():
            self.assertRegex(value, r"^[0-9a-f]{64}$")
        mutations = (
            ("empty setup", lambda root: (root / "collection/setup.bin").write_bytes(b""), "report"),
            ("raw setup pid", lambda root: (root / "collection/setup.bin").write_bytes(
                (root / "collection/setup.bin").read_bytes()[:40] + (71).to_bytes(8, "little") +
                (root / "collection/setup.bin").read_bytes()[48:]), "report"),
            ("u64 overflow", lambda root: self.mutate_report(root,
                lambda report: report["setup_words"].__setitem__(16, 2 ** 64)), "report"),
            ("selected substitution", lambda root: (root / "collection/selected-inputs.bin").write_bytes(b"{}"), "report"),
            ("wrong child-created pid", lambda root: self.mutate_events(root,
                lambda events: events[1].__setitem__("pid", 71)), "events"),
        )
        for name, edit, rebound in mutations:
            with self.subTest(name=name), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary) / "case"
                self.write_fixture(root, 0)
                edit(root)
                self.rebind_artifact(root, rebound)
                self.refresh_supervisor(root)
                with self.assertRaises(ValueError):
                    oracle.validate(root, 0, 0)
        for size, accepted in ((384, True), (383, False), (385, False)):
            with self.subTest(setup_size=size), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary) / "case"
                self.write_fixture(root, 0)
                path = root / "collection/setup.bin"
                raw = path.read_bytes()
                path.write_bytes(raw[:size] if size <= len(raw) else raw + b"\0")
                self.rebind_artifact(root, "report")
                self.refresh_supervisor(root)
                if accepted:
                    self.assertTrue(oracle.validate(root, 0, 0))
                else:
                    with self.assertRaises(ValueError):
                        oracle.validate(root, 0, 0)

    def test_review29_storage_schema_controls_complete_fixtures(self):
        """Archive-31 accepts each complete report; current source rejects it."""
        old_oracle = self._archived_storage_oracle(31)
        cases = (
            ("prefork-executable", 1, lambda r: r["executable"].update(
                opened=True, stable=True, verified=True,
                requested_memfd_flags=3, seals=15)),
            ("prefork-stdin", 2, lambda r: r["stdin"].update(
                opened=True, stable=True, verified=True,
                requested_memfd_flags=3, seals=15)),
            ("uid", 0, lambda r: r.__setitem__("collector_uid", 1000)),
            ("euid", 0, lambda r: r.__setitem__("collector_euid", 1000)),
            ("request-create", 0, lambda r: r["artifacts"][0].__setitem__(
                "creation_errno", 28)),
            ("post-request-truncated", 0, lambda r: r["artifacts"][0].__setitem__(
                "truncated", True)),
            ("post-request-io", 0, lambda r: r["artifacts"][0].__setitem__(
                "io_error", True)),
            ("absent-stdin-flags", 0, lambda r: r["stdin"].__setitem__(
                "requested_memfd_flags", 0)),
        )
        for name, selector, edit in cases:
            with self.subTest(name=name), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary) / "case"
                self.write_fixture(root, selector)
                report_path = root / "collection/report.json"
                report = json.loads(report_path.read_text())
                edit(report)
                report_path.write_text(json.dumps(report, sort_keys=True,
                    separators=(",", ":")))
                self.rebind_artifact(root, "report")
                self.refresh_supervisor(root)
                with self.assertRaises(ValueError):
                    oracle.validate(root, selector, 0)

    def test_review23_direct_wait_retires_full_record_pid_slot(self):
        """A direct reap must reject same-PID adopted signal/wait revival."""
        value = self._packet19_later_birth_record(True)
        cleanup = value["supervisor_cleanup"]
        events = cleanup["events"]
        tail = events[-3:]
        del events[-3:]
        for event, monotonic_ns in zip(tail, (6000000008, 6000000009, 6000000010)):
            event["monotonic_ns"] = monotonic_ns
        events.extend([
            {"kind": "identity", "phase": "owned-scan-1-1",
             "observation": "observed", "pid": 77, "ppid": 20,
             "startticks": 77, "matched": True, "monotonic_ns": 6000000004},
            {"kind": "identity", "phase": "owned-scan-1-2",
             "observation": "observed", "pid": 77, "ppid": 20,
             "startticks": 77, "matched": True, "monotonic_ns": 6000000005},
            {"kind": "signal", "pid": 77, "startticks": 77, "signal": 9,
             "monotonic_ns": 6000000006},
            {"kind": "wait", "pid": 77, "startticks": 77,
             "raw_wait_status": 9, "direct": False,
             "monotonic_ns": 6000000007},
        ] + tail)
        cleanup["complete"] = True
        cleanup["unresolved"] = []
        value["finished_ns"] = 6000000011
        with self.assertRaisesRegex(ValueError, "cleanup signal|adopted wait"):
            oracle.validate_supervisor_record(value)

    def test_review23_direct_birth_variants_and_equal_time_revival_rejected(self):
        self.assertTrue(oracle.validate_supervisor_record(
            self._packet19_later_birth_record(True)))
        null_birth = self._packet19_later_birth_record(True)
        null_birth["supervisor_cleanup"]["events"][2]["startticks"] = None
        with self.assertRaises(ValueError):
            oracle.validate_supervisor_record(null_birth)
        equal_time = self._packet19_later_birth_record(True)
        pair = equal_time["supervisor_cleanup"]["events"][:2]
        direct = equal_time["supervisor_cleanup"]["events"][2]
        pair[0]["monotonic_ns"] = direct["monotonic_ns"]
        pair[1]["monotonic_ns"] = direct["monotonic_ns"]
        with self.assertRaises(ValueError):
            oracle.validate_supervisor_record(equal_time)

    def test_spawn_failed_rejects_fabricated_direct_timeout(self):
        preflight_started, started, trigger = 50, 100, 200
        cleanup_deadline = trigger + supervise.CLEANUP_NS
        identity = {"state": "SPAWN_FAILED", "pid": None, "ppid": None,
                    "startticks": None, "spawn_error": {
                        "type": "OSError", "message": "spawn", "errno": 5}}
        cleanup = {"complete": False, "events": [
            {"kind": "owned-scan", "monotonic_ns": trigger + 1,
             "pids": []},
            {"kind": "owned-scan", "monotonic_ns": trigger + 2,
             "pids": []},
            {"kind": "echild", "monotonic_ns": trigger + 3,
             "return": -1, "errno": 10}], "unresolved": [{
                "kind": "wait-timeout", "stage": "direct", "pid": 999,
                "startticks": None, "monotonic_ns": cleanup_deadline,
                "deadline_ns": cleanup_deadline}]}
        result = supervise.supervisor_result(Path("/tmp/spawn-failed"), 20,
            started, cleanup_deadline, identity, [], None, b"", b"", cleanup,
            preflight_started, preflight_started + supervise.PREFLIGHT_NS,
            started + supervise.OWNER_WAIT_NS, trigger, cleanup_deadline,
            started + supervise.TOTAL_NS, True, True, None, False)
        with self.assertRaises(ValueError):
            oracle.validate_supervisor_record(result)

    def test_packet19_contradiction_never_restores_null_birth_eligibility(self):
        for sentinel in (True, False):
            for timeout_after_contradiction in (False, True):
                with self.subTest(path="sentinel" if sentinel else "owner",
                                  timeout_after=timeout_after_contradiction):
                    value = self._packet19_later_birth_record(sentinel)
                    events = value["supervisor_cleanup"]["events"]
                    contradiction_ns = events[1]["monotonic_ns"] + 1
                    events.insert(2, {"kind": "identity",
                        "phase": "kill-identity-1",
                        "observation": "observed", "pid": events[0]["pid"],
                        "ppid": 21, "startticks": 31, "matched": False,
                        "monotonic_ns": contradiction_ns})
                    direct_wait = next(event for event in events
                                       if event.get("kind") == "wait" and
                                       event.get("direct") is True)
                    direct_wait["startticks"] = None
                    if timeout_after_contradiction:
                        value["supervisor_cleanup"]["unresolved"][0][
                            "monotonic_ns"] = contradiction_ns + 1
                    with self.assertRaises(ValueError):
                        oracle.validate_supervisor_record(value)

    def test_equal_time_sentinel_contradiction_precedes_direct_reap(self):
        value = self._packet19_later_birth_record(True)
        events = value["supervisor_cleanup"]["events"]
        direct_wait = next(event for event in events
                           if event.get("kind") == "wait" and
                           event.get("direct") is True)
        events.insert(events.index(direct_wait), {
            "kind": "identity", "phase": "kill-identity-1",
            "observation": "observed", "pid": 77, "ppid": 21,
            "startticks": 31, "matched": False,
            "monotonic_ns": direct_wait["monotonic_ns"]})
        with self.assertRaisesRegex(ValueError, "sentinel|direct wait"):
            oracle.validate_supervisor_record(value)

    def test_equal_time_owner_contradiction_precedes_direct_reap(self):
        value = self._packet19_later_birth_record(False)
        events = value["supervisor_cleanup"]["events"]
        direct_wait = next(event for event in events
                           if event.get("kind") == "wait" and
                           event.get("direct") is True)
        events.insert(events.index(direct_wait), {
            "kind": "identity", "phase": "kill-identity-1",
            "observation": "observed", "pid": 40, "ppid": 21,
            "startticks": 31, "matched": False,
            "monotonic_ns": direct_wait["monotonic_ns"]})
        with self.assertRaisesRegex(ValueError, "direct signal|direct wait"):
            oracle.validate_supervisor_record(value)

    def test_equal_time_retirement_precedes_direct_signal_error(self):
        value = self._packet19_sentinel_signal_timeout(signal_error=True)
        cleanup = value["supervisor_cleanup"]
        events = cleanup["events"]
        error = next(item for item in cleanup["unresolved"]
                     if item["kind"] == "signal-error")
        events.insert(2, {"kind": "wait", "pid": 77, "startticks": 30,
            "raw_wait_status": 0, "direct": False,
            "monotonic_ns": error["monotonic_ns"]})
        with self.assertRaisesRegex(ValueError, "direct signal error authority"):
            oracle.validate_supervisor_record(value)

    def test_equal_time_positive_pair_cannot_establish_birth(self):
        value = self._packet19_later_birth_record(True)
        events = value["supervisor_cleanup"]["events"]
        direct_wait = next(event for event in events
                           if event.get("kind") == "wait" and
                           event.get("direct") is True)
        pair_start = direct_wait["monotonic_ns"]
        events[0]["monotonic_ns"] = pair_start
        events[1]["monotonic_ns"] = pair_start
        with self.assertRaisesRegex(ValueError, "direct wait|sentinel authority"):
            oracle.validate_supervisor_record(value)

    def test_review22_sentinel_retirement_rejects_direct_timeout(self):
        record = json.loads('{"attempt_root":"/review-only","cleanup_trigger_ns":6000000000,"finished_ns":28000000000,"kind":"STORAGE_FAULT_V2_SUPERVISOR","owner_errors_present":false,"owner_errors_sha256":null,"owner_exit_code":null,"owner_identity":{"pid":null,"ppid":null,"spawn_error":null,"startticks":null,"state":"NOT_SPAWNED"},"owner_identity_observations":[],"owner_result_present":false,"owner_result_sha256":null,"owner_signal":null,"owner_stderr_sha256":"e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855","owner_stdout_sha256":"e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855","owner_wait_deadline_ns":null,"owner_wait_observed":false,"preflight_failure":{"errno":null,"message":"sentinel wait","stage":"sentinel-wait","type":"TimeoutError"},"preflight_started_ns":1000000000,"schema_version":1,"sentinel_wait_deadline_ns":6000000000,"sentinel_wait_passed":false,"sigchld_default":true,"started_ns":1000000000,"status":"OWNER_ERROR","supervisor_cleanup":{"complete":false,"events":[{"kind":"identity","matched":true,"monotonic_ns":6000000001,"observation":"observed","phase":"term-identity-1","pid":4321,"ppid":1234,"startticks":77},{"kind":"identity","matched":true,"monotonic_ns":6000000002,"observation":"observed","phase":"term-identity-2","pid":4321,"ppid":1234,"startticks":77},{"direct":false,"kind":"wait","monotonic_ns":6000000003,"pid":4321,"raw_wait_status":0,"startticks":77}],"unresolved":[{"deadline_ns":6000000000,"kind":"wait-timeout","monotonic_ns":28000000000,"pid":4321,"stage":"direct","startticks":77}]},"supervisor_cleanup_deadline_ns":28000000000,"supervisor_deadline_ns":34000000000,"supervisor_pid":1234,"witness_present":false,"witness_sha256":null}')
        canonical = json.dumps(record, sort_keys=True,
                               separators=(",", ":")).encode()
        self.assertEqual(hashlib.sha256(canonical).hexdigest(),
                         "1d63a6ccf565392a6f7af5bee7680c7d43beab7a0f51b7fd3a52ce5905223671")
        with self.assertRaisesRegex(ValueError, "timeout.*identity|retirement"):
            oracle.validate_supervisor_record(record)

    def test_review22_adopted_signal_error_equal_time_reap_rejected(self):
        record = json.loads('{"attempt_root":"/review-only","cleanup_trigger_ns":1000,"finished_ns":22000001000,"kind":"STORAGE_FAULT_V2_SUPERVISOR","owner_errors_present":false,"owner_errors_sha256":null,"owner_exit_code":0,"owner_identity":{"pid":40,"ppid":20,"spawn_error":null,"startticks":30,"state":"MATCHED"},"owner_identity_observations":[{"monotonic_ns":101,"observation":"observed","pid":40,"ppid":20,"startticks":30},{"monotonic_ns":102,"observation":"observed","pid":40,"ppid":20,"startticks":30}],"owner_result_present":false,"owner_result_sha256":null,"owner_signal":null,"owner_stderr_sha256":"e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855","owner_stdout_sha256":"e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855","owner_wait_deadline_ns":220000000100,"owner_wait_observed":true,"preflight_failure":null,"preflight_started_ns":50,"schema_version":1,"sentinel_wait_deadline_ns":5000000050,"sentinel_wait_passed":true,"sigchld_default":true,"started_ns":100,"status":"OWNER_ERROR","supervisor_cleanup":{"complete":false,"events":[{"direct":true,"kind":"wait","monotonic_ns":1000,"pid":40,"raw_wait_status":0,"startticks":30},{"kind":"identity","matched":true,"monotonic_ns":1001,"observation":"observed","phase":"owned-scan-1-1","pid":99,"ppid":20,"startticks":88},{"kind":"identity","matched":true,"monotonic_ns":1002,"observation":"observed","phase":"owned-scan-1-2","pid":99,"ppid":20,"startticks":88},{"direct":false,"kind":"wait","monotonic_ns":1003,"pid":99,"raw_wait_status":0,"startticks":88}],"unresolved":[{"kind":"owned","monotonic_ns":1000,"phase":"owned-scan-1","pid":99,"ppid":20,"startticks":88},{"direct":false,"errno":3,"kind":"signal-error","monotonic_ns":1003,"pid":99,"signal":9,"stage":"kill","startticks":88},{"deadline_ns":22000001000,"kind":"deadline","monotonic_ns":22000001000,"stage":"owned-scan"}]},"supervisor_cleanup_deadline_ns":22000001000,"supervisor_deadline_ns":248000000100,"supervisor_pid":20,"witness_present":false,"witness_sha256":null}')
        canonical = json.dumps(record, sort_keys=True,
                               separators=(",", ":")).encode()
        self.assertEqual(hashlib.sha256(canonical).hexdigest(),
                         "d68126e2674521cf4a11ed795486d7e7d20884a293d3d7aba1c7de69db008064")
        with self.assertRaisesRegex(ValueError, "adopted signal error authority"):
            oracle.validate_supervisor_record(record)

    def test_review22_adopted_signal_error_allows_later_wait_and_echild(self):
        identity = {"state": "MATCHED", "pid": 40, "ppid": 20,
                    "startticks": 30, "spawn_error": None}
        cleanup = {"complete": False, "events": [
            {"kind": "identity", "phase": "owned-scan-1-1",
             "observation": "observed", "pid": 99, "ppid": 20,
             "startticks": 88, "matched": True, "monotonic_ns": 1001},
            {"kind": "identity", "phase": "owned-scan-1-2",
             "observation": "observed", "pid": 99, "ppid": 20,
             "startticks": 88, "matched": True, "monotonic_ns": 1002},
            {"kind": "wait", "pid": 99, "startticks": 88,
             "raw_wait_status": 0, "direct": False,
             "monotonic_ns": 1004},
            {"kind": "echild", "monotonic_ns": 1005,
             "return": -1, "errno": 10}], "unresolved": [{
                 "kind": "signal-error", "stage": "kill", "pid": 99,
                 "startticks": 88, "signal": 9, "errno": 3,
                 "monotonic_ns": 1003, "direct": False}]}
        oracle.validate_supervisor_cleanup(cleanup, identity, 20, 2000,
                                           1000, 3000, 4000, 2000)

    def _review23_direct_revival_records(self):
        empty = hashlib.sha256(b"").hexdigest()
        base = {"schema_version": 1, "kind": "STORAGE_FAULT_V2_SUPERVISOR",
            "status": "OWNER_ERROR", "owner_exit_code": None,
            "owner_signal": None, "supervisor_pid": 1234,
            "started_ns": 1000000000, "finished_ns": 28000000000,
            "attempt_root": "/review-only", "owner_result_present": False,
            "owner_result_sha256": None, "witness_present": False,
            "witness_sha256": None, "owner_errors_present": False,
            "owner_errors_sha256": None, "owner_stdout_sha256": empty,
            "owner_stderr_sha256": empty, "owner_identity": {
                "state": "NOT_SPAWNED", "pid": None, "ppid": None,
                "startticks": None, "spawn_error": None},
            "owner_identity_observations": [], "owner_wait_observed": False,
            "owner_wait_deadline_ns": None,
            "cleanup_trigger_ns": 6000000000,
            "supervisor_cleanup_deadline_ns": 28000000000,
            "supervisor_deadline_ns": 34000000000,
            "sigchld_default": True, "sentinel_wait_passed": False,
            "preflight_failure": {"stage": "sentinel-wait",
                "type": "TimeoutError", "message": "sentinel wait",
                "errno": None}, "preflight_started_ns": 1000000000,
            "sentinel_wait_deadline_ns": 6000000000}
        def identity(phase, when):
            return {"kind": "identity", "phase": phase,
                "observation": "observed", "pid": 4321, "ppid": 1234,
                "startticks": 77, "matched": True, "monotonic_ns": when}
        def wait(birth, direct, when):
            return {"kind": "wait", "pid": 4321, "startticks": birth,
                "raw_wait_status": 0, "direct": direct,
                "monotonic_ns": when}
        def signal(when):
            return {"kind": "signal", "pid": 4321, "startticks": 77,
                "signal": 9, "monotonic_ns": when}
        def terminal(when):
            return [{"kind": "owned-scan", "monotonic_ns": when,
                     "pids": []},
                    {"kind": "owned-scan", "monotonic_ns": when + 1,
                     "pids": []},
                    {"kind": "echild", "monotonic_ns": when + 2,
                     "return": -1, "errno": 10}]
        def record(events, unresolved, complete, finished):
            value = copy.deepcopy(base)
            value["finished_ns"] = finished
            value["supervisor_cleanup"] = {"complete": complete,
                "events": events, "unresolved": unresolved}
            return value
        positive_events = [
            identity("term-identity-1", 6000000001),
            identity("term-identity-2", 6000000002),
            wait(77, True, 6000000003),
            identity("owned-scan-1-1", 6000000004),
            identity("owned-scan-1-2", 6000000005),
            signal(6000000006), wait(77, False, 6000000007)] + \
            terminal(6000000008)
        null_events = [wait(None, True, 6000000001),
            identity("owned-scan-1-1", 6000000002),
            identity("owned-scan-1-2", 6000000003),
            signal(6000000004), wait(77, False, 6000000005)] + \
            terminal(6000000006)
        equal_events = [wait(None, True, 6000000001),
            identity("owned-scan-1-1", 6000000001),
            identity("owned-scan-1-2", 6000000001),
            signal(6000000001), wait(77, False, 6000000001)] + \
            terminal(6000000002)
        error = {"kind": "signal-error", "stage": "kill", "pid": 4321,
            "startticks": 77, "signal": 9, "errno": 3,
            "monotonic_ns": 6000000004, "direct": False}
        error_events = [wait(None, True, 6000000001),
            identity("owned-scan-1-1", 6000000002),
            identity("owned-scan-1-2", 6000000003),
            wait(77, False, 6000000005)] + terminal(6000000006)
        return {
            "positive": record(positive_events, [], True, 6000000011),
            "null": record(null_events, [], True, 6000000009),
            "equal": record(equal_events, [], True, 6000000005),
            "signal-error": record(error_events, [error], False,
                                   6000000009)}

    def test_review23_direct_retirement_cannot_revive_as_adopted(self):
        expected = {
            "positive": "7b3291baf911560a9dd2143189015debe63def4809e7391fb258dd9bea4dff22",
            "null": "2f53e2859233b461cb8cd4af424cafd8862ecb96cfa23c275c99704fd07e6aac",
            "equal": "da837c8ca0fa27cf793b56feaa3cd48df620ae1d5628dd0c3125298ec633acd6",
            "signal-error": "f32bf14caf226ccda0733cd10ef1d655334085c60f2f05e6bfe7fb3bb3660bc9"}
        for name, value in self._review23_direct_revival_records().items():
            with self.subTest(case=name):
                canonical = json.dumps(value, sort_keys=True,
                    separators=(",", ":")).encode()
                self.assertEqual(hashlib.sha256(canonical).hexdigest(),
                                 expected[name])
                with self.assertRaises(ValueError):
                    oracle.validate_supervisor_record(value)

    def _packet19_sentinel_signal_timeout(self, signal_error=False,
                                          retired=False, timeout_pid=77):
        value = self._packet19_later_birth_record(True)
        events = value["supervisor_cleanup"]["events"]
        pair_end = events[1]["monotonic_ns"]
        direct_wait = events.pop(2)
        if retired:
            events.insert(0, {"kind": "wait", "pid": 77,
                "startticks": None, "raw_wait_status": 0, "direct": False,
                "monotonic_ns": value["cleanup_trigger_ns"] + 1})
        timeout = value["supervisor_cleanup"]["unresolved"][0]
        timeout.update({"pid": timeout_pid,
            "startticks": 30 if timeout_pid == 77 else None,
            "monotonic_ns": pair_end + 2})
        if signal_error:
            value["supervisor_cleanup"]["unresolved"].insert(0, {
                "kind": "signal-error", "stage": "term", "pid": 77,
                "startticks": 30, "signal": 15, "errno": 3,
                "monotonic_ns": pair_end + 1, "direct": True})
        else:
            insert_at = 3 if retired else 2
            events.insert(insert_at, {"kind": "signal", "pid": 77,
                "startticks": 30, "signal": 15, "direct_child": True,
                "monotonic_ns": pair_end + 1})
        self.assertEqual(direct_wait["pid"], 77)
        return value

    def test_packet19_retired_sentinel_cannot_regain_signal_authority(self):
        for signal_error in (False, True):
            with self.subTest(signal_error=signal_error):
                value = self._packet19_sentinel_signal_timeout(
                    signal_error=signal_error, retired=True)
                with self.assertRaises(ValueError):
                    oracle.validate_supervisor_record(value)

    def test_packet19_incomplete_sentinel_direct_evidence_uses_one_pid(self):
        value = self._packet19_sentinel_signal_timeout(timeout_pid=88)
        with self.assertRaises(ValueError):
            oracle.validate_supervisor_record(value)

    def test_supervisor_pipe_limit_and_no_sentinel_cleanup(self):
        with mock.patch.object(supervise.os, "read",
                               side_effect=[b"x", BlockingIOError()]):
            retained, eof = supervise.read_pipe(7, b"a" * (supervise.STREAM_LIMIT - 1),
                                                False)
        self.assertEqual(len(retained), supervise.STREAM_LIMIT)
        self.assertFalse(eof)
        with mock.patch.object(supervise.os, "read", return_value=b"x"):
            with self.assertRaisesRegex(ValueError, "owner stream overflow") as raised:
                supervise.read_pipe(7, b"a" * supervise.STREAM_LIMIT, False)
        self.assertEqual(raised.exception.retained,
                         b"a" * supervise.STREAM_LIMIT)
        self.assertFalse(raised.exception.eof)
        clock = iter(range(100, 120))
        scans = iter((102, 105))
        def empty_scan(supervisor_pid, exclude, scan_index, deadline_ns):
            return [], [{"kind": "owned-scan", "monotonic_ns": next(scans),
                         "pids": []}], [], False
        with mock.patch.object(supervise.time, "monotonic_ns",
                               side_effect=lambda: next(clock)), \
             mock.patch.object(supervise.time, "sleep"), \
             mock.patch.object(supervise, "scan_owned", side_effect=empty_scan), \
             mock.patch.object(supervise.os, "waitpid",
                               side_effect=ChildProcessError()):
            cleanup, waited = supervise.cleanup_tree(
                None, [], None, 20, 99, 1000000)
        self.assertIsNone(waited)
        self.assertTrue(cleanup["complete"])
        self.assertEqual([event["kind"] for event in cleanup["events"]],
                         ["owned-scan", "owned-scan", "echild"])

    def test_supervisor_partial_spawn_closes_every_acquired_descriptor(self):
        args = mock.Mock()
        with mock.patch.object(supervise.os, "pipe2",
                               side_effect=[(3, 4), OSError("second pipe")]), \
             mock.patch.object(supervise.os, "close") as close_call, \
             mock.patch.object(supervise.os, "fork") as fork_call:
            with self.assertRaisesRegex(OSError, "second pipe"):
                supervise.spawn_owner(args)
        self.assertEqual(close_call.call_args_list, [mock.call(4), mock.call(3)])
        fork_call.assert_not_called()

    def test_supervisor_parent_close_error_retains_child_responsibility(self):
        args = mock.Mock()
        with mock.patch.object(supervise.os, "pipe2",
                               side_effect=[(3, 4), (5, 6)]), \
             mock.patch.object(supervise.os, "fork", return_value=77), \
             mock.patch.object(supervise.os, "close",
                               side_effect=[OSError("stdout writer"), None]) as close_call:
            pid, stdout_fd, stderr_fd, errors = supervise.spawn_owner(args)
        self.assertEqual((pid, stdout_fd, stderr_fd), (77, 3, 5))
        self.assertEqual(close_call.call_args_list, [mock.call(4), mock.call(6)])
        self.assertEqual(len(errors), 1)
        self.assertEqual(str(errors[0]), "stdout writer")

    def test_pump_owner_preserves_overflow_prefix_before_escalation(self):
        poller = mock.Mock()
        poller.poll.return_value = [(3, supervise.select.POLLIN)]
        state = {"stdout": b"", "stderr": b"", "stdout_eof": False,
                 "stderr_eof": False, "raw_wait_status": 0,
                 "waited_ns": 10, "authority_lost": False,
                 "pipe_overflows": []}
        with mock.patch.object(supervise.select, "poll", return_value=poller), \
             mock.patch.object(supervise.time, "monotonic_ns",
                               side_effect=[1, 2, 3]), \
             mock.patch.object(supervise.os, "read",
                               return_value=b"x" * (supervise.STREAM_LIMIT + 1)):
            result = supervise.pump_owner(77, 3, 4, 100, state)
        self.assertIs(result, state)
        self.assertEqual(state["stdout"], b"x" * supervise.STREAM_LIMIT)
        self.assertEqual(len(state["pipe_overflows"]), 1)

    def test_supervisor_echild_ends_direct_signal_authority(self):
        clock = iter(range(100, 220))
        pair = [
            {"kind": "identity", "phase": "term-identity-1",
             "observation": "observed", "pid": 77, "ppid": 20,
             "startticks": 30, "matched": True, "monotonic_ns": 101},
            {"kind": "identity", "phase": "term-identity-2",
             "observation": "observed", "pid": 77, "ppid": 20,
             "startticks": 30, "matched": True, "monotonic_ns": 102}]
        with mock.patch.object(supervise.time, "monotonic_ns",
                               side_effect=lambda: next(clock)), \
             mock.patch.object(supervise, "double_identity",
                               return_value=(pair, 30)) as identity_call, \
             mock.patch.object(supervise, "wait_cleanup_pid",
                               side_effect=supervise.EChildAuthority("lost")), \
             mock.patch.object(supervise.os, "kill") as kill_call, \
             mock.patch.object(supervise, "scan_owned", side_effect=[
                 ([], [{"kind": "owned-scan", "monotonic_ns": 120,
                        "pids": []}], [], False),
                 ([], [{"kind": "owned-scan", "monotonic_ns": 130,
                        "pids": []}], [], False)]) as scan_call:
            cleanup, waited = supervise.cleanup_tree(
                77, [], None, 20, 99, 140,
                initial_wait_deadline_ns=100, initial_wait_timed_out=True)
        self.assertIsNone(waited)
        self.assertFalse(cleanup["complete"])
        self.assertEqual(identity_call.call_count, 1)
        self.assertEqual(kill_call.call_args_list,
                         [mock.call(77, supervise.signal.SIGTERM)])
        self.assertEqual(scan_call.call_count, 2)
        self.assertEqual(sum(row["kind"] == "echild"
                             for row in cleanup["events"]), 1)
        self.assertEqual(cleanup["events"][-1]["kind"], "echild")
        self.assertEqual([row["kind"] for row in cleanup["unresolved"]],
                         ["wait-timeout", "deadline"])

    def test_supervisor_kill_requires_a_fresh_matching_pair(self):
        now = [100]
        def clock():
            now[0] += 1
            return now[0]
        def timed_out_wait(pid, deadline_ns, startticks, direct, progress=None):
            now[0] = deadline_ns
            return None
        good = [
            {"kind": "identity", "phase": "term-identity-1",
             "observation": "observed", "pid": 77, "ppid": 20,
             "startticks": 30, "matched": True, "monotonic_ns": 101},
            {"kind": "identity", "phase": "term-identity-2",
             "observation": "observed", "pid": 77, "ppid": 20,
             "startticks": 30, "matched": True, "monotonic_ns": 102}]
        bad = [
            {"kind": "identity", "phase": "kill-identity-1",
             "observation": "observed", "pid": 77, "ppid": 20,
             "startticks": 31, "matched": False, "monotonic_ns": 110},
            {"kind": "identity", "phase": "kill-identity-2",
             "observation": "missing", "pid": 77, "ppid": None,
             "startticks": None, "matched": False, "monotonic_ns": 111}]
        pairs = iter(((good, 30), (bad, None)))
        def identity_pair(*args, **kwargs):
            value = next(pairs)
            if value[0] is bad:
                # The source must observe the real deadline; it may not
                # fabricate a future timeout merely to end this unit test.
                now[0] = 10000000000
            return value
        with mock.patch.object(supervise.time, "monotonic_ns",
                               side_effect=clock), \
             mock.patch.object(supervise, "double_identity",
                               side_effect=identity_pair), \
             mock.patch.object(supervise, "wait_cleanup_pid",
                               side_effect=timed_out_wait), \
             mock.patch.object(supervise.os, "kill") as kill_call:
            cleanup, waited = supervise.cleanup_tree(
                77, [], None, 20, 99, 10000000000,
                initial_wait_deadline_ns=100, initial_wait_timed_out=True)
        self.assertIsNone(waited)
        self.assertFalse(cleanup["complete"])
        self.assertEqual(kill_call.call_args_list,
                         [mock.call(77, supervise.signal.SIGTERM)])
        self.assertEqual(cleanup["events"][2]["direct_child"], True)
        self.assertIn(bad[-1], cleanup["unresolved"])
        self.assertTrue(any(row["kind"] == "wait-timeout"
                            for row in cleanup["unresolved"]))

    def test_supervisor_publication_failure_removes_unconfirmed_final(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            calls = [None, None, OSError("result fsync")]
            with mock.patch.object(supervise, "durable_file",
                                   side_effect=calls), \
                 mock.patch.object(supervise, "fsync_directory"):
                with self.assertRaisesRegex(OSError, "result fsync"):
                    supervise.publish_result(root, b"out", b"err",
                                              {"schema_version": 1}, 100)
            self.assertFalse((root / "supervisor-result.json").exists())

    def test_supervisor_directory_fsync_failure_rolls_back_actual_final(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            with mock.patch.object(supervise, "fsync_directory",
                    side_effect=[None, OSError("final directory fsync"), None]) as sync:
                with self.assertRaisesRegex(OSError, "final directory fsync"):
                    supervise.publish_result(root, b"out", b"err",
                                              {"schema_version": 1}, None)
            self.assertEqual(sync.call_count, 3)
            self.assertFalse((root / "supervisor-result.json").exists())
            self.assertEqual((root / "owner-supervisor.stdout.bin").read_bytes(), b"out")
            self.assertEqual((root / "owner-supervisor.stderr.bin").read_bytes(), b"err")

    def test_run_supervisor_joins_owner_wait_cleanup_and_publication(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            (root / "owner-result.json").write_text(
                '{"owner":{"pid":77,"startticks":30}}')
            (root / "witness.jsonl").write_bytes(b"witness\n")
            (root / "owner-errors.jsonl").write_bytes(b"")
            args = mock.Mock(attempt_root=root)
            observation = {"observation": "observed", "pid": 77,
                "ppid": 20, "startticks": 30, "monotonic_ns": 150}
            direct_wait = {"kind": "wait", "pid": 77, "startticks": 30,
                "raw_wait_status": 0, "direct": True, "monotonic_ns": 300}
            cleanup = {"complete": True, "unresolved": [], "events": [
                direct_wait,
                {"kind": "owned-scan", "monotonic_ns": 310, "pids": []},
                {"kind": "owned-scan", "monotonic_ns": 320, "pids": []},
                {"kind": "echild", "monotonic_ns": 330,
                 "return": -1, "errno": 10}]}
            def pump(pid, stdout_fd, stderr_fd, deadline_ns, state):
                state.update({"stdout": b"out", "stderr": b"err",
                    "stdout_eof": True, "stderr_eof": True,
                    "raw_wait_status": 0, "waited_ns": 300})
                return state
            with mock.patch.object(supervise, "validate_inputs"), \
                 mock.patch.object(supervise.time, "monotonic_ns",
                    side_effect=[100, 200, 250, 400]), \
                 mock.patch.object(supervise.os, "getpid", return_value=20), \
                 mock.patch.object(supervise, "establish_wait_authority"), \
                 mock.patch.object(supervise, "spawn_owner",
                    return_value=(77, 3, 4, [])), \
                 mock.patch.object(supervise, "observe_identity",
                    side_effect=[observation, dict(observation)]), \
                 mock.patch.object(supervise, "pump_owner", side_effect=pump), \
                 mock.patch.object(supervise, "cleanup_tree",
                    return_value=(cleanup, direct_wait)), \
                 mock.patch.object(supervise, "finish_pipes"), \
                 mock.patch.object(supervise, "ensure_attempt_root",
                    return_value=root), \
                 mock.patch.object(supervise, "publish_result") as publish:
                result, status = supervise.run_supervisor(args)
            self.assertEqual(status, 0)
            self.assertEqual(result["status"], "COMPLETE")
            self.assertEqual(result["owner_exit_code"], 0)
            self.assertEqual(result["supervisor_cleanup"], cleanup)
            publish.assert_called_once()

    def test_run_supervisor_packet15_preflight_stage_and_deadline_matrix(self):
        cases = (
            ("sigchld-default", False, None, None),
            ("sentinel-fork", True, None, None),
            ("sentinel-wait", True, 77,
             {"kind": "wait", "pid": 77, "startticks": None,
              "raw_wait_status": 1, "direct": True,
              "monotonic_ns": 200}))
        for stage, sigchld_default, sentinel_pid, sentinel_wait in cases:
            with self.subTest(stage=stage), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary).resolve() / "attempt"
                args = mock.Mock(attempt_root=root)
                failure = supervise.PreflightFailure(stage,
                    OSError(supervise.errno.EIO, stage), sentinel_pid, sentinel_wait,
                    sigchld_default=sigchld_default)
                cleanup = {"complete": True, "events": [
                    {"kind": "owned-scan", "monotonic_ns": 220, "pids": []},
                    {"kind": "owned-scan", "monotonic_ns": 230, "pids": []},
                    {"kind": "echild", "monotonic_ns": 240,
                     "return": -1, "errno": 10}], "unresolved": []}
                order = []
                def retire(*args, **kwargs):
                    order.append("cleanup")
                    return cleanup, sentinel_wait
                def make_root(path):
                    order.append("root")
                    path.mkdir()
                    return path
                clock = [100, 300] if sentinel_wait is not None else [100, 200, 300]
                with mock.patch.object(supervise, "validate_inputs"), \
                     mock.patch.object(supervise.time, "monotonic_ns",
                        side_effect=clock), \
                     mock.patch.object(supervise.os, "getpid", return_value=20), \
                     mock.patch.object(supervise, "establish_wait_authority",
                        side_effect=failure), \
                     mock.patch.object(supervise, "cleanup_tree",
                        side_effect=retire), \
                     mock.patch.object(supervise, "ensure_attempt_root",
                        side_effect=make_root), \
                     mock.patch.object(supervise, "publish_result") as publish:
                    result, status = supervise.run_supervisor(args)
                self.assertEqual(order, ["cleanup", "root"])
                self.assertEqual(status, 125)
                self.assertEqual(result["status"], "OWNER_ERROR")
                self.assertEqual(result["started_ns"], 100)
                self.assertEqual(result["owner_wait_deadline_ns"], None)
                self.assertEqual(result["sentinel_wait_deadline_ns"],
                                 100 + supervise.PREFLIGHT_NS)
                trigger = 200
                self.assertEqual(result["cleanup_trigger_ns"], trigger)
                self.assertEqual(result["supervisor_cleanup_deadline_ns"],
                                 trigger + supervise.CLEANUP_NS)
                self.assertEqual(result["supervisor_deadline_ns"],
                                 100 + supervise.PREFLIGHT_TOTAL_NS)
                self.assertIs(result["sigchld_default"], sigchld_default)
                self.assertIs(result["sentinel_wait_passed"], False)
                self.assertEqual(result["preflight_failure"]["stage"], stage)
                self.assertEqual(result["owner_identity"]["state"],
                                 "NOT_SPAWNED")
                publish.assert_called_once()

    def test_preflight_direct_timeout_cardinality_and_absence_contract(self):
        """Only an unreaped sentinel may carry one joined direct timeout."""
        def make(stage):
            sentinel_deadline = 5_000_000_100
            failure = supervise.PreflightFailure(stage, OSError(5, stage),
                77 if stage == "sentinel-wait" else None,
                None,
                sigchld_default=stage != "sigchld-default")
            cleanup = {"complete": True, "events": [
                {"kind": "owned-scan", "monotonic_ns": 220, "pids": []},
                {"kind": "owned-scan", "monotonic_ns": 230, "pids": []},
                {"kind": "echild", "monotonic_ns": 240,
                 "return": -1, "errno": 10}], "unresolved": []}
            args = mock.Mock(attempt_root=Path("/tmp/preflight-contract"))
            with mock.patch.object(supervise, "validate_inputs"), \
                 mock.patch.object(supervise.time, "monotonic_ns",
                    side_effect=([100, sentinel_deadline,
                                   sentinel_deadline + supervise.CLEANUP_NS]
                                  if stage == "sentinel-wait"
                                 else [100, 200, 300])), \
                 mock.patch.object(supervise.os, "getpid", return_value=20), \
                 mock.patch.object(supervise, "establish_wait_authority",
                    side_effect=failure), \
                 mock.patch.object(supervise, "cleanup_tree",
                    return_value=(cleanup, failure.sentinel_wait)), \
                 mock.patch.object(supervise, "ensure_attempt_root",
                    side_effect=lambda path: path), \
                 mock.patch.object(supervise, "publish_result"):
                return supervise.run_supervisor(args)[0]
        valid = make("sentinel-wait")
        valid["supervisor_cleanup"]["complete"] = False
        valid["supervisor_cleanup"]["events"] = valid["supervisor_cleanup"]["events"][1:]
        for index, event in enumerate(valid["supervisor_cleanup"]["events"], 1):
            event["monotonic_ns"] = 5_000_000_100 + index
        timeout_deadline = valid["sentinel_wait_deadline_ns"]
        timeout = {"kind": "wait-timeout", "stage": "direct", "pid": 77,
                   "startticks": None, "monotonic_ns": timeout_deadline,
                   "deadline_ns": timeout_deadline}
        valid["supervisor_cleanup"]["unresolved"] = [timeout]
        oracle.validate_supervisor_record(valid)
        missing = copy.deepcopy(valid)
        missing["supervisor_cleanup"]["unresolved"] = [{
            "kind": "deadline", "stage": "owned-scan",
            "monotonic_ns": missing["supervisor_cleanup_deadline_ns"],
            "deadline_ns": missing["supervisor_cleanup_deadline_ns"]}]
        with self.assertRaisesRegex(ValueError, "sentinel.*timeout"):
            oracle.validate_supervisor_record(missing)
        duplicate = copy.deepcopy(valid)
        duplicate["supervisor_cleanup"]["unresolved"].append(copy.deepcopy(timeout))
        with self.assertRaisesRegex(ValueError, "direct timeout|direct wait timeout"):
            oracle.validate_supervisor_record(duplicate)
        reaped = copy.deepcopy(valid)
        reaped["supervisor_cleanup"]["events"] = [{
            "kind": "wait", "pid": 77, "startticks": None,
            "raw_wait_status": 73 << 8, "direct": True,
            "monotonic_ns": timeout_deadline + 1}, {
            "kind": "owned-scan", "monotonic_ns": timeout_deadline + 2,
            "pids": []}, {
            "kind": "owned-scan", "monotonic_ns": timeout_deadline + 3,
            "pids": []}, {
            "kind": "echild", "monotonic_ns": timeout_deadline + 4,
            "return": -1, "errno": 10}]
        oracle.validate_supervisor_record(reaped)
        wrong_pid = copy.deepcopy(reaped)
        wrong_pid["supervisor_cleanup"]["unresolved"][0]["pid"] = 999
        with self.assertRaisesRegex(ValueError, "timeout.*identity"):
            oracle.validate_supervisor_record(wrong_pid)
        after_reap = copy.deepcopy(reaped)
        after_reap["supervisor_cleanup"]["unresolved"][0][
            "monotonic_ns"] = timeout_deadline + 5
        with self.assertRaisesRegex(ValueError, "timeout.*retirement"):
            oracle.validate_supervisor_record(after_reap)
        later_birth = copy.deepcopy(reaped)
        later_birth["supervisor_cleanup"]["events"] = [{
            "kind": "identity", "phase": "term-identity-1",
            "observation": "observed", "pid": 77, "ppid": 20,
            "startticks": 30, "matched": True,
            "monotonic_ns": timeout_deadline + 1}, {
            "kind": "identity", "phase": "term-identity-2",
            "observation": "observed", "pid": 77, "ppid": 20,
            "startticks": 30, "matched": True,
            "monotonic_ns": timeout_deadline + 2}, {
            "kind": "wait", "pid": 77, "startticks": 30,
            "raw_wait_status": 73 << 8, "direct": True,
            "monotonic_ns": timeout_deadline + 3}, {
            "kind": "owned-scan", "monotonic_ns": timeout_deadline + 4,
            "pids": []}, {
            "kind": "owned-scan", "monotonic_ns": timeout_deadline + 5,
            "pids": []}, {
            "kind": "echild", "monotonic_ns": timeout_deadline + 6,
            "return": -1, "errno": 10}]
        self.assertTrue(oracle.validate_supervisor_record(later_birth))
        for stage in ("sentinel-fork", "sigchld-default"):
            value = make(stage)
            value["supervisor_cleanup"]["complete"] = False
            value["finished_ns"] = timeout_deadline
            value["supervisor_cleanup"]["unresolved"] = [dict(timeout, pid=999)]
            with self.subTest(stage=stage), self.assertRaisesRegex(ValueError,
                    "sentinel.*timeout"):
                oracle.validate_supervisor_record(value)

    def test_owner_sticky_direct_timeout_precedes_matching_reap(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "case"
            self.write_fixture(root, 0)
            result = json.loads((root / "supervisor-result.json").read_text())
            trigger = result["owner_wait_deadline_ns"]
            result.update({"status": "OWNER_ERROR",
                           "cleanup_trigger_ns": trigger,
                           "supervisor_cleanup_deadline_ns":
                               trigger + supervise.CLEANUP_NS,
                           "finished_ns": trigger + supervise.CLEANUP_NS})
            direct = {"kind": "wait", "pid": 40, "startticks": 30,
                "raw_wait_status": 0, "direct": True,
                "monotonic_ns": trigger + 10}
            timeout = {"kind": "wait-timeout", "stage": "direct",
                "pid": 40, "startticks": 30, "monotonic_ns": trigger,
                "deadline_ns": trigger}
            result["supervisor_cleanup"] = {"complete": False,
                "events": [direct,
                    {"kind": "owned-scan", "monotonic_ns": trigger + 20,
                     "pids": []},
                    {"kind": "owned-scan", "monotonic_ns": trigger + 30,
                     "pids": []},
                    {"kind": "echild", "monotonic_ns": trigger + 40,
                     "return": -1, "errno": 10}],
                "unresolved": [timeout]}
            self.assertTrue(oracle.validate_supervisor_record(result))
            after_reap = copy.deepcopy(result)
            after_reap["supervisor_cleanup"]["unresolved"][0][
                "monotonic_ns"] = trigger + 50
            with self.assertRaisesRegex(ValueError, "timeout.*retirement"):
                oracle.validate_supervisor_record(after_reap)
            later_birth = copy.deepcopy(result)
            later_birth["owner_identity"].update({"state": "UNOBSERVED",
                "ppid": None, "startticks": None})
            later_birth["owner_identity_observations"] = [
                {"observation": "missing", "pid": 40, "ppid": None,
                 "startticks": None, "monotonic_ns": 400},
                {"observation": "error", "pid": 40, "ppid": None,
                 "startticks": None, "monotonic_ns": 500}]
            later_birth["supervisor_cleanup"]["unresolved"][0][
                "startticks"] = None
            later_birth["supervisor_cleanup"]["events"] = [{
                "kind": "identity", "phase": "term-identity-1",
                "observation": "observed", "pid": 40, "ppid": 20,
                "startticks": 30, "matched": True,
                "monotonic_ns": trigger + 1}, {
                "kind": "identity", "phase": "term-identity-2",
                "observation": "observed", "pid": 40, "ppid": 20,
                "startticks": 30, "matched": True,
                "monotonic_ns": trigger + 2}] + \
                later_birth["supervisor_cleanup"]["events"]
            self.assertTrue(oracle.validate_supervisor_record(later_birth))

    def test_supervisor_failure_producers_round_trip_oracle(self):
        terminal = lambda direct=None: {"complete": True, "events":
            ([] if direct is None else [direct]) + [
                {"kind": "owned-scan", "monotonic_ns": 210, "pids": []},
                {"kind": "owned-scan", "monotonic_ns": 220, "pids": []},
                {"kind": "echild", "monotonic_ns": 230,
                 "return": -1, "errno": 10}], "unresolved": []}
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve() / "spawn-failed"
            args = mock.Mock(attempt_root=root)
            with mock.patch.object(supervise, "validate_inputs"), \
                 mock.patch.object(supervise.time, "monotonic_ns",
                                   side_effect=[100, 110, 120, 300]), \
                 mock.patch.object(supervise.os, "getpid", return_value=20), \
                 mock.patch.object(supervise, "establish_wait_authority"), \
                 mock.patch.object(supervise, "spawn_owner",
                                   side_effect=OSError(5, "spawn")), \
                 mock.patch.object(supervise, "cleanup_tree",
                                   return_value=(terminal(), None)), \
                 mock.patch.object(supervise, "finish_pipes"), \
                 mock.patch.object(supervise, "ensure_attempt_root",
                                   side_effect=lambda path: path.mkdir() or path), \
                 mock.patch.object(supervise, "publish_result"):
                result, status = supervise.run_supervisor(args)
            self.assertEqual(status, 125)
            self.assertEqual(result["owner_identity"]["state"], "SPAWN_FAILED")
            self.assertEqual(result["owner_wait_deadline_ns"],
                             result["started_ns"] + supervise.OWNER_WAIT_NS)
            self.assertTrue(oracle.validate_supervisor_record(result))
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve() / "owner-exit"
            args = mock.Mock(attempt_root=root)
            observation = {"observation": "observed", "pid": 77,
                "ppid": 20, "startticks": 30, "monotonic_ns": 150}
            direct = {"kind": "wait", "pid": 77, "startticks": 30,
                "raw_wait_status": 7 << 8, "direct": True,
                "monotonic_ns": 200}
            def pump(*values):
                values[-1].update({"raw_wait_status": 7 << 8,
                                   "waited_ns": 200,
                                   "stdout_eof": True, "stderr_eof": True})
            with mock.patch.object(supervise, "validate_inputs"), \
                 mock.patch.object(supervise.time, "monotonic_ns",
                                   side_effect=[100, 110, 300]), \
                 mock.patch.object(supervise.os, "getpid", return_value=20), \
                 mock.patch.object(supervise, "establish_wait_authority"), \
                 mock.patch.object(supervise, "spawn_owner",
                                   return_value=(77, 3, 4, [])), \
                 mock.patch.object(supervise, "observe_identity",
                                   side_effect=[observation, dict(observation)]), \
                 mock.patch.object(supervise, "pump_owner", side_effect=pump), \
                 mock.patch.object(supervise, "cleanup_tree",
                                   return_value=(terminal(direct), direct)), \
                 mock.patch.object(supervise, "finish_pipes"), \
                 mock.patch.object(supervise, "ensure_attempt_root",
                                   side_effect=lambda path: path.mkdir() or path), \
                 mock.patch.object(supervise, "publish_result"):
                result, status = supervise.run_supervisor(args)
            self.assertEqual(status, 125)
            self.assertEqual(result["owner_exit_code"], 7)
            self.assertEqual(result["owner_identity"]["state"], "MATCHED")
            self.assertTrue(oracle.validate_supervisor_record(result))

    def rewrite_json(self, path, edit):
        value = json.loads(path.read_text())
        edit(value)
        path.write_text(json.dumps(value, sort_keys=True, separators=(",", ":")))

    def make_legacy_empty(self, legacy, original):
        old, new = str(original), str(legacy)
        for path in legacy.rglob("*"):
            if path.is_file() and path.suffix in (".json", ".jsonl"):
                path.write_bytes(path.read_bytes().replace(old.encode(), new.encode()))
        (legacy / "collection/stdout.bin").write_bytes(b"")
        self.refresh_supervisor(legacy)

    def rewrite_journal(self, path, edit):
        rows = [json.loads(line) for line in path.read_text().splitlines()]
        edit(rows)
        path.write_bytes(b"".join(json.dumps(row, sort_keys=True,
            separators=(",", ":")).encode() + b"\n" for row in rows))

    def refresh_supervisor(self, root):
        path = root / "supervisor-result.json"
        value = json.loads(path.read_text())
        for key, filename in (("owner_result", "owner-result.json"),
                              ("witness", "witness.jsonl"),
                              ("owner_errors", "owner-errors.jsonl")):
            target = root / filename
            value[key + "_present"] = target.exists()
            value[key + "_sha256"] = hashlib.sha256(target.read_bytes()).hexdigest() \
                if target.exists() else None
        path.write_text(json.dumps(value, sort_keys=True,
                                   separators=(",", ":")) + "\n")

    def republish_owner(self, root, edit=lambda value: None):
        owner_path = root / "owner-result.json"
        value = json.loads(owner_path.read_text())
        edit(value)
        owner_path.write_text(json.dumps(value, sort_keys=True,
            separators=(",", ":")) + "\n")
        self.rewrite_journal(root / "witness.jsonl",
            lambda rows: rows[-1].__setitem__("packet", value))

    def rebind_artifact(self, root, name):
        filename = {"events": "events.jsonl", "request": "request.bin",
                    "report": "report.json"}[name]
        path = root / "collection" / filename
        raw = path.read_bytes()
        def edit(value):
            value["artifacts"][name].update({"present": True, "size": len(raw),
                "sha256": hashlib.sha256(raw).hexdigest()})
        self.republish_owner(root, edit)
        if name == "report":
            self.rewrite_journal(root / "witness.jsonl", lambda rows: [
                packet["target_stat"].__setitem__("size", len(raw))
                for row in rows[:-1] for packet in [row["packet"]]
                if packet.get("site") in ("report-flush", "report-sync") and
                   not (packet["site"] == "report-flush" and
                        packet["kind"] == "BEFORE")])

    def mutate_report(self, root, edit):
        self.rewrite_json(root / "collection/report.json", edit)
        self.rebind_artifact(root, "report")

    def mutate_events(self, root, edit):
        path = root / "collection/events.jsonl"
        values = [json.loads(line) for line in path.read_text().splitlines()]
        edit(values)
        path.write_bytes(b"".join(json.dumps(value, sort_keys=True,
            separators=(",", ":")).encode() + b"\n" for value in values))
        self.rebind_artifact(root, "events")

    def replace_retained_with_symlink(self, root):
        path = root / "retained-inputs/request.bin"
        path.unlink()
        path.symlink_to(root / "retained-inputs/fixture")

    def test_oracle_independent_negative_matrix(self):
        self.mutate(0, lambda root: self.rewrite_json(root / "owner-result.json",
                    lambda value: value.__setitem__("raw_wait_status", 1)), "owner result")
        self.mutate(0, lambda root: self.rewrite_journal(root / "witness.jsonl",
                    lambda rows: rows[1]["packet"].__setitem__("sequence", 7)), "witness identity")
        self.mutate(0, lambda root: self.rewrite_journal(root / "witness.jsonl",
                    lambda rows: rows[0]["packet"].__setitem__("nonce", "e" * 32)), "witness identity")
        self.mutate(0, lambda root: self.rewrite_journal(root / "witness.jsonl",
                    lambda rows: rows[0]["packet"].__setitem__("elf_sha256", "0" * 64)), "generated hash")
        self.mutate(0, lambda root: self.rewrite_journal(root / "witness.jsonl",
                    lambda rows: rows.pop(-2)), "witness packet count")
        self.mutate(0, lambda root: self.rewrite_journal(root / "witness.jsonl",
                    lambda rows: rows.insert(2, copy.deepcopy(rows[1]))), "witness packet count")
        self.mutate(0, lambda root: self.rewrite_json(root / "collection/report.json",
                    lambda value: value.__setitem__("status", "COLLECTOR_ERROR")), "evidence hash")
        self.mutate(4, lambda root: (root / "collection/report.json").write_text("{}"),
                    "evidence absence")
        self.mutate(2, lambda root: (root / "collection/request.bin").write_bytes(b"BROKEN!"),
                    "evidence hash")
        self.mutate(5, lambda root: self.rewrite_journal(root / "witness.jsonl",
                    lambda rows: next(row for row in rows
                        if row["packet"].get("site") == "report-sync" and
                        row["packet"].get("kind") == "AFTER" and
                        row["packet"].get("return") == -1)["packet"].__setitem__("errno", 0)),
                    "after result")
        self.mutate(0, lambda root: (root / "witness.jsonl").write_bytes(
                    (root / "witness.jsonl").read_bytes()[:-1]), "journal terminal newline")
        self.mutate(0, lambda root: self.republish_owner(root,
                    lambda value: value.__setitem__("unexpected", 1)), "owner result")
        self.mutate(0, lambda root: self.republish_owner(root,
                    lambda value: value["environment"].__setitem__("EXTRA", "1")),
                    "owner environment")
        self.mutate(0, lambda root: self.republish_owner(root,
                    lambda value: value["argv"].__setitem__(0,
                        value["inputs"]["source"]["path"])), "executed ELF path")
        self.mutate(0, lambda root: self.rewrite_journal(root / "witness.jsonl",
                    lambda rows: rows[-1]["packet"]["owner"].__setitem__(
                        "startticks", 31)),
                    "owner publication")
        self.mutate(0, lambda root: self.mutate_report(root,
                    lambda value: value.__setitem__("unexpected", 1)), "report fields")
        self.mutate(0, lambda root: self.mutate_report(root,
                    lambda value: value["desired"].pop("argc")), "report desired")
        self.mutate(0, lambda root: self.mutate_report(root,
                    lambda value: value["linux_child"].__setitem__("startticks", 81)),
                    "report child cleanup")
        self.mutate(2, lambda root: self.mutate_report(root,
                    lambda value: value["artifacts"][0].__setitem__("seen_bytes", 405)),
                    "report request sink")
        self.mutate(0, lambda root: self.mutate_events(root,
                    lambda values: values[-1].__setitem__("first_failure", "artifact-write")),
                    "events failure snapshot")
        self.mutate(0, lambda root: self.rewrite_journal(root / "witness.jsonl",
                    lambda rows: [packet["target_stat"].__setitem__("size", 1)
                        for row in rows[:-1] for packet in [row["packet"]]
                        if packet.get("site") in ("report-flush", "report-sync") and
                           not (packet["site"] == "report-flush" and
                                packet["kind"] == "BEFORE")]), "report witness size")
        self.mutate(0, lambda root: self.rewrite_journal(root / "witness.jsonl",
                    lambda rows: rows[0]["packet"].__setitem__("extra", 1)),
                    "witness exact fields")
        self.mutate(0, lambda root: self.rewrite_journal(root / "witness.jsonl",
                    lambda rows: rows[1]["packet"].__setitem__("phase", "post-fork")),
                    "witness phase")
        self.mutate(0, lambda root: self.rewrite_journal(root / "witness.jsonl",
                    lambda rows: next(row for row in rows if
                        row["packet"].get("site") == "request-write")["packet"].
                        __setitem__("acquisition_id", 1)), "request acquisition")
        self.mutate(0, lambda root: self.rewrite_journal(root / "witness.jsonl",
                    lambda rows: next(row for row in rows if
                        row["packet"].get("site") == "request-write")["packet"].
                        __setitem__("requested_bytes", 405)), "request bytes")
        self.mutate(0, lambda root: self.rewrite_journal(root / "witness.jsonl",
                    lambda rows: next(row for row in rows if
                        row["packet"].get("site") == "request-write")["packet"]
                        ["target_stat"].__setitem__("mode", 0o40700)),
                    "witness target type")
        self.mutate(0, lambda root: self.rewrite_journal(root / "witness.jsonl",
                    lambda rows: next(row for row in rows if
                        row["packet"].get("kind") == "CLEANUP_FINAL")["packet"].
                        __setitem__("first_failure", "artifact-write")),
                    "collector cleanup result")

    def test_review35_setup_witness_and_absent_report_counterexamples(self):
        """SETUP is singular, ordered, dynamic and binds selector-4 artifacts."""
        def setup_row(rows):
            return next(row for row in rows if row["packet"].get("kind") == "SETUP")
        self.mutate(0, lambda root: self.rewrite_journal(root / "witness.jsonl",
                    lambda rows: setup_row(rows)["packet"]["stdout_pipe_stat"].__setitem__("ino", 901)),
                    "setup witness identity join")
        self.mutate(0, lambda root: self.rewrite_journal(root / "witness.jsonl",
                    lambda rows: setup_row(rows)["packet"].__setitem__("cwd_stat", None)),
                    "witness stat")
        self.mutate(0, lambda root: self.rewrite_journal(root / "witness.jsonl",
                    lambda rows: rows.insert(1, copy.deepcopy(setup_row(rows)))),
                    "witness packet count")
        self.mutate(0, lambda root: self.rewrite_journal(root / "witness.jsonl",
                    lambda rows: rows.__setitem__(1, rows.pop(next(i for i, row in enumerate(rows)
                        if row["packet"].get("kind") == "SETUP")))), "witness packet count")
        self.mutate(4, lambda root: (root / "collection/setup.bin").write_bytes(
                    b"\0" * 384), "setup witness identity join")
        self.mutate(4, lambda root: (root / "collection/executable.verified.bin").write_bytes(
                    b"garbage"), "absent report reached artifact binding")
        self.mutate(4, lambda root: self.mutate_events(root,
                    lambda values: values[1].__setitem__("startticks", 81)),
                    "events child identity")
        self.mutate(0, lambda root: self.republish_owner(root,
                    lambda value: value["cleanup"]["events"][-2].
                        __setitem__("pids", [{"pid": 99, "ppid": 40,
                                             "startticks": 88}])),
                    "owner cleanup terminal")
        self.mutate(0, lambda root: self.republish_owner(root,
                    lambda value: value["cleanup"]["events"][1].
                        __setitem__("monotonic_ns", 6150)),
                    "owner cleanup event order")
        self.mutate(0, lambda root: self.rewrite_journal(root / "witness.jsonl",
                    lambda rows: next(row for row in rows if
                        row["packet"].get("site") == "request-sync")["packet"]
                        ["target_stat"].__setitem__("ino", 999)),
                    "request sync identity")
        self.mutate(1, lambda root: self.mutate_report(root,
                    lambda value: value["artifacts"][4].
                        __setitem__("creation_errno", 5)),
                    "report events create failure")
        self.mutate(0, lambda root: self.mutate_report(root,
                    lambda value: value["setup_words"].__setitem__(5, 71)),
                    "report setup semantics")
        self.mutate(0, self.replace_retained_with_symlink,
                    "canonical evidence path")

    def test_durable_journal_and_protocol_helpers(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "journal"
            journal = owner.DurableJournal(root, create_root=True)
            journal.append({"kind": "READY"}, 1)
            journal.close()
            raw = (root / "witness.jsonl").read_bytes()
            self.assertTrue(raw.endswith(b"\n"))
            self.assertEqual(json.loads(raw)["packet"], {"kind": "READY"})
        packet = self.packet(0, 0, "READY", phase="pre-fork")
        owner.validate_common(packet, self.NONCE, 0, 0,
                              {"source_sha256": self.SOURCE_SHA, **self.HASHES})
        wrong = copy.deepcopy(packet)
        wrong["sequence"] = 1
        with self.assertRaisesRegex(ValueError, "witness identity"):
            owner.validate_common(wrong, self.NONCE, 0, 0,
                                  {"source_sha256": self.SOURCE_SHA, **self.HASHES})

    def test_owner_error_ledger_preserves_primary_and_poisoned_ordinal(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            journal = owner.OwnerErrorJournal(root)
            ledger = owner.FailureLedger(journal)
            primary = ValueError("primary")
            journal_failure = OSError("journal write")
            with mock.patch.object(owner, "complete_write",
                                   side_effect=journal_failure):
                self.assertIsNone(ledger.record(primary, "pre-ack",
                    {"sequence": -7, "kind": "bad"}))
            secondary = RuntimeError("secondary")
            self.assertIsNone(ledger.record(secondary, "cleanup"))
            self.assertEqual(journal.next_ordinal, 1)
            self.assertTrue(journal.poisoned)
            self.assertEqual(journal.records, [])
            self.assertEqual(ledger.exceptions, [primary, journal_failure, secondary])
            with self.assertRaises(ValueError) as raised:
                ledger.raise_first()
            self.assertIs(raised.exception, primary)
            self.assertIs(primary.__context__, journal_failure)
            self.assertIs(journal_failure.__context__, secondary)
            journal.close()

    def test_constructor_preserves_fsync_before_close_failure_without_cycle(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            primary = OSError("constructor fsync")
            secondary = OSError("constructor close")
            with mock.patch.object(owner.os, "open", return_value=77), \
                 mock.patch.object(owner, "fsync_directory", side_effect=primary), \
                 mock.patch.object(owner.os, "close", side_effect=secondary):
                with self.assertRaises(OSError) as raised:
                    owner.DurableJournal(root)
            self.assertIs(raised.exception, primary)
            self.assertIs(primary.__context__, secondary)
            self.assertIsNone(secondary.__context__)

    def test_failure_ledger_operation_close_journal_order_and_nested_chain(self):
        journal = mock.Mock(poisoned=False, fd=7)
        journal_failure = OSError("journal")
        nested = OSError("journal close")
        owner.attach_secondary(journal_failure, nested)
        def fail_journal(*args, **kwargs):
            journal.poisoned = True
            raise journal_failure
        journal.append.side_effect = fail_journal
        ledger = owner.FailureLedger(journal)
        primary = ValueError("operation")
        close_failure = OSError("operation close")
        owner.attach_secondary(primary, close_failure)
        ledger.record(primary, "pre-ack")
        self.assertEqual(ledger.exceptions,
            [primary, close_failure, journal_failure, nested])
        with self.assertRaises(ValueError) as raised:
            ledger.raise_first()
        self.assertIs(raised.exception, primary)
        chain = []
        current = primary
        while current is not None:
            self.assertNotIn(id(current), chain)
            chain.append(id(current))
            current = current.__context__
        self.assertEqual(chain, [id(value) for value in ledger.exceptions])

    def test_owner_error_journal_strict_times_and_claimed_sequence(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            journal = owner.OwnerErrorJournal(root)
            with mock.patch.object(owner.time, "monotonic_ns", return_value=5):
                first = journal.append(ValueError("one"), "pre-ack",
                                       {"sequence": -1})
                second = journal.append(RuntimeError(), "cleanup")
            journal.close()
            self.assertEqual((first["ordinal"], first["primary"],
                              first["packet_sequence"]), (0, True, None))
            self.assertIsNotNone(first["packet_sha256"])
            self.assertEqual((first["monotonic_ns"], second["monotonic_ns"]),
                             (5, 6))
            self.assertEqual(second["message"], "<empty-RuntimeError>")
            rows = [json.loads(line) for line in
                    (root / "owner-errors.jsonl").read_text().splitlines()]
            self.assertEqual(rows, [first, second])

    def test_duplicate_clock_cutoff_includes_frozen_errors(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            journal = owner.OwnerErrorJournal(root)
            with mock.patch.object(owner.time, "monotonic_ns", return_value=5):
                journal.append(ValueError("one"), "pre-ack")
                journal.append(ValueError("two"), "cleanup")
                cutoff = owner.result_serialization_cutoff(journal)
                later = journal.append(ValueError("later"), "journal-result")
            journal.close()
            self.assertEqual(cutoff, 6)
            self.assertEqual([row["monotonic_ns"] for row in journal.records],
                             [5, 6, 7])
            self.assertGreater(later["monotonic_ns"], cutoff)

    def test_result_persistence_failure_suppresses_terminal(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            witness = owner.DurableJournal(root / "attempt", create_root=True)
            errors = owner.OwnerErrorJournal(witness.root)
            ledger = owner.FailureLedger(errors)
            result = {"kind": "OWNER_RESULT"}
            raw = b'{"kind":"OWNER_RESULT"}\n'
            with mock.patch.object(owner, "durable_file",
                                   side_effect=OSError("result write")):
                persisted, terminal = owner.publish_owner_result(
                    witness.root, raw, result, witness, ledger)
            self.assertFalse(persisted or terminal)
            self.assertEqual((witness.root / "witness.jsonl").read_bytes(), b"")
            self.assertFalse((witness.root / "owner-result.json").exists())
            self.assertEqual(ledger.exceptions[0].args, ("result write",))
            witness.close(); errors.close()

    def test_terminal_failure_keeps_result_bytes_immutable(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            witness = owner.DurableJournal(root / "attempt", create_root=True)
            errors = owner.OwnerErrorJournal(witness.root)
            ledger = owner.FailureLedger(errors)
            result = {"kind": "OWNER_RESULT", "frozen": True}
            raw = (json.dumps(result, sort_keys=True, separators=(",", ":")) +
                   "\n").encode()
            with mock.patch.object(witness, "append",
                                   side_effect=OSError("terminal write")):
                persisted, terminal = owner.publish_owner_result(
                    witness.root, raw, result, witness, ledger)
            self.assertTrue(persisted)
            self.assertFalse(terminal)
            self.assertEqual((witness.root / "owner-result.json").read_bytes(), raw)
            self.assertEqual(ledger.exceptions[0].args, ("terminal write",))
            witness.close(); errors.close()

    def test_owner_error_partition_boundaries(self):
        def error(ordinal, when, primary=None):
            return {"schema_version": 2, "kind": "OWNER_ERROR",
                "ordinal": ordinal, "primary": ordinal == 0 if primary is None else primary,
                "stage": "pre-ack", "type": "ValueError", "message": "bad",
                "monotonic_ns": when, "packet_sequence": ordinal,
                "packet_sha256": "%064x" % (ordinal + 1)}
        rows = [error(0, 10), error(1, 20), error(2, 30)]
        raw = b"".join(json.dumps(row, sort_keys=True,
            separators=(",", ":")).encode() + b"\n" for row in rows)
        result = {"result_serialized_ns": 20, "owner_failure": rows[0],
                  "secondary_failures": [rows[1]]}
        self.assertEqual(oracle.validate_owner_errors(raw, result), rows)
        for edit, message in (
                (lambda values: values[1].__setitem__("ordinal", 2),
                 "owner error record"),
                (lambda values: values[1].__setitem__("primary", True),
                 "owner error record"),
                (lambda values: values[1].__setitem__("monotonic_ns", 10),
                 "owner error record"),
                (lambda values: values[1].__setitem__("stage", "unknown"),
                 "owner error record"),
                (lambda values: values[1].__setitem__("message", "<empty-OSError>"),
                 "owner error message"),
                (lambda values: values[1].__setitem__("packet_sequence", True),
                 "owner error packet sequence"),
                (lambda values: values[1].__setitem__("packet_sha256", "A" * 64),
                 "owner error packet hash")):
            changed = copy.deepcopy(rows); edit(changed)
            changed_raw = b"".join(json.dumps(row, sort_keys=True,
                separators=(",", ":")).encode() + b"\n" for row in changed)
            with self.assertRaisesRegex(ValueError, message):
                oracle.validate_owner_errors(changed_raw)
        bad_result = copy.deepcopy(result); bad_result["secondary_failures"] = []
        with self.assertRaisesRegex(ValueError, "owner error partition"):
            oracle.validate_owner_errors(raw, bad_result)
        changed = copy.deepcopy(rows); changed[0]["schema_version"] = 2.0
        changed_raw = b"".join(json.dumps(row, sort_keys=True,
            separators=(",", ":")).encode() + b"\n" for row in changed)
        with self.assertRaisesRegex(ValueError, "owner error record"):
            oracle.validate_owner_errors(changed_raw)
        conflated = copy.deepcopy(result)
        conflated["owner_failure"]["ordinal"] = False
        with self.assertRaisesRegex(ValueError, "owner error partition"):
            oracle.validate_owner_errors(raw, conflated)

    def test_cleanup_unresolved_tagged_union(self):
        values = [
            {"kind": "identity", "phase": "term-identity-1",
             "observation": "missing", "pid": 7, "ppid": None,
             "startticks": None, "matched": False, "monotonic_ns": 10},
            {"kind": "deadline", "stage": "owned-scan",
             "monotonic_ns": 20, "deadline_ns": 20},
            {"kind": "signal-error", "stage": "kill", "pid": 7,
             "startticks": 9, "signal": 9, "errno": 3, "monotonic_ns": 21},
            {"kind": "wait-timeout", "stage": "direct", "pid": 7,
             "startticks": None, "monotonic_ns": 22, "deadline_ns": 20},
            {"kind": "owned", "phase": "owned-scan-2047", "pid": 8,
             "ppid": 6, "startticks": 10, "monotonic_ns": 23}]
        self.assertEqual(oracle.validate_cleanup_unresolved(values), values)
        mutations = [
            lambda row: row[0].__setitem__("phase", "owned-scan-2048-1"),
            lambda row: row[1].__setitem__("monotonic_ns", 19),
            lambda row: row[2].__setitem__("signal", 15),
            lambda row: row[3].__setitem__("pid", True),
            lambda row: row[4].__setitem__("phase", "owned-scan-2048")]
        for mutation in mutations:
            changed = copy.deepcopy(values); mutation(changed)
            with self.assertRaises(ValueError):
                oracle.validate_cleanup_unresolved(changed)
        changed = copy.deepcopy(values); changed[2]["signal"] = 9.0
        with self.assertRaisesRegex(ValueError, "owner cleanup signal error"):
            oracle.validate_cleanup_unresolved(changed)

    def test_real_bounded_cleanup_direct_wait_and_terminal_proof(self):
        class Clock:
            def __init__(self): self.value = 100
            def __call__(self):
                self.value += 1
                return self.value
        for raw_status in self.WAITS:
            with self.subTest(raw_wait_status=raw_status):
                clock = Clock()
                direct = {"kind": "wait", "pid": 50, "startticks": 60,
                    "raw_wait_status": raw_status, "direct": True,
                    "monotonic_ns": 102}
                scans = iter((104, 106))
                def empty_scan(owner_pid, exclude, phase):
                    return [], [{"kind": "owned-scan",
                        "monotonic_ns": next(scans), "pids": []}], []
                with mock.patch.object(owner.time, "monotonic_ns", side_effect=clock), \
                     mock.patch.object(owner.time, "sleep") as sleep_call, \
                     mock.patch.object(owner, "wait_direct", return_value=direct), \
                     mock.patch.object(owner, "owned_scan", side_effect=empty_scan), \
                     mock.patch.object(owner.os, "waitpid",
                                       side_effect=ChildProcessError()), \
                     mock.patch.object(owner.os, "kill") as kill_call:
                    cleanup, waited = owner.bounded_cleanup(50,
                        {"pid": 50, "ppid": 40, "startticks": 60}, 40,
                        "normal-eof", 10)
                self.assertIs(waited, direct)
                self.assertTrue(cleanup["complete"])
                self.assertEqual([event["kind"] for event in cleanup["events"]],
                                 ["wait", "owned-scan", "owned-scan", "echild"])
                self.assertEqual(cleanup["unresolved"], [])
                kill_call.assert_not_called()
                self.assertEqual(sleep_call.call_count, 1)

    def test_real_bounded_cleanup_timeout_term_reap_is_sticky(self):
        class Clock:
            def __init__(self): self.value = 100
            def __call__(self):
                self.value += 1
                return self.value
        clock = Clock()
        waits = []
        def wait_direct(pid, deadline_ns, startticks=None, direct=True):
            waits.append((pid, deadline_ns, startticks, direct))
            if len(waits) == 1:
                clock.value = deadline_ns
                return None
            return {"kind": "wait", "pid": pid, "startticks": startticks,
                    "raw_wait_status": 15, "direct": direct,
                    "monotonic_ns": clock()}
        scan_count = [0]
        def empty_scan(owner_pid, exclude, phase):
            scan_count[0] += 1
            return [], [{"kind": "owned-scan", "monotonic_ns": clock(),
                         "pids": []}], []
        with mock.patch.object(owner.time, "monotonic_ns", side_effect=clock), \
             mock.patch.object(owner.time, "sleep"), \
             mock.patch.object(owner, "wait_direct", side_effect=wait_direct), \
             mock.patch.object(owner, "process_identity",
                               return_value={"pid": 50, "ppid": 40,
                                             "startticks": 60}), \
             mock.patch.object(owner, "owned_scan", side_effect=empty_scan), \
             mock.patch.object(owner.os, "waitpid", side_effect=ChildProcessError()), \
             mock.patch.object(owner.os, "kill") as kill_call:
            cleanup, waited = owner.bounded_cleanup(50,
                {"pid": 50, "ppid": 40, "startticks": 60}, 40,
                "owner-failure", 10)
        self.assertIsNotNone(waited)
        self.assertFalse(cleanup["complete"])
        self.assertEqual([row["kind"] for row in cleanup["unresolved"]],
                         ["wait-timeout"])
        self.assertGreaterEqual(cleanup["unresolved"][0]["monotonic_ns"],
                                cleanup["unresolved"][0]["deadline_ns"])
        self.assertEqual([event["kind"] for event in cleanup["events"]],
            ["identity", "identity", "signal", "wait",
             "owned-scan", "owned-scan", "echild"])
        self.assertEqual(kill_call.call_args_list,
                         [mock.call(50, owner.signal.SIGTERM)])
        self.assertEqual(waits[1][2], 60)

    def test_real_bounded_cleanup_reap_resets_empty_scan_proof(self):
        class Clock:
            def __init__(self): self.value = 100
            def __call__(self):
                self.value += 1
                return self.value
        clock = Clock()
        direct = {"kind": "wait", "pid": 50, "startticks": 60,
            "raw_wait_status": 0, "direct": True, "monotonic_ns": 102}
        scan_count = [0]
        def empty_scan(owner_pid, exclude, phase):
            scan_count[0] += 1
            return [], [{"kind": "owned-scan", "monotonic_ns": clock(),
                         "pids": []}], []
        wait_results = [ChildProcessError(), (88, 0), (0, 0),
                        ChildProcessError(), ChildProcessError()]
        with mock.patch.object(owner.time, "monotonic_ns", side_effect=clock), \
             mock.patch.object(owner.time, "sleep"), \
             mock.patch.object(owner, "wait_direct", return_value=direct), \
             mock.patch.object(owner, "owned_scan", side_effect=empty_scan), \
             mock.patch.object(owner.os, "waitpid", side_effect=wait_results), \
             mock.patch.object(owner.os, "kill") as kill_call:
            cleanup, waited = owner.bounded_cleanup(50,
                {"pid": 50, "ppid": 40, "startticks": 60}, 40,
                "normal-eof", 10)
        self.assertTrue(cleanup["complete"])
        self.assertEqual(scan_count[0], 3)
        self.assertEqual([event["kind"] for event in cleanup["events"]],
            ["wait", "owned-scan", "wait", "owned-scan", "owned-scan", "echild"])
        self.assertEqual(cleanup["events"][2]["startticks"], None)
        kill_call.assert_not_called()

    def test_bounded_cleanup_retains_direct_prefix_after_scan_exception(self):
        now = [100]
        def clock():
            now[0] += 1_000_000_000
            return now[0]
        direct = {"kind": "wait", "pid": 50, "startticks": 60,
            "raw_wait_status": 0, "direct": True,
            "monotonic_ns": 1_000_000_100}
        scans = [RuntimeError("scan helper"),
            ([], [{"kind": "owned-scan", "monotonic_ns": 7_000_000_100,
                   "pids": []}], []),
            ([], [{"kind": "owned-scan", "monotonic_ns": 11_000_000_100,
                   "pids": []}], [])]
        errors = []
        session = {"events": [], "adopted_reaps": [], "unresolved": [],
            "waited": None, "evidence_invalidated": False,
            "direct_authority": True, "terminal_empty": False}
        with mock.patch.object(owner.time, "monotonic_ns", side_effect=clock), \
             mock.patch.object(owner.time, "sleep"), \
             mock.patch.object(owner, "wait_direct", return_value=direct), \
             mock.patch.object(owner, "owned_scan", side_effect=scans), \
             mock.patch.object(owner.os, "waitpid",
                               side_effect=ChildProcessError()):
            cleanup, waited = owner.bounded_cleanup(50,
                {"pid": 50, "ppid": 40, "startticks": 60}, 40,
                "owner-failure", 100, on_error=lambda error, stage:
                errors.append((error, stage)), session=session)
        self.assertIs(waited, direct)
        self.assertIs(session["waited"], direct)
        self.assertEqual(cleanup["events"][0], direct)
        self.assertEqual(cleanup["events"][-1]["kind"], "echild")
        self.assertFalse(cleanup["complete"])
        self.assertEqual(str(errors[0][0]), "scan helper")
        self.assertTrue(all(row["kind"] != "cleanup-error"
                            for row in cleanup["unresolved"]))

    def test_bounded_cleanup_retains_adopted_reap_before_wait_exception(self):
        now = [100]
        def clock():
            now[0] += 1_000_000_000
            return now[0]
        direct = {"kind": "wait", "pid": 50, "startticks": 60,
            "raw_wait_status": 0, "direct": True,
            "monotonic_ns": 1_000_000_100}
        wait_calls = [0]
        def waitpid(*args):
            wait_calls[0] += 1
            if wait_calls[0] == 1:
                return 88, 0
            if wait_calls[0] == 2:
                raise OSError("wait helper")
            raise ChildProcessError()
        def empty_scan(*args):
            return [], [{"kind": "owned-scan",
                "monotonic_ns": clock(), "pids": []}], []
        session = {"events": [], "adopted_reaps": [], "unresolved": [],
            "waited": None, "evidence_invalidated": False,
            "direct_authority": True, "terminal_empty": False}
        with mock.patch.object(owner.time, "monotonic_ns", side_effect=clock), \
             mock.patch.object(owner.time, "sleep"), \
             mock.patch.object(owner, "wait_direct", return_value=direct), \
             mock.patch.object(owner, "owned_scan", side_effect=empty_scan), \
             mock.patch.object(owner.os, "waitpid", side_effect=waitpid):
            cleanup, waited = owner.bounded_cleanup(50,
                {"pid": 50, "ppid": 40, "startticks": 60}, 40,
                "owner-failure", 100, on_error=lambda *_args: None,
                session=session)
        self.assertIs(waited, direct)
        self.assertEqual(len(cleanup["adopted_reaps"]), 1)
        self.assertEqual(cleanup["adopted_reaps"][0]["pid"], 88)
        self.assertEqual(cleanup["adopted_reaps"], session["adopted_reaps"])
        self.assertEqual(cleanup["events"][-1]["kind"], "echild")
        self.assertFalse(cleanup["complete"])

    def test_wait_authority_and_identity_are_not_fabricated(self):
        with mock.patch.object(owner.time, "monotonic_ns", return_value=1), \
             mock.patch.object(owner.os, "waitpid", side_effect=ChildProcessError()):
            with self.assertRaises(ChildProcessError):
                owner.wait_direct(50, 2)
        for value in ({"pid": 51, "ppid": 40, "startticks": 60},
                      {"pid": 50.0, "ppid": 40, "startticks": 60},
                      {"pid": 50, "ppid": True, "startticks": 60}):
            with self.subTest(value=value), \
                 mock.patch.object(owner.time, "monotonic_ns", return_value=10), \
                 mock.patch.object(owner, "process_identity", return_value=value):
                record = owner.observe_identity(50, "term-identity-1",
                    {"startticks": 60}, 40)
            self.assertEqual(record, {"kind": "identity",
                "phase": "term-identity-1", "observation": "error",
                "pid": 50, "ppid": None, "startticks": None,
                "matched": False, "monotonic_ns": 10})

    def test_serialization_boundary_precedes_every_late_error(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            journal = owner.OwnerErrorJournal(root)
            with mock.patch.object(owner.time, "monotonic_ns", return_value=100):
                cutoff = owner.result_serialization_cutoff(journal)
                later = journal.append(OSError("late"), "owner-result-write")
            journal.close()
            self.assertEqual(cutoff, 100)
            self.assertEqual(later["monotonic_ns"], 101)

    def test_clean_eof_requires_complete_selector_schedule(self):
        for selector in range(7):
            packets = self.packets(selector)
            owner.validate_schedule_complete(packets, selector)
            for prefix in ([], packets[:1], packets[:-1]):
                with self.assertRaisesRegex(ValueError,
                                            "incomplete witness schedule"):
                    owner.validate_schedule_complete(prefix, selector)

    def test_cleanup_signal_requires_immediately_preceding_identity(self):
        def insert_unbound_signal(value):
            value["cleanup"]["events"].insert(1,
                {"kind": "signal", "pid": 99, "startticks": 88,
                 "signal": 9, "monotonic_ns": 6250})
        self.mutate(0, lambda root: self.republish_owner(root,
                    insert_unbound_signal), "owner signal identity")
        def insert_unreaped_adopted(value):
            events = value["cleanup"]["events"]
            events[1:1] = [
                {"kind": "identity", "phase": "owned-scan-1-1",
                 "observation": "observed", "pid": 99, "ppid": 40,
                 "startticks": 88, "matched": True, "monotonic_ns": 6210},
                {"kind": "identity", "phase": "owned-scan-1-2",
                 "observation": "observed", "pid": 99, "ppid": 40,
                 "startticks": 88, "matched": True, "monotonic_ns": 6220},
                {"kind": "signal", "pid": 99, "startticks": 88,
                 "signal": 9, "monotonic_ns": 6230}]
        self.mutate(0, lambda root: self.republish_owner(root,
                    insert_unreaped_adopted), "owner adopted signal wait")

    def test_owner_cleanup_reap_and_terminal_joins_are_exact(self):
        def add_unlisted_adopted_wait(value):
            events = value["cleanup"]["events"]
            events[1:1] = [
                {"kind": "owned-scan", "monotonic_ns": 6210,
                 "pids": [{"pid": 99, "ppid": 40, "startticks": 88}]},
                {"kind": "wait", "pid": 99, "startticks": 88,
                 "raw_wait_status": 0, "direct": False,
                 "monotonic_ns": 6220}]
        self.mutate(0, lambda root: self.republish_owner(
            root, add_unlisted_adopted_wait), "owner adopted reap join")

        def add_early_echild(value):
            value["cleanup"]["events"].insert(1,
                {"kind": "echild", "monotonic_ns": 6210,
                 "return": -1, "errno": 10})
        self.mutate(0, lambda root: self.republish_owner(root, add_early_echild),
                    "owner cleanup terminal order")

        def signal_reaped_collector(value):
            value["cleanup"]["events"][1:1] = [
                {"kind": "identity", "phase": "kill-identity-1",
                 "observation": "observed", "pid": 50, "ppid": 40,
                 "startticks": 61, "matched": True, "monotonic_ns": 6210},
                {"kind": "identity", "phase": "kill-identity-2",
                 "observation": "observed", "pid": 50, "ppid": 40,
                 "startticks": 61, "matched": True, "monotonic_ns": 6220},
                {"kind": "signal", "pid": 50, "startticks": 61,
                 "signal": 9, "monotonic_ns": 6230}]
        self.mutate(0, lambda root: self.republish_owner(
            root, signal_reaped_collector), "owner direct signal after wait")

    def test_deadline_arithmetic_and_receipt_joins(self):
        self.mutate(0, lambda root: self.republish_owner(root,
            lambda value: value["deadlines"].__setitem__("owner_start_ns", True)),
            "owner deadlines")
        self.mutate(0, lambda root: self.republish_owner(root,
            lambda value: value["deadlines"].__setitem__("ready_deadline_ns",
                value["deadlines"]["ready_deadline_ns"] + 1)), "owner deadlines")
        def lose_release(value):
            value["deadlines"]["release_send_start_ns"] = None
        self.mutate(0, lambda root: self.republish_owner(root, lose_release),
                    "owner release deadline")
        def shift_first(value):
            value["deadlines"]["first_postfork_receipt_ns"] += 1
            value["deadlines"]["postfork_deadline_ns"] += 1
        self.mutate(0, lambda root: self.republish_owner(root, shift_first),
                    "owner postfork receipt join")
        def shift_cleanup(value):
            value["deadlines"]["cleanup_trigger_ns"] += 1
            value["deadlines"]["cleanup_deadline_ns"] += 1
        self.mutate(0, lambda root: self.republish_owner(root, shift_cleanup),
                    "owner cleanup deadline join")
        self.mutate(0, lambda root: self.republish_owner(root,
            lambda value: value.__setitem__("result_serialized_ns", 6500)),
            "owner cleanup deadline join")
        self.mutate(0, lambda root: self.rewrite_journal(root / "witness.jsonl",
            lambda rows: rows[-1].__setitem__("receipt_monotonic_ns", 6999)),
            "owner terminal chronology")

    def test_canonical_fresh_root_rejects_alias_before_mutation(self):
        with tempfile.TemporaryDirectory() as temporary:
            parent = Path(temporary).resolve()
            alias = parent / "alias"
            alias.symlink_to(parent)
            requested = alias / "attempt"
            with self.assertRaisesRegex(ValueError, "canonical witness root"):
                owner.canonical_fresh_root(requested)
            self.assertFalse((parent / "attempt").exists())

    def test_owner_main_maps_infrastructure_failure_to_125(self):
        args = mock.Mock(witness_root=Path("/unused"), nonce=self.NONCE,
            selector=0, hashes=mock.Mock(read_bytes=mock.Mock(return_value=b"{}")),
            source=Path("/s"), generated_source=Path("/g"),
            header=Path("/h"), elf=Path("/e"), request=Path("/r"),
            selected_inputs=Path("/i"), fixture=Path("/f"))
        with mock.patch.object(owner.argparse.ArgumentParser, "parse_args",
                               return_value=args), \
             mock.patch.object(owner, "launch", side_effect=ValueError("boom")), \
             mock.patch.object(owner.sys, "stderr", io.StringIO()) as stream:
            self.assertEqual(owner.main(), 125)
            self.assertEqual(stream.getvalue(),
                             "owner infrastructure failure: ValueError: boom\n")

    def test_postfork_close_failure_still_runs_cleanup_once(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve() / "attempt"
            parent_endpoint = mock.Mock()
            child_endpoint = mock.Mock()
            child_endpoint.close.side_effect = OSError("child endpoint close")
            owner_pid = os.getpid()
            identity = {"pid": owner_pid, "ppid": os.getppid(), "startticks": 9}
            cleanup = {"complete": True, "trigger_kind": "owner-failure",
                "trigger_ns": 1, "cleanup_start_ns": 2,
                "cleanup_deadline_ns": 22000000001, "cleanup_finished_ns": 3,
                "events": [], "adopted_reaps": [], "unresolved": []}
            waited = {"kind": "wait", "pid": 77, "startticks": None,
                "raw_wait_status": 0, "direct": True, "monotonic_ns": 3}
            records = {name: {"path": "/" + name, "present": True,
                       "size": 1, "sha256": "a" * 64}
                       for name in ("source", "generated_source", "header", "elf")}
            runtime = {name: {"source_path": "/" + name,
                "destination_path": str(root / "retained-inputs" / filename),
                "size": size, "sha256": digest}
                for name, (size, digest, filename) in owner.RUNTIME_SPECS.items()}
            hashes = {"source_sha256": "a" * 64,
                "generated_sha256": "a" * 64, "header_sha256": "a" * 64,
                "elf_sha256": "a" * 64}
            with mock.patch.object(owner, "bind_inputs", return_value=records), \
                 mock.patch.object(owner, "bind_runtime_sources", return_value={}), \
                 mock.patch.object(owner, "retain_runtime_inputs", return_value=runtime), \
                 mock.patch.object(owner, "subreaper"), \
                 mock.patch.object(owner, "process_identity", return_value=identity), \
                 mock.patch.object(owner.socket, "socketpair",
                                   return_value=(parent_endpoint, child_endpoint)), \
                 mock.patch.object(owner.os, "fork", return_value=77), \
                 mock.patch.object(owner, "bounded_cleanup",
                                   return_value=(cleanup, waited)) as cleanup_call:
                with self.assertRaisesRegex(OSError, "child endpoint close"):
                    owner.launch(root, self.NONCE, 0, hashes, {}, {})
            cleanup_call.assert_called_once()
            self.assertTrue((root / "owner-result.json").exists())

    def test_exact_retained_input_and_executable_bindings(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            raw = {"source": prepare.SOURCE.read_bytes(),
                   "generated_source": b"generated-source\n",
                   "header": b"header\n", "elf": b"elf\n"}
            paths = {}
            for name, value in raw.items():
                path = root / name
                path.write_bytes(value)
                paths[name] = path
            hashes = {"source_sha256": hashlib.sha256(raw["source"]).hexdigest(),
                      "generated_sha256": hashlib.sha256(raw["generated_source"]).hexdigest(),
                      "header_sha256": hashlib.sha256(raw["header"]).hexdigest(),
                      "elf_sha256": hashlib.sha256(raw["elf"]).hexdigest()}
            records = owner.bind_inputs(paths, hashes)
            self.assertEqual(set(records), {"source", "generated_source",
                                             "header", "elf"})
            self.assertEqual(records["source"]["sha256"], self.SOURCE_SHA)
            owner.validate_executable([str(paths["elf"])], records)
            with self.assertRaisesRegex(ValueError, "executed ELF path"):
                owner.validate_executable([str(paths["source"])], records)
            bad = dict(hashes); bad["header_sha256"] = "0" * 64
            with self.assertRaisesRegex(ValueError, "input hash header"):
                owner.bind_inputs(paths, bad)
            link = root / "elf-link"
            link.symlink_to(paths["elf"])
            linked = dict(paths); linked["elf"] = link
            with self.assertRaisesRegex(ValueError, "canonical input path"):
                owner.bind_inputs(linked, hashes)

    def test_packet15_not_spawned_stage_flags_deadlines_and_empty_owner(self):
        """Preflight failures must retain an exact absent-owner contract."""
        failure = supervise.PreflightFailure("sentinel-fork", OSError("fork"),
                                             sigchld_default=True)
        cleanup = {"complete": True, "events": [
            {"kind": "owned-scan", "monotonic_ns": 201, "pids": []},
            {"kind": "owned-scan", "monotonic_ns": 202, "pids": []},
            {"kind": "echild", "monotonic_ns": 203, "return": -1,
             "errno": 10}], "unresolved": []}
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve() / "attempt"
            args = mock.Mock(attempt_root=root)
            with mock.patch.object(supervise, "validate_inputs"), \
                 mock.patch.object(supervise.time, "monotonic_ns",
                                   side_effect=[100, 200, 300]), \
                 mock.patch.object(supervise.os, "getpid", return_value=20), \
                 mock.patch.object(supervise, "establish_wait_authority",
                                   side_effect=failure), \
                 mock.patch.object(supervise, "cleanup_tree",
                                   return_value=(cleanup, None)), \
                 mock.patch.object(supervise, "ensure_attempt_root",
                                   side_effect=lambda path: path.mkdir() or path), \
                 mock.patch.object(supervise, "publish_result"):
                result, status = supervise.run_supervisor(args)
            self.assertEqual(status, 125)
            self.assertTrue(oracle.validate_supervisor_record(result))
            mutations = (
                (lambda value: value["preflight_failure"].__setitem__(
                    "stage", "owner-start"), "supervisor preflight failure"),
                (lambda value: value.__setitem__("sigchld_default", False),
                 "supervisor preflight flags"),
                (lambda value: value.__setitem__("sentinel_wait_passed", True),
                 "supervisor preflight flags"),
                (lambda value: value.__setitem__("supervisor_deadline_ns",
                    value["supervisor_deadline_ns"] + 1),
                 "supervisor absent evidence"),
                (lambda value: value.__setitem__("owner_wait_deadline_ns", 0),
                 "supervisor absent owner"),
                (lambda value: value.__setitem__("owner_exit_code", ""),
                 "supervisor absent owner"),
                (lambda value: value["owner_identity"].__setitem__(
                    "spawn_error", {}), "supervisor preflight state"),
            )
            for edit, message in mutations:
                changed = copy.deepcopy(result); edit(changed)
                with self.subTest(message=message), \
                     self.assertRaisesRegex(ValueError, message):
                    oracle.validate_supervisor_record(changed)

    def test_supervisor_exception_recovery_retains_prefix_and_drains_progress(self):
        """A cleanup helper fault cannot discard its event/wait prefix."""
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve() / "attempt"
            args = mock.Mock(attempt_root=root)
            observation = {"observation": "observed", "pid": 77,
                "ppid": 20, "startticks": 30, "monotonic_ns": 150}
            direct = {"kind": "wait", "pid": 77, "startticks": 30,
                "raw_wait_status": 0, "direct": True, "monotonic_ns": 200}
            session_prefix = {"events": [direct], "unresolved": [],
                              "direct_wait": direct, "direct_reaped": True,
                              "authority_lost": False}
            recovered = {"complete": True, "events": [direct,
                {"kind": "owned-scan", "monotonic_ns": 210, "pids": []},
                {"kind": "owned-scan", "monotonic_ns": 220, "pids": []},
                {"kind": "echild", "monotonic_ns": 230,
                 "return": -1, "errno": 10}], "unresolved": []}
            calls = []
            def cleanup(*values, **kwargs):
                calls.append(kwargs.get("authority_lost", False))
                session = kwargs["session"]
                if len(calls) == 1:
                    session["events"].append({"kind": "wait", "pid": 77,
                        "startticks": 30, "raw_wait_status": 0, "direct": True,
                        "monotonic_ns": 200})
                    raise OSError("cleanup helper")
                return recovered, direct
            def pump(*values, **kwargs):
                state = values[-1]
                state.update({"stdout_eof": True, "stderr_eof": True,
                              "raw_wait_status": 0, "waited_ns": 200})
                return state
            with mock.patch.object(supervise, "validate_inputs"), \
                 mock.patch.object(supervise.time, "monotonic_ns",
                                   side_effect=[100, 110, 120, 300, 310]), \
                 mock.patch.object(supervise.os, "getpid", return_value=20), \
                 mock.patch.object(supervise, "establish_wait_authority"), \
                 mock.patch.object(supervise, "spawn_owner",
                                   return_value=(77, 3, 4, [])), \
                 mock.patch.object(supervise, "observe_identity",
                                   side_effect=[observation, dict(observation)]), \
                 mock.patch.object(supervise, "pump_owner", side_effect=pump), \
                 mock.patch.object(supervise, "cleanup_tree", side_effect=cleanup), \
                 mock.patch.object(supervise, "finish_pipes"), \
                 mock.patch.object(supervise, "ensure_attempt_root",
                                   side_effect=lambda path: path.mkdir() or path), \
                 mock.patch.object(supervise, "publish_result"):
                result, status = supervise.run_supervisor(args)
            self.assertEqual(status, 125)
            self.assertEqual(calls, [False, True])
            self.assertEqual(result["supervisor_cleanup"]["events"][0], direct)
            self.assertLessEqual(result["finished_ns"],
                                 result["supervisor_cleanup_deadline_ns"])

    def test_cleanup_recognizes_generic_direct_reap_and_echild_authority(self):
        progress = mock.Mock()
        scans = iter((110, 120))
        def empty_scan(*values):
            return [], [{"kind": "owned-scan", "monotonic_ns": next(scans),
                         "pids": []}], [], False
        with mock.patch.object(supervise.time, "monotonic_ns",
                               side_effect=iter(range(100, 300))), \
             mock.patch.object(supervise.time, "sleep"), \
             mock.patch.object(supervise, "scan_owned", side_effect=empty_scan), \
             mock.patch.object(supervise.os, "waitpid",
                               side_effect=[(77, 0), ChildProcessError(),
                                            ChildProcessError(), ChildProcessError()]):
            cleanup, waited = supervise.cleanup_tree(
                77, [], None, 20, 100, 1000, authority_lost=True,
                progress=progress)
        self.assertIsNotNone(waited)
        self.assertTrue(waited["direct"])
        self.assertEqual(waited["pid"], 77)
        self.assertTrue(cleanup["complete"])
        self.assertEqual(cleanup["events"][-1]["kind"], "echild")
        self.assertGreater(progress.call_count, 0)
        self.assertTrue(all(event["monotonic_ns"] <= 1000
                            for event in cleanup["events"]))

    def test_cleanup_normalizes_absent_direct_child_and_proves_empty_tree(self):
        scans = iter((110, 120))
        def empty_scan(*values):
            return [], [{"kind": "owned-scan", "monotonic_ns": next(scans),
                         "pids": []}], [], False
        session = {"events": [], "unresolved": [], "direct_wait": None,
                   "direct_reaped": False, "authority_lost": False}
        with mock.patch.object(supervise.time, "monotonic_ns",
                               side_effect=iter(range(100, 300))), \
             mock.patch.object(supervise.time, "sleep"), \
             mock.patch.object(supervise, "scan_owned", side_effect=empty_scan), \
             mock.patch.object(supervise.os, "waitpid",
                               side_effect=ChildProcessError()):
            cleanup, waited = supervise.cleanup_tree(
                None, [], None, 20, 100, 1000, session=session)
        self.assertIsNone(waited)
        self.assertTrue(session["direct_reaped"])
        self.assertTrue(cleanup["complete"])
        self.assertEqual([event["kind"] for event in cleanup["events"]],
                         ["owned-scan", "owned-scan", "echild"])

    def test_packet15_real_sentinel_wait_cleanup_round_trips_oracle(self):
        direct = {"kind": "wait", "pid": 77, "startticks": None,
            "raw_wait_status": 1, "direct": True, "monotonic_ns": 200}
        clock = iter(range(201, 500))
        scan_index = [0]
        def empty_scan(*values):
            scan_index[0] += 1
            return [], [{"kind": "owned-scan",
                "monotonic_ns": next(clock), "pids": []}], [], False
        with mock.patch.object(supervise.time, "monotonic_ns",
                               side_effect=lambda: next(clock)), \
             mock.patch.object(supervise.time, "sleep"), \
             mock.patch.object(supervise, "scan_owned", side_effect=empty_scan), \
             mock.patch.object(supervise.os, "waitpid",
                               side_effect=ChildProcessError()):
            cleanup, waited = supervise.cleanup_tree(
                77, [], direct, 20, 200, 22_000_000_200,
                require_direct_birth=True,
                initial_wait_deadline_ns=5_000_000_100)
            finished = next(clock)
        self.assertEqual(waited, direct)
        self.assertTrue(cleanup["complete"])
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            result = supervise.supervisor_result(
                root, 20, 100, finished,
                {"state": "NOT_SPAWNED", "pid": None, "ppid": None,
                 "startticks": None, "spawn_error": None}, [], None,
                b"", b"", cleanup, 100, 5_000_000_100, None, 200,
                22_000_000_200, 33_000_000_100, True, False,
                {"stage": "sentinel-wait", "type": "OSError",
                 "message": "wrong sentinel wait", "errno": None}, False)
            self.assertTrue(oracle.validate_supervisor_record(result))
            invented = copy.deepcopy(result)
            invented["preflight_failure"]["stage"] = "sentinel-fork"
            with self.assertRaisesRegex(ValueError,
                                        "unexpected sentinel wait"):
                oracle.validate_supervisor_record(invented)
            invented_error = copy.deepcopy(result)
            invented_error["preflight_failure"]["stage"] = "sentinel-fork"
            invented_error["supervisor_cleanup"]["complete"] = False
            invented_error["supervisor_cleanup"]["events"] = \
                invented_error["supervisor_cleanup"]["events"][1:]
            invented_error["supervisor_cleanup"]["unresolved"] = [{
                "kind": "signal-error", "stage": "term", "pid": 77,
                "startticks": 88, "signal": 15, "errno": 3,
                "monotonic_ns": 205, "direct": True}]
            with self.assertRaisesRegex(ValueError,
                                        "supervisor sentinel authority"):
                oracle.validate_supervisor_record(invented_error)

    def test_oracle_rejects_boolean_acquisition_identity(self):
        def replace(root):
            self.rewrite_journal(root / "witness.jsonl", lambda rows: [
                row["packet"].__setitem__("acquisition_id", False)
                for row in rows if row["packet"].get("site") in
                ("request-write", "request-sync")])
        self.mutate(0, replace, "request acquisition")

    def test_supervisor_oracle_rejects_post_reap_adopted_signal(self):
        identity = {"state": "MATCHED", "pid": 40, "ppid": 20,
                    "startticks": 30, "spawn_error": None}
        direct = {"kind": "wait", "pid": 40, "startticks": 30,
            "raw_wait_status": 0, "direct": True, "monotonic_ns": 110}
        pair1 = [
            {"kind": "identity", "phase": "owned-scan-1-1",
             "observation": "observed", "pid": 99, "ppid": 20,
             "startticks": 88, "matched": True, "monotonic_ns": 120},
            {"kind": "identity", "phase": "owned-scan-1-2",
             "observation": "observed", "pid": 99, "ppid": 20,
             "startticks": 88, "matched": True, "monotonic_ns": 130}]
        signal1 = {"kind": "signal", "pid": 99, "startticks": 88,
                   "signal": 9, "monotonic_ns": 140}
        reap = {"kind": "wait", "pid": 99, "startticks": 88,
                "raw_wait_status": 9, "direct": False,
                "monotonic_ns": 150}
        pair2 = copy.deepcopy(pair1)
        pair2[0].update({"phase": "owned-scan-2-1", "monotonic_ns": 160})
        pair2[1].update({"phase": "owned-scan-2-2", "monotonic_ns": 170})
        signal2 = dict(signal1, monotonic_ns=180)
        cleanup = {"complete": False,
            "events": [direct, *pair1, signal1, reap, *pair2, signal2],
            "unresolved": [{"kind": "owned", "phase": "owned-scan-1",
                "pid": 99, "ppid": 20, "startticks": 88,
                "monotonic_ns": 115}]}
        with self.assertRaisesRegex(ValueError, "supervisor cleanup signal"):
            oracle.validate_supervisor_cleanup(cleanup, identity, 20, 200, 100,
                                               1000, 2000, 200)

    def test_owner_oracle_rejects_post_reap_adopted_signal(self):
        def inject(root):
            def edit(value):
                pair1 = [
                    {"kind": "identity", "phase": "owned-scan-1-1",
                     "observation": "observed", "pid": 99, "ppid": 40,
                     "startticks": 88, "matched": True,
                     "monotonic_ns": 6210},
                    {"kind": "identity", "phase": "owned-scan-1-2",
                     "observation": "observed", "pid": 99, "ppid": 40,
                     "startticks": 88, "matched": True,
                     "monotonic_ns": 6220}]
                signal1 = {"kind": "signal", "pid": 99,
                    "startticks": 88, "signal": 9, "monotonic_ns": 6230}
                reap = {"kind": "wait", "pid": 99, "startticks": 88,
                    "raw_wait_status": 9, "direct": False,
                    "monotonic_ns": 6240}
                pair2 = copy.deepcopy(pair1)
                pair2[0].update({"phase": "owned-scan-2-1",
                                 "monotonic_ns": 6250})
                pair2[1].update({"phase": "owned-scan-2-2",
                                 "monotonic_ns": 6260})
                signal2 = dict(signal1, monotonic_ns=6270)
                value["cleanup"]["events"][1:1] = [
                    *pair1, signal1, reap, *pair2, signal2]
                value["cleanup"]["adopted_reaps"] = [reap]
            self.republish_owner(root, edit)
        self.mutate(0, inject, "owner signal after reap")

    def test_oracles_accept_never_observed_adopted_reaps(self):
        supervisor_identity = {"state": "MATCHED", "pid": 40, "ppid": 20,
            "startticks": 30, "spawn_error": None}
        supervisor_cleanup = {"complete": True, "unresolved": [], "events": [
            {"kind": "wait", "pid": 40, "startticks": 30,
             "raw_wait_status": 0, "direct": True, "monotonic_ns": 110},
            {"kind": "wait", "pid": 99, "startticks": None,
             "raw_wait_status": 0, "direct": False, "monotonic_ns": 120},
            {"kind": "owned-scan", "monotonic_ns": 130, "pids": []},
            {"kind": "owned-scan", "monotonic_ns": 140, "pids": []},
            {"kind": "echild", "monotonic_ns": 150,
             "return": -1, "errno": 10}]}
        oracle.validate_supervisor_cleanup(supervisor_cleanup,
            supervisor_identity, 20, 200, 100, 1000, 2000, 160)
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "case"
            self.write_fixture(root, 0)
            def edit(value):
                reap = {"kind": "wait", "pid": 99, "startticks": None,
                    "raw_wait_status": 0, "direct": False,
                    "monotonic_ns": 6250}
                value["cleanup"]["events"].insert(1, reap)
                value["cleanup"]["adopted_reaps"] = [reap]
            self.republish_owner(root, edit)
            self.refresh_supervisor(root)
            self.assertTrue(oracle.validate(root, 0, 0))

    def test_oracle_rejects_exact_selector4_observation_semantics(self):
        mutations = (
            lambda rows: rows[0].__setitem__("occurrence", False),
            lambda rows: next(row for row in rows if row["kind"] ==
                "CLEANUP_READY").__setitem__("stdout_eof", 1),
            lambda rows: next(row for row in rows if row["kind"] ==
                "REAP").__setitem__("raw_wait_status", 256),
            lambda rows: next(row for row in rows if row["kind"] ==
                "EOF").__setitem__("closed_fd", -1),
            lambda rows: next(row for row in rows if row["kind"] ==
                "CLEANUP_FINAL").__setitem__("cleanup_deadline_ns",
                    15_000_003_501),
        )
        for index, mutation in enumerate(mutations):
            with self.subTest(index=index), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary) / "case"
                self.write_fixture(root, 4)
                self.rewrite_journal(root / "witness.jsonl", lambda rows:
                    mutation([row["packet"] for row in rows]))
                self.refresh_supervisor(root)
                with self.assertRaises(ValueError):
                    oracle.validate(root, 4, 0)

    def test_live_descriptor_ledger_rejects_retained_bind_collision(self):
        packets = copy.deepcopy(self.packets(0))
        next(packet for packet in packets if packet["kind"] == "BIND" and
             packet["site"] == "events-create")["new_fd"] = 12
        state = owner.PacketState(0)
        with self.assertRaisesRegex(ValueError, "descriptor"):
            for packet in packets:
                owner.validate_packet_schema(packet, 0)
                state.validate(packet)
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "case"
            self.write_fixture(root, 0)
            self.rewrite_journal(root / "witness.jsonl", lambda rows:
                next(row["packet"] for row in rows if
                     row["packet"]["kind"] == "BIND" and
                     row["packet"]["site"] == "events-create").
                     __setitem__("new_fd", 12))
            self.refresh_supervisor(root)
            with self.assertRaisesRegex(ValueError, "descriptor"):
                oracle.validate(root, 0, 0)

    def test_eof_rejects_directory_and_live_file_capability_aliases(self):
        # Post-fork selectors emit EOF while fd 5 is the attempt directory
        # and fds 10/11 are live file capabilities.
        for selector in (0, 3, 4, 5):
            eof_count = sum(packet["kind"] == "EOF"
                            for packet in self.packets(selector))
            for eof_index in range(eof_count):
                for alias in (5, 10, 11):
                    with self.subTest(selector=selector, eof_index=eof_index,
                                      alias=alias), \
                            tempfile.TemporaryDirectory() as temporary:
                        def replace_eof(rows):
                            eof_packets = [row["packet"] for row in rows
                                           if row["packet"]["kind"] == "EOF"]
                            eof_packets[eof_index]["closed_fd"] = alias

                        packets = copy.deepcopy(self.packets(selector))
                        eof_packets = [packet for packet in packets
                                       if packet["kind"] == "EOF"]
                        eof_packets[eof_index]["closed_fd"] = alias
                        state = owner.PacketState(selector)
                        with self.assertRaisesRegex(ValueError, "eof descriptor"):
                            for packet in packets:
                                owner.validate_packet_schema(packet, selector)
                                state.validate(packet)
                        root = Path(temporary) / "case"
                        self.write_fixture(root, selector)
                        self.rewrite_journal(root / "witness.jsonl", replace_eof)
                        self.refresh_supervisor(root)
                        with self.assertRaisesRegex(ValueError, "eof descriptor"):
                            oracle.validate(root, selector, 0)

    def test_bind_sizes_match_empty_create_snapshot(self):
        """Every pre-write BIND must preserve the empty create snapshot size."""
        for selector in range(7):
            bind_count = sum(packet["kind"] == "BIND"
                             for packet in self.packets(selector))
            for bind_index in range(bind_count):
                for mutation in ("old", "new", "both"):
                    with self.subTest(selector=selector, bind_index=bind_index,
                                      mutation=mutation), \
                            tempfile.TemporaryDirectory() as temporary:
                        def replace_bind(rows):
                            bind_packets = [row["packet"] for row in rows
                                            if row["packet"]["kind"] == "BIND"]
                            bind = bind_packets[bind_index]
                            if mutation in ("old", "both"):
                                bind["old_stat"]["size"] = 1
                            if mutation in ("new", "both"):
                                bind["new_stat"]["size"] = 1

                        packets = copy.deepcopy(self.packets(selector))
                        bind_packets = [packet for packet in packets
                                        if packet["kind"] == "BIND"]
                        bind = bind_packets[bind_index]
                        if mutation in ("old", "both"):
                            bind["old_stat"]["size"] = 1
                        if mutation in ("new", "both"):
                            bind["new_stat"]["size"] = 1
                        state = owner.PacketState(selector)
                        with self.assertRaisesRegex(ValueError, "bind identity"):
                            for packet in packets:
                                owner.validate_packet_schema(packet, selector)
                                state.validate(packet)
                        root = Path(temporary) / "case"
                        self.write_fixture(root, selector)
                        self.rewrite_journal(root / "witness.jsonl", replace_bind)
                        self.refresh_supervisor(root)
                        with self.assertRaisesRegex(ValueError, "bind identity"):
                            oracle.validate(root, selector, 0)

    def test_descriptor_domain_transport_and_directory_inode_invariants(self):
        def rejected(selector, edit, message):
            packets = copy.deepcopy(self.packets(selector))
            edit(packets)
            state = owner.PacketState(selector)
            with self.assertRaisesRegex(ValueError, message):
                for packet in packets:
                    owner.validate_packet_schema(packet, selector)
                    state.validate(packet)
            with tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary) / "case"
                self.write_fixture(root, selector)
                self.rewrite_journal(root / "witness.jsonl",
                    lambda rows: edit([row["packet"] for row in rows]))
                self.refresh_supervisor(root)
                with self.assertRaisesRegex(ValueError, message):
                    oracle.validate(root, selector, 0)

        def packets_of(packets, kind=None, site=None, object_name=None):
            return [packet for packet in packets
                    if (kind is None or packet["kind"] == kind) and
                       (site is None or packet["site"] == site) and
                       (object_name is None or
                        packet.get("object") == object_name)]

        for selector in range(7):
            baseline = self.packets(selector)
            bind_count = len(packets_of(baseline, kind="BIND"))
            for bind_index in range(bind_count):
                with self.subTest(rule="high-fd-relocation", selector=selector,
                                  bind_index=bind_index):
                    def relocate(packets):
                        packets_of(packets, kind="BIND")[bind_index]["new_fd"] = 30
                    rejected(selector, relocate, "bind descriptor")

                with self.subTest(rule="unrelocated-low-fd", selector=selector,
                                  bind_index=bind_index):
                    def low_bind(packets):
                        bind = packets_of(packets, kind="BIND")[bind_index]
                        create = packets_of(packets, kind="AFTER",
                                            site=bind["site"])[0]
                        create["fd"] = create["return"] = 0
                        bind["old_fd"] = bind["new_fd"] = 0
                    rejected(selector, low_bind, "high descriptor")

            with self.subTest(rule="low-directory", selector=selector):
                def low_directory(packets):
                    for packet in packets:
                        if "dirfd" in packet:
                            packet["dirfd"] = 0
                rejected(selector, low_directory, "high descriptor")

            request_packets = packets_of(baseline, object_name="request.bin")
            if request_packets:
                with self.subTest(rule="low-request", selector=selector):
                    def low_request(packets):
                        for packet in packets_of(packets, object_name="request.bin"):
                            if "fd" in packet:
                                packet["fd"] = 0
                    rejected(selector, low_request, "high descriptor")

            eof_count = len(packets_of(baseline, kind="EOF"))
            for eof_index in range(eof_count):
                with self.subTest(rule="low-eof", selector=selector,
                                  eof_index=eof_index):
                    def low_eof(packets):
                        packets_of(packets, kind="EOF")[eof_index]["closed_fd"] = 0
                    rejected(selector, low_eof, "high descriptor")

            with self.subTest(rule="transport-directory", selector=selector):
                def transport_directory(packets):
                    for packet in packets:
                        if "dirfd" in packet:
                            packet["dirfd"] = owner.WITNESS_FD
                rejected(selector, transport_directory, "transport descriptor")

            for bind_index in range(bind_count):
                with self.subTest(rule="transport-acquisition", selector=selector,
                                  bind_index=bind_index):
                    def transport_acquisition(packets):
                        bind = packets_of(packets, kind="BIND")[bind_index]
                        create = packets_of(packets, kind="AFTER",
                                            site=bind["site"])[0]
                        create["fd"] = create["return"] = owner.WITNESS_FD
                        bind["old_fd"] = bind["new_fd"] = owner.WITNESS_FD
                    rejected(selector, transport_acquisition,
                             "transport descriptor")

                with self.subTest(rule="transport-bind", selector=selector,
                                  bind_index=bind_index):
                    def transport_bind(packets):
                        packets_of(packets, kind="BIND")[bind_index]["new_fd"] = \
                            owner.WITNESS_FD
                    rejected(selector, transport_bind, "transport descriptor")

            if request_packets:
                with self.subTest(rule="transport-request", selector=selector):
                    def transport_request(packets):
                        for packet in packets_of(packets, object_name="request.bin"):
                            if "fd" in packet:
                                packet["fd"] = owner.WITNESS_FD
                    rejected(selector, transport_request, "transport descriptor")

            for eof_index in range(eof_count):
                with self.subTest(rule="transport-eof", selector=selector,
                                  eof_index=eof_index):
                    def transport_eof(packets):
                        packets_of(packets, kind="EOF")[eof_index]["closed_fd"] = \
                            owner.WITNESS_FD
                    rejected(selector, transport_eof, "transport descriptor")

            for bind_index in range(bind_count):
                with self.subTest(rule="directory-file-alias", selector=selector,
                                  bind_index=bind_index):
                    def directory_file_alias(packets):
                        bind = packets_of(packets, kind="BIND")[bind_index]
                        object_name = bind["object"]
                        for packet in packets_of(packets, object_name=object_name):
                            for stat_name in ("target_stat", "old_stat", "new_stat"):
                                value = packet.get(stat_name)
                                if value is not None:
                                    value["dev"], value["ino"] = 1, 90
                    rejected(selector, directory_file_alias,
                             "directory inode collision")

            if request_packets:
                with self.subTest(rule="directory-request-alias", selector=selector):
                    def directory_request_alias(packets):
                        for packet in packets_of(packets, object_name="request.bin"):
                            value = packet.get("target_stat")
                            if value is not None:
                                value["dev"], value["ino"] = 1, 90
                    rejected(selector, directory_request_alias,
                             "directory inode collision")

    def test_counterexample_cleanup_exhausts_term_kill_and_keeps_direct_timeout(self):
        now = [100]
        def clock():
            now[0] += 1_000_000_000
            return now[0]
        def no_scan(*args):
            return [], [{"kind": "owned-scan", "monotonic_ns": clock(), "pids": []}], [], False
        def timeout(_pid, deadline, *_args, **_kwargs):
            now[0] = deadline
            return None
        with mock.patch.object(supervise.time, "monotonic_ns", side_effect=clock), \
             mock.patch.object(supervise.time, "sleep"), \
             mock.patch.object(supervise, "double_identity", side_effect=lambda pid, phase, parent, ticks=None:
                 ([{"kind": "identity", "phase": phase + "-1", "observation": "observed",
                   "pid": pid, "ppid": parent, "startticks": 30, "matched": True,
                   "monotonic_ns": clock()}, {"kind": "identity", "phase": phase + "-2",
                   "observation": "observed", "pid": pid, "ppid": parent, "startticks": 30,
                   "matched": True, "monotonic_ns": clock()}], 30)), \
             mock.patch.object(supervise, "wait_cleanup_pid", side_effect=timeout), \
             mock.patch.object(supervise.os, "kill"), \
             mock.patch.object(supervise, "scan_owned", side_effect=no_scan), \
             mock.patch.object(supervise.os, "waitpid", side_effect=ChildProcessError()):
            cleanup, waited = supervise.cleanup_tree(77, [], None, 20, 100,
                20_000_000_000, initial_wait_timed_out=True,
                initial_wait_deadline_ns=100)
        self.assertIsNone(waited)
        self.assertEqual([x["stage"] for x in cleanup["unresolved"]
                          if x["kind"] == "wait-timeout"], ["direct", "term", "kill"])

    def test_counterexample_direct_wait_deadline_and_wrong_parent_birth_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "case"; self.write_fixture(root, 0)
            self.rewrite_json(root / "supervisor-result.json", lambda value:
                value["supervisor_cleanup"]["events"][0].__setitem__(
                    "monotonic_ns", value["owner_wait_deadline_ns"] + 1))
            self.refresh_supervisor(root)
            with self.assertRaisesRegex(ValueError, "direct wait|owner wait|event time"):
                oracle.validate(root, 0, 0)
            result = json.loads((root / "supervisor-result.json").read_text())
            result["owner_identity_observations"][1]["ppid"] = 21
            with self.assertRaisesRegex(ValueError, "owner observations|classification"):
                oracle.validate_supervisor_record(result)

    def test_counterexample_signal_errors_cannot_follow_wait_or_unbound_adopted(self):
        identity = {"state": "MATCHED", "pid": 40, "ppid": 20,
                    "startticks": 30, "spawn_error": None}
        events = [{"kind": "wait", "pid": 40, "startticks": 30,
                   "raw_wait_status": 0, "direct": True, "monotonic_ns": 10}]
        cleanup = {"complete": False, "events": events,
                   "unresolved": [{"kind": "signal-error", "stage": "term",
                     "pid": 40, "startticks": 30, "signal": 15, "errno": 3,
                     "monotonic_ns": 11, "direct": True}]}
        with self.assertRaisesRegex(ValueError, "after wait|signal error"):
            oracle.validate_supervisor_cleanup(cleanup, identity, 20, 20, 1, 30, 30, 20, None)
        adopted = copy.deepcopy(cleanup)
        adopted["unresolved"][0].update({"direct": False, "pid": 41, "startticks": 31})
        with self.assertRaisesRegex(ValueError, "signal error|identity"):
            oracle.validate_supervisor_cleanup(adopted, identity, 20, 20, 1, 30, 30, 20, None)

    def test_counterexample_adopted_raw_wait_values_rejected_through_validate_owner(self):
        for raw in (-1, 65536, 127, 65535):
            with self.subTest(raw=raw):
                with tempfile.TemporaryDirectory() as temporary:
                    root = Path(temporary) / "case"
                    self.write_fixture(root, 0)
                    def edit(value):
                        value["cleanup"]["events"].insert(-1, {
                            "kind": "owned-scan", "monotonic_ns": 6550,
                            "pids": [{"pid": 71, "ppid": 40, "startticks": 81}]})
                        value["cleanup"]["events"].insert(-1, {
                            "kind": "wait", "pid": 71, "startticks": 81,
                            "raw_wait_status": raw, "direct": False,
                            "monotonic_ns": 6551})
                    self.republish_owner(root, edit)
                    self.refresh_supervisor(root)
                    with self.assertRaisesRegex(ValueError, "wait|cleanup terminal"):
                        oracle.validate(root, 0, 0)

    def test_counterexample_scan_cap_still_requires_direct_timeout(self):
        now = [100]
        def clock():
            return now[0]
        def sleep(_seconds):
            now[0] += 100
        def empty_scan(*_args):
            return [], [{"kind": "owned-scan", "monotonic_ns": now[0],
                         "pids": []}], [], False
        session = {"events": [], "unresolved": [], "authority_lost": True,
                   "direct_wait": None, "direct_reaped": False,
                   "scan_index": 2046, "consecutive_empty": 0}
        with mock.patch.object(supervise.time, "monotonic_ns", side_effect=clock), \
             mock.patch.object(supervise.time, "sleep", side_effect=sleep), \
             mock.patch.object(supervise, "scan_owned", side_effect=empty_scan), \
             mock.patch.object(supervise.os, "waitpid", return_value=(0, 0)):
            cleanup, waited = supervise.cleanup_tree(77, [], None, 20, 1, 1000,
                initial_wait_timed_out=False, initial_wait_deadline_ns=1000,
                authority_lost=True, session=session)
        self.assertIsNone(waited)
        self.assertGreaterEqual(session["finished_ns"], 1000)
        self.assertTrue(any(item.get("kind") == "wait-timeout" and
                            item.get("stage") == "direct"
                            for item in cleanup["unresolved"]))

    def test_counterexample_adopted_signal_error_joins_owned_expiration(self):
        identity = {"state": "MATCHED", "pid": 40, "ppid": 20,
                    "startticks": 30, "spawn_error": None}
        cleanup = {"complete": False, "events": [
            {"kind": "wait", "pid": 40, "startticks": 30,
             "raw_wait_status": 0, "direct": True, "monotonic_ns": 10},
            {"kind": "identity", "phase": "owned-scan-1-1",
             "observation": "observed", "pid": 41, "ppid": 20,
             "startticks": 31, "matched": True, "monotonic_ns": 20},
            {"kind": "identity", "phase": "owned-scan-1-2",
             "observation": "observed", "pid": 41, "ppid": 20,
             "startticks": 31, "matched": True, "monotonic_ns": 21},
            {"kind": "owned-scan", "monotonic_ns": 22,
             "pids": [{"pid": 41, "ppid": 20, "startticks": 31}]},
            {"kind": "identity", "phase": "owned-scan-1-1",
             "observation": "observed", "pid": 41, "ppid": 20,
             "startticks": 31, "matched": True, "monotonic_ns": 24},
            {"kind": "identity", "phase": "owned-scan-1-2",
             "observation": "observed", "pid": 41, "ppid": 20,
             "startticks": 31, "matched": True, "monotonic_ns": 25}],
            "unresolved": [
                {"kind": "owned", "phase": "owned-scan-1", "pid": 41,
                 "ppid": 20, "startticks": 31, "monotonic_ns": 23},
                {"kind": "signal-error", "stage": "kill", "pid": 41,
                 "startticks": 31, "signal": 9, "errno": 1,
                 "monotonic_ns": 26, "direct": False},
                {"kind": "deadline", "stage": "owned-scan",
                 "monotonic_ns": 50, "deadline_ns": 50}]}
        oracle.validate_supervisor_cleanup(cleanup, identity, 20, 200,
                                           1, 50, 100, 50)
        for mutation, message in (
                (lambda value: value["unresolved"][1].__setitem__(
                    "startticks", 32), "authority"),
                (lambda value: value["events"][4].__setitem__(
                    "ppid", 21), "authority"),
                (lambda value: value["events"][4].__setitem__(
                    "phase", "owned-scan-2-1"), "authority"),
                (lambda value: value["unresolved"].pop(0), "join"),
                (lambda value: value["unresolved"][2].__setitem__(
                    "monotonic_ns", 49), "deadline")):
            changed = copy.deepcopy(cleanup); mutation(changed)
            with self.assertRaisesRegex(ValueError, message):
                oracle.validate_supervisor_cleanup(changed, identity, 20,
                                                    200, 1, 50, 100, 50)
        post_reap = copy.deepcopy(cleanup)
        post_reap["events"].insert(4, {"kind": "wait", "pid": 41,
            "startticks": 31, "raw_wait_status": 0, "direct": False,
            "monotonic_ns": 23})
        with self.assertRaisesRegex(ValueError, "authority"):
            oracle.validate_supervisor_cleanup(post_reap, identity, 20,
                                                200, 1, 50, 100, 50)
        intervening_echild = copy.deepcopy(cleanup)
        intervening_echild["events"].append({"kind": "echild",
            "monotonic_ns": 30, "return": -1, "errno": 10})
        with self.assertRaisesRegex(ValueError, "join|authority"):
            oracle.validate_supervisor_cleanup(intervening_echild, identity,
                                                20, 200, 1, 50, 100, 50)

    def test_scan_cap_direct_reap_and_echild_do_not_fake_terminal_proof(self):
        def run(waitpid):
            now = [100]
            def clock(): return now[0]
            def sleep(_seconds): now[0] += 100
            session = {"events": [
                    {"kind": "owned-scan", "monotonic_ns": 80, "pids": []},
                    {"kind": "owned-scan", "monotonic_ns": 90, "pids": []}],
                "unresolved": [], "authority_lost": True,
                "direct_wait": None, "direct_reaped": False,
                "last_birth": 30, "scan_index": 2047,
                "consecutive_empty": 2}
            with mock.patch.object(supervise.time, "monotonic_ns",
                    side_effect=clock), \
                 mock.patch.object(supervise.time, "sleep", side_effect=sleep), \
                 mock.patch.object(supervise.os, "waitpid", side_effect=waitpid):
                cleanup, waited = supervise.cleanup_tree(77, [], None, 20,
                    1, 500, initial_wait_deadline_ns=500,
                    authority_lost=True, session=session)
            return cleanup, waited, session

        calls = [0]
        def reap_direct(_pid, _flags):
            calls[0] += 1
            return (77, 0) if calls[0] == 1 else (0, 0)
        cleanup, waited, session = run(reap_direct)
        self.assertEqual(waited["pid"], 77)
        self.assertFalse(cleanup["complete"])
        self.assertGreaterEqual(session["finished_ns"], 500)
        self.assertFalse(any(item.get("kind") == "wait-timeout" and
                             item.get("stage") == "direct"
                             for item in cleanup["unresolved"]))
        self.assertTrue(any(item.get("kind") == "deadline" and
                            item.get("stage") == "owned-scan"
                            for item in cleanup["unresolved"]))

        cleanup, waited, session = run(ChildProcessError())
        self.assertIsNone(waited)
        self.assertFalse(cleanup["complete"])
        self.assertGreaterEqual(session["finished_ns"], 500)
        self.assertTrue(any(item.get("kind") == "wait-timeout" and
                            item.get("stage") == "direct"
                            for item in cleanup["unresolved"]))

    def test_run_supervisor_published_finish_cannot_cross_cleanup_deadline(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            (root / "owner-result.json").write_text(
                '{"owner":{"pid":77,"startticks":30}}')
            (root / "witness.jsonl").write_bytes(b"witness\n")
            (root / "owner-errors.jsonl").write_bytes(b"")
            args = mock.Mock(attempt_root=root)
            observation = {"observation": "observed", "pid": 77,
                "ppid": 20, "startticks": 30, "monotonic_ns": 210}
            direct_wait = {"kind": "wait", "pid": 77, "startticks": 30,
                "raw_wait_status": 0, "direct": True, "monotonic_ns": 300}
            cleanup = {"complete": True, "unresolved": [], "events": [
                direct_wait,
                {"kind": "owned-scan", "monotonic_ns": 310, "pids": []},
                {"kind": "owned-scan", "monotonic_ns": 320, "pids": []},
                {"kind": "echild", "monotonic_ns": 330,
                 "return": -1, "errno": 10}]}
            def pump(_pid, _stdout_fd, _stderr_fd, _deadline_ns, state):
                state.update({"stdout": b"out", "stderr": b"err",
                    "stdout_eof": True, "stderr_eof": True,
                    "raw_wait_status": 0, "waited_ns": 300})
                return state
            published_finish = 300 + supervise.CLEANUP_NS + 1
            with mock.patch.object(supervise, "validate_inputs"), \
                 mock.patch.object(supervise.time, "monotonic_ns",
                    side_effect=[100, 200, published_finish]), \
                 mock.patch.object(supervise.os, "getpid", return_value=20), \
                 mock.patch.object(supervise, "establish_wait_authority"), \
                 mock.patch.object(supervise, "spawn_owner",
                    return_value=(77, 3, 4, [])), \
                 mock.patch.object(supervise, "observe_identity",
                    side_effect=[observation, dict(observation)]), \
                 mock.patch.object(supervise, "pump_owner", side_effect=pump), \
                 mock.patch.object(supervise, "cleanup_tree",
                    return_value=(cleanup, direct_wait)), \
                 mock.patch.object(supervise, "finish_pipes"), \
                 mock.patch.object(supervise, "ensure_attempt_root",
                    return_value=root), \
                 mock.patch.object(supervise, "publish_result"):
                result, status = supervise.run_supervisor(args)
            self.assertEqual(result["finished_ns"], published_finish)
            self.assertEqual(status, 125)
            self.assertEqual(result["status"], "OWNER_ERROR")
            self.assertTrue(oracle.validate_supervisor_record(result))
            deadline = result["supervisor_cleanup"]["unresolved"][0]
            self.assertEqual(deadline, {"kind": "deadline",
                "stage": "publication-finish",
                "monotonic_ns": published_finish,
                "deadline_ns": 300 + supervise.CLEANUP_NS})
            for mutation in (
                    lambda value: value["supervisor_cleanup"].__setitem__(
                        "complete", True),
                    lambda value: value["supervisor_cleanup"]["unresolved"][0].
                        __setitem__("monotonic_ns", published_finish + 1),
                    lambda value: value["supervisor_cleanup"]["unresolved"][0].
                        __setitem__("monotonic_ns", 300 + supervise.CLEANUP_NS - 1),
                    lambda value: value["supervisor_cleanup"]["unresolved"][0].
                        __setitem__("deadline_ns", 301 + supervise.CLEANUP_NS)):
                changed = copy.deepcopy(result); mutation(changed)
                with self.assertRaises(ValueError):
                    oracle.validate_supervisor_record(changed)
            duplicate = copy.deepcopy(result)
            duplicate["supervisor_cleanup"]["unresolved"].append(
                copy.deepcopy(deadline))
            with self.assertRaisesRegex(ValueError, "publication finish"):
                oracle.validate_supervisor_record(duplicate)
            for version in (True, 1.0):
                changed = copy.deepcopy(result); changed["schema_version"] = version
                with self.assertRaisesRegex(ValueError, "supervisor record"):
                    oracle.validate_supervisor_record(changed)

    def test_postfork_observation_exception_first_still_retires_and_publishes(self):
        self._postfork_observation_exception_case(0)

    def test_postfork_observation_exception_second_retains_first_and_publishes(self):
        self._postfork_observation_exception_case(1)

    def _postfork_observation_exception_case(self, failure_index):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve() / "attempt"
            args = mock.Mock(attempt_root=root)
            observation = {"observation": "observed", "pid": 77,
                "ppid": 20, "startticks": 30, "monotonic_ns": 150}
            direct = {"kind": "wait", "pid": 77, "startticks": 30,
                "raw_wait_status": 0, "direct": True, "monotonic_ns": 200}
            cleanup = {"complete": True, "events": [
                {"kind": "identity", "phase": "term-identity-1",
                 "observation": "observed", "pid": 77, "ppid": 20,
                 "startticks": 30, "matched": True, "monotonic_ns": 170},
                {"kind": "identity", "phase": "term-identity-2",
                 "observation": "observed", "pid": 77, "ppid": 20,
                 "startticks": 30, "matched": True, "monotonic_ns": 180},
                direct,
                {"kind": "owned-scan", "monotonic_ns": 210, "pids": []},
                {"kind": "owned-scan", "monotonic_ns": 220, "pids": []},
                {"kind": "echild", "monotonic_ns": 230,
                 "return": -1, "errno": 10}], "unresolved": []}
            observations = [observation, dict(observation)]
            observations[failure_index] = OSError("identity observation")
            def pump(*values, **kwargs):
                state = values[-1]
                state.update({"stdout": b"", "stderr": b"", "stdout_eof": True,
                              "stderr_eof": True, "raw_wait_status": 0,
                              "waited_ns": 200})
                return state
            with mock.patch.object(supervise, "validate_inputs"), \
                 mock.patch.object(supervise.time, "monotonic_ns",
                    side_effect=[100, 110, 160, 300, 310, 320]), \
                 mock.patch.object(supervise.os, "getpid", return_value=20), \
                 mock.patch.object(supervise, "establish_wait_authority"), \
                 mock.patch.object(supervise, "spawn_owner", return_value=(77, 3, 4, [])), \
                 mock.patch.object(supervise, "observe_identity", side_effect=observations) as observe, \
                 mock.patch.object(supervise, "pump_owner", side_effect=pump) as pump_mock, \
                 mock.patch.object(supervise, "cleanup_tree", return_value=(cleanup, direct)) as retire, \
                 mock.patch.object(supervise, "finish_pipes") as finish, \
                 mock.patch.object(supervise, "ensure_attempt_root", return_value=root), \
                 mock.patch.object(supervise, "publish_result") as publish:
                result, status = supervise.run_supervisor(args)
            self.assertEqual(status, 125)
            self.assertEqual(result["status"], "OWNER_ERROR")
            observe.assert_called()
            retire.assert_called_once()
            expected = [] if failure_index == 0 else [observation]
            self.assertEqual(result["owner_identity_observations"], expected)
            self.assertEqual(retire.call_args.args[1], expected)
            pump_mock.assert_not_called()
            finish.assert_called_once()
            publish.assert_called_once()
            self.assertTrue(oracle.validate_supervisor_record(result))

    def test_preflight_late_publication_gets_exact_finish_deadline(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = (Path(temporary) / "attempt").resolve()
            args = mock.Mock(attempt_root=root)
            failure = supervise.PreflightFailure("sentinel-fork",
                OSError(supervise.errno.EIO, "sentinel-fork"), None, None,
                sigchld_default=True)
            trigger = 200
            cleanup_deadline = trigger + supervise.CLEANUP_NS
            cleanup = {"complete": True, "events": [
                {"kind": "owned-scan", "monotonic_ns": 210, "pids": []},
                {"kind": "owned-scan", "monotonic_ns": 220, "pids": []},
                {"kind": "echild", "monotonic_ns": 230,
                 "return": -1, "errno": 10}], "unresolved": []}
            with mock.patch.object(supervise, "validate_inputs"), \
                 mock.patch.object(supervise.time, "monotonic_ns",
                    side_effect=[100, trigger, cleanup_deadline + 1]), \
                 mock.patch.object(supervise.os, "getpid", return_value=20), \
                 mock.patch.object(supervise, "establish_wait_authority",
                    side_effect=failure), \
                 mock.patch.object(supervise, "cleanup_tree",
                    return_value=(cleanup, None)), \
                 mock.patch.object(supervise, "ensure_attempt_root",
                    side_effect=lambda path: path.mkdir() or path), \
                 mock.patch.object(supervise, "publish_result"):
                result, status = supervise.run_supervisor(args)
            self.assertEqual(status, 125)
            self.assertFalse(result["supervisor_cleanup"]["complete"])
            self.assertEqual(result["supervisor_cleanup"]["unresolved"], [{
                "kind": "deadline", "stage": "publication-finish",
                "monotonic_ns": cleanup_deadline + 1,
                "deadline_ns": cleanup_deadline}])
            self.assertTrue(oracle.validate_supervisor_record(result))

    def test_incomplete_cleanup_late_publication_adds_finish_deadline(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            (root / "owner-result.json").write_text(
                '{"owner":{"pid":77,"startticks":30}}')
            (root / "witness.jsonl").write_bytes(b"witness\n")
            (root / "owner-errors.jsonl").write_bytes(b"")
            args = mock.Mock(attempt_root=root)
            observation = {"observation": "observed", "pid": 77,
                "ppid": 20, "startticks": 30, "monotonic_ns": 210}
            direct_wait = {"kind": "wait", "pid": 77, "startticks": 30,
                "raw_wait_status": 0, "direct": True, "monotonic_ns": 300}
            cleanup_deadline = 300 + supervise.CLEANUP_NS
            cleanup = {"complete": False, "events": [direct_wait],
                "unresolved": [{"kind": "deadline", "stage": "owned-scan",
                    "monotonic_ns": cleanup_deadline,
                    "deadline_ns": cleanup_deadline}]}
            def pump(_pid, _stdout_fd, _stderr_fd, _deadline_ns, state):
                state.update({"stdout_eof": True, "stderr_eof": True,
                    "raw_wait_status": 0, "waited_ns": 300})
            published_finish = cleanup_deadline + 1
            with mock.patch.object(supervise, "validate_inputs"), \
                 mock.patch.object(supervise.time, "monotonic_ns",
                    side_effect=[100, 200, published_finish]), \
                 mock.patch.object(supervise.os, "getpid", return_value=20), \
                 mock.patch.object(supervise, "establish_wait_authority"), \
                 mock.patch.object(supervise, "spawn_owner",
                    return_value=(77, 3, 4, [])), \
                 mock.patch.object(supervise, "observe_identity",
                    side_effect=[observation, dict(observation)]), \
                 mock.patch.object(supervise, "pump_owner", side_effect=pump), \
                 mock.patch.object(supervise, "cleanup_tree",
                    return_value=(cleanup, direct_wait)), \
                 mock.patch.object(supervise, "finish_pipes"), \
                 mock.patch.object(supervise, "ensure_attempt_root",
                    return_value=root), \
                 mock.patch.object(supervise, "publish_result"):
                result, status = supervise.run_supervisor(args)
            self.assertEqual(status, 125)
            self.assertEqual([value.get("stage") for value in
                result["supervisor_cleanup"]["unresolved"]],
                ["owned-scan", "publication-finish"])
            self.assertTrue(oracle.validate_supervisor_record(result))

    def test_counterexample_finished_after_cleanup_deadline_rejects_complete(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "case"; self.write_fixture(root, 0)
            self.rewrite_json(root / "supervisor-result.json", lambda value:
                value.update({"finished_ns": value["supervisor_cleanup_deadline_ns"] + 1}))
            self.refresh_supervisor(root)
            with self.assertRaisesRegex(ValueError, "deadline|supervisor"):
                oracle.validate(root, 0, 0)

    def test_owner_error_unreaped_requires_direct_wait_timeout(self):
        """A matched owner that is not reaped is bounded OWNER_ERROR evidence."""
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "case"
            self.write_fixture(root, 0)

            def edit(value):
                value.update({"status": "OWNER_ERROR", "owner_wait_observed": False,
                              "owner_exit_code": None, "owner_signal": None})
                value["supervisor_cleanup"]["complete"] = False
                value["supervisor_cleanup"]["events"] = [event for event in
                    value["supervisor_cleanup"]["events"]
                    if not (event.get("kind") == "wait" and event.get("direct"))]
                value["supervisor_cleanup"]["unresolved"] = []
            self.rewrite_json(root / "supervisor-result.json", edit)
            with self.assertRaisesRegex(ValueError, "supervisor cleanup unresolved|owner wait"):
                oracle.validate_supervisor_record(json.loads(
                    (root / "supervisor-result.json").read_text()))

            # The same record is valid once the mandatory timeout is retained.
            def add_direct_timeout(value):
                value["finished_ns"] = value["supervisor_cleanup_deadline_ns"]
                value["supervisor_cleanup"]["unresolved"].append({
                    "kind": "wait-timeout", "stage": "direct", "pid": 40,
                    "startticks": 30,
                    "monotonic_ns": value["supervisor_cleanup_deadline_ns"],
                    "deadline_ns": value["supervisor_cleanup_deadline_ns"]})
            self.rewrite_json(root / "supervisor-result.json",
                              add_direct_timeout)
            self.refresh_supervisor(root)
            value = json.loads((root / "supervisor-result.json").read_text())
            self.assertFalse(value["supervisor_cleanup"]["complete"])
            self.assertEqual(value["supervisor_cleanup"]["unresolved"][0]["kind"],
                             "wait-timeout")
            self.assertTrue(oracle.validate_supervisor_record(value))

            duplicate = copy.deepcopy(value)
            duplicate["supervisor_cleanup"]["unresolved"].append(copy.deepcopy(
                duplicate["supervisor_cleanup"]["unresolved"][0]))
            with self.assertRaisesRegex(ValueError,
                                        "direct wait timeout cardinality"):
                oracle.validate_supervisor_record(duplicate)

    def test_owner_exit_and_signal_raw_wait_results_join_exactly(self):
        for raw_status, exit_code, signal_number in ((7 << 8, 7, None),
                                                       (9, None, 9)):
            with self.subTest(raw_status=raw_status), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary) / "case"
                self.write_fixture(root, 0)
                self.rewrite_json(root / "supervisor-result.json", lambda value: value.update(
                    {"status": "OWNER_ERROR", "owner_wait_observed": True,
                     "owner_exit_code": exit_code, "owner_signal": signal_number,
                     "supervisor_cleanup": dict(value["supervisor_cleanup"])}))
                self.rewrite_json(root / "supervisor-result.json", lambda value:
                    value["supervisor_cleanup"]["events"][0].__setitem__(
                        "raw_wait_status", raw_status))
                self.refresh_supervisor(root)
                self.assertTrue(oracle.validate_supervisor_record(json.loads(
                    (root / "supervisor-result.json").read_text())))

                self.rewrite_json(root / "supervisor-result.json", lambda value:
                    value["supervisor_cleanup"]["events"][0].__setitem__(
                        "raw_wait_status", 0))
                self.refresh_supervisor(root)
                with self.assertRaisesRegex(ValueError, "owner wait"):
                    oracle.validate_supervisor_record(json.loads(
                        (root / "supervisor-result.json").read_text()))

    def test_direct_signal_error_nullable_and_positive_birth_joins(self):
        def signal_error(startticks, observations, identity_state="MATCHED"):
            value = {"kind": "signal-error", "stage": "term", "pid": 40,
                     "startticks": startticks, "signal": 15, "errno": 3,
                     "monotonic_ns": 7225, "direct": True}
            cleanup_events = [
                {"kind": "identity", "phase": "term-identity-1",
                 "observation": observations[0], "pid": 40,
                 "ppid": 20 if observations[0] == "observed" else None,
                 "startticks": startticks if observations[0] == "observed" else None,
                 "matched": observations[0] == "observed", "monotonic_ns": 7220},
                {"kind": "identity", "phase": "term-identity-2",
                 "observation": observations[1], "pid": 40,
                 "ppid": 20 if observations[1] == "observed" else None,
                 "startticks": startticks if observations[1] == "observed" else None,
                 "matched": observations[1] == "observed", "monotonic_ns": 7222}]
            return value, cleanup_events

        for startticks, observations in ((None, ("missing", "error")),
                                         (30, ("observed", "observed"))):
            with self.subTest(startticks=startticks), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary) / "case"
                self.write_fixture(root, 0)
                self.rewrite_json(root / "supervisor-result.json", lambda value: value.update(
                    {"status": "OWNER_ERROR", "owner_wait_observed": False,
                     "owner_exit_code": None, "owner_signal": None,
                     "supervisor_cleanup": dict(value["supervisor_cleanup"])}))
                error, identities = signal_error(startticks, observations)
                def edit(value):
                    if startticks is None:
                        value["owner_identity"].update({"state": "UNOBSERVED",
                            "ppid": None, "startticks": None})
                        value["owner_identity_observations"] = []
                    value["supervisor_cleanup"]["complete"] = False
                    value["finished_ns"] = \
                        value["supervisor_cleanup_deadline_ns"] + 1
                    value["supervisor_cleanup"]["events"] = identities + [
                        {"kind": "owned-scan", "monotonic_ns": 7230, "pids": []},
                        {"kind": "owned-scan", "monotonic_ns": 7240, "pids": []},
                        {"kind": "echild", "monotonic_ns": 7250,
                         "return": -1, "errno": 10}]
                    value["supervisor_cleanup"]["unresolved"] = [error, {
                        "kind": "wait-timeout", "stage": "direct", "pid": 40,
                        "startticks": startticks,
                        "monotonic_ns": value["finished_ns"],
                        "deadline_ns": value["supervisor_cleanup_deadline_ns"]}, {
                        "kind": "deadline", "stage": "publication-finish",
                        "monotonic_ns": value["finished_ns"],
                        "deadline_ns": value["supervisor_cleanup_deadline_ns"]}]
                self.rewrite_json(root / "supervisor-result.json", edit)
                self.refresh_supervisor(root)
                self.assertTrue(oracle.validate_supervisor_record(json.loads(
                    (root / "supervisor-result.json").read_text())))

    def test_negative_descriptor_bind_and_raw_wait_shape_controls(self):
        for field in ("old_fd", "new_fd"):
            packets = copy.deepcopy(self.packets(0))
            bind = next(packet for packet in packets if packet["kind"] == "BIND")
            bind[field] = -1
            with self.subTest(field=field), self.assertRaisesRegex(ValueError, "bind"):
                owner.validate_packet_schema(bind, 0)
        packets = copy.deepcopy(self.packets(0))
        bind = next(packet for packet in packets if packet["kind"] == "BIND")
        bind["acquisition_id"] = -1
        with self.assertRaisesRegex(ValueError, "bind"):
            owner.validate_packet_schema(bind, 0)

    def test_sentinel_signal_and_signal_error_require_birth_and_wait_join(self):
        identity = {"state": "NOT_SPAWNED", "pid": None, "ppid": None,
                    "startticks": None, "spawn_error": None}
        events = [{"kind": "identity", "phase": "term-identity-1",
                   "observation": "observed", "pid": 77, "ppid": 20,
                   "startticks": 30, "matched": True, "monotonic_ns": 7220},
                  {"kind": "identity", "phase": "term-identity-2",
                   "observation": "observed", "pid": 77, "ppid": 20,
                   "startticks": 30, "matched": True, "monotonic_ns": 7222}]
        tail = [{"kind": "wait", "pid": 77, "startticks": 30,
                 "raw_wait_status": 15, "direct": True, "monotonic_ns": 7230},
                {"kind": "owned-scan", "monotonic_ns": 7240, "pids": []},
                {"kind": "owned-scan", "monotonic_ns": 7250, "pids": []},
                {"kind": "echild", "monotonic_ns": 7260,
                 "return": -1, "errno": 10}]
        cleanup = {"complete": True, "events": events + [
            {"kind": "signal", "pid": 77, "startticks": 30, "signal": 15,
             "direct_child": True, "monotonic_ns": 7225}] + tail,
                   "unresolved": []}
        oracle.validate_supervisor_cleanup(cleanup, identity, 20, 8000, 7200,
                                           9000, 10000, 8000, "sentinel-wait")
        bad = copy.deepcopy(cleanup)
        bad["events"][2]["startticks"] = 31
        with self.assertRaisesRegex(ValueError, "sentinel authority"):
            oracle.validate_supervisor_cleanup(bad, identity, 20, 8000, 7200,
                                               9000, 10000, 8000, "sentinel-wait")
        error_cleanup = copy.deepcopy(cleanup)
        error_cleanup["complete"] = False
        error_cleanup["events"] = events + tail
        error_cleanup["unresolved"] = [{"kind": "signal-error", "stage": "term",
            "pid": 77, "startticks": 30, "signal": 15, "errno": 3,
            "monotonic_ns": 7225, "direct": True}]
        oracle.validate_supervisor_cleanup(error_cleanup, identity, 20, 8000, 7200,
                                           9000, 10000, 8000, "sentinel-wait")

        conflicting_parent = copy.deepcopy(cleanup)
        conflicting_parent["events"][1]["ppid"] = 21
        with self.assertRaisesRegex(ValueError, "sentinel authority"):
            oracle.validate_supervisor_cleanup(conflicting_parent, identity, 20,
                                               8000, 7200, 9000, 10000,
                                               8000, "sentinel-wait")

    def test_packet17_supervisor_pid_recomputes_exclusive_identity(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "case"
            self.write_fixture(root, 0)
            result = json.loads((root / "supervisor-result.json").read_text())
            result.update({"status": "OWNER_ERROR", "owner_wait_observed": True,
                           "owner_exit_code": 0, "owner_signal": None})
            result["owner_identity"].update({"state": "UNOBSERVED",
                "ppid": None, "startticks": None})
            result["owner_identity_observations"] = [
                {"observation": "observed", "pid": 40, "ppid": 20,
                 "startticks": 30, "monotonic_ns": 400},
                {"observation": "missing", "pid": 40, "ppid": None,
                 "startticks": None, "monotonic_ns": 500}]
            result["supervisor_cleanup"]["events"][0]["startticks"] = None
            self.assertTrue(oracle.validate_supervisor_record(result))

            ambiguous = copy.deepcopy(result)
            ambiguous["owner_identity"]["state"] = "MISMATCH"
            with self.assertRaisesRegex(ValueError, "classification"):
                oracle.validate_supervisor_record(ambiguous)
            third = copy.deepcopy(result)
            third["owner_identity_observations"].append(
                copy.deepcopy(third["owner_identity_observations"][-1]))
            with self.assertRaisesRegex(ValueError, "owner observations"):
                oracle.validate_supervisor_record(third)
            wrong_parent = copy.deepcopy(result)
            wrong_parent["owner_identity"]["state"] = "MISMATCH"
            wrong_parent["owner_identity_observations"][0]["ppid"] = 21
            self.assertTrue(oracle.validate_supervisor_record(wrong_parent))

    def test_packet17_later_owner_birth_does_not_promote_summary(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "case"
            self.write_fixture(root, 0)
            result = json.loads((root / "supervisor-result.json").read_text())
            result.update({"status": "OWNER_ERROR", "owner_wait_observed": True,
                           "owner_exit_code": None, "owner_signal": 15})
            result["owner_identity"].update({"state": "UNOBSERVED",
                "ppid": None, "startticks": None})
            result["owner_identity_observations"] = [
                {"observation": "missing", "pid": 40, "ppid": None,
                 "startticks": None, "monotonic_ns": 400},
                {"observation": "error", "pid": 40, "ppid": None,
                 "startticks": None, "monotonic_ns": 500}]
            result["supervisor_cleanup"] = {"complete": True, "unresolved": [],
                "events": [
                    {"kind": "identity", "phase": "term-identity-1",
                     "observation": "observed", "pid": 40, "ppid": 20,
                     "startticks": 30, "matched": True,
                     "monotonic_ns": 7210},
                    {"kind": "identity", "phase": "term-identity-2",
                     "observation": "observed", "pid": 40, "ppid": 20,
                     "startticks": 30, "matched": True,
                     "monotonic_ns": 7220},
                    {"kind": "signal", "pid": 40, "startticks": 30,
                     "signal": 15, "direct_child": True,
                     "monotonic_ns": 7230},
                    {"kind": "wait", "pid": 40, "startticks": 30,
                     "raw_wait_status": 15, "direct": True,
                     "monotonic_ns": 7240},
                    {"kind": "owned-scan", "monotonic_ns": 7250,
                     "pids": []},
                    {"kind": "owned-scan", "monotonic_ns": 7260,
                     "pids": []},
                    {"kind": "echild", "monotonic_ns": 7270,
                     "return": -1, "errno": 10}]}
            self.assertTrue(oracle.validate_supervisor_record(result))

    def test_packet17_cleanup_deadlines_are_actual_and_fixed(self):
        identity = {"state": "MATCHED", "pid": 40, "ppid": 20,
                    "startticks": 30, "spawn_error": None}
        stage_deadline = 1_000_000_100
        cleanup_deadline = 2_000_000_000
        finished = cleanup_deadline + 1
        cleanup = {"complete": False, "events": [
            {"kind": "identity", "phase": "term-identity-1",
             "observation": "observed", "pid": 40, "ppid": 20,
             "startticks": 30, "matched": True, "monotonic_ns": 80},
            {"kind": "identity", "phase": "term-identity-2",
             "observation": "observed", "pid": 40, "ppid": 20,
             "startticks": 30, "matched": True, "monotonic_ns": 90},
            {"kind": "signal", "pid": 40, "startticks": 30,
             "signal": 15, "direct_child": True, "monotonic_ns": 100}],
            "unresolved": [
                {"kind": "wait-timeout", "stage": "term", "pid": 40,
                 "startticks": 30, "monotonic_ns": stage_deadline,
                 "deadline_ns": stage_deadline},
                {"kind": "wait-timeout", "stage": "direct", "pid": 40,
                 "startticks": 30, "monotonic_ns": finished,
                 "deadline_ns": cleanup_deadline},
                {"kind": "deadline", "stage": "publication-finish",
                 "monotonic_ns": finished,
                 "deadline_ns": cleanup_deadline}]}
        oracle.validate_supervisor_cleanup(cleanup, identity, 20,
            220_000_000_000, 50, cleanup_deadline, 3_000_000_000, finished)
        for delta in (-1, 1):
            changed = copy.deepcopy(cleanup)
            changed["unresolved"][0]["deadline_ns"] += delta
            if delta > 0:
                changed["unresolved"][0]["monotonic_ns"] += delta
            with self.subTest(delta=delta), self.assertRaisesRegex(
                    ValueError, "stage deadline"):
                oracle.validate_supervisor_cleanup(changed, identity, 20,
                    220_000_000_000, 50, cleanup_deadline,
                    3_000_000_000, finished)
        future = copy.deepcopy(cleanup)
        future["unresolved"][1]["monotonic_ns"] = finished + 1
        with self.assertRaisesRegex(ValueError, "unresolved time"):
            oracle.validate_supervisor_cleanup(future, identity, 20,
                220_000_000_000, 50, cleanup_deadline,
                3_000_000_000, finished)

        kill_cleanup = copy.deepcopy(cleanup)
        kill_cleanup["events"][0]["phase"] = "kill-identity-1"
        kill_cleanup["events"][1]["phase"] = "kill-identity-2"
        kill_cleanup["events"][2].update({"signal": 9,
                                           "monotonic_ns": 200})
        kill_cleanup["unresolved"][0].update({"stage": "kill",
            "monotonic_ns": 5_000_000_200, "deadline_ns": 5_000_000_200})
        kill_cleanup["unresolved"][1].update({
            "monotonic_ns": 8_000_000_001, "deadline_ns": 8_000_000_000})
        kill_cleanup["unresolved"][2].update({
            "monotonic_ns": 8_000_000_001, "deadline_ns": 8_000_000_000})
        oracle.validate_supervisor_cleanup(kill_cleanup, identity, 20,
            220_000_000_000, 50, 8_000_000_000, 10_000_000_000,
            8_000_000_001)
        shortened_kill = copy.deepcopy(kill_cleanup)
        shortened_kill["unresolved"][0]["deadline_ns"] -= 1
        with self.assertRaisesRegex(ValueError, "stage deadline"):
            oracle.validate_supervisor_cleanup(shortened_kill, identity, 20,
                220_000_000_000, 50, 8_000_000_000, 10_000_000_000,
                8_000_000_001)

    def test_packet17_early_unreaped_owner_uses_cleanup_deadline(self):
        trigger = 7200
        cleanup_deadline = trigger + 22_000_000_000
        value = [trigger]
        def clock():
            value[0] += 2_000_000_000
            return value[0]
        def empty_scan(*args):
            return [], [{"kind": "owned-scan", "monotonic_ns": clock(),
                         "pids": []}], [], False
        session = {"events": [], "unresolved": [], "authority_lost": True,
                   "direct_wait": None, "direct_reaped": False}
        with mock.patch.object(supervise.time, "monotonic_ns", side_effect=clock), \
             mock.patch.object(supervise.time, "sleep"), \
             mock.patch.object(supervise, "scan_owned", side_effect=empty_scan), \
             mock.patch.object(supervise.os, "waitpid", side_effect=[
                 (0, 0), (0, 0), ChildProcessError()]):
            cleanup, waited = supervise.cleanup_tree(77, [], None, 20,
                trigger, cleanup_deadline,
                initial_wait_deadline_ns=220_000_000_300,
                authority_lost=True, session=session)
        self.assertIsNone(waited)
        direct_timeout = next(item for item in cleanup["unresolved"]
                              if item["kind"] == "wait-timeout")
        self.assertEqual(direct_timeout["deadline_ns"], cleanup_deadline)
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            identity = {"state": "UNOBSERVED", "pid": 77, "ppid": None,
                        "startticks": None, "spawn_error": None}
            observations = [
                {"observation": "missing", "pid": 77, "ppid": None,
                 "startticks": None, "monotonic_ns": 400},
                {"observation": "error", "pid": 77, "ppid": None,
                 "startticks": None, "monotonic_ns": 500}]
            result = supervise.supervisor_result(root, 20, 300,
                session["finished_ns"], identity, observations, None, b"", b"",
                supervise.finalize_cleanup_publication(cleanup,
                    session["finished_ns"], cleanup_deadline),
                100, 5_000_000_100, 220_000_000_300, trigger,
                cleanup_deadline, 248_000_000_300, True, True, None, False)
            self.assertTrue(oracle.validate_supervisor_record(result))

    def test_packet17_all_postfork_observation_controls(self):
        for selector in (0, 3, 4, 5):
            mutations = (
                lambda rows: next(row for row in rows if row["packet"]["kind"] ==
                    "REAP")["packet"].__setitem__("raw_wait_status", 256),
                lambda rows: [row for row in rows if row["packet"]["kind"] ==
                    "EOF"][1]["packet"].__setitem__("closed_fd", [row for row in
                    rows if row["packet"]["kind"] == "EOF"][0]["packet"]["closed_fd"]),
                lambda rows: next(row for row in rows if row["packet"]["kind"] ==
                    "CLEANUP_FINAL")["packet"].__setitem__("cleanup_deadline_ns",
                    15_000_003_501),
            )
            for index, mutation in enumerate(mutations):
                with self.subTest(selector=selector, mutation=index), \
                     tempfile.TemporaryDirectory() as temporary:
                    root = Path(temporary) / "case"
                    self.write_fixture(root, selector)
                    self.rewrite_journal(root / "witness.jsonl", mutation)
                    self.refresh_supervisor(root)
                    with self.assertRaises(ValueError):
                        oracle.validate(root, selector, 0)

    def test_packet17_oracle_rejects_negative_and_boolean_descriptors(self):
        edits = (
            lambda packet: packet.__setitem__("new_fd", -1),
            lambda packet: packet.__setitem__("old_fd", False),
        )
        for index, edit in enumerate(edits):
            with self.subTest(index=index), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary) / "case"
                self.write_fixture(root, 0)
                self.rewrite_journal(root / "witness.jsonl", lambda rows:
                    edit(next(row["packet"] for row in rows if
                              row["packet"]["kind"] == "BIND")))
                self.refresh_supervisor(root)
                with self.assertRaisesRegex(ValueError, "descriptor"):
                    oracle.validate(root, 0, 0)

    def test_packet17_wait_decoder_rejects_nonterminal_and_out_of_range(self):
        for raw in (True, -1, 1 << 16, 0x7f, 0xffff):
            with self.subTest(raw=raw):
                with self.assertRaisesRegex(ValueError, "wait status"):
                    oracle.wait_fields(raw)
                with self.assertRaisesRegex(ValueError, "wait status"):
                    supervise.wait_fields(raw)

if __name__ == "__main__":
    unittest.main()
