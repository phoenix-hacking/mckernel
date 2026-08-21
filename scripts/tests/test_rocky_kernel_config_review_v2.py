#!/usr/bin/env python3
"""Fail-closed tests for the independent RK-005 config v2 review."""

from __future__ import print_function

import ast
import copy
import hashlib
import importlib.util
import io
import json
import os
import stat
import subprocess
import sys
import tempfile
import unittest
import warnings
import zipfile
from pathlib import Path
from unittest import mock


REPO_ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = REPO_ROOT / "scripts/rocky_kernel_config_review_v2.py"
SPEC = importlib.util.spec_from_file_location(
    "rocky_kernel_config_review_v2", str(MODULE_PATH)
)
reviewer = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(reviewer)


def set_path(value, path, replacement):
    cursor = value
    for key in path[:-1]:
        cursor = cursor[key]
    cursor[path[-1]] = replacement


class UnseekableBuffer(object):
    """Force zipfile to emit the reviewed data-descriptor flag."""

    def __init__(self):
        self.buffer = io.BytesIO()

    def write(self, data):
        return self.buffer.write(data)

    def tell(self):
        return self.buffer.tell()

    def flush(self):
        return None

    def seek(self, *unused):
        raise OSError("fixture is intentionally unseekable")


def repack_artifact(source, replacements):
    with zipfile.ZipFile(str(source), "r") as archive:
        rows = [(info, archive.read(info)) for info in archive.infolist()]
    sink = UnseekableBuffer()
    with zipfile.ZipFile(sink, "w") as archive:
        for original, data in rows:
            info = zipfile.ZipInfo(original.filename, original.date_time)
            info.comment = original.comment
            info.compress_type = original.compress_type
            info.create_system = original.create_system
            info.external_attr = original.external_attr
            info.extra = original.extra
            archive.writestr(info, replacements.get(original.filename, data))
    return sink.buffer.getvalue()


