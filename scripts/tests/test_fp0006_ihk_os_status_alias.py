#!/usr/bin/env python3
"""Isolated-CLI tests for the bounded FP-0006 OS-status alias witness."""

from __future__ import print_function

import ast
import contextlib
import errno
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import re
import runpy
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest import mock


ROOT = Path(__file__).resolve().parents[2]
CHECKER = ROOT / "scripts/fp0006_ihk_os_status_alias.py"
CONTRACT_PATH = ROOT / "host-kernel/contracts/fp0006-ihk-os-status-alias-v1.json"
C_PRODUCER = ROOT / "scripts/smoke/fp0006-ihk-os-status-alias.c"
RUST_PRODUCER = ROOT / "scripts/tests/fixtures/ihk_ioctl_fp0006_status_alias.rs"
SECURITY_SOURCE = ROOT / "scripts/fp0006_ihk_device_negative_dispatch.py"
EXPECTED_CHECKER_SHA256 = "fdf00899d69052837ab7b2a93d9c8cdab05bbe47b28415d6a6fc59db679696b7"
EXPECTED_CHECKER_SIZE = 87029
EXPECTED_NORMALIZED_SELF_SHA256 = "5930b0e715c6d791b854763226dd1642f833cb1a67f45996d57bbb096888e630"
REAL_POPEN = subprocess.Popen

from scripts import fp0006_ihk_os_status_alias as imported_witness


def canonical(value):
    return (json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n").encode(
        "utf-8"
    )


def expected_claims():
    return {
        "credit_eligible": False,
        "current_head_provenance_proven": False,
        "current_head_runtime_reachability_proven": False,
        "durable_evidence": False,
        "failure_semantics_covered": False,
        "fp0006_complete": False,
        "gate_pass": False,
        "independent_review_complete": False,
        "legacy_runtime_executed": False,
        "native_module_runtime_executed": False,
        "native_runtime_executed": False,
        "runtime_reachability_proven": False,
        "tracker_credit": False,
    }


def expected_vectors():
    return [
        (0, "query-status-arg0", 1124867, 0),
        (1, "query-status-arg-u64-max", 1124867, 18446744073709551615),
        (2, "status-alias-arg0", 1124884, 0),
        (3, "status-alias-arg-u64-max", 1124884, 18446744073709551615),
    ]


def capture_bytes(surface):
    raw = []
    results = []
    ledger = []
    for sequence, vector_id, request, argument in expected_vectors():
        raw.append(
            {
                "argument": argument,
                "request": request,
                "sequence": sequence,
                "vector_id": vector_id,
            }
        )
        results.append(
            {
                "errno": 0,
                "interface_return": 5,
                "normalized_return": 5,
                "sequence": sequence,
                "surface": surface,
                "vector_id": vector_id,
            }
        )
        for phase in ("before", "after"):
            ledger.append(
                {
                    "minor": 0,
                    "phase": phase,
                    "sequence": sequence,
                    "status": 5,
                    "status_name": "RUNNING",
                    "surface": surface,
                    "vector_id": vector_id,
                }
            )
    return {
        "raw.jsonl": b"".join(canonical(row) for row in raw),
        "result.jsonl": b"".join(canonical(row) for row in results),
        "state-ledger.jsonl": b"".join(canonical(row) for row in ledger),
    }


def write_capture(path, surface):
    path.mkdir()
    for name, data in capture_bytes(surface).items():
        member = path / name
        member.write_bytes(data)
        member.chmod(0o444)


def copy_authority_repo(destination):
    contract = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
    relative_paths = [
        "host-kernel/contracts/fp0006-ihk-os-status-alias-v1.json"
    ]
    relative_paths.extend(
        binding["path"] for binding in contract["frozen_inputs"].values()
    )
    relative_paths.extend(
        binding["path"] for binding in contract["producers"].values()
    )
    for relative in relative_paths:
        source = ROOT / relative
        target = destination / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(str(source), str(target))


