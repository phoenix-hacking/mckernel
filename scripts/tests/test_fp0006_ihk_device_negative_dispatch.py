#!/usr/bin/env python3

from __future__ import print_function

import ast
import contextlib
import copy
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest import mock


REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts import fp0006_ihk_device_negative_dispatch as witness


class Fp0006IhkDeviceNegativeDispatchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temporary = tempfile.TemporaryDirectory(
            prefix="fp0006-negative-dispatch-"
        )
        cls.roots = {}
        try:
            for name in unittest.defaultTestLoader.getTestCaseNames(cls):
                root = Path(cls.temporary.name) / name
                root.mkdir(mode=0o700)
                cls.roots[name] = root
        except Exception:
            cls.temporary.cleanup()
            raise

    @classmethod
    def tearDownClass(cls):
        cls.temporary.cleanup()

    def setUp(self):
        self.root = self.__class__.roots[self._testMethodName]
        self.authority = json.loads(
            (REPO_ROOT / witness.DEFAULT_CONTRACT).read_text(encoding="utf-8")
        )
        self.legacy_surface = self.authority["artifact_contract"]["legacy_surface"]
        self.native_surface = self.authority["artifact_contract"]["native_surface"]

    def copy_contract_repository(self, name="repo"):
        repo = self.root / name
        if repo.exists():
            shutil.rmtree(str(repo))
        paths = {witness.DEFAULT_CONTRACT.as_posix()}
        paths.update(item["path"] for item in self.authority["frozen_inputs"].values())
        paths.update(item["path"] for item in self.authority["producers"].values())
        paths.add(self.authority["current_head_boundary"]["current_host_driver"]["path"])
        for relative in sorted(paths):
            destination = repo / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(str(REPO_ROOT / relative), str(destination))
        return repo

    def load_contract(self, repo):
        return json.loads((repo / witness.DEFAULT_CONTRACT).read_text(encoding="utf-8"))

    def write_contract(self, repo, contract, canonical=True):
        path = repo / witness.DEFAULT_CONTRACT
        if canonical:
            text = json.dumps(contract, indent=2, sort_keys=True) + "\n"
        else:
            text = json.dumps(contract) + "\n"
        path.write_text(text, encoding="utf-8")

    def raw_expectations(self):
        return [
            {
                "argument": vector["argument"],
                "request": vector["request"],
                "sequence": vector["sequence"],
                "vector_id": vector["vector_id"],
            }
            for vector in self.authority["vectors"]
        ]

    def capture_records(self, surface, bitmap="0000000000000000"):
        raw = self.raw_expectations()
        encoding = self.authority["artifact_contract"]["surface_result_encoding"][surface]
        results = []
        for vector in self.authority["vectors"]:
            results.append(
                {
                    "errno": encoding["errno"],
                    "interface_return": encoding["interface_return"],
                    "normalized_return": vector["expected_normalized_return"],
                    "sequence": vector["sequence"],
                    "surface": surface,
                    "vector_id": vector["vector_id"],
                }
            )
        count = bin(int(bitmap, 16)).count("1")
        ledger = []
        for sequence, phase in ((0, "before"), (0, "after"), (1, "before"), (1, "after")):
            ledger.append(
                {
                    "minor63_empty": True,
                    "occupied_minor_bitmap": bitmap,
                    "occupied_minor_count": count,
                    "phase": phase,
                    "sequence": sequence,
                    "surface": surface,
                    "vector_id": self.authority["vectors"][sequence]["vector_id"],
                }
            )
        return raw, results, ledger

    def write_capture(self, name, surface, bitmap="0000000000000000"):
        root = self.root / name
        root.mkdir()
        raw, results, ledger = self.capture_records(surface, bitmap)
        values = {
            "raw.jsonl": raw,
            "result.jsonl": results,
            "state-ledger.jsonl": ledger,
        }
        for member, records in values.items():
            data = b"".join(witness._canonical_json(record) for record in records)
            path = root / member
            path.write_bytes(data)
            path.chmod(0o444)
        return root

    def replace_member(self, root, member, data, mode=0o444):
        path = root / member
        path.chmod(0o644)
        path.write_bytes(data)
        path.chmod(mode)

    def mutate_records(self, root, member, callback):
        path = root / member
        records = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
        callback(records)
        self.replace_member(
            root,
            member,
            b"".join(witness._canonical_json(record) for record in records),
        )

    def run_checked(self, command):
        completed = subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True,
            check=False,
        )
        self.assertEqual(
            0,
            completed.returncode,
            msg="command failed: {0}\nstdout:\n{1}\nstderr:\n{2}".format(
                command, completed.stdout, completed.stderr
            ),
        )
        return completed

    def test_recursive_exact_json_equality_rejects_bool_integer_aliases(self):
        aliases = ((False, 0), (0, False), (True, 1), (1, True))
        for actual, expected in aliases:
            with self.subTest(actual=actual, expected=expected):
                self.assertFalse(witness._exact_json_equal(actual, expected))
                self.assertFalse(
                    witness._exact_json_equal(
                        {"nested": [actual]}, {"nested": [expected]}
                    )
                )
        self.assertTrue(
            witness._exact_json_equal(
                {"a": [False, 0, {"b": True}]},
                {"a": [False, 0, {"b": True}]},
            )
        )

    def test_directory_identity_ignores_unrelated_entry_churn(self):
        directory = self.root / "directory-identity"
        directory.mkdir()
        before = directory.stat()
        sibling = directory / "unrelated"
        sibling.mkdir()
        after = directory.stat()
        self.assertNotEqual(witness._file_identity(before), witness._file_identity(after))
        self.assertEqual(
            witness._directory_identity(before), witness._directory_identity(after)
        )
        self.assertEqual(
            [before.st_dev, before.st_ino, before.st_mode, before.st_uid, before.st_gid],
            witness._directory_identity(before),
        )
        self.assertEqual(12, len(witness._file_identity(before)))
        self.assertEqual(
            [
                before.st_dev,
                before.st_ino,
                before.st_mode,
                before.st_nlink,
                before.st_uid,
                before.st_gid,
                before.st_rdev,
                before.st_size,
                before.st_mtime_ns,
                before.st_ctime_ns,
                before.st_blksize,
                before.st_blocks,
            ],
            witness._file_identity(before),
        )

    def test_repository_contract_and_local_external_evidence_validate_noncrediting(self):
        summary = witness.validate_contract(REPO_ROOT)
        self.assertEqual(self.authority["contract_id"], summary["contract_id"])
        self.assertEqual(2, summary["vector_count"])
        self.assertEqual("required-missing", summary["result_authority"])
        self.assertTrue(all(value is False for value in summary["claims"].values()))
        external = summary["external_failure_evidence"]
        if not external["records_verified"]:
            self.skipTest("exact ef58860e external failure evidence is not materialized")
        self.assertTrue(external["records_verified"])
        self.assertFalse(external["independent_provenance_review_complete"])
        self.assertEqual(
            "408f700403de23b705c603d7eff5cd39a2e3c6e2c7fb956cbdccf99c6db4b4b5",
            external["failure_site_sha256"],
        )
        self.assertEqual(
            "d92f6eeffed29b9690042efd91861b367d18737d47b20344c605d4ed22f0fe9e",
            external["failure_flow_sha256"],
        )

    def test_contract_is_exact_canonical_pretty_json(self):
        data = (REPO_ROOT / witness.DEFAULT_CONTRACT).read_bytes()
        value = witness._load_json_bytes(data, "contract")
        self.assertEqual(witness._pretty_json(value), data)

    def test_exact_type_contract_mutations_are_rejected(self):
        mutations = (
            lambda value: value["claims"].__setitem__("credit_eligible", 0),
            lambda value: value["gate"].__setitem__("points_awarded", False),
            lambda value: value["artifact_contract"]["result_authority"].__setitem__(
                "independent_review_required", 1
            ),
            lambda value: value.__setitem__("schema_version", True),
            lambda value: value["vectors"][0].__setitem__("argument", False),
        )
        for index, mutation in enumerate(mutations):
            with self.subTest(index=index):
                repo = self.copy_contract_repository("type-{0}".format(index))
                contract = self.load_contract(repo)
                mutation(contract)
                self.write_contract(repo, contract)
                with self.assertRaisesRegex(witness.WitnessError, "contract (size|digest)"):
                    witness.validate_contract(repo)

    def test_all_completion_and_provenance_claims_are_exact_false(self):
        expected = {
            "credit_eligible",
            "current_head_legacy_provenance_proven",
            "current_head_runtime_reachability_proven",
            "fp0006_complete",
            "full_failure_semantics_covered",
            "gate_pass",
            "legacy_runtime_executed",
            "native_runtime_executed",
            "runtime_reachability_proven",
            "tracker_credit",
        }
        self.assertEqual(expected, set(self.authority["claims"]))
        self.assertTrue(all(value is False for value in self.authority["claims"].values()))

    def test_both_producer_bytes_are_bound_by_exact_hash_and_size(self):
        for producer in ("legacy", "native"):
            binding = self.authority["producers"][producer]
            data = (REPO_ROOT / binding["path"]).read_bytes()
            self.assertEqual(binding["size"], len(data))
            self.assertEqual(binding["sha256"], witness._sha256(data))

    def test_each_producer_byte_mutation_is_rejected(self):
        for producer in ("legacy", "native"):
            with self.subTest(producer=producer):
                repo = self.copy_contract_repository("producer-" + producer)
                path = repo / self.authority["producers"][producer]["path"]
                path.write_bytes(path.read_bytes() + b"\n")
                with self.assertRaisesRegex(witness.WitnessError, "producer (size|digest)"):
                    witness.validate_contract(repo)

    def test_authority_producer_forged_by_descriptor_close_hook_is_rejected(self):
        repo = self.copy_contract_repository("producer-close-race")
        binding = self.authority["producers"]["legacy"]
        producer = repo / binding["path"]
        valid_bytes = producer.read_bytes()
        producer.write_bytes(b"FORGED\n")
        original_open = witness.os.open
        original_close = witness.os.close
        retained_producer = [None]
        valid_window = [False]
        forged = [False]

        def recording_open(path, flags, mode=0o777, *, dir_fd=None):
            descriptor = original_open(path, flags, mode, dir_fd=dir_fd)
            if (
                path == producer.parent.name
                and dir_fd is not None
                and not valid_window[0]
            ):
                producer.write_bytes(valid_bytes)
                valid_window[0] = True
            if (
                path == producer.name
                and dir_fd is not None
                and retained_producer[0] is None
            ):
                retained_producer[0] = descriptor
            return descriptor

        def racing_close(descriptor):
            original_close(descriptor)
            if descriptor == retained_producer[0] and not forged[0]:
                producer.write_bytes(b"FORGED\n")
                forged[0] = True

        with mock.patch.object(
            witness.os, "open", side_effect=recording_open
        ), mock.patch.object(witness.os, "close", side_effect=racing_close):
            with self.assertRaisesRegex(witness.WitnessError, "post-close named leaf replay"):
                witness.validate_contract(repo)
        self.assertTrue(valid_window[0])
        self.assertIsNotNone(retained_producer[0])
        self.assertTrue(forged[0])
        self.assertEqual(b"FORGED\n", producer.read_bytes())

    def test_authority_named_stat_to_leaf_open_swap_is_rejected(self):
        repo = self.copy_contract_repository("producer-open-race")
        binding = self.authority["producers"]["legacy"]
        producer = repo / binding["path"]
        replacement = self.root / "same-bytes-different-inode"
        replacement.write_bytes(producer.read_bytes())
        original_open = witness.os.open
        swapped = [False]

        def racing_open(path, flags, mode=0o777, *, dir_fd=None):
            if path == producer.name and dir_fd is not None and not swapped[0]:
                os.replace(str(replacement), str(producer))
                swapped[0] = True
            return original_open(path, flags, mode, dir_fd=dir_fd)

        with mock.patch.object(witness.os, "open", side_effect=racing_open):
            with self.assertRaisesRegex(
                witness.WitnessError, "leaf named/descriptor identity"
            ):
                witness.validate_contract(repo)
        self.assertTrue(swapped[0])

    def test_later_authority_close_cannot_forge_earlier_producer(self):
        repo = self.copy_contract_repository("authority-aggregate-race")
        legacy = repo / self.authority["producers"]["legacy"]["path"]
        native = repo / self.authority["producers"]["native"]["path"]
        original_open = witness.os.open
        original_close = witness.os.close
        retained_native = [None]
        forged = [False]

        def recording_open(path, flags, mode=0o777, *, dir_fd=None):
            descriptor = original_open(path, flags, mode, dir_fd=dir_fd)
            if path == native.name and dir_fd is not None and retained_native[0] is None:
                retained_native[0] = descriptor
            return descriptor

        def racing_close(descriptor):
            original_close(descriptor)
            if descriptor == retained_native[0] and not forged[0]:
                legacy.write_bytes(b"FORGED\n")
                forged[0] = True

        with mock.patch.object(
            witness.os, "open", side_effect=recording_open
        ), mock.patch.object(witness.os, "close", side_effect=racing_close):
            with self.assertRaisesRegex(
                witness.WitnessError,
                "legacy capture producer post-close named leaf replay",
            ):
                witness.validate_contract(repo)
        self.assertTrue(forged[0])

    def test_public_review_revalidates_authority_on_every_invocation(self):
        repo = self.copy_contract_repository("revalidate")
        capture = self.write_capture("revalidate-capture", self.legacy_surface)
        first = witness.review_artifact(repo, capture, self.legacy_surface)
        self.assertTrue(first["capture_schema_validated"])
        producer = repo / self.authority["producers"]["legacy"]["path"]
        producer.write_bytes(producer.read_bytes() + b"\n")
        with self.assertRaisesRegex(witness.WitnessError, "producer (size|digest)"):
            witness.review_artifact(repo, capture, self.legacy_surface)

    def test_mutable_module_globals_cannot_redirect_vectors_or_claims(self):
        capture = self.write_capture("immutable-authority", self.legacy_surface)
        fabricated_vectors = [
            {"argument": 9, "request": 9, "sequence": 0, "vector_id": "fabricated"}
        ]
        fabricated_claims = {"tracker_credit": True}
        with mock.patch.object(witness, "CONTRACT_ID", "fabricated"), mock.patch.object(
            witness, "LEGACY_SURFACE", "fabricated"
        ), mock.patch.object(
            witness, "EXPECTED_VECTORS", fabricated_vectors, create=True
        ), mock.patch.object(
            witness, "EXPECTED_CLAIMS", fabricated_claims, create=True
        ):
            result = witness.review_artifact(REPO_ROOT, capture, self.legacy_surface)
            self.assertEqual(self.authority["contract_id"], result["contract_id"])
            self.assertEqual(self.authority["claims"], result["claims"])
            self.mutate_records(
                capture,
                "raw.jsonl",
                lambda records: records[0].update(
                    {"argument": 9, "request": 9, "vector_id": "fabricated"}
                ),
            )
            with self.assertRaisesRegex(witness.WitnessError, "raw vector stream"):
                witness.review_artifact(REPO_ROOT, capture, self.legacy_surface)

    def test_current_host_driver_and_hff_effective_source_are_explicitly_distinct(self):
        boundary = self.authority["current_head_boundary"]
        current = boundary["current_host_driver"]
        self.assertEqual(
            "be75185f5b1a0aea84b0be995f67405e45964999b6ed28ae60adb3ed1dece722",
            current["sha256"],
        )
        self.assertEqual(
            "f677c7dde6de2160fd9062fa998cb2c4aa14ba9eafdac8b86b592b78776bcd2e",
            boundary["hff_effective_source_sha256"],
        )
        self.assertNotEqual(current["sha256"], boundary["hff_effective_source_sha256"])
        self.assertFalse(boundary["current_head_legacy_provenance_claimed"])
        self.assertFalse(boundary["current_head_runtime_reachability_claimed"])

    def test_five_exact_hff_records_bind_empty_reachable_roots_and_source(self):
        evidence = self.authority["failure_evidence"]
        records = evidence["hff_records"]
        self.assertEqual(5, len(records))
        self.assertEqual(
            {
                "HFF-630FB69B83A3C6E59C9F397C",
                "HFF-440A8A64489D446B45EA992A",
                "HFF-C4E5AAF7C10B3803681570C6",
                "HFF-79204C286836C113FFB37A89",
                "HFF-15E5BF9893165A7F1FBC6D85",
            },
            {record["id"] for record in records},
        )
        for record in records:
            self.assertEqual([], record["reachable_entry_roots"])
            self.assertEqual(
                self.authority["current_head_boundary"]["hff_effective_source_sha256"],
                record["source_sha256"],
            )
        flow = evidence["failure_flow_artifact"]
        self.assertEqual(
            evidence["failure_site_authority"]["sha256"],
            flow["input_failure_sites"]["artifact_sha256"],
        )
        self.assertEqual(
            evidence["failure_site_authority"]["size"],
            flow["input_failure_sites"]["artifact_bytes"],
        )

    def test_legacy_behavior_authority_and_inputs_are_exactly_bound(self):
        legacy = self.authority["legacy_behavior_authority"]
        self.assertEqual(2, len(legacy["behaviors"]))
        self.assertEqual(2, len(legacy["acceptance_tests"]))
        for key, input_id in (("inventory", "legacy_inventory"), ("policy", "legacy_policy")):
            binding = legacy["inputs"][key]
            frozen = self.authority["frozen_inputs"][input_id]
            self.assertEqual(binding["path"], frozen["path"])
            self.assertEqual(binding["sha256"], frozen["sha256"])

    def test_missing_external_evidence_remains_required_missing(self):
        repo = self.copy_contract_repository("without-external")
        summary = witness.validate_contract(repo)
        external = summary["external_failure_evidence"]
        self.assertFalse(external["records_verified"])
        self.assertFalse(external["independent_provenance_review_complete"])
        self.assertEqual("required-missing", external["failure_site_authority"])
        self.assertEqual("required-missing", external["failure_flow_artifact"])

    def test_missing_external_evidence_created_by_close_hook_is_rejected(self):
        repo = self.copy_contract_repository("external-close-race")
        binding = self.authority["failure_evidence"]["failure_site_authority"]
        site = repo.parent / binding["external_path_hint"]
        original_stat = witness.os.stat
        original_close = witness.os.close
        armed = [False]
        created = [False]

        def recording_stat(path, *args, **kwargs):
            try:
                return original_stat(path, *args, **kwargs)
            except FileNotFoundError:
                if path == "ci-evidence":
                    armed[0] = True
                raise

        def racing_close(descriptor):
            original_close(descriptor)
            if armed[0] and not created[0]:
                site.parent.mkdir(parents=True, exist_ok=True)
                site.write_bytes(b"FORGED\n")
                created[0] = True

        with mock.patch.object(
            witness.os, "stat", side_effect=recording_stat
        ), mock.patch.object(witness.os, "close", side_effect=racing_close):
            with self.assertRaises(witness.WitnessError):
                witness.validate_contract(repo)
        self.assertTrue(armed[0])
        self.assertTrue(created[0])

    def test_partial_or_wrong_external_evidence_is_rejected(self):
        repo = self.copy_contract_repository("bad-external")
        site = repo.parent / self.authority["failure_evidence"]["failure_site_authority"][
            "external_path_hint"
        ]
        site.parent.mkdir(parents=True, exist_ok=True)
        site.write_bytes(b"wrong")
        with self.assertRaisesRegex(witness.WitnessError, "partially available"):
            witness.validate_contract(repo)
        flow = repo.parent / self.authority["failure_evidence"]["failure_flow_artifact"][
            "external_path_hint"
        ]
        flow.write_bytes(b"wrong")
        with self.assertRaises(witness.WitnessError):
            witness.validate_contract(repo)

    def test_frozen_repository_input_mutation_is_rejected(self):
        repo = self.copy_contract_repository("input-mutation")
        path = repo / self.authority["frozen_inputs"]["abi"]["path"]
        path.write_bytes(path.read_bytes() + b"\n")
        with self.assertRaisesRegex(witness.WitnessError, "frozen input digest abi"):
            witness.validate_contract(repo)

    def test_checker_parses_as_python_36(self):
        source = (REPO_ROOT / "scripts/fp0006_ihk_device_negative_dispatch.py").read_text(
            encoding="utf-8"
        )
        ast.parse(source, feature_version=(3, 6))

    def test_c_producer_compiles_and_describe_mode_is_nonexecution(self):
        compiler = shutil.which("cc")
        if compiler is None:
            self.skipTest("C compiler is unavailable")
        binary = self.root / "legacy-producer"
        source = REPO_ROOT / self.authority["producers"]["legacy"]["path"]
        self.run_checked(
            [compiler, "-std=c11", "-Wall", "-Wextra", "-Werror", str(source), "-o", str(binary)]
        )
        value = json.loads(self.run_checked([str(binary), "--describe"]).stdout)
        self.assertFalse(value["live_execution_performed"])
        self.assertFalse(value["tracker_credit"])
        self.assertEqual(self.legacy_surface, value["surface"])

    def test_rust_producer_compiles_emits_and_stays_source_fixture_only(self):
        compiler = shutil.which("rustc")
        if compiler is None:
            self.skipTest("rustc is unavailable")
        binary = self.root / "native-producer"
        source = REPO_ROOT / self.authority["producers"]["native"]["path"]
        self.run_checked([compiler, "--edition=2021", "-Dwarnings", str(source), "-o", str(binary)])
        value = json.loads(self.run_checked([str(binary), "--describe"]).stdout)
        self.assertFalse(value["native_module_runtime_executed"])
        self.assertFalse(value["tracker_credit"])
        capture = self.root / "native-emitted"
        capture.mkdir()
        self.run_checked([str(binary), str(capture)])
        summary = witness.review_artifact(REPO_ROOT, capture, self.native_surface)
        self.assertTrue(summary["capture_schema_validated"])

    def test_valid_artifact_pair_is_schema_validated_but_unreviewed(self):
        legacy = self.write_capture("legacy", self.legacy_surface, "0000000000000005")
        native = self.write_capture("native", self.native_surface)
        result = witness.review_artifacts(REPO_ROOT, legacy, native)
        self.assertTrue(result["artifact_pair_validated"])
        self.assertEqual("CAPTURED_UNREVIEWED_NONCREDITING", result["status"])
        self.assertEqual("required-missing", result["result_authority"])
        self.assertTrue(all(value is False for value in result["claims"].values()))

    def test_artifact_review_is_deterministic(self):
        capture = self.write_capture("legacy-deterministic", self.legacy_surface)
        first = witness.review_artifact(REPO_ROOT, capture, self.legacy_surface)
        second = witness.review_artifact(REPO_ROOT, capture, self.legacy_surface)
        self.assertEqual(first, second)

    def test_unrelated_ancestor_entry_churn_does_not_change_path_identity(self):
        capture = self.write_capture("ancestor-entry-churn", self.legacy_surface)
        original_open = witness.os.open
        original_close = witness.os.close
        retained_raw = [None]
        churned = [False]

        def recording_open(path, flags, mode=0o777, *, dir_fd=None):
            descriptor = original_open(path, flags, mode, dir_fd=dir_fd)
            if path == "raw.jsonl" and dir_fd is not None and retained_raw[0] is None:
                retained_raw[0] = descriptor
            return descriptor

        def racing_close(descriptor):
            original_close(descriptor)
            if descriptor == retained_raw[0] and not churned[0]:
                sibling = self.root / "unrelated-sibling"
                sibling.mkdir()
                sibling.rmdir()
                churned[0] = True

        with mock.patch.object(
            witness.os, "open", side_effect=recording_open
        ), mock.patch.object(witness.os, "close", side_effect=racing_close):
            result = witness.review_artifact(REPO_ROOT, capture, self.legacy_surface)
        self.assertTrue(churned[0])
        self.assertTrue(result["capture_schema_validated"])

    def test_ancestor_replacement_is_rejected_despite_stable_metadata(self):
        capture = self.write_capture("ancestor-replacement", self.legacy_surface)
        replacement = self.root / "replacement-directory"
        replacement.mkdir(mode=0o755)
        moved = self.root / "moved-capture"
        original_open = witness.os.open
        original_close = witness.os.close
        retained_raw = [None]
        replaced = [False]

        def recording_open(path, flags, mode=0o777, *, dir_fd=None):
            descriptor = original_open(path, flags, mode, dir_fd=dir_fd)
            if path == "raw.jsonl" and dir_fd is not None and retained_raw[0] is None:
                retained_raw[0] = descriptor
            return descriptor

        def racing_close(descriptor):
            original_close(descriptor)
            if descriptor == retained_raw[0] and not replaced[0]:
                os.replace(str(capture), str(moved))
                os.replace(str(replacement), str(capture))
                replaced[0] = True

        with mock.patch.object(
            witness.os, "open", side_effect=recording_open
        ), mock.patch.object(witness.os, "close", side_effect=racing_close):
            with self.assertRaisesRegex(
                witness.WitnessError,
                "capture path after member close retained named ancestor replay differs",
            ):
                witness.review_artifact(REPO_ROOT, capture, self.legacy_surface)
        self.assertTrue(replaced[0])

    def test_ancestor_mode_change_is_rejected(self):
        capture = self.write_capture("ancestor-mode-change", self.legacy_surface)
        original_open = witness.os.open
        original_close = witness.os.close
        retained_raw = [None]
        changed = [False]

        def recording_open(path, flags, mode=0o777, *, dir_fd=None):
            descriptor = original_open(path, flags, mode, dir_fd=dir_fd)
            if path == "raw.jsonl" and dir_fd is not None and retained_raw[0] is None:
                retained_raw[0] = descriptor
            return descriptor

        def racing_close(descriptor):
            original_close(descriptor)
            if descriptor == retained_raw[0] and not changed[0]:
                self.root.chmod(0o750)
                changed[0] = True

        try:
            with mock.patch.object(
                witness.os, "open", side_effect=recording_open
            ), mock.patch.object(witness.os, "close", side_effect=racing_close):
                with self.assertRaisesRegex(
                    witness.WitnessError,
                    "capture path after member close retained ancestor descriptor replay differs",
                ):
                    witness.review_artifact(REPO_ROOT, capture, self.legacy_surface)
            self.assertTrue(changed[0])
        finally:
            self.root.chmod(0o700)

    def test_named_stat_to_directory_open_swaps_are_rejected(self):
        rooted = self.root / "rooted-authority"
        rooted.mkdir()
        leaf = rooted / "item"
        leaf.write_bytes(b"original")
        replacement = self.root / "rooted-replacement"
        replacement.mkdir()
        (replacement / "item").write_bytes(b"replacement")
        moved = self.root / "rooted-moved"
        original_open = witness.os.open
        swapped = [False]

        def racing_rooted_open(path, flags, mode=0o777, *, dir_fd=None):
            if path == rooted.name and dir_fd is not None and not swapped[0]:
                os.replace(str(rooted), str(moved))
                os.replace(str(replacement), str(rooted))
                swapped[0] = True
            return original_open(path, flags, mode, dir_fd=dir_fd)

        with mock.patch.object(witness.os, "open", side_effect=racing_rooted_open):
            with self.assertRaisesRegex(
                witness.WitnessError, "rooted swap ancestor named/descriptor identity"
            ):
                witness._read_rooted_file(self.root, "rooted-authority/item", "rooted swap")
        self.assertTrue(swapped[0])

        capture = self.write_capture("capture-open-swap", self.legacy_surface)
        replacement = self.root / "capture-open-replacement"
        replacement.mkdir()
        moved = self.root / "capture-open-moved"
        swapped = [False]

        def racing_capture_open(path, flags, mode=0o777, *, dir_fd=None):
            if path == capture.name and dir_fd is not None and not swapped[0]:
                os.replace(str(capture), str(moved))
                os.replace(str(replacement), str(capture))
                swapped[0] = True
            return original_open(path, flags, mode, dir_fd=dir_fd)

        with mock.patch.object(witness.os, "open", side_effect=racing_capture_open):
            with self.assertRaisesRegex(
                witness.WitnessError, "capture ancestor named/descriptor identity"
            ):
                witness.review_artifact(REPO_ROOT, capture, self.legacy_surface)
        self.assertTrue(swapped[0])

    def test_post_close_directory_replacement_is_rejected(self):
        capture = self.write_capture("post-close-replacement", self.legacy_surface)
        replacement = self.root / "post-close-replacement-directory"
        replacement.mkdir()
        moved = self.root / "post-close-moved"
        original_open = witness.os.open
        original_close = witness.os.close
        retained_directory = [None]
        replaced = [False]

        def recording_open(path, flags, mode=0o777, *, dir_fd=None):
            descriptor = original_open(path, flags, mode, dir_fd=dir_fd)
            if path == capture.name and dir_fd is not None:
                retained_directory[0] = descriptor
            return descriptor

        def racing_close(descriptor):
            original_close(descriptor)
            if descriptor == retained_directory[0] and not replaced[0]:
                os.replace(str(capture), str(moved))
                os.replace(str(replacement), str(capture))
                replaced[0] = True

        with mock.patch.object(
            witness.os, "open", side_effect=recording_open
        ), mock.patch.object(witness.os, "close", side_effect=racing_close):
            with self.assertRaisesRegex(
                witness.WitnessError,
                "capture path post-close named ancestor replay differs",
            ):
                witness.review_artifact(REPO_ROOT, capture, self.legacy_surface)
        self.assertTrue(replaced[0])

    def test_post_close_directory_symlink_substitution_is_rejected(self):
        capture = self.write_capture("post-close-symlink", self.legacy_surface)
        moved = self.root / "post-close-symlink-target"
        original_open = witness.os.open
        original_close = witness.os.close
        retained_directory = [None]
        replaced = [False]

        def recording_open(path, flags, mode=0o777, *, dir_fd=None):
            descriptor = original_open(path, flags, mode, dir_fd=dir_fd)
            if path == capture.name and dir_fd is not None:
                retained_directory[0] = descriptor
            return descriptor

        def racing_close(descriptor):
            original_close(descriptor)
            if descriptor == retained_directory[0] and not replaced[0]:
                os.replace(str(capture), str(moved))
                capture.symlink_to(moved, target_is_directory=True)
                replaced[0] = True

        with mock.patch.object(
            witness.os, "open", side_effect=recording_open
        ), mock.patch.object(witness.os, "close", side_effect=racing_close):
            with self.assertRaisesRegex(
                witness.WitnessError, "capture path ancestor became a non-directory"
            ):
                witness.review_artifact(REPO_ROOT, capture, self.legacy_surface)
        self.assertTrue(replaced[0])

    def test_extra_capture_member_after_initial_listing_is_rejected(self):
        capture = self.write_capture("late-extra-member", self.legacy_surface)
        original_open = witness.os.open
        injected = [False]

        def racing_open(path, flags, mode=0o777, *, dir_fd=None):
            if path == "raw.jsonl" and dir_fd is not None and not injected[0]:
                extra = capture / "late-extra.json"
                extra.write_bytes(b"{}\n")
                extra.chmod(0o444)
                injected[0] = True
            return original_open(path, flags, mode, dir_fd=dir_fd)

        with mock.patch.object(witness.os, "open", side_effect=racing_open):
            with self.assertRaisesRegex(
                witness.WitnessError, "retained capture member-set replay differs"
            ):
                witness.review_artifact(REPO_ROOT, capture, self.legacy_surface)
        self.assertTrue(injected[0])

    def test_aggregate_replay_rejects_replaced_earlier_capture_directory(self):
        legacy = self.write_capture("aggregate-legacy", self.legacy_surface)
        native = self.write_capture("aggregate-native", self.native_surface)
        replacement = self.root / "aggregate-legacy-replacement"
        replacement.mkdir()
        moved = self.root / "aggregate-legacy-moved"
        original_open = witness.os.open
        native_directory = [None]
        replaced = [False]

        def racing_open(path, flags, mode=0o777, *, dir_fd=None):
            descriptor = original_open(path, flags, mode, dir_fd=dir_fd)
            if path == native.name and dir_fd is not None:
                native_directory[0] = descriptor
            elif (
                path == "raw.jsonl"
                and dir_fd == native_directory[0]
                and not replaced[0]
            ):
                os.replace(str(legacy), str(moved))
                os.replace(str(replacement), str(legacy))
                replaced[0] = True
            return descriptor

        with mock.patch.object(witness.os, "open", side_effect=racing_open):
            with self.assertRaisesRegex(
                witness.WitnessError,
                "capture path post-close named ancestor replay differs",
            ):
                witness.review_artifacts(REPO_ROOT, legacy, native)
        self.assertTrue(replaced[0])

    def test_unknown_artifact_surface_is_rejected(self):
        capture = self.write_capture("legacy-unknown", self.legacy_surface)
        with self.assertRaisesRegex(witness.WitnessError, "not recognized"):
            witness.review_artifact(REPO_ROOT, capture, "fabricated")

    def test_missing_and_extra_capture_members_are_rejected(self):
        capture = self.write_capture("legacy-missing", self.legacy_surface)
        (capture / "raw.jsonl").unlink()
        with self.assertRaisesRegex(witness.WitnessError, "member set"):
            witness.review_artifact(REPO_ROOT, capture, self.legacy_surface)
        capture = self.write_capture("legacy-extra", self.legacy_surface)
        extra = capture / "extra.json"
        extra.write_text("{}\n", encoding="utf-8")
        extra.chmod(0o444)
        with self.assertRaisesRegex(witness.WitnessError, "member set"):
            witness.review_artifact(REPO_ROOT, capture, self.legacy_surface)

    def test_symlink_hardlink_and_directory_alias_are_rejected(self):
        capture = self.write_capture("legacy-symlink", self.legacy_surface)
        raw = capture / "raw.jsonl"
        data = raw.read_bytes()
        raw.unlink()
        outside = self.root / "outside-raw"
        outside.write_bytes(data)
        outside.chmod(0o444)
        raw.symlink_to(outside)
        with self.assertRaises(witness.WitnessError):
            witness.review_artifact(REPO_ROOT, capture, self.legacy_surface)

        capture = self.write_capture("legacy-hardlink", self.legacy_surface)
        os.link(str(capture / "raw.jsonl"), str(self.root / "linked-raw"))
        with self.assertRaisesRegex(witness.WitnessError, "singly linked"):
            witness.review_artifact(REPO_ROOT, capture, self.legacy_surface)

        capture = self.write_capture("legacy-real", self.legacy_surface)
        alias = self.root / "capture-alias"
        alias.symlink_to(capture, target_is_directory=True)
        with self.assertRaisesRegex(witness.WitnessError, "non-symlink directory"):
            witness.review_artifact(REPO_ROOT, alias, self.legacy_surface)

    def test_wrong_mode_empty_and_oversized_members_are_rejected(self):
        capture = self.write_capture("legacy-mode", self.legacy_surface)
        (capture / "raw.jsonl").chmod(0o644)
        with self.assertRaisesRegex(witness.WitnessError, "exact mode"):
            witness.review_artifact(REPO_ROOT, capture, self.legacy_surface)
        capture = self.write_capture("legacy-empty", self.legacy_surface)
        self.replace_member(capture, "raw.jsonl", b"")
        with self.assertRaisesRegex(witness.WitnessError, "size is invalid"):
            witness.review_artifact(REPO_ROOT, capture, self.legacy_surface)
        capture = self.write_capture("legacy-large", self.legacy_surface)
        maximum = self.authority["artifact_contract"]["maximum_member_bytes"]
        self.replace_member(capture, "raw.jsonl", b"x" * (maximum + 1))
        with self.assertRaisesRegex(witness.WitnessError, "size is invalid"):
            witness.review_artifact(REPO_ROOT, capture, self.legacy_surface)

    def test_noncanonical_duplicate_unterminated_and_bom_jsonl_are_rejected(self):
        capture = self.write_capture("legacy-space", self.legacy_surface)
        original = (capture / "raw.jsonl").read_bytes()
        self.replace_member(capture, "raw.jsonl", original.replace(b"{", b"{ ", 1))
        with self.assertRaisesRegex(witness.WitnessError, "not canonical"):
            witness.review_artifact(REPO_ROOT, capture, self.legacy_surface)
        capture = self.write_capture("legacy-duplicate", self.legacy_surface)
        original = (capture / "raw.jsonl").read_bytes()
        self.replace_member(capture, "raw.jsonl", original.replace(b"{", b'{"argument":0,', 1))
        with self.assertRaisesRegex(witness.WitnessError, "duplicate JSON key"):
            witness.review_artifact(REPO_ROOT, capture, self.legacy_surface)
        capture = self.write_capture("legacy-unterminated", self.legacy_surface)
        original = (capture / "raw.jsonl").read_bytes()
        self.replace_member(capture, "raw.jsonl", original[:-1])
        with self.assertRaisesRegex(witness.WitnessError, "final LF"):
            witness.review_artifact(REPO_ROOT, capture, self.legacy_surface)
        capture = self.write_capture("legacy-bom", self.legacy_surface)
        original = (capture / "raw.jsonl").read_bytes()
        self.replace_member(capture, "raw.jsonl", b"\xef\xbb\xbf" + original)
        with self.assertRaisesRegex(witness.WitnessError, "final LF"):
            witness.review_artifact(REPO_ROOT, capture, self.legacy_surface)

    def test_raw_false_alias_value_and_extra_key_mutations_are_rejected(self):
        mutations = (
            lambda rows: rows[0].__setitem__("argument", False),
            lambda rows: rows[0].__setitem__("request", 0xfffffffe),
            lambda rows: rows[0].__setitem__("sequence", False),
            lambda rows: rows[0].__setitem__("invented", 1),
        )
        for index, mutation in enumerate(mutations):
            with self.subTest(index=index):
                capture = self.write_capture("raw-{0}".format(index), self.legacy_surface)
                self.mutate_records(capture, "raw.jsonl", mutation)
                with self.assertRaises(witness.WitnessError):
                    witness.review_artifact(REPO_ROOT, capture, self.legacy_surface)

    def test_result_type_value_surface_and_key_mutations_are_rejected(self):
        mutations = (
            lambda rows: rows[0].__setitem__("errno", False),
            lambda rows: rows[0].__setitem__("interface_return", -22),
            lambda rows: rows[0].__setitem__("normalized_return", 0),
            lambda rows: rows[0].__setitem__("surface", self.native_surface),
            lambda rows: rows[0].__setitem__("sequence", False),
            lambda rows: rows[0].__setitem__("invented", False),
        )
        for index, mutation in enumerate(mutations):
            with self.subTest(index=index):
                capture = self.write_capture("result-{0}".format(index), self.legacy_surface)
                self.mutate_records(capture, "result.jsonl", mutation)
                with self.assertRaises(witness.WitnessError):
                    witness.review_artifact(REPO_ROOT, capture, self.legacy_surface)

    def test_state_ledger_claim_shape_and_transition_mutations_are_rejected(self):
        mutations = (
            lambda rows: rows[0].__setitem__("minor63_empty", 1),
            lambda rows: rows[0].__setitem__("minor63_empty", False),
            lambda rows: rows[0].__setitem__("occupied_minor_bitmap", "8000000000000000"),
            lambda rows: rows[0].__setitem__("occupied_minor_bitmap", "000000000000000A"),
            lambda rows: rows[0].__setitem__("occupied_minor_count", False),
            lambda rows: rows[1].__setitem__("occupied_minor_bitmap", "0000000000000001"),
            lambda rows: rows[0].__setitem__("phase", "after"),
            lambda rows: rows[0].__setitem__("invented", False),
        )
        for index, mutation in enumerate(mutations):
            with self.subTest(index=index):
                capture = self.write_capture("ledger-{0}".format(index), self.legacy_surface)
                self.mutate_records(capture, "state-ledger.jsonl", mutation)
                with self.assertRaises(witness.WitnessError):
                    witness.review_artifact(REPO_ROOT, capture, self.legacy_surface)

    def test_native_fixture_nonempty_registry_claim_is_rejected(self):
        capture = self.write_capture("native-nonempty", self.native_surface, "0000000000000001")
        with self.assertRaisesRegex(witness.WitnessError, "fresh registry"):
            witness.review_artifact(REPO_ROOT, capture, self.native_surface)

    def test_transient_valid_descriptor_with_restored_invalid_named_leaf_is_rejected(self):
        capture = self.write_capture("transient", self.legacy_surface)
        replacement = self.root / "invalid-raw"
        replacement.write_bytes(b'{"invalid":true}\n')
        replacement.chmod(0o444)
        original_open = witness.os.open
        swapped = [False]

        def racing_open(path, flags, mode=0o777, *, dir_fd=None):
            descriptor = original_open(path, flags, mode, dir_fd=dir_fd)
            if path == "raw.jsonl" and dir_fd is not None and not swapped[0]:
                os.replace(str(replacement), str(capture / "raw.jsonl"))
                swapped[0] = True
            return descriptor

        with mock.patch.object(witness.os, "open", side_effect=racing_open):
            with self.assertRaises(witness.WitnessError):
                witness.review_artifact(REPO_ROOT, capture, self.legacy_surface)
        self.assertTrue(swapped[0])

    def test_capture_raw_forged_by_member_close_hook_is_rejected(self):
        capture = self.write_capture("capture-close-race", self.legacy_surface)
        raw = capture / "raw.jsonl"
        original_open = witness.os.open
        original_close = witness.os.close
        retained_raw = [None]
        forged = [False]

        def recording_open(path, flags, mode=0o777, *, dir_fd=None):
            descriptor = original_open(path, flags, mode, dir_fd=dir_fd)
            if path == "raw.jsonl" and dir_fd is not None and retained_raw[0] is None:
                retained_raw[0] = descriptor
            return descriptor

        def racing_close(descriptor):
            original_close(descriptor)
            if descriptor == retained_raw[0] and not forged[0]:
                raw.chmod(0o644)
                raw.write_bytes(b'{"forged":true}\n')
                raw.chmod(0o444)
                forged[0] = True

        with mock.patch.object(
            witness.os, "open", side_effect=recording_open
        ), mock.patch.object(witness.os, "close", side_effect=racing_close):
            with self.assertRaisesRegex(
                witness.WitnessError, "post-member-close named leaf replay"
            ):
                witness.review_artifact(REPO_ROOT, capture, self.legacy_surface)
        self.assertIsNotNone(retained_raw[0])
        self.assertTrue(forged[0])
        self.assertEqual(b'{"forged":true}\n', raw.read_bytes())

    def test_capture_raw_forged_by_directory_close_hook_is_rejected(self):
        capture = self.write_capture("capture-directory-close-race", self.legacy_surface)
        raw = capture / "raw.jsonl"
        original_open = witness.os.open
        original_close = witness.os.close
        retained_directory = [None]
        forged = [False]

        def recording_open(path, flags, mode=0o777, *, dir_fd=None):
            descriptor = original_open(path, flags, mode, dir_fd=dir_fd)
            if path == capture.name and dir_fd is not None and retained_directory[0] is None:
                retained_directory[0] = descriptor
            return descriptor

        def racing_close(descriptor):
            original_close(descriptor)
            if descriptor == retained_directory[0] and not forged[0]:
                raw.chmod(0o644)
                raw.write_bytes(b'{"forged":"directory-close"}\n')
                raw.chmod(0o444)
                forged[0] = True

        with mock.patch.object(
            witness.os, "open", side_effect=recording_open
        ), mock.patch.object(witness.os, "close", side_effect=racing_close):
            with self.assertRaisesRegex(
                witness.WitnessError, "post-close path-rooted leaf replay"
            ):
                witness.review_artifact(REPO_ROOT, capture, self.legacy_surface)
        self.assertTrue(forged[0])

    def test_capture_close_cannot_forge_already_validated_authority(self):
        repo = self.copy_contract_repository("review-aggregate-race")
        producer = repo / self.authority["producers"]["legacy"]["path"]
        capture = self.write_capture("review-aggregate-capture", self.legacy_surface)
        original_open = witness.os.open
        original_close = witness.os.close
        retained_raw = [None]
        forged = [False]

        def recording_open(path, flags, mode=0o777, *, dir_fd=None):
            descriptor = original_open(path, flags, mode, dir_fd=dir_fd)
            if path == "raw.jsonl" and dir_fd is not None and retained_raw[0] is None:
                retained_raw[0] = descriptor
            return descriptor

        def racing_close(descriptor):
            original_close(descriptor)
            if descriptor == retained_raw[0] and not forged[0]:
                producer.write_bytes(b"FORGED\n")
                forged[0] = True

        with mock.patch.object(
            witness.os, "open", side_effect=recording_open
        ), mock.patch.object(witness.os, "close", side_effect=racing_close):
            with self.assertRaisesRegex(
                witness.WitnessError,
                "legacy capture producer post-close named leaf replay",
            ):
                witness.review_artifact(repo, capture, self.legacy_surface)
        self.assertTrue(forged[0])

    def test_native_close_cannot_forge_already_reviewed_legacy_capture(self):
        legacy = self.write_capture("pair-aggregate-legacy", self.legacy_surface)
        native = self.write_capture("pair-aggregate-native", self.native_surface)
        legacy_raw = legacy / "raw.jsonl"
        original_open = witness.os.open
        original_close = witness.os.close
        native_directory = [None]
        native_raw = [None]
        forged = [False]

        def recording_open(path, flags, mode=0o777, *, dir_fd=None):
            descriptor = original_open(path, flags, mode, dir_fd=dir_fd)
            if path == native.name and dir_fd is not None and native_directory[0] is None:
                native_directory[0] = descriptor
            elif path == "raw.jsonl" and dir_fd == native_directory[0]:
                native_raw[0] = descriptor
            return descriptor

        def racing_close(descriptor):
            original_close(descriptor)
            if descriptor == native_raw[0] and not forged[0]:
                legacy_raw.chmod(0o644)
                legacy_raw.write_bytes(b'{"forged":"native-close"}\n')
                legacy_raw.chmod(0o444)
                forged[0] = True

        with mock.patch.object(
            witness.os, "open", side_effect=recording_open
        ), mock.patch.object(witness.os, "close", side_effect=racing_close):
            with self.assertRaisesRegex(
                witness.WitnessError, "post-close path-rooted leaf replay raw.jsonl"
            ):
                witness.review_artifacts(REPO_ROOT, legacy, native)
        self.assertIsNotNone(native_raw[0])
        self.assertTrue(forged[0])

    def test_review_api_does_not_leak_retained_descriptors(self):
        descriptor_root = Path("/proc/self/fd")
        if not descriptor_root.is_dir():
            self.skipTest("/proc/self/fd is unavailable")
        capture = self.write_capture("fd", self.legacy_surface)
        before = len(list(descriptor_root.iterdir()))
        for _ in range(5):
            witness.review_artifact(REPO_ROOT, capture, self.legacy_surface)
        after = len(list(descriptor_root.iterdir()))
        self.assertLessEqual(after, before + 1)

    def test_check_and_review_cli_remain_noncrediting(self):
        stdout = io.StringIO()
        stderr = io.StringIO()
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            status = witness.main(["check-contract", "--repo", str(REPO_ROOT)])
        self.assertEqual(0, status)
        self.assertEqual("", stderr.getvalue())
        checked = json.loads(stdout.getvalue())
        self.assertEqual("CONTRACT_VALIDATED_NONCREDITING", checked["status"])
        self.assertTrue(all(value is False for value in checked["claims"].values()))

        legacy = self.write_capture("legacy-cli", self.legacy_surface)
        native = self.write_capture("native-cli", self.native_surface)
        stdout = io.StringIO()
        stderr = io.StringIO()
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            status = witness.main(
                [
                    "review-artifacts", "--repo", str(REPO_ROOT),
                    "--legacy", str(legacy), "--native", str(native),
                ]
            )
        self.assertEqual(0, status)
        self.assertEqual("", stderr.getvalue())
        reviewed = json.loads(stdout.getvalue())
        self.assertEqual("required-missing", reviewed["result_authority"])
        self.assertEqual("CAPTURED_UNREVIEWED_NONCREDITING", reviewed["status"])


if __name__ == "__main__":
    unittest.main()