class ConfigReviewV2Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.review_path = reviewer.discover_review(REPO_ROOT)
        cls.review = reviewer.load_review(cls.review_path)
        artifact = os.environ.get("MCKERNEL_RK005_CONFIG_V2_ARTIFACT")
        cls.artifact_path = Path(artifact).resolve() if artifact else None

    def test_checked_in_review_is_valid_and_credit_forbidden(self):
        value = reviewer.validate_review_object(copy.deepcopy(self.review))
        self.assertEqual(value["claims"], reviewer.EXPECTED_CLAIMS)
        self.assertFalse(value["claims"]["credit_eligible"])
        self.assertFalse(value["claims"]["durable_archive"])
        self.assertFalse(value["claims"]["offline_replay_proven"])
        self.assertFalse(value["claims"]["production_build_proven"])
        self.assertFalse(value["claims"]["tracker_credit"])

    def test_manifest_is_canonical_and_digest_pinned(self):
        data = self.review_path.read_bytes()
        self.assertEqual(hashlib.sha256(data).hexdigest(), reviewer.REVIEW_SHA256)
        self.assertEqual(data, reviewer.canonical_json_bytes(self.review))
        with tempfile.TemporaryDirectory() as temporary:
            mutated = copy.deepcopy(self.review)
            mutated["review_id"] = "retargeted"
            path = Path(temporary) / "mutated.json"
            path.write_bytes(reviewer.canonical_json_bytes(mutated))
            with self.assertRaisesRegex(
                reviewer.ConfigReviewV2Error, "manifest digest"
            ):
                reviewer.load_review(path)

    def test_review_discovery_rejects_external_and_symlinked_ancestor_paths(self):
        with tempfile.TemporaryDirectory() as temporary:
            temporary = Path(temporary)
            repository = temporary / "repository"
            external = temporary / "external"
            evidence = external / "evidence"
            (repository / "host-kernel/rocky").mkdir(parents=True)
            evidence.mkdir(parents=True)
            external_review = evidence / self.review_path.name
            external_review.write_bytes(self.review_path.read_bytes())

            with self.assertRaisesRegex(
                reviewer.ConfigReviewV2Error, "outside the repository"
            ):
                reviewer.discover_review(repository, external_review)

            os.symlink(
                str(evidence),
                str(repository / "host-kernel/rocky/evidence"),
            )
            with self.assertRaisesRegex(
                reviewer.ConfigReviewV2Error,
                "escapes the repository|traverses a symlink",
            ):
                reviewer.discover_review(repository)

            with self.assertRaisesRegex(
                reviewer.ConfigReviewV2Error,
                "escapes the repository|traverses a symlink",
            ):
                reviewer.discover_review(
                    repository,
                    Path("host-kernel/rocky/evidence") / self.review_path.name,
                )

    def test_historical_review_rejects_current_active_patch_inputs(self):
        value = reviewer.validate_review_object(copy.deepcopy(self.review))
        self.assertEqual(value["runtime_candidate"]["head_sha"], reviewer.RUNTIME_HEAD_SHA)
        self.assertFalse(
            value["current_repository_input_policy"]["runtime_identity_claimed"]
        )
        with self.assertRaisesRegex(
                reviewer.ConfigReviewV2Error, "worktree size differs"):
            reviewer.validate_repository(REPO_ROOT, value)

    def test_all_claim_promotions_are_rejected(self):
        scalar = (
            "credit_eligible",
            "durable_archive",
            "network_isolation_claimed",
            "offline_replay_proven",
            "production_build_config_bound",
            "production_build_proven",
            "runtime_identity_claimed",
            "tracker_credit",
        )
        for key in scalar:
            with self.subTest(key=key):
                mutated = copy.deepcopy(self.review)
                mutated["claims"][key] = True
                with self.assertRaisesRegex(reviewer.ConfigReviewV2Error, "claims"):
                    reviewer.validate_review_object(mutated)
        for gate in sorted(reviewer.EXPECTED_GATE_CLAIMS):
            with self.subTest(gate=gate):
                mutated = copy.deepcopy(self.review)
                mutated["claims"]["gate_claims"][gate] = True
                with self.assertRaisesRegex(reviewer.ConfigReviewV2Error, "claims"):
                    reviewer.validate_review_object(mutated)

    def test_durable_source_and_current_identity_promotions_are_rejected(self):
        mutated = copy.deepcopy(self.review)
        mutated["source_artifact"]["durable_archive"] = True
        with self.assertRaisesRegex(reviewer.ConfigReviewV2Error, "durable"):
            reviewer.validate_review_object(mutated)
        mutated = copy.deepcopy(self.review)
        mutated["current_repository_input_policy"]["runtime_identity_claimed"] = True
        with self.assertRaisesRegex(reviewer.ConfigReviewV2Error, "runtime claim"):
            reviewer.validate_review_object(mutated)

    def test_caveats_are_closed_exact_and_cannot_be_promoted(self):
        mutations = (
            ("archive_bytes_committed", True),
            ("artifact_retention_is_durable", True),
            ("independent_offline_replay_performed", True),
            ("raw_rustavailable_streams_archived", True),
            ("top_level_diagnostics_in_internal_manifests", True),
            ("top_level_diagnostics_bound_by_zip_sha256", False),
        )
        for key, replacement in mutations:
            with self.subTest(key=key):
                mutated = copy.deepcopy(self.review)
                mutated["caveats"][key] = replacement
                with self.assertRaisesRegex(reviewer.ConfigReviewV2Error, "caveats"):
                    reviewer.validate_review_object(mutated)
        mutated = copy.deepcopy(self.review)
        mutated["caveats"].pop("raw_rustavailable_streams_archived")
        with self.assertRaisesRegex(reviewer.ConfigReviewV2Error, "caveats"):
            reviewer.validate_review_object(mutated)

    def test_exact_run_job_artifact_head_tree_and_expiry_are_pinned(self):
        mutations = (
            (("source_artifact", "artifact", "id"), 1),
            (("source_artifact", "artifact", "name"), "retargeted"),
            (("source_artifact", "artifact", "archive_file_name"), "retargeted.zip"),
            (("source_artifact", "artifact", "size"), 1),
            (("source_artifact", "artifact", "sha256"), "0" * 64),
            (("source_artifact", "expires_at"), "2099-01-01T00:00:00Z"),
            (("source_artifact", "github", "job_id"), 1),
            (("source_artifact", "github", "run_attempt"), 2),
            (("source_artifact", "github", "run_id"), 1),
            (("source_artifact", "github", "runtime_head_sha"), "0" * 40),
            (("source_artifact", "github", "runtime_tree_sha"), "0" * 40),
            (("runtime_candidate", "head_sha"), "0" * 40),
            (("runtime_candidate", "tree_sha"), "0" * 40),
        )
        for path, replacement in mutations:
            with self.subTest(path=".".join(path)):
                mutated = copy.deepcopy(self.review)
                set_path(mutated, path, replacement)
                with self.assertRaises(reviewer.ConfigReviewV2Error):
                    reviewer.validate_review_object(mutated)

    def test_boolean_integer_coercions_are_rejected(self):
        paths = (
            ("current_repository_input_policy", "bound_input_count"),
            ("source_artifact", "artifact", "id"),
            ("source_artifact", "artifact", "size"),
            ("source_artifact", "github", "job_id"),
            ("source_artifact", "github", "run_attempt"),
            ("source_artifact", "github", "run_id"),
            ("source_artifact", "retention_days"),
            ("verified_facts", "delta", "baseline_to_control", "total_count"),
            ("verified_facts", "delta", "control_to_resolved", "presence_count"),
            ("zip_closure", "entry_count"),
        )
        for path in paths:
            with self.subTest(path=".".join(path)):
                mutated = copy.deepcopy(self.review)
                set_path(mutated, path, True)
                with self.assertRaises(reviewer.ConfigReviewV2Error):
                    reviewer.validate_review_object(mutated)

    def test_committed_inputs_reject_empty_missing_reorder_and_retarget(self):
        mutated = copy.deepcopy(self.review)
        mutated["runtime_candidate"]["committed_inputs"] = []
        with self.assertRaisesRegex(reviewer.ConfigReviewV2Error, "committed inputs"):
            reviewer.validate_review_object(mutated)
        mutated = copy.deepcopy(self.review)
        mutated["runtime_candidate"]["committed_inputs"].pop()
        with self.assertRaisesRegex(reviewer.ConfigReviewV2Error, "committed inputs"):
            reviewer.validate_review_object(mutated)
        mutated = copy.deepcopy(self.review)
        mutated["runtime_candidate"]["committed_inputs"].reverse()
        with self.assertRaisesRegex(reviewer.ConfigReviewV2Error, "committed inputs"):
            reviewer.validate_review_object(mutated)
        mutated = copy.deepcopy(self.review)
        mutated["runtime_candidate"]["committed_inputs"][0]["path"] = (
            "host-kernel/rocky/config-policy-v2.json"
        )
        with self.assertRaisesRegex(reviewer.ConfigReviewV2Error, "committed inputs"):
            reviewer.validate_review_object(mutated)

    def test_patch_authority_rejects_empty_missing_duplicate_and_reorder(self):
        for operation in ("empty", "missing", "duplicate", "reorder"):
            with self.subTest(operation=operation):
                mutated = copy.deepcopy(self.review)
                patches = mutated["verified_facts"]["patch_authority"]["patches"]
                if operation == "empty":
                    patches[:] = []
                elif operation == "missing":
                    patches.pop()
                elif operation == "duplicate":
                    patches[-1] = copy.deepcopy(patches[0])
                else:
                    patches.reverse()
                with self.assertRaises(reviewer.ConfigReviewV2Error):
                    reviewer.validate_review_object(mutated)

    def test_exact_six_blockers_reject_removal_reorder_addition_and_rewording(self):
        operations = (
            lambda rows: rows.pop(),
            lambda rows: rows.reverse(),
            lambda rows: rows.append("Everything is complete."),
            lambda rows: rows.__setitem__(0, "No remaining RK-003 blocker."),
        )
        for operation in operations:
            mutated = copy.deepcopy(self.review)
            operation(mutated["remaining_prerequisites"])
            with self.assertRaisesRegex(
                reviewer.ConfigReviewV2Error, "remaining prerequisites"
            ):
                reviewer.validate_review_object(mutated)

    def test_config_facts_and_delta_counts_are_exact(self):
        mutations = (
            (("verified_facts", "configurations", "baseline", "symbol_count"), 1),
            (("verified_facts", "configurations", "control", "line_count"), 1),
            (("verified_facts", "configurations", "resolved", "sha256"), "0" * 64),
            (("verified_facts", "delta", "baseline_to_control", "semantic_count"), 1732),
            (("verified_facts", "delta", "baseline_to_control", "presence_count"), 1150),
            (("verified_facts", "delta", "control_to_resolved", "total_count"), 12),
            (("verified_facts", "delta", "control_to_resolved", "semantic_count"), 4),
        )
        for path, replacement in mutations:
            with self.subTest(path=".".join(path)):
                mutated = copy.deepcopy(self.review)
                set_path(mutated, path, replacement)
                with self.assertRaises(reviewer.ConfigReviewV2Error):
                    reviewer.validate_review_object(mutated)

    def test_delta_categories_reject_empty_overlap_and_generated_retarget(self):
        mutated = copy.deepcopy(self.review)
        mutated["verified_facts"]["delta"]["requested_changes"] = []
        with self.assertRaises(reviewer.ConfigReviewV2Error):
            reviewer.validate_review_object(mutated)
        mutated = copy.deepcopy(self.review)
        mutated["verified_facts"]["delta"]["representation_changes"][0] = copy.deepcopy(
            mutated["verified_facts"]["delta"]["requested_changes"][0]
        )
        with self.assertRaises(reviewer.ConfigReviewV2Error):
            reviewer.validate_review_object(mutated)
        mutated = copy.deepcopy(self.review)
        mutated["verified_facts"]["delta"]["generated_symbol_results"][
            "CONFIG_RUSTC_HAS_UNNECESSARY_TRANSMUTES"
        ] = "n"
        with self.assertRaises(reviewer.ConfigReviewV2Error):
            reviewer.validate_review_object(mutated)

    def test_dependency_and_warning_policy_facts_are_exact(self):
        mutated = copy.deepcopy(self.review)
        mutated["verified_facts"]["dependency_assertions"][
            "preservation_group_counts"
        ].pop("warning_policy")
        with self.assertRaises(reviewer.ConfigReviewV2Error):
            reviewer.validate_review_object(mutated)
        mutated = copy.deepcopy(self.review)
        mutated["verified_facts"]["dependency_assertions"]["dependency_count"] = 10
        with self.assertRaises(reviewer.ConfigReviewV2Error):
            reviewer.validate_review_object(mutated)

    def test_tool_probe_facts_reject_llvm_owner_path_and_missing_probe(self):
        mutations = (
            lambda probes: probes.pop("rustc"),
            lambda probes: probes["llvm"].__setitem__("owner", "llvm-0:21.1.8-1.el10.x86_64"),
            lambda probes: probes["llvm"].__setitem__("path", "/usr/bin/llvm-config-21"),
            lambda probes: probes["rustc"].__setitem__("stdout_sha256", "0" * 64),
        )
        for operation in mutations:
            mutated = copy.deepcopy(self.review)
            operation(mutated["verified_facts"]["tool_probes"])
            with self.assertRaises(reviewer.ConfigReviewV2Error):
                reviewer.validate_review_object(mutated)

    def test_safe_relative_paths_reject_ambiguous_or_escaping_names(self):
        unsafe = (
            "/absolute",
            "../escape",
            "a/../escape",
            "a//b",
            "a\\b",
            "./a",
            "a/./b",
            "a\x00b",
            "",
        )
        for value in unsafe:
            with self.subTest(value=value):
                with self.assertRaises(reviewer.ConfigReviewV2Error):
                    reviewer.safe_relative_path(value, "fixture")
        self.assertEqual(
            reviewer.safe_relative_path("capture/file", "fixture"),
            "capture/file",
        )

    def test_repository_file_rejects_symlinked_ancestors_and_leaf(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "repo"
            root.mkdir()
            normal = root / "normal"
            normal.write_bytes(b"bound\n")
            self.assertEqual(reviewer.repository_file(root, "normal", "fixture"), normal)
            outside = Path(temporary) / "outside"
            outside.mkdir()
            (outside / "input").write_bytes(b"bound\n")
            os.symlink(str(outside), str(root / "linked"))
            with self.assertRaisesRegex(
                reviewer.ConfigReviewV2Error,
                "escapes the repository|traverses a symlink",
            ):
                reviewer.repository_file(root, "linked/input", "fixture")
            os.symlink(str(outside / "input"), str(root / "leaf"))
            with self.assertRaises(reviewer.ConfigReviewV2Error):
                reviewer.repository_file(root, "leaf", "fixture")

    def test_duplicate_json_keys_and_noncanonical_json_are_rejected(self):
        with self.assertRaisesRegex(reviewer.ConfigReviewV2Error, "duplicate JSON key"):
            reviewer.read_json_bytes(b'{"a":1,"a":2}\n', "fixture")
        with self.assertRaisesRegex(reviewer.ConfigReviewV2Error, "not canonical"):
            reviewer.read_json_bytes(b'{ "a": 1 }\n', "fixture", require_canonical=True)
        self.assertEqual(
            reviewer.read_json_bytes(b'{"a":1}\n', "fixture", require_canonical=True),
            {"a": 1},
        )

    def test_sha256sums_requires_exact_nonempty_order_and_digests(self):
        good = b"".join(
            (
                "{}  {}\n".format(reviewer.EXPECTED_CHECKSUM_DIGESTS[name], name)
            ).encode("ascii")
            for name in reviewer.EXPECTED_CHECKSUM_NAMES
        )
        parsed = reviewer.parse_sha256sums(good)
        self.assertEqual(parsed, reviewer.EXPECTED_CHECKSUM_DIGESTS)
        with self.assertRaises(reviewer.ConfigReviewV2Error):
            reviewer.parse_sha256sums(b"")
        with self.assertRaisesRegex(reviewer.ConfigReviewV2Error, "checksum paths"):
            reviewer.parse_sha256sums(b"".join(reversed(good.splitlines(True))))
        duplicate = good + good.splitlines(True)[0]
        with self.assertRaisesRegex(reviewer.ConfigReviewV2Error, "duplicate"):
            reviewer.parse_sha256sums(duplicate)
        changed = good.replace(reviewer.BASELINE_CONFIG_SHA256.encode("ascii"), b"0" * 64, 1)
        with self.assertRaisesRegex(reviewer.ConfigReviewV2Error, "checksum digests"):
            reviewer.parse_sha256sums(changed)

    def test_config_parser_preserves_absence_and_recomputes_partitions(self):
        before = reviewer.parse_config(
            b"CONFIG_A=y\n# CONFIG_B is not set\nCONFIG_C=y\n", "before"
        )
        after = reviewer.parse_config(
            b"# CONFIG_A is not set\n# CONFIG_B is not set\n# CONFIG_D is not set\n",
            "after",
        )
        rows = reviewer.changed_symbols(before, after)
        self.assertEqual(
            rows,
            [
                {"after": "n", "before": "y", "symbol": "CONFIG_A"},
                {"after": "<absent>", "before": "y", "symbol": "CONFIG_C"},
                {"after": "n", "before": "<absent>", "symbol": "CONFIG_D"},
            ],
        )
        semantic, presence = reviewer.partition_changes(rows)
        self.assertEqual(len(semantic), 2)
        self.assertEqual(presence, [rows[2]])
        self.assertEqual(reviewer.semantic_config_value("<absent>"), "n")

    def test_config_parser_rejects_duplicate_empty_and_malformed_inputs(self):
        with self.assertRaisesRegex(reviewer.ConfigReviewV2Error, "duplicates"):
            reviewer.parse_config(b"CONFIG_RUST=y\nCONFIG_RUST=n\n", "duplicate")
        with self.assertRaisesRegex(reviewer.ConfigReviewV2Error, "contains no"):
            reviewer.parse_config(b"# ordinary comment\n", "empty")
        with self.assertRaisesRegex(reviewer.ConfigReviewV2Error, "malformed row"):
            reviewer.parse_config(b"CONFIG_RUST=y\nTHIS IS MALFORMED\n", "malformed")
        for malformed_comment in (
            b"# CONFIG_HIDDEN is not sett\n",
            b"# CONFIG_HIDDEN=y\n",
            b"# CONFIG_ HIDDEN\n",
        ):
            with self.assertRaisesRegex(
                reviewer.ConfigReviewV2Error, "malformed config comment"
            ):
                reviewer.parse_config(malformed_comment, "malformed comment")
        with self.assertRaisesRegex(reviewer.ConfigReviewV2Error, "malformed assignment"):
            reviewer.parse_config(b"CONFIG_RUST=\n", "empty assignment")
        with self.assertRaisesRegex(reviewer.ConfigReviewV2Error, "malformed assignment"):
            reviewer.parse_config(b"CONFIG_RUST=y # injected\n", "injected assignment")
        with self.assertRaisesRegex(reviewer.ConfigReviewV2Error, "control"):
            reviewer.parse_config(b"CONFIG_RUST=y\r\n", "CRLF config")
        for controlled in (
            b'CONFIG_A="x\x01y"\n',
            b"# ordinary\tcomment\n",
            b'CONFIG_A="x\x7fy"\n',
            "# ordinary\u2028comment\n".encode("utf-8"),
        ):
            with self.assertRaisesRegex(reviewer.ConfigReviewV2Error, "control"):
                reviewer.parse_config(controlled, "controlled config")
        with self.assertRaisesRegex(reviewer.ConfigReviewV2Error, "final newline"):
            reviewer.parse_config(b"CONFIG_RUST=y", "unterminated")

    def test_zip_builder_rejects_unsafe_symlink_extra_and_empty_archives(self):
        with tempfile.TemporaryDirectory() as temporary:
            temporary = Path(temporary)
            unsafe = temporary / "unsafe.zip"
            with zipfile.ZipFile(str(unsafe), "w") as stream:
                info = zipfile.ZipInfo("../escape")
                info.external_attr = (stat.S_IFREG | 0o400) << 16
                stream.writestr(info, b"data")
            with zipfile.ZipFile(str(unsafe), "r") as stream:
                with self.assertRaises(reviewer.ConfigReviewV2Error):
                    reviewer.zip_entry_records(stream)

            linked = temporary / "linked.zip"
            with zipfile.ZipFile(str(linked), "w") as stream:
                info = zipfile.ZipInfo("capture/link")
                info.external_attr = (stat.S_IFLNK | 0o777) << 16
                stream.writestr(info, b"target")
            with zipfile.ZipFile(str(linked), "r") as stream:
                with self.assertRaisesRegex(reviewer.ConfigReviewV2Error, "regular"):
                    reviewer.zip_entry_records(stream)

            extra = temporary / "extra.zip"
            with zipfile.ZipFile(str(extra), "w") as stream:
                info = zipfile.ZipInfo("capture/file")
                info.external_attr = ((stat.S_IFREG | 0o400) << 16) | 0x20
                info.extra = b"\x01\x00\x00\x00"
                stream.writestr(info, b"data")
            with zipfile.ZipFile(str(extra), "r") as stream:
                with self.assertRaisesRegex(reviewer.ConfigReviewV2Error, "extra"):
                    reviewer.zip_entry_records(stream)

            empty = temporary / "empty.zip"
            with zipfile.ZipFile(str(empty), "w"):
                pass
            with zipfile.ZipFile(str(empty), "r") as stream:
                with self.assertRaisesRegex(reviewer.ConfigReviewV2Error, "no entries"):
                    reviewer.zip_entry_records(stream)

    def test_zip_duplicate_paths_are_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "duplicate.zip"
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", UserWarning)
                with zipfile.ZipFile(str(path), "w") as stream:
                    for data in (b"first", b"second"):
                        info = zipfile.ZipInfo("capture/file")
                        info.external_attr = ((stat.S_IFREG | 0o400) << 16) | 0x20
                        stream.writestr(info, data)
            with zipfile.ZipFile(str(path), "r") as stream:
                with self.assertRaises(reviewer.ConfigReviewV2Error):
                    reviewer.zip_entry_records(stream)

    def test_environment_document_rejects_probe_and_type_mutations(self):
        if self.artifact_path is None:
            self.skipTest("MCKERNEL_RK005_CONFIG_V2_ARTIFACT is not set")
        with zipfile.ZipFile(str(self.artifact_path), "r") as stream:
            environment = reviewer.read_json_bytes(
                stream.read("capture/environment.json"),
                "environment",
                require_canonical=True,
            )
        identity = {
            "head_sha": reviewer.RUNTIME_HEAD_SHA,
            "repository": reviewer.GITHUB_REPOSITORY,
            "run_attempt": reviewer.GITHUB_RUN_ATTEMPT,
            "run_id": reviewer.GITHUB_RUN_ID,
        }
        reviewer.verify_environment_document(environment, self.review, identity)
        operations = (
            lambda value: value["probes"].pop("rustc"),
            lambda value: value["probes"]["derived"].__setitem__("rustc_version", True),
            lambda value: value["probes"]["llvm"].__setitem__("binary_path", "/usr/bin/llvm-config-21"),
            lambda value: value["probes"]["llvm"].__setitem__("package_nevra", "llvm-0:21.1.8-1.el10.x86_64"),
            lambda value: value["fixed_environment"].__setitem__("UNREVIEWED", "1"),
        )
        for operation in operations:
            mutated = copy.deepcopy(environment)
            operation(mutated)
            with self.assertRaises(reviewer.ConfigReviewV2Error):
                reviewer.verify_environment_document(mutated, self.review, identity)

    def test_commands_document_rejects_empty_bool_retarget_and_patch_mutations(self):
        if self.artifact_path is None:
            self.skipTest("MCKERNEL_RK005_CONFIG_V2_ARTIFACT is not set")
        with zipfile.ZipFile(str(self.artifact_path), "r") as stream:
            commands = reviewer.read_json_bytes(
                stream.read("capture/commands.json"), "commands", require_canonical=True
            )
        reviewer.verify_commands_document(commands, self.review)
        operations = (
            lambda value: value.__setitem__("passes", []),
            lambda value: value["passes"][0]["requested_rustavailable"].__setitem__("exit_code", True),
            lambda value: value["passes"][0]["requested_rustavailable"].__setitem__("success_line_count", True),
            lambda value: value["passes"][0]["requested_rustavailable"].__setitem__("stdout_sha256", "0" * 64),
            lambda value: value["passes"][1]["source_cleanup"].__setitem__(2, value["passes"][0]["source_cleanup"][2]),
            lambda value: value["patches"].pop(),
        )
        for operation in operations:
            mutated = copy.deepcopy(commands)
            operation(mutated)
            with self.assertRaises(reviewer.ConfigReviewV2Error):
                reviewer.verify_commands_document(mutated, self.review)

    def test_exact_artifact_verifies_full_closure_when_supplied(self):
        if self.artifact_path is None:
            self.skipTest("MCKERNEL_RK005_CONFIG_V2_ARTIFACT is not set")
        value = reviewer.validate_review_object(copy.deepcopy(self.review))
        result = reviewer.verify_artifact(self.artifact_path, value)
        self.assertEqual(result["artifact_sha256"], reviewer.ARTIFACT_SHA256)
        self.assertEqual(result["resolved_config_sha256"], reviewer.RESOLVED_CONFIG_SHA256)

    def test_single_byte_artifact_mutation_is_rejected(self):
        if self.artifact_path is None:
            self.skipTest("MCKERNEL_RK005_CONFIG_V2_ARTIFACT is not set")
        data = bytearray(self.artifact_path.read_bytes())
        data[len(data) // 2] ^= 1
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "mutated.zip"
            path.write_bytes(bytes(data))
            with self.assertRaisesRegex(reviewer.ConfigReviewV2Error, "artifact digest"):
                reviewer.verify_artifact(path, self.review)

    def test_retargeted_zip_digest_cannot_hide_internal_content_mutation(self):
        if self.artifact_path is None:
            self.skipTest("MCKERNEL_RK005_CONFIG_V2_ARTIFACT is not set")
        with zipfile.ZipFile(str(self.artifact_path), "r") as archive:
            blockers = archive.read("capture/blockers.json")
        self.assertIn(b"remain false", blockers)
        mutated_blockers = blockers.replace(b"remain false", b"remain true!", 1)
        data = repack_artifact(
            self.artifact_path,
            {"capture/blockers.json": mutated_blockers},
        )
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "retargeted.zip"
            path.write_bytes(data)
            with zipfile.ZipFile(str(path), "r") as archive:
                records = reviewer.zip_entry_records(archive)
            mutated_review = copy.deepcopy(self.review)
            mutated_review["source_artifact"]["artifact"]["size"] = len(data)
            mutated_review["source_artifact"]["artifact"]["sha256"] = (
                reviewer.sha256_bytes(data)
            )
            mutated_review["zip_closure"]["entry_index_sha256"] = (
                reviewer.sha256_bytes(reviewer.canonical_json_bytes(records))
            )
            with self.assertRaisesRegex(
                reviewer.ConfigReviewV2Error, "checksum blockers.json"
            ):
                reviewer.verify_artifact(path, mutated_review)

    def test_cli_check_fails_closed_for_historical_input_binding(self):
        environment = dict(os.environ)
        environment["PYTHONDONTWRITEBYTECODE"] = "1"
        completed = subprocess.run(
            [sys.executable, str(MODULE_PATH), "--repo", str(REPO_ROOT), "--check"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=environment,
        )
        self.assertEqual(completed.returncode, 2)
        self.assertEqual("", completed.stdout.decode("utf-8"))
        self.assertIn("worktree size differs", completed.stderr.decode("utf-8"))

    def test_reviewer_and_tests_parse_as_python_3_6(self):
        for path in (MODULE_PATH, Path(__file__).resolve()):
            source = path.read_text(encoding="utf-8")
            try:
                ast.parse(source, filename=str(path), feature_version=(3, 6))
            except TypeError:
                try:
                    ast.parse(source, filename=str(path), feature_version=6)
                except TypeError:
                    ast.parse(source, filename=str(path))

    def test_cli_verify_artifact_when_supplied(self):
        if self.artifact_path is None:
            self.skipTest("MCKERNEL_RK005_CONFIG_V2_ARTIFACT is not set")
        environment = dict(os.environ)
        environment["PYTHONDONTWRITEBYTECODE"] = "1"
        completed = subprocess.run(
            [
                sys.executable,
                str(MODULE_PATH),
                "--repo",
                str(REPO_ROOT),
                "--verify-artifact",
                str(self.artifact_path),
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=environment,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr.decode("utf-8"))
        self.assertIn("all credit claims remain false", completed.stdout.decode("utf-8"))

    def test_cli_verify_artifact_rejects_leaf_and_ancestor_symlinks(self):
        if self.artifact_path is None:
            self.skipTest("MCKERNEL_RK005_CONFIG_V2_ARTIFACT is not set")
        environment = dict(os.environ)
        environment["PYTHONDONTWRITEBYTECODE"] = "1"
        with tempfile.TemporaryDirectory() as temporary:
            temporary = Path(temporary)
            leaf = temporary / "artifact.zip"
            leaf.symlink_to(self.artifact_path)
            ancestor = temporary / "artifact-parent"
            ancestor.symlink_to(self.artifact_path.parent, target_is_directory=True)
            for candidate in (leaf, ancestor / self.artifact_path.name):
                completed = subprocess.run(
                    [
                        sys.executable,
                        str(MODULE_PATH),
                        "--repo",
                        str(REPO_ROOT),
                        "--verify-artifact",
                        str(candidate),
                    ],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    env=environment,
                )
                self.assertEqual(completed.returncode, 2)
                self.assertIn("traverses a symlink", completed.stderr.decode("utf-8"))

    def test_cli_verify_artifact_rejects_symlink_dotdot_path_confusion(self):
        if self.artifact_path is None:
            self.skipTest("MCKERNEL_RK005_CONFIG_V2_ARTIFACT is not set")
        environment = dict(os.environ)
        environment["PYTHONDONTWRITEBYTECODE"] = "1"
        with tempfile.TemporaryDirectory() as temporary:
            temporary = Path(temporary)
            (temporary / "artifact.zip").write_bytes(self.artifact_path.read_bytes())
            alias = temporary / "alias"
            alias.symlink_to(Path("/var"), target_is_directory=True)
            candidate = str(alias) + "/../artifact.zip"
            completed = subprocess.run(
                [
                    sys.executable,
                    str(MODULE_PATH),
                    "--repo",
                    str(REPO_ROOT),
                    "--verify-artifact",
                    candidate,
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=environment,
            )
            self.assertEqual(completed.returncode, 2)
            self.assertIn("path is unsafe", completed.stderr.decode("utf-8"))

    def test_verifier_parses_the_same_artifact_bytes_it_hashes(self):
        if self.artifact_path is None:
            self.skipTest("MCKERNEL_RK005_CONFIG_V2_ARTIFACT is not set")
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "artifact.zip"
            path.write_bytes(self.artifact_path.read_bytes())
            original_read_bytes = Path.read_bytes

            def read_then_replace(candidate):
                data = original_read_bytes(candidate)
                candidate.write_bytes(b"replacement is not the reviewed ZIP")
                return data

            with mock.patch.object(Path, "read_bytes", read_then_replace):
                result = reviewer.verify_artifact(path, self.review)
            self.assertEqual(result["artifact_sha256"], reviewer.ARTIFACT_SHA256)
            self.assertEqual(path.read_bytes(), b"replacement is not the reviewed ZIP")


if __name__ == "__main__":
    unittest.main()