def run_command(command, cwd=ROOT, environment=None, timeout=30):
    env = dict(os.environ)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    if environment:
        env.update(environment)
    process = REAL_POPEN(
        [str(item) for item in command],
        cwd=str(cwd),
        env=env,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    stdout, stderr = process.communicate(timeout=timeout)
    return process.returncode, stdout, stderr, process.pid


def run_cli(arguments, checker=CHECKER, isolated=True, timeout=30):
    command = [sys.executable]
    if isolated:
        command.append("-I")
    command.append(str(checker))
    command.extend(arguments)
    return run_command(command, timeout=timeout)


def require_success(testcase, execution):
    returncode, stdout, stderr, _ = execution
    testcase.assertEqual(0, returncode, stderr.decode("utf-8", "replace"))
    testcase.assertEqual(b"", stderr)
    result = json.loads(stdout.decode("utf-8"))
    testcase.assertEqual(canonical(result), stdout)
    testcase.assertEqual(expected_claims(), result["claims"])
    testcase.assertEqual("required-missing", result["result_authority"])
    return result


class StatusAliasIsolatedCliTests(unittest.TestCase):
    def test_exec_seal_post_close_error_fd_reuse_preserves_replacement(self):
        imported_witness._load_exact_security_primitives(str(CHECKER))
        original_close = os.close
        original_open = os.open

        for replacement_kind in ("different-inode", "same-inode"):
            with self.subTest(replacement_kind=replacement_kind):
                with tempfile.TemporaryDirectory() as directory:
                    root = Path(directory)
                    owned_path = root / "owned"
                    other_path = root / "other"
                    owned_path.write_bytes(b"owned")
                    other_path.write_bytes(b"other")
                    descriptor = original_open(str(owned_path), os.O_RDONLY)
                    expected_identity = imported_witness._file_identity(
                        os.fstat(descriptor)
                    )
                    replacement = [None]

                    def close_reuse_and_fail(candidate):
                        self.assertEqual(descriptor, candidate)
                        original_close(candidate)
                        reopened_path = (
                            owned_path
                            if replacement_kind == "same-inode"
                            else other_path
                        )
                        reopened = original_open(str(reopened_path), os.O_RDONLY)
                        if reopened != candidate:
                            os.dup2(reopened, candidate)
                            original_close(reopened)
                            reopened = candidate
                        replacement[0] = reopened
                        raise OSError(errno.EINTR, "synthetic post-close failure")

                    with mock.patch.object(
                        imported_witness.os, "close", side_effect=close_reuse_and_fail
                    ):
                        retired, error = imported_witness._cleanup_owned_fd(
                            descriptor,
                            expected_identity,
                            "synthetic exec-seal descriptor",
                        )

                    self.assertTrue(retired)
                    self.assertIsInstance(error, OSError)
                    self.assertEqual(descriptor, replacement[0])
                    os.lseek(descriptor, 0, os.SEEK_SET)
                    expected = (
                        b"owned" if replacement_kind == "same-inode" else b"other"
                    )
                    self.assertEqual(expected, os.read(descriptor, len(expected)))
                    original_close(descriptor)

    def test_frozen_identities_and_normalized_self_seal(self):
        expected = {
            CONTRACT_PATH: (
                "1a75d2f4169e788075a9a0e0f10bcb5a9547b65be8db3abd8ddb8c1770dfb75a",
                10968,
            ),
            C_PRODUCER: (
                "ba92ad889ca521ec5bef6fdbf44fb95c5a165663505ad4380180f56e6b780023",
                7374,
            ),
            RUST_PRODUCER: (
                "4ec5ab91da89eff9ea3d506a0429a5c15a1eb11c0b53a45232b9b0b5738f0769",
                6800,
            ),
            SECURITY_SOURCE: (
                "9d72d215f2fc618ac05c2f729a57ad865391c105de2e70995b8eb251d81855a7",
                51559,
            ),
            CHECKER: (EXPECTED_CHECKER_SHA256, EXPECTED_CHECKER_SIZE),
        }
        for path, identity in expected.items():
            with self.subTest(path=str(path)):
                data = path.read_bytes()
                self.assertEqual(identity[1], len(data))
                self.assertEqual(identity[0], hashlib.sha256(data).hexdigest())
        checker = CHECKER.read_bytes()
        pattern = br"SELF_" + br"DIGEST:[0-9a-f]{64}"
        markers = re.findall(pattern, checker)
        normalized, count = re.subn(
            pattern, b"SELF_" + b"DIGEST:" + b"0" * 64, checker
        )
        self.assertEqual(1, count)
        self.assertEqual(1, len(markers))
        marker_digest = markers[0].split(b":", 1)[1].decode("ascii")
        self.assertEqual(EXPECTED_NORMALIZED_SELF_SHA256, marker_digest)
        self.assertEqual(
            EXPECTED_NORMALIZED_SELF_SHA256,
            hashlib.sha256(normalized).hexdigest(),
        )

    def test_cli_only_boundary_and_prior_public_attacks_are_unavailable(self):
        for name in (
            "validate_contract",
            "review_surface",
            "review_pair",
            "build_census",
            "main",
            "_cli_entry",
            "_load_authority",
            "_review_pair_internal",
            "_review_surface_internal",
            "_review_surface_with_authority",
            "_validate_contract_internal",
        ):
            self.assertFalse(hasattr(imported_witness, name), name)
        with self.assertRaises(AttributeError):
            imported_witness.build_census.__closure__
        with self.assertRaises(AttributeError):
            type(imported_witness.build_census).__call__.__code__
        original_name = imported_witness.__name__
        try:
            imported_witness.__name__ = "__main__"
            self.assertFalse(hasattr(imported_witness, "main"))
            self.assertFalse(hasattr(imported_witness, "_cli_entry"))
        finally:
            imported_witness.__name__ = original_name
        returncode, stdout, error, _ = run_cli(
            ["check-contract", "--repo", str(ROOT)], isolated=False
        )
        self.assertEqual(1, returncode)
        self.assertEqual(b"", stdout)
        self.assertIn(b"requires python3 -I", error)

    def test_exact_imported_name_validator_envelope_promotion_attack_is_unavailable(self):
        original_name = imported_witness.__name__
        original_claims = imported_witness._expected_claims
        original_canonical = imported_witness._canonical_json
        promoted = {
            "claims": {"gate_pass": True, "credit_eligible": True},
            "status": "PASS",
        }
        try:
            imported_witness.__name__ = "__main__"
            imported_witness._expected_claims = lambda: promoted["claims"]
            imported_witness._canonical_json = lambda value: canonical(promoted)
            for entry in (
                "main",
                "_cli_entry",
                "_require_cli_noncrediting_result",
                "_review_surface_internal",
                "_validate_contract_internal",
            ):
                with self.subTest(entry=entry):
                    with self.assertRaises(AttributeError):
                        getattr(imported_witness, entry)
        finally:
            imported_witness.__name__ = original_name
            imported_witness._expected_claims = original_claims
            imported_witness._canonical_json = original_canonical

    def test_runpy_and_spec_loader_entry_attempts_fail_closed(self):
        for loader in ("runpy", "spec"):
            with self.subTest(loader=loader):
                stderr = io.StringIO()
                with contextlib.redirect_stderr(stderr):
                    with self.assertRaises(SystemExit) as stopped:
                        if loader == "runpy":
                            runpy.run_path(str(CHECKER), run_name="__main__")
                        else:
                            spec = importlib.util.spec_from_file_location(
                                "__main__", str(CHECKER)
                            )
                            module = importlib.util.module_from_spec(spec)
                            spec.loader.exec_module(module)
                self.assertEqual(1, stopped.exception.code)
                self.assertIn("requires python3 -I", stderr.getvalue())

        program = (
            "import runpy; "
            "runpy.run_path({0!r}, run_name='__main__')".format(str(CHECKER))
        )
        returncode, stdout, error, _ = run_command(
            [sys.executable, "-I", "-c", program]
        )
        self.assertEqual(1, returncode)
        self.assertEqual(b"", stdout)
        self.assertIn(b"isolated process command does not name the direct CLI", error)

    def test_check_contract_is_canonical_exact_and_noncrediting(self):
        result = require_success(
            self,
            run_cli(["check-contract", "--repo", str(ROOT)]),
        )
        self.assertEqual("fp-0006-ihk-os-status-alias-v1", result["contract_id"])
        self.assertEqual(
            "1a75d2f4169e788075a9a0e0f10bcb5a9547b65be8db3abd8ddb8c1770dfb75a",
            result["contract_sha256"],
        )
        self.assertEqual("CONTRACT_VALIDATED_NONCREDITING", result["status"])
        self.assertEqual(4, result["vector_count"])

    def test_valid_legacy_native_and_pair_cli_routes(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            legacy = root / "legacy"
            native = root / "native"
            write_capture(legacy, "legacy-live-ioctl")
            write_capture(native, "native-rust-source-fixture")
            legacy_result = require_success(
                self,
                run_cli(
                    [
                        "review-surface", "--repo", str(ROOT), "--surface",
                        "legacy", "--artifact", str(legacy),
                    ]
                ),
            )
            native_result = require_success(
                self,
                run_cli(
                    [
                        "review-surface", "--repo", str(ROOT), "--surface",
                        "native", "--artifact", str(native),
                    ]
                ),
            )
            pair = require_success(
                self,
                run_cli(
                    [
                        "review-pair", "--repo", str(ROOT), "--legacy",
                        str(legacy), "--native", str(native),
                    ]
                ),
            )
            self.assertEqual("legacy-live-ioctl", legacy_result["surface"])
            self.assertEqual("native-rust-source-fixture", native_result["surface"])
            self.assertTrue(pair["artifact_pair_validated"])
            self.assertEqual(expected_claims(), pair["legacy"]["claims"])
            self.assertEqual(expected_claims(), pair["native"]["claims"])

    def test_exact_fake_parent_popen_attack_cannot_cross_cli_boundary(self):
        with tempfile.TemporaryDirectory() as directory:
            capture = Path(directory) / "capture"
            write_capture(capture, "legacy-live-ioctl")
            raw = capture / "raw.jsonl"
            original = raw.read_bytes()
            forged = b"W" * len(original)

            class ForgedSuccessfulProcess(object):
                def __init__(self, *args, **kwargs):
                    raw.write_bytes(forged)

                def kill(self):
                    pass

                def wait(self, timeout=None):
                    return 0

            fake = mock.Mock(side_effect=ForgedSuccessfulProcess)
            with mock.patch.object(imported_witness.subprocess, "Popen", fake):
                result = require_success(
                    self,
                    run_cli(
                        [
                            "review-surface", "--repo", str(ROOT), "--surface",
                            "legacy", "--artifact", str(capture),
                        ]
                    ),
                )
            self.assertEqual(0, fake.call_count)
            self.assertEqual(original, raw.read_bytes())
            self.assertTrue(result["capture_schema_validated"])

    def test_importing_globals_code_defaults_and_classes_are_non_authoritative(self):
        with tempfile.TemporaryDirectory() as directory:
            capture = Path(directory) / "capture"
            write_capture(capture, "legacy-live-ioctl")
            target = imported_witness._exact_json_equal
            original_code = target.__code__
            original_defaults = target.__defaults__
            original_kwdefaults = target.__kwdefaults__

            def promoted(*args, **kwargs):
                return {
                    "claims": {"gate_pass": True, "credit_eligible": True},
                    "status": "PASS",
                }

            try:
                target.__code__ = promoted.__code__
                target.__defaults__ = ()
                target.__kwdefaults__ = {}
                with mock.patch.object(
                    imported_witness, "DEFAULT_CONTRACT", Path("attacker.json")
                ), mock.patch.object(
                    imported_witness, "CONTRACT_ID", "attacker-contract"
                ), mock.patch.object(
                    imported_witness, "LEGACY_SURFACE", "forged-legacy"
                ), mock.patch.object(
                    imported_witness, "NATIVE_SURFACE", "forged-native"
                ), mock.patch.object(
                    imported_witness, "_expected_claims", return_value={"gate_pass": True}
                ), mock.patch.object(
                    imported_witness, "_canonical_json", return_value=b'{"gate_pass":true}\n'
                ), mock.patch.object(
                    imported_witness, "WitnessError", RuntimeError
                ):
                    result = require_success(
                        self,
                        run_cli(
                            [
                                "review-surface", "--repo", str(ROOT), "--surface",
                                "legacy", "--artifact", str(capture),
                            ]
                        ),
                    )
            finally:
                target.__code__ = original_code
                target.__defaults__ = original_defaults
                target.__kwdefaults__ = original_kwdefaults
            self.assertEqual(expected_claims(), result["claims"])
            self.assertEqual("CAPTURED_UNREVIEWED_NONCREDITING", result["status"])

    def test_checker_tamper_symlink_and_hardlink_fail_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            changed = root / "changed.py"
            changed.write_bytes(CHECKER.read_bytes() + b"\n")
            returncode, stdout, error, _ = run_cli(
                ["check-contract", "--repo", str(ROOT)], checker=changed
            )
            self.assertEqual(1, returncode)
            self.assertEqual(b"", stdout)
            self.assertIn(b"source identity differs", error)

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            alias = root / "alias.py"
            alias.symlink_to(CHECKER)
            returncode, stdout, error, _ = run_cli(
                ["check-contract", "--repo", str(ROOT)], checker=alias
            )
            self.assertEqual(1, returncode)
            self.assertEqual(b"", stdout)
            self.assertIn(b"status-alias witness error", error)

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            first = root / "first.py"
            linked = root / "linked.py"
            first.write_bytes(CHECKER.read_bytes())
            os.link(str(first), str(linked))
            returncode, stdout, error, _ = run_cli(
                ["check-contract", "--repo", str(ROOT)], checker=linked
            )
            self.assertEqual(1, returncode)
            self.assertEqual(b"", stdout)
            self.assertIn(b"regular unlinked authority", error)

    def test_contract_and_frozen_input_mutations_fail(self):
        mutations = ("claim", "duplicate", "dispatcher", "security")
        for mutation in mutations:
            with self.subTest(mutation=mutation):
                with tempfile.TemporaryDirectory() as directory:
                    repo = Path(directory) / "repo"
                    repo.mkdir()
                    copy_authority_repo(repo)
                    contract_path = repo / imported_witness.DEFAULT_CONTRACT
                    if mutation == "claim":
                        contract = json.loads(contract_path.read_text(encoding="utf-8"))
                        contract["claims"]["gate_pass"] = True
                        contract_path.write_text(
                            json.dumps(contract, indent=2, sort_keys=True) + "\n",
                            encoding="utf-8",
                        )
                    elif mutation == "duplicate":
                        data = contract_path.read_bytes()
                        contract_path.write_bytes(
                            data.replace(
                                b'"schema_version": 1',
                                b'"schema_version": 1, "schema_version": 1',
                                1,
                            )
                        )
                    elif mutation == "dispatcher":
                        target = repo / "host-kernel/native-rust/ihk_ioctl.rs"
                        target.write_bytes(target.read_bytes() + b"\n")
                    else:
                        target = repo / "scripts/fp0006_ihk_device_negative_dispatch.py"
                        target.write_bytes(target.read_bytes() + b"\n")
                    returncode, stdout, error, _ = run_cli(
                        ["check-contract", "--repo", str(repo)]
                    )
                    self.assertEqual(1, returncode)
                    self.assertEqual(b"", stdout)
                    self.assertIn(b"status-alias witness error", error)

    def test_capture_content_path_and_namespace_mutations_fail(self):
        mutations = (
            "wrong-request", "bool-result", "duplicate-key", "nonfinite",
            "ledger-state", "missing", "extra", "mode", "member-symlink",
            "member-hardlink",
        )
        for mutation in mutations:
            with self.subTest(mutation=mutation):
                with tempfile.TemporaryDirectory() as directory:
                    root = Path(directory)
                    capture = root / "capture"
                    write_capture(capture, "legacy-live-ioctl")
                    raw = capture / "raw.jsonl"
                    result = capture / "result.jsonl"
                    ledger = capture / "state-ledger.jsonl"
                    if mutation == "wrong-request":
                        rows = raw.read_bytes().splitlines(True)
                        row = json.loads(rows[0])
                        row["request"] = 1124884
                        raw.chmod(0o644)
                        raw.write_bytes(canonical(row) + b"".join(rows[1:]))
                        raw.chmod(0o444)
                    elif mutation == "bool-result":
                        rows = result.read_bytes().splitlines(True)
                        row = json.loads(rows[0])
                        row["interface_return"] = True
                        result.chmod(0o644)
                        result.write_bytes(canonical(row) + b"".join(rows[1:]))
                        result.chmod(0o444)
                    elif mutation == "duplicate-key":
                        rows = raw.read_bytes().splitlines(True)
                        rows[0] = rows[0].replace(
                            b'"argument":0', b'"argument":0,"argument":0', 1
                        )
                        raw.chmod(0o644)
                        raw.write_bytes(b"".join(rows))
                        raw.chmod(0o444)
                    elif mutation == "nonfinite":
                        rows = raw.read_bytes().splitlines(True)
                        rows[0] = rows[0].replace(
                            b'"argument":0', b'"argument":NaN', 1
                        )
                        raw.chmod(0o644)
                        raw.write_bytes(b"".join(rows))
                        raw.chmod(0o444)
                    elif mutation == "ledger-state":
                        rows = ledger.read_bytes().splitlines(True)
                        row = json.loads(rows[1])
                        row["status"] = 4
                        ledger.chmod(0o644)
                        ledger.write_bytes(rows[0] + canonical(row) + b"".join(rows[2:]))
                        ledger.chmod(0o444)
                    elif mutation == "missing":
                        raw.unlink()
                    elif mutation == "extra":
                        extra = capture / "extra"
                        extra.write_bytes(b"x")
                        extra.chmod(0o444)
                    elif mutation == "mode":
                        raw.chmod(0o644)
                    elif mutation == "member-symlink":
                        target = root / "raw-target"
                        raw.rename(target)
                        raw.symlink_to(target)
                    else:
                        os.link(str(raw), str(root / "raw-hardlink"))
                    returncode, stdout, error, _ = run_cli(
                        [
                            "review-surface", "--repo", str(ROOT), "--surface",
                            "legacy", "--artifact", str(capture),
                        ]
                    )
                    self.assertEqual(1, returncode)
                    self.assertEqual(b"", stdout)
                    self.assertIn(b"status-alias witness error", error)

    def test_capture_root_symlink_and_pair_surface_substitution_fail(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            capture = root / "capture"
            write_capture(capture, "legacy-live-ioctl")
            alias = root / "alias"
            alias.symlink_to(capture, target_is_directory=True)
            returncode, stdout, error, _ = run_cli(
                [
                    "review-surface", "--repo", str(ROOT), "--surface", "legacy",
                    "--artifact", str(alias),
                ]
            )
            self.assertEqual(1, returncode)
            self.assertEqual(b"", stdout)
            self.assertIn(b"status-alias witness error", error)

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            legacy = root / "legacy"
            native = root / "native"
            write_capture(legacy, "legacy-live-ioctl")
            write_capture(native, "legacy-live-ioctl")
            returncode, stdout, error, _ = run_cli(
                [
                    "review-pair", "--repo", str(ROOT), "--legacy", str(legacy),
                    "--native", str(native),
                ]
            )
            self.assertEqual(1, returncode)
            self.assertEqual(b"", stdout)
            self.assertIn(b"status-alias witness error", error)

    def test_repeated_cli_success_reaps_children_and_preserves_parent_fds(self):
        with tempfile.TemporaryDirectory() as directory:
            capture = Path(directory) / "capture"
            write_capture(capture, "legacy-live-ioctl")
            before = set(os.listdir("/proc/self/fd"))
            pids = []
            for _ in range(3):
                execution = run_cli(
                    [
                        "review-surface", "--repo", str(ROOT), "--surface",
                        "legacy", "--artifact", str(capture),
                    ]
                )
                require_success(self, execution)
                pids.append(execution[3])
            after = set(os.listdir("/proc/self/fd"))
            self.assertEqual(before, after)
            for pid in pids:
                self.assertFalse(Path("/proc/{0}".format(pid)).exists())

    def test_invalid_surface_and_unknown_command_fail_without_output(self):
        with tempfile.TemporaryDirectory() as directory:
            capture = Path(directory) / "capture"
            write_capture(capture, "legacy-live-ioctl")
            for arguments in (
                ["unknown-command"],
                [
                    "review-surface", "--repo", str(ROOT), "--surface", "Legacy",
                    "--artifact", str(capture),
                ],
            ):
                with self.subTest(arguments=arguments):
                    returncode, stdout, error, _ = run_cli(arguments)
                    self.assertEqual(2, returncode)
                    self.assertEqual(b"", stdout)
                    self.assertIn(b"usage:", error)

    def test_python_36_grammar(self):
        for path in (CHECKER, Path(__file__)):
            source = path.read_text(encoding="utf-8")
            with self.subTest(path=str(path)):
                ast.parse(source, filename=str(path), feature_version=(3, 6))

    def test_c_producer_compiles_with_werror_when_available(self):
        compiler = shutil.which("cc") or shutil.which("gcc")
        if compiler is None:
            self.skipTest("C compiler is unavailable")
        with tempfile.TemporaryDirectory() as directory:
            binary = Path(directory) / "status-alias-capture"
            returncode, stdout, stderr, _ = run_command(
                [
                    compiler, "-std=c11", "-Wall", "-Wextra", "-Werror",
                    str(C_PRODUCER), "-o", str(binary),
                ]
            )
            self.assertEqual(0, returncode, stderr.decode("utf-8", "replace"))
            self.assertEqual(b"", stdout)
            self.assertEqual(b"", stderr)
            returncode, stdout, stderr, _ = run_command([str(binary), "--describe"])
            self.assertEqual(0, returncode, stderr.decode("utf-8", "replace"))
            description = json.loads(stdout.decode("utf-8"))
            self.assertFalse(description["gate_pass"])
            self.assertFalse(description["legacy_runtime_executed"])
            self.assertFalse(description["tracker_credit"])

    def test_native_fixture_compiles_runs_and_reviews_when_available(self):
        compiler = shutil.which("rustc")
        if compiler is None:
            self.skipTest("rustc is unavailable")
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            binary = root / "status-alias-fixture"
            returncode, stdout, stderr, _ = run_command(
                [
                    compiler, "--edition=2021", "-Dwarnings", str(RUST_PRODUCER),
                    "-o", str(binary),
                ]
            )
            self.assertEqual(0, returncode, stderr.decode("utf-8", "replace"))
            self.assertEqual(b"", stdout)
            description_execution = run_command([str(binary), "--describe"])
            self.assertEqual(0, description_execution[0])
            description = json.loads(description_execution[1].decode("utf-8"))
            self.assertFalse(description["native_module_runtime_executed"])
            self.assertFalse(description["gate_pass"])
            capture = root / "capture"
            capture.mkdir()
            execution = run_command([str(binary), str(capture)])
            self.assertEqual(0, execution[0], execution[2].decode("utf-8", "replace"))
            reviewed = require_success(
                self,
                run_cli(
                    [
                        "review-surface", "--repo", str(ROOT), "--surface", "native",
                        "--artifact", str(capture),
                    ]
                ),
            )
            self.assertEqual(4, reviewed["validated_result_count"])
            self.assertEqual(8, reviewed["validated_state_record_count"])


if __name__ == "__main__":
    unittest.main()
