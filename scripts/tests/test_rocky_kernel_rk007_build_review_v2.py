#!/usr/bin/env python3
"""Adversarial tests for the fresh, non-crediting RK-007 v2 review."""

from __future__ import print_function

import ast
import copy
import hashlib
import io
import json
import os
import stat
import struct
import subprocess
import sys
import tempfile
import unittest
import warnings
import zipfile
from pathlib import Path
from unittest import mock


REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = REPO_ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import rocky_kernel_rk007_build_review as historical
import rocky_kernel_rk007_build_review_v2 as reviewer


MANIFEST = (
    REPO_ROOT
    / "host-kernel/rocky/evidence/rk007-native-build-review-ef58-v2.json"
)


def set_path(value, path, replacement):
    current = value
    for key in path[:-1]:
        current = current[key]
    current[path[-1]] = replacement


def unix_zip(entries, compression=zipfile.ZIP_STORED, archive_comment=b"", modes=None):
    modes = modes or {}
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w") as archive:
        archive.comment = archive_comment
        for name, data in entries:
            info = zipfile.ZipInfo(name, date_time=(2026, 8, 18, 0, 0, 0))
            info.create_system = 3
            info.external_attr = (
                modes.get(name, stat.S_IFREG | 0o644) << 16
            )
            info.compress_type = compression
            archive.writestr(info, data)
    return output.getvalue()


class Rk007BuildReviewV2Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.review_bytes = MANIFEST.read_bytes()
        cls.review = reviewer.read_json_bytes(
            cls.review_bytes, "checked review", require_canonical=True
        )

    def artifact_path(self):
        candidates = []
        configured = os.environ.get("MCKERNEL_RK007_V2_ARTIFACT")
        if configured:
            candidates.append(Path(configured))
        candidates.append(Path("/tmp") / (reviewer.ARTIFACT_NAME + ".zip"))
        for candidate in candidates:
            if candidate.is_file():
                return candidate
        self.skipTest("exact ef58860e RK-007 v2 artifact ZIP is not materialized")

    def artifact_files(self):
        data = self.artifact_path().read_bytes()
        files, unused_index = reviewer.read_zip_members(data)
        return data, files

    def test_checked_review_is_canonical_digest_locked_and_valid(self):
        self.assertEqual(
            hashlib.sha256(self.review_bytes).hexdigest(), reviewer.REVIEW_SHA256
        )
        self.assertEqual(self.review_bytes, reviewer.canonical_json_bytes(self.review))
        self.assertEqual(
            reviewer.validate_review_object(copy.deepcopy(self.review)), self.review
        )

    def test_historical_v1_discovery_and_identity_are_not_retargeted(self):
        self.assertEqual(historical.REVIEW_GLOB, "rk007-native-build-review-*-v1.json")
        self.assertEqual(
            historical.RUNTIME_HEAD_SHA, "bc60eed563527ad72761e0ad8209a9b5f9242fb3"
        )
        self.assertNotEqual(reviewer.RUNTIME_HEAD_SHA, historical.RUNTIME_HEAD_SHA)
        self.assertFalse(MANIFEST.match(historical.REVIEW_GLOB))

    def test_every_credit_durability_runtime_and_gate_claim_is_false(self):
        for name, value in sorted(self.review["claims"].items()):
            if name == "gate_claims":
                for gate, gate_value in sorted(value.items()):
                    self.assertIs(gate_value, False, gate)
            else:
                self.assertIs(value, False, name)

    def test_every_claim_mutation_is_rejected(self):
        for name in sorted(set(reviewer.EXPECTED_CLAIMS) - {"gate_claims"}):
            with self.subTest(claim=name):
                mutated = copy.deepcopy(self.review)
                mutated["claims"][name] = True
                with self.assertRaisesRegex(reviewer.BuildReviewV2Error, "bounded claims"):
                    reviewer.validate_review_object(mutated)
        for gate in sorted(reviewer.EXPECTED_GATE_CLAIMS):
            with self.subTest(gate=gate):
                mutated = copy.deepcopy(self.review)
                mutated["claims"]["gate_claims"][gate] = True
                with self.assertRaisesRegex(reviewer.BuildReviewV2Error, "bounded claims"):
                    reviewer.validate_review_object(mutated)

    def test_unknown_top_nested_and_claim_keys_are_rejected(self):
        mutations = []
        top = copy.deepcopy(self.review)
        top["unknown"] = False
        mutations.append(top)
        nested = copy.deepcopy(self.review)
        nested["verified_facts"]["kconfig_solver_matrix"]["unknown"] = False
        mutations.append(nested)
        claim = copy.deepcopy(self.review)
        claim["claims"]["invented"] = False
        mutations.append(claim)
        for mutation in mutations:
            with self.assertRaises(reviewer.BuildReviewV2Error):
                reviewer.validate_review_object(mutation)

    def test_boolean_as_integer_identities_are_rejected(self):
        paths = (
            ("source_artifact", "artifact", "id"),
            ("source_artifact", "artifact", "size"),
            ("source_artifact", "github", "run_id"),
            ("source_artifact", "github", "job_id"),
            ("artifact_closure", "entry_count"),
            ("verified_facts", "kconfig_solver_matrix", "case_count"),
        )
        for path in paths:
            with self.subTest(path=".".join(path)):
                mutated = copy.deepcopy(self.review)
                set_path(mutated, path, True)
                with self.assertRaises(reviewer.BuildReviewV2Error):
                    reviewer.validate_review_object(mutated)

    def test_run_job_artifact_head_and_tree_identities_are_pinned(self):
        mutations = (
            (("source_artifact", "artifact", "id"), 1),
            (("source_artifact", "artifact", "name"), "retargeted"),
            (("source_artifact", "artifact", "sha256"), "1" * 64),
            (("source_artifact", "github", "run_id"), 1),
            (("source_artifact", "github", "job_id"), 1),
            (("source_artifact", "github", "runtime_head_sha"), "1" * 40),
            (("runtime_candidate", "head_sha"), "1" * 40),
            (("runtime_candidate", "tree_sha"), "1" * 40),
        )
        for path, replacement in mutations:
            with self.subTest(path=".".join(path)):
                mutated = copy.deepcopy(self.review)
                set_path(mutated, path, replacement)
                with self.assertRaises(reviewer.BuildReviewV2Error):
                    reviewer.validate_review_object(mutated)

    def test_expiry_durability_and_remaining_prerequisites_are_immutable(self):
        mutations = []
        expiry = copy.deepcopy(self.review)
        expiry["source_artifact"]["expires_at"] = "2099-01-01T00:00:00Z"
        mutations.append(expiry)
        durable = copy.deepcopy(self.review)
        durable["source_artifact"]["durable_archive"] = True
        mutations.append(durable)
        removed = copy.deepcopy(self.review)
        removed["remaining_prerequisites"].pop()
        mutations.append(removed)
        reordered = copy.deepcopy(self.review)
        reordered["remaining_prerequisites"].reverse()
        mutations.append(reordered)
        for mutation in mutations:
            with self.assertRaises(reviewer.BuildReviewV2Error):
                reviewer.validate_review_object(mutation)

    def test_committed_input_order_mode_blob_digest_and_size_are_exact(self):
        mutations = []
        reordered = copy.deepcopy(self.review)
        reordered["runtime_candidate"]["committed_inputs"].reverse()
        mutations.append(reordered)
        for field, replacement in (
            ("mode", "100755"), ("git_blob_sha1", "1" * 40),
            ("sha256", "1" * 64), ("size", 1),
        ):
            changed = copy.deepcopy(self.review)
            changed["runtime_candidate"]["committed_inputs"][0][field] = replacement
            mutations.append(changed)
        for mutation in mutations:
            with self.assertRaisesRegex(reviewer.BuildReviewV2Error, "committed inputs"):
                reviewer.validate_review_object(mutation)

    def test_current_input_port_is_closed_and_preserves_every_ef58_record(self):
        policy = self.review["current_repository_input_policy"]
        self.assertEqual(policy["bound_input_count"], len(reviewer.EXPECTED_INPUTS))
        self.assertEqual(policy["current_override_count"], 9)
        self.assertEqual(policy["current_overrides"], reviewer.EXPECTED_CURRENT_OVERRIDES)
        self.assertIs(policy["historical_runtime_inputs_immutable"], True)
        self.assertIs(policy["require_head_index_worktree_equality"], True)
        self.assertIs(policy["runtime_identity_claimed"], False)
        self.assertEqual(
            [row["path"] for row in policy["current_overrides"]],
            [
                ".github/workflows/native-rust-host-modules-exact-build.yml",
                "host-kernel/kbuild/stage-manifest.json",
                "host-kernel/native-rust/abi/x86_64.rs",
                "host-kernel/native-rust/ihk.rs",
                "host-kernel/native-rust/ihk_smp_x86_64.rs",
                "scripts/rocky_rust_staging.py",
                "scripts/native_rust_kbuild_link_closure.py",
                "scripts/native_rust_kconfig_solver.py",
                "scripts/rocky_kernel_rk007_build_review.py",
            ],
        )
        for row in policy["current_overrides"]:
            runtime = reviewer.EXPECTED_INPUT_BY_PATH[row["path"]]
            self.assertEqual(row["runtime_git_blob_sha1"], runtime["git_blob_sha1"])
            self.assertEqual(row["runtime_sha256"], runtime["sha256"])
            self.assertEqual(row["runtime_size"], runtime["size"])
            self.assertEqual(row["mode"], runtime["mode"])

    def test_current_input_port_rejects_unknown_retargeted_or_weakened_records(self):
        mutations = []
        unknown = copy.deepcopy(self.review)
        unknown["current_repository_input_policy"]["unknown"] = False
        mutations.append(unknown)
        retargeted = copy.deepcopy(self.review)
        retargeted["current_repository_input_policy"]["current_overrides"][0][
            "runtime_sha256"
        ] = "1" * 64
        mutations.append(retargeted)
        weakened = copy.deepcopy(self.review)
        weakened["current_repository_input_policy"][
            "require_head_index_worktree_equality"
        ] = False
        mutations.append(weakened)
        for mutation in mutations:
            with self.assertRaises(reviewer.BuildReviewV2Error):
                reviewer.validate_review_object(mutation)

    def test_historical_module_oracle_source_record_is_exact_and_immutable(self):
        self.assertEqual(
            self.review["verified_facts"]["historical_oracle_source"],
            reviewer.EXPECTED_HISTORICAL_ORACLE_SOURCE,
        )
        for field, replacement in (
            ("git_blob_sha1", "1" * 40), ("mode", "100755"),
            ("sha256", "1" * 64), ("size", 1),
        ):
            with self.subTest(field=field):
                mutated = copy.deepcopy(self.review)
                mutated["verified_facts"]["historical_oracle_source"][field] = replacement
                with self.assertRaisesRegex(
                    reviewer.BuildReviewV2Error, "historical module-oracle source"
                ):
                    reviewer.validate_review_object(mutated)

    def test_current_repository_accepts_exact_reviewed_descendant(self):
        expected_head = reviewer.v1_review.run_git(
            REPO_ROOT, ["rev-parse", "HEAD"]
        ).stdout.decode("ascii").strip()
        self.assertEqual(
            reviewer.validate_repository(
                REPO_ROOT, reviewer.validate_review_object(copy.deepcopy(self.review))
            ),
            expected_head,
        )
    def test_repository_public_api_rejects_empty_or_altered_input_bindings(self):
        empty = copy.deepcopy(self.review)
        empty["runtime_candidate"]["committed_inputs"] = []
        altered = copy.deepcopy(self.review)
        altered["runtime_candidate"]["committed_inputs"][0]["sha256"] = "1" * 64
        for mutation in (empty, altered):
            with self.assertRaisesRegex(reviewer.BuildReviewV2Error, "committed inputs"):
                reviewer.validate_repository(REPO_ROOT, mutation)

    def test_repository_validation_ignores_git_redirection_environment(self):
        redirected = {
            "GIT_CONFIG_COUNT": "1", "GIT_CONFIG_KEY_0": "core.useReplaceRefs",
            "GIT_CONFIG_VALUE_0": "true", "GIT_DIR": "/not/the/repository",
            "GIT_INDEX_FILE": "/not/the/index", "GIT_NO_REPLACE_OBJECTS": "0",
            "GIT_WORK_TREE": "/not/the/worktree",
        }
        expected_head = reviewer.v1_review.run_git(
            REPO_ROOT, ["rev-parse", "HEAD"]
        ).stdout.decode("ascii").strip()
        with mock.patch.dict(os.environ, redirected, clear=False):
            self.assertEqual(
                reviewer.validate_repository(REPO_ROOT, copy.deepcopy(self.review)),
                expected_head,
            )
            for name, item in redirected.items():
                self.assertEqual(os.environ.get(name), item)
    def test_reused_modules_have_exact_repo_origins(self):
        expected = {
            "kconfig_policy": SCRIPTS / "native_rust_kconfig_policy.py",
            "kconfig_solver": SCRIPTS / "native_rust_kconfig_solver.py",
            "link_closure": SCRIPTS / "native_rust_kbuild_link_closure.py",
            "v1_review": SCRIPTS / "rocky_kernel_rk007_build_review.py",
        }
        self.assertEqual(
            reviewer.REUSED_MODULE_ORIGINS,
            dict((name, str(path.resolve())) for name, path in expected.items()),
        )
        self.assertEqual(
            reviewer.REUSED_MODULE_SOURCES,
            {
                "kconfig_policy": "repository-file",
                "kconfig_solver": (
                    "git-blob:8211d19c56c56368718fe1420937fd5187530773"
                ),
                "link_closure": (
                    "git-blob:8b571f2c122ae8a6102e8ed83129f584701feea2"
                ),
                "v1_review": "repository-file",
            },
        )

    def test_frozen_reused_module_blobs_are_rehashed_before_execution(self):
        cases = (
            (
                "_mckernel_rk007_v2_mutated_link_closure",
                "native_rust_kbuild_link_closure.py",
            ),
            (
                "_mckernel_rk007_v2_mutated_solver",
                "native_rust_kconfig_solver.py",
            ),
        )
        for module_name, file_name in cases:
            with self.subTest(file_name=file_name):
                with mock.patch.object(
                    reviewer, "_read_historical_blob", return_value=b"mutated"
                ):
                    with self.assertRaisesRegex(
                        reviewer.BuildReviewV2Error,
                        "frozen reused-module blob bytes differ",
                    ):
                        reviewer._load_exact_module(module_name, file_name)

    def test_hostile_pythonpath_scripts_package_cannot_hijack_reused_checkers(self):
        with tempfile.TemporaryDirectory() as temporary:
            package = Path(temporary) / "scripts"
            package.mkdir()
            (package / "__init__.py").write_text(
                "raise RuntimeError('foreign scripts package imported')\n"
            )
            for name in (
                "native_rust_kbuild_link_closure.py",
                "native_rust_kconfig_policy.py",
                "native_rust_kconfig_solver.py",
                "rocky_kernel_rk007_build_review.py",
            ):
                (package / name).write_text(
                    "raise RuntimeError('foreign reused checker imported')\n"
                )
            environment = dict(os.environ)
            environment["PYTHONPATH"] = temporary
            environment["PYTHONDONTWRITEBYTECODE"] = "1"
            completed = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPTS / "rocky_kernel_rk007_build_review_v2.py"),
                    "--repo", str(REPO_ROOT), "--check",
                ],
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=environment,
            )
        self.assertEqual(completed.returncode, 0)
        self.assertEqual(completed.stderr, b"")
        self.assertNotIn(b"foreign reused checker imported", completed.stdout)
        self.assertNotIn(b"foreign scripts package imported", completed.stdout)
    def test_duplicate_json_keys_and_noncanonical_json_are_rejected(self):
        with self.assertRaisesRegex(reviewer.BuildReviewV2Error, "duplicate JSON key"):
            reviewer.read_json_bytes(b'{"a":1,"a":2}\n', "duplicate")
        with self.assertRaisesRegex(reviewer.BuildReviewV2Error, "not canonical"):
            reviewer.read_json_bytes(b'{"b": 1}\n', "spaced", require_canonical=True)

    def test_safe_paths_reject_absolute_traversal_empty_backslash_and_nul(self):
        for value in ("/absolute", "../up", "a/../b", "a//b", "a\\b", "a\x00b", "."):
            with self.subTest(value=repr(value)):
                with self.assertRaises(reviewer.BuildReviewV2Error):
                    reviewer.safe_relative_path(value, "fixture")

    def test_checksum_parser_rejects_duplicate_unsorted_and_non_lf_rows(self):
        digest = "1" * 64
        cases = (
            ("duplicate", (digest + "  a\n" + digest + "  a\n").encode("ascii")),
            ("unsorted", (digest + "  b\n" + digest + "  a\n").encode("ascii")),
            ("crlf", (digest + "  a\r\n").encode("ascii")),
            ("no-lf", (digest + "  a").encode("ascii")),
        )
        for label, data in cases:
            with self.subTest(label=label):
                with self.assertRaises(reviewer.BuildReviewV2Error):
                    reviewer.parse_sum_manifest(data, label)

    def test_zip_reader_accepts_one_exact_safe_stored_regular_member(self):
        data = unix_zip([("member", b"value")])
        files, index = reviewer.read_zip_members(
            data, expected_paths=("member",), expected_flag_bits=0
        )
        self.assertEqual(files, {"member": b"value"})
        self.assertEqual(index[0]["mode"], "100644")

    def test_zip_reader_rejects_duplicate_and_unsafe_paths(self):
        cases = []
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", UserWarning)
            cases.append(unix_zip([("member", b"one"), ("member", b"two")]))
        cases.extend(
            [unix_zip([("../member", b"x")]), unix_zip([("/member", b"x")])]
        )
        for data in cases:
                with self.assertRaises(reviewer.BuildReviewV2Error):
                    reviewer.read_zip_members(
                        data, expected_paths=("member",), expected_flag_bits=0
                    )

    def test_zip_reader_rejects_symlink_executable_compression_and_comments(self):
        cases = (
            unix_zip([("member", b"x")], modes={"member": stat.S_IFLNK | 0o777}),
            unix_zip([("member", b"x")], modes={"member": stat.S_IFREG | 0o755}),
            unix_zip([("member", b"x" * 1024)], compression=zipfile.ZIP_DEFLATED),
            unix_zip([("member", b"x")], archive_comment=b"comment"),
        )
        for data in cases:
            with self.assertRaises(reviewer.BuildReviewV2Error):
                reviewer.read_zip_members(
                    data, expected_paths=("member",), expected_flag_bits=0
                )

    def test_real_shape_requires_data_descriptor_flag_and_rejects_zero_flag(self):
        data = self.artifact_path().read_bytes()
        files, index = reviewer.read_zip_members(data, expected_flag_bits=0x8)
        self.assertEqual(len(files), 48)
        self.assertEqual(set(row["flag_bits"] for row in index), {0x8})
        with self.assertRaisesRegex(reviewer.BuildReviewV2Error, "forbidden metadata"):
            reviewer.read_zip_members(data, expected_flag_bits=0)

    def test_local_header_flag_and_data_descriptor_are_independently_pinned(self):
        original = self.artifact_path().read_bytes()
        with zipfile.ZipFile(io.BytesIO(original)) as archive:
            info = archive.infolist()[0]
            local_flag_offset = info.header_offset + 6
            name_length, extra_length = struct.unpack_from(
                "<HH", original, info.header_offset + 26
            )
            descriptor_offset = (
                info.header_offset + 30 + name_length + extra_length
                + info.compress_size
            )
        local_mismatch = bytearray(original)
        struct.pack_into("<H", local_mismatch, local_flag_offset, 0)
        with self.assertRaisesRegex(reviewer.BuildReviewV2Error, "local/central flag"):
            reviewer.read_zip_members(bytes(local_mismatch), expected_flag_bits=0x8)

        bad_signature = bytearray(original)
        bad_signature[descriptor_offset] ^= 1
        with self.assertRaisesRegex(reviewer.BuildReviewV2Error, "data descriptor"):
            reviewer.read_zip_members(bytes(bad_signature), expected_flag_bits=0x8)

        bad_crc = bytearray(original)
        struct.pack_into("<I", bad_crc, descriptor_offset + 4, 0)
        with self.assertRaisesRegex(reviewer.BuildReviewV2Error, "data descriptor"):
            reviewer.read_zip_members(bytes(bad_crc), expected_flag_bits=0x8)

    def test_eocd_central_attributes_versions_and_local_metadata_are_pinned(self):
        original = self.artifact_path().read_bytes()
        with zipfile.ZipFile(io.BytesIO(original)) as archive:
            info = archive.infolist()[0]
            central = archive.start_dir
            header = info.header_offset
        mutations = []

        trailing = bytearray(original)
        trailing.extend(b"trailing")
        mutations.append(trailing)

        external = bytearray(original)
        old_external = struct.unpack_from("<I", external, central + 38)[0]
        struct.pack_into("<I", external, central + 38, old_external | 0x10)
        mutations.append(external)

        internal = bytearray(original)
        struct.pack_into("<H", internal, central + 36, 1)
        mutations.append(internal)

        create_version = bytearray(original)
        made_by = struct.unpack_from("<H", create_version, central + 4)[0]
        struct.pack_into("<H", create_version, central + 4, (made_by & 0xFF00) | 44)
        mutations.append(create_version)

        extract_version = bytearray(original)
        struct.pack_into("<H", extract_version, central + 6, 21)
        mutations.append(extract_version)

        local_version = bytearray(original)
        struct.pack_into("<H", local_version, header + 4, 21)
        mutations.append(local_version)

        local_time = bytearray(original)
        old_time = struct.unpack_from("<H", local_time, header + 10)[0]
        struct.pack_into("<H", local_time, header + 10, old_time ^ 1)
        mutations.append(local_time)

        local_date = bytearray(original)
        old_date = struct.unpack_from("<H", local_date, header + 12)[0]
        struct.pack_into("<H", local_date, header + 12, old_date ^ 1)
        mutations.append(local_date)

        for index, mutation in enumerate(mutations):
            with self.subTest(index=index):
                with self.assertRaises(reviewer.BuildReviewV2Error):
                    reviewer.read_zip_members(bytes(mutation), expected_flag_bits=0x8)

    def test_solver_hash_rebinding_does_not_accept_credit_or_oracle_mutation(self):
        unused, files = self.artifact_files()
        fact = copy.deepcopy(self.review["verified_facts"]["kconfig_solver_matrix"])
        document = json.loads(files["kconfig-solver-matrix.json"].decode("ascii"))
        mutations = []
        credited = copy.deepcopy(document)
        credited["claims"]["credit_eligible"] = True
        mutations.append(credited)
        wrong_case = copy.deepcopy(document)
        wrong_case["matrix"][53]["result"]["CONFIG_MCKERNEL_MCCTRL_RUST"] = "n"
        mutations.append(wrong_case)
        extra = copy.deepcopy(document)
        extra["matrix"][0]["unknown"] = False
        mutations.append(extra)
        rebound_seed = copy.deepcopy(document)
        rebound_seed["inputs"]["seed_config"]["sha256"] = "1" * 64
        mutations.append(rebound_seed)
        for mutation in mutations:
            data = reviewer.canonical_json_bytes(mutation)
            rebound = copy.deepcopy(fact)
            rebound["sha256"] = hashlib.sha256(data).hexdigest()
            rebound["size"] = len(data)
            with self.assertRaises(reviewer.BuildReviewV2Error):
                reviewer.verify_solver_report(
                    data, rebound, resolved_config=files["resolved.config"]
                )

    def test_solver_duplicate_key_survives_hash_rebind_but_is_rejected(self):
        unused, files = self.artifact_files()
        original = files["kconfig-solver-matrix.json"]
        data = original.replace(b'{"claims":{', b'{"claims":{},"claims":{', 1)
        fact = copy.deepcopy(self.review["verified_facts"]["kconfig_solver_matrix"])
        fact["sha256"] = hashlib.sha256(data).hexdigest()
        fact["size"] = len(data)
        with self.assertRaises(reviewer.BuildReviewV2Error):
            reviewer.verify_solver_report(
                data, fact, resolved_config=files["resolved.config"]
            )

    def test_solver_public_helper_requires_resolved_config_bytes(self):
        unused, files = self.artifact_files()
        fact = self.review["verified_facts"]["kconfig_solver_matrix"]
        with self.assertRaisesRegex(
            reviewer.BuildReviewV2Error, "configuration bytes are required"
        ):
            reviewer.verify_solver_report(
                files["kconfig-solver-matrix.json"], fact, resolved_config=None
            )

    def test_link_report_is_independently_regenerated_from_all_sixteen_records(self):
        unused, files = self.artifact_files()
        value = reviewer.verify_link_report(
            files, self.review["verified_facts"]["kbuild_link_closure"]
        )
        self.assertEqual(len(value["raw_records"]), 16)
        self.assertEqual(
            sum(name.endswith(".cmd") for name in value["raw_record_names"]), 13
        )
        self.assertEqual(
            sum(name.endswith(".mod") for name in value["raw_record_names"]), 3
        )

    def test_cmd_and_mod_mutations_are_rejected_by_independent_reparse(self):
        unused, files = self.artifact_files()
        for name, suffix in ((".ihk.o.cmd", b"# injected\n"), ("ihk.mod", b"extra.o\n")):
            with self.subTest(name=name):
                mutated = dict(files)
                mutated[name] = mutated[name] + suffix
                with self.assertRaises(reviewer.BuildReviewV2Error):
                    reviewer.verify_link_report(
                        mutated,
                        self.review["verified_facts"]["kbuild_link_closure"],
                    )

    def test_link_report_credit_mutation_is_rejected_after_digest_rebind(self):
        unused, files = self.artifact_files()
        document = json.loads(files["kbuild-link-closure.json"].decode("ascii"))
        document["claims"]["credit_eligible"] = True
        data = reviewer.canonical_json_bytes(document)
        mutated = dict(files)
        mutated["kbuild-link-closure.json"] = data
        fact = copy.deepcopy(self.review["verified_facts"]["kbuild_link_closure"])
        fact["sha256"] = hashlib.sha256(data).hexdigest()
        fact["size"] = len(data)
        with self.assertRaises(reviewer.BuildReviewV2Error):
            reviewer.verify_link_report(mutated, fact)

    def test_stage_lock_kbuild_kconfig_and_all_rust_bindings_cannot_be_rebound(self):
        unused, files = self.artifact_files()
        original = json.loads(files["stage-lock.json"].decode("ascii"))
        self.assertEqual(
            reviewer.verify_stage_lock_binding(files["stage-lock.json"])["files"],
            reviewer.EXPECTED_STAGE_FILE_RECORDS,
        )
        for path in reviewer.EXPECTED_STAGE_FILE_ORDER:
            with self.subTest(path=path):
                mutated = copy.deepcopy(original)
                record = next(row for row in mutated["files"] if row["path"] == path)
                record["sha256"] = "1" * 64
                data = reviewer.canonical_json_bytes(mutated)
                with self.assertRaisesRegex(
                    reviewer.BuildReviewV2Error,
                    "exact repository file bindings",
                ):
                    reviewer.verify_stage_lock_binding(data)

    def test_each_direct_module_byte_mutation_is_rejected(self):
        unused, files = self.artifact_files()
        for fact in reviewer.EXPECTED_MODULE_RECORDS:
            with self.subTest(module=fact["path"]):
                mutated = dict(files)
                binary = bytearray(mutated[fact["path"]])
                binary[-1] ^= 1
                mutated[fact["path"]] = bytes(binary)
                with self.assertRaises(reviewer.BuildReviewV2Error):
                    reviewer.verify_modules(mutated, reviewer.EXPECTED_MODULE_RECORDS)

    def test_module_target_and_built_lists_require_exact_lf_bytes(self):
        unused, files = self.artifact_files()
        reviewer.verify_exact_output_texts(files)
        for name in ("module-targets.txt", "built-module-artifacts.txt"):
            for mutation in (
                files[name].replace(b"\n", b"\r\n"), files[name].rstrip(b"\n")
            ):
                with self.subTest(name=name, size=len(mutation)):
                    changed = dict(files)
                    changed[name] = mutation
                    with self.assertRaises(reviewer.BuildReviewV2Error):
                        reviewer.verify_exact_output_texts(changed)

    def test_exact_fresh_artifact_verifies_when_materialized(self):
        result = reviewer.verify_artifact(
            self.artifact_path(), reviewer.validate_review_object(copy.deepcopy(self.review))
        )
        self.assertEqual(result["cmd_record_count"], 13)
        self.assertEqual(result["mod_record_count"], 3)
        self.assertEqual(result["module_count"], 3)
        self.assertEqual(result["kconfig_case_count"], 54)

    def test_outer_artifact_size_and_digest_are_exact(self):
        data = self.artifact_path().read_bytes()
        self.assertEqual(len(data), reviewer.ARTIFACT_SIZE)
        self.assertEqual(hashlib.sha256(data).hexdigest(), reviewer.ARTIFACT_SHA256)
        with self.assertRaisesRegex(reviewer.BuildReviewV2Error, "artifact size"):
            reviewer.verify_artifact_bytes(data + b"x", self.review)

    def test_cli_check_mode_accepts_exact_reviewed_descendant(self):
        completed = subprocess.run(
            [
                sys.executable, str(SCRIPTS / "rocky_kernel_rk007_build_review_v2.py"),
                "--repo", str(REPO_ROOT), "--check",
            ],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        )
        self.assertEqual(completed.returncode, 0)
        self.assertEqual(completed.stderr, b"")
        result = json.loads(completed.stdout.decode("ascii"))
        self.assertEqual(result["review_id"], reviewer.REVIEW_ID)
        self.assertFalse(result["claims"]["credit_eligible"])
    def test_checker_source_parses_as_python_3_6(self):
        source = (SCRIPTS / "rocky_kernel_rk007_build_review_v2.py").read_text()
        try:
            ast.parse(source, feature_version=(3, 6))
        except TypeError:
            ast.parse(source, feature_version=6)


if __name__ == "__main__":
    unittest.main()
