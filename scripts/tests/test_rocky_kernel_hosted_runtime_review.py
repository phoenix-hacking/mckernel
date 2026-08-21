#!/usr/bin/env python3
"""Fail-closed tests for the exact-head hosted Rocky runtime review."""

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
import tarfile
import tempfile
import unittest
import warnings
import zipfile
from pathlib import Path
from unittest import mock


REPO_ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = REPO_ROOT / "scripts/rocky_kernel_hosted_runtime_review.py"
SPEC = importlib.util.spec_from_file_location("rocky_kernel_hosted_runtime_review", str(MODULE_PATH))
reviewer = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(reviewer)


def set_path(value, path, replacement):
    cursor = value
    for key in path[:-1]:
        cursor = cursor[key]
    cursor[path[-1]] = replacement


def regular_zip_info(name):
    info = zipfile.ZipInfo(name)
    info.create_system = 3
    info.external_attr = (stat.S_IFREG | 0o644) << 16
    return info


def make_tar(members):
    output = io.BytesIO()
    with tarfile.open(fileobj=output, mode="w") as archive:
        for name, kind, data in members:
            info = tarfile.TarInfo(name)
            info.uid = 1000
            info.gid = 1000
            info.mode = 0o700 if kind == "directory" else 0o644
            if kind == "directory":
                info.type = tarfile.DIRTYPE
                archive.addfile(info)
            elif kind == "symlink":
                info.type = tarfile.SYMTYPE
                info.linkname = "target"
                archive.addfile(info)
            else:
                info.type = tarfile.REGTYPE
                info.size = len(data)
                archive.addfile(info, io.BytesIO(data))
    return output.getvalue()


class HostedRuntimeReviewTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.review_path = reviewer.discover_review(REPO_ROOT)
        cls.review = reviewer.load_review(cls.review_path)
        artifact = os.environ.get("MCKERNEL_HOSTED_RUNTIME_ARTIFACT")
        cls.artifact_path = Path(artifact) if artifact else None

    def test_checked_in_review_is_closed_bounded_and_valid(self):
        checked = reviewer.validate_review_object(copy.deepcopy(self.review))
        self.assertEqual(checked["claims"], reviewer.EXPECTED_CLAIMS)
        self.assertEqual(checked["caveats"], reviewer.EXPECTED_CAVEATS)
        self.assertFalse(checked["source_artifact"]["durable_archive"])
        self.assertIn(reviewer.ARTIFACT_EXPIRES_AT, checked["remaining_prerequisites"][0])

    def test_manifest_is_canonical_and_digest_locked(self):
        data = self.review_path.read_bytes()
        self.assertEqual(hashlib.sha256(data).hexdigest(), reviewer.REVIEW_SHA256)
        self.assertEqual(data, reviewer.canonical_json_bytes(self.review))
        with tempfile.TemporaryDirectory() as temporary:
            mutated = copy.deepcopy(self.review)
            mutated["source_artifact"]["artifact"]["id"] = 9309472207
            path = Path(temporary) / "review.json"
            path.write_bytes(reviewer.canonical_json_bytes(mutated))
            path.chmod(reviewer.REVIEW_MODE)
            with self.assertRaisesRegex(reviewer.HostedRuntimeReviewError, "manifest digest"):
                reviewer.load_review(path)

    def test_manifest_mode_is_exact(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "review.json"
            path.write_bytes(self.review_path.read_bytes())
            path.chmod(0o600)
            with self.assertRaisesRegex(reviewer.HostedRuntimeReviewError, "manifest mode"):
                reviewer.load_review(path)

    def test_manifest_leaf_and_ancestor_swaps_fail_closed(self):
        cases = ("leaf", "ancestor")
        for case in cases:
            with self.subTest(case=case), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                evidence = root / "repo/host-kernel/rocky/evidence"
                evidence.mkdir(parents=True)
                manifest = evidence / self.review_path.name
                manifest.write_bytes(self.review_path.read_bytes())
                manifest.chmod(reviewer.REVIEW_MODE)
                external = root / "external"
                external.mkdir()
                external_manifest = external / self.review_path.name
                external_manifest.write_bytes(self.review_path.read_bytes())
                external_manifest.chmod(reviewer.REVIEW_MODE)
                discovered = reviewer.discover_review(root / "repo")
                original_read = reviewer.read_descriptor_bytes
                swapped = {"value": False}

                def swapping_read(descriptor, expected_size, label):
                    data = original_read(descriptor, expected_size, label)
                    if case == "leaf":
                        manifest.rename(evidence / (manifest.name + ".held"))
                        manifest.symlink_to(external_manifest)
                    else:
                        evidence.rename(evidence.parent / "evidence-held")
                        evidence.symlink_to(external, target_is_directory=True)
                    swapped["value"] = True
                    return data

                with mock.patch.object(
                    reviewer, "read_descriptor_bytes", side_effect=swapping_read
                ):
                    with self.assertRaisesRegex(
                        reviewer.HostedRuntimeReviewError, "identity replay"
                    ):
                        reviewer.load_review(discovered)
                self.assertTrue(swapped["value"])

    def test_duplicate_json_keys_are_rejected(self):
        with self.assertRaisesRegex(reviewer.HostedRuntimeReviewError, "duplicate JSON key"):
            reviewer.read_json_bytes(b'{"a":1,"a":2}\n', "duplicate")

    def test_every_claim_and_added_true_claim_are_rejected(self):
        for claim in sorted(set(reviewer.EXPECTED_CLAIMS) - {"gate_claims"}):
            with self.subTest(claim=claim):
                mutated = copy.deepcopy(self.review)
                mutated["claims"][claim] = True
                with self.assertRaisesRegex(reviewer.HostedRuntimeReviewError, "bounded claims"):
                    reviewer.validate_review_object(mutated)
        for gate in sorted(reviewer.EXPECTED_GATE_CLAIMS):
            with self.subTest(gate=gate):
                mutated = copy.deepcopy(self.review)
                mutated["claims"]["gate_claims"][gate] = True
                with self.assertRaisesRegex(reviewer.HostedRuntimeReviewError, "bounded claims"):
                    reviewer.validate_review_object(mutated)
        mutated = copy.deepcopy(self.review)
        mutated["claims"]["new_credit_claim"] = True
        with self.assertRaisesRegex(reviewer.HostedRuntimeReviewError, "bounded claims"):
            reviewer.validate_review_object(mutated)

    def test_exact_run_job_artifact_head_and_tree_identities_are_pinned(self):
        mutations = (
            (("source_artifact", "artifact", "id"), 1),
            (("source_artifact", "artifact", "name"), "retargeted"),
            (("source_artifact", "artifact", "sha256"), "0" * 64),
            (("source_artifact", "artifact", "size"), 1),
            (("source_artifact", "github", "repository"), "other/repo"),
            (("source_artifact", "github", "run_id"), 1),
            (("source_artifact", "github", "run_attempt"), 2),
            (("source_artifact", "github", "job_id"), 1),
            (("source_artifact", "github", "workflow_id"), 1),
            (("source_artifact", "github", "runtime_head_sha"), "0" * 40),
            (("runtime_candidate", "head_sha"), "0" * 40),
            (("runtime_candidate", "tree_sha"), "0" * 40),
        )
        for path, replacement in mutations:
            with self.subTest(path=".".join(path)):
                mutated = copy.deepcopy(self.review)
                set_path(mutated, path, replacement)
                with self.assertRaises(reviewer.HostedRuntimeReviewError):
                    reviewer.validate_review_object(mutated)

    def test_boolean_as_integer_identities_are_rejected(self):
        paths = (
            ("source_artifact", "artifact", "id"),
            ("source_artifact", "artifact", "size"),
            ("source_artifact", "github", "run_id"),
            ("source_artifact", "github", "job_id"),
            ("verified_facts", "qemu", "cpu_count"),
            ("verified_facts", "tar_closure", "member_count"),
        )
        for path in paths:
            with self.subTest(path=".".join(path)):
                mutated = copy.deepcopy(self.review)
                set_path(mutated, path, True)
                with self.assertRaises(reviewer.HostedRuntimeReviewError):
                    reviewer.validate_review_object(mutated)

    def test_expiration_and_non_durability_are_immutable(self):
        mutations = (
            (("source_artifact", "expires_at"), "2099-01-01T00:00:00Z"),
            (("source_artifact", "retention_days"), 3650),
            (("source_artifact", "durable_archive"), True),
            (("caveats", "artifact_retention_is_durable"), True),
            (("caveats", "artifact_bytes_committed"), True),
        )
        for path, replacement in mutations:
            with self.subTest(path=".".join(path)):
                mutated = copy.deepcopy(self.review)
                set_path(mutated, path, replacement)
                with self.assertRaises(reviewer.HostedRuntimeReviewError):
                    reviewer.validate_review_object(mutated)

    def test_remaining_prerequisites_are_exact_ordered_and_non_contradictory(self):
        mutations = []
        contradictory_archive = copy.deepcopy(self.review)
        contradictory_archive["remaining_prerequisites"][0] = (
            "Durably archive is unnecessary; expiry grants permanent authority."
        )
        mutations.append(contradictory_archive)
        contradictory_breadth = copy.deepcopy(self.review)
        contradictory_breadth["remaining_prerequisites"][1] = (
            "This single hosted run proves broad hardware compatibility."
        )
        mutations.append(contradictory_breadth)
        reordered = copy.deepcopy(self.review)
        reordered["remaining_prerequisites"].reverse()
        mutations.append(reordered)
        removed = copy.deepcopy(self.review)
        removed["remaining_prerequisites"].pop()
        mutations.append(removed)
        added = copy.deepcopy(self.review)
        added["remaining_prerequisites"].append("Contradictory extra authority.")
        mutations.append(added)
        for index, mutated in enumerate(mutations):
            with self.subTest(index=index):
                with self.assertRaisesRegex(
                    reviewer.HostedRuntimeReviewError, "remaining prerequisites"
                ):
                    reviewer.validate_review_object(mutated)

    def test_ordered_markers_cannot_be_emptied_reordered_or_resized(self):
        mutations = []
        emptied = copy.deepcopy(self.review)
        emptied["verified_facts"]["marker_review"]["ordered_exact_lines"] = []
        mutations.append(emptied)
        reordered = copy.deepcopy(self.review)
        reordered["verified_facts"]["marker_review"]["ordered_exact_lines"].reverse()
        mutations.append(reordered)
        removed = copy.deepcopy(self.review)
        removed["verified_facts"]["marker_review"]["ordered_exact_lines"].pop()
        mutations.append(removed)
        added = copy.deepcopy(self.review)
        added["verified_facts"]["marker_review"]["ordered_exact_lines"].append(
            {"count": 1, "first_line": 4037, "line": "invented marker: OK"}
        )
        mutations.append(added)
        for index, mutated in enumerate(mutations):
            with self.subTest(index=index):
                with self.assertRaises(reviewer.HostedRuntimeReviewError):
                    reviewer.validate_review_object(mutated)

    def test_archive_file_records_cannot_be_emptied_reordered_or_resized(self):
        mutations = []
        emptied = copy.deepcopy(self.review)
        emptied["verified_facts"]["archive_file_records"] = []
        mutations.append(emptied)
        reordered = copy.deepcopy(self.review)
        reordered["verified_facts"]["archive_file_records"].reverse()
        mutations.append(reordered)
        removed = copy.deepcopy(self.review)
        removed["verified_facts"]["archive_file_records"].pop()
        mutations.append(removed)
        added = copy.deepcopy(self.review)
        added["verified_facts"]["archive_file_records"].append(
            {"path": "invented.log", "sha256": "0" * 64, "size": 0}
        )
        mutations.append(added)
        for index, mutated in enumerate(mutations):
            with self.subTest(index=index):
                with self.assertRaises(reviewer.HostedRuntimeReviewError):
                    reviewer.validate_review_object(mutated)

    def test_unknown_nested_keys_and_probe_drift_are_rejected(self):
        mutations = []
        first = copy.deepcopy(self.review)
        first["unknown"] = False
        mutations.append(first)
        second = copy.deepcopy(self.review)
        second["verified_facts"]["runtime"]["unknown"] = "value"
        mutations.append(second)
        third = copy.deepcopy(self.review)
        third["verified_facts"]["marker_review"]["trace_counts"]["unknown"] = 1
        mutations.append(third)
        fourth = copy.deepcopy(self.review)
        fourth["verified_facts"]["archive_file_records"][0]["unknown"] = False
        mutations.append(fourth)
        for index, mutated in enumerate(mutations):
            with self.subTest(index=index):
                with self.assertRaises(reviewer.HostedRuntimeReviewError):
                    reviewer.validate_review_object(mutated)

    def test_committed_input_set_order_and_values_are_exact(self):
        mutated = copy.deepcopy(self.review)
        mutated["runtime_candidate"]["committed_inputs"].reverse()
        with self.assertRaisesRegex(reviewer.HostedRuntimeReviewError, "committed inputs"):
            reviewer.validate_review_object(mutated)
        mutated = copy.deepcopy(self.review)
        mutated["runtime_candidate"]["committed_inputs"][0]["size"] = True
        with self.assertRaises(reviewer.HostedRuntimeReviewError):
            reviewer.validate_review_object(mutated)

    def test_historical_review_passes_and_current_workflow_drift_is_stale(self):
        review = reviewer.validate_review_object(copy.deepcopy(self.review))
        state = reviewer.validate_repository(REPO_ROOT, review)
        self.assertRegex(state["current_head"], r"^[0-9a-f]{40}$")
        self.assertTrue(state["historical_runtime_verified"])
        self.assertFalse(state["runtime_equivalence_claimed"])
        self.assertFalse(state["current_head_is_runtime_head"])
        self.assertFalse(state["current_head_bound_inputs_match"])
        self.assertFalse(state["current_head_applicable"])
        self.assertEqual(state["current_head_status"], "stale-input-drift")
        self.assertEqual(
            state["drifted_committed_inputs"],
            [
                ".github/workflows/rust-x86_64-validation.yml",
                "scripts/rocky-rust-validation.sh",
            ],
        )

    def test_repository_state_rejects_recursive_type_and_invariant_drift(self):
        state = reviewer.validate_repository(
            REPO_ROOT, reviewer.validate_review_object(copy.deepcopy(self.review))
        )
        mutations = []
        wrong_boolean = copy.deepcopy(state)
        wrong_boolean["current_head_applicable"] = 0
        mutations.append(wrong_boolean)
        wrong_drift_type = copy.deepcopy(state)
        wrong_drift_type["drifted_committed_inputs"] = [
            {"path": ".github/workflows/rust-x86_64-validation.yml"}
        ]
        mutations.append(wrong_drift_type)
        wrong_status = copy.deepcopy(state)
        wrong_status["current_head_status"] = "exact-runtime-head"
        mutations.append(wrong_status)
        invented_path = copy.deepcopy(state)
        invented_path["drifted_committed_inputs"].append("invented")
        mutations.append(invented_path)
        extra_key = copy.deepcopy(state)
        extra_key["credit"] = False
        mutations.append(extra_key)
        for index, mutation in enumerate(mutations):
            with self.subTest(index=index):
                with self.assertRaises(reviewer.HostedRuntimeReviewError):
                    reviewer.validate_repository_state(mutation)

    def test_repository_rejects_head_movement_at_begin_and_final_input_boundary(self):
        review = reviewer.validate_review_object(copy.deepcopy(self.review))
        current_head = reviewer.run_git(
            REPO_ROOT, ["rev-parse", "HEAD"], "test current HEAD"
        ).decode("ascii").strip()
        transitions = (
            (current_head, reviewer.RUNTIME_HEAD_SHA, "current HEAD"),
            (reviewer.RUNTIME_HEAD_SHA, current_head, "current HEAD"),
            (
                current_head,
                reviewer.RUNTIME_HEAD_SHA,
                "current input scripts/rocky-rust-validation.sh",
            ),
            (
                reviewer.RUNTIME_HEAD_SHA,
                current_head,
                "current input scripts/rocky-rust-validation.sh",
            ),
        )
        for start, end, trigger_label in transitions:
            with self.subTest(start=start, end=end, trigger=trigger_label):
                with tempfile.TemporaryDirectory() as temporary:
                    clone = Path(temporary) / "repo"
                    clone_result = subprocess.run(
                        [
                            reviewer.GIT_EXECUTABLE,
                            "--no-pager",
                            "--no-replace-objects",
                            "-c",
                            "core.hooksPath=/dev/null",
                            "clone",
                            "--no-hardlinks",
                            "--quiet",
                            str(REPO_ROOT),
                            str(clone),
                        ],
                        env=reviewer.GIT_ENVIRONMENT,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                    )
                    self.assertEqual(
                        clone_result.returncode,
                        0,
                        clone_result.stderr.decode("utf-8", "replace"),
                    )

                    def checkout(commit):
                        result = subprocess.run(
                            [
                                reviewer.GIT_EXECUTABLE,
                                "--no-pager",
                                "--no-replace-objects",
                                "-c",
                                "core.hooksPath=/dev/null",
                                "-C",
                                str(clone),
                                "checkout",
                                "--quiet",
                                "--detach",
                                commit,
                            ],
                            env=reviewer.GIT_ENVIRONMENT,
                            stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE,
                        )
                        self.assertEqual(
                            result.returncode,
                            0,
                            result.stderr.decode("utf-8", "replace"),
                        )

                    checkout(start)
                    original_run_git = reviewer.run_git
                    moved = {"value": False}

                    def moving_run_git(repo, arguments, label):
                        output = original_run_git(repo, arguments, label)
                        if not moved["value"] and label == trigger_label:
                            checkout(end)
                            moved["value"] = True
                        return output

                    with mock.patch.object(
                        reviewer, "run_git", side_effect=moving_run_git
                    ):
                        with self.assertRaisesRegex(
                            reviewer.HostedRuntimeReviewError,
                            "current HEAD stability",
                        ):
                            reviewer.validate_repository(clone, review)
                    self.assertTrue(moved["value"])
                    final_head = original_run_git(
                        clone, ["rev-parse", "HEAD"], "test final HEAD"
                    ).decode("ascii").strip()
                    self.assertEqual(final_head, end)

    def test_contained_repository_input_rejects_symlink_ancestors(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            target = root / "target"
            target.mkdir()
            (target / "file").write_text("x")
            (root / "linked").symlink_to(target, target_is_directory=True)
            with self.assertRaisesRegex(reviewer.HostedRuntimeReviewError, "symlink"):
                reviewer.contained_repository_file(root, "linked/file", "input")

    def test_review_discovery_rejects_symlinked_evidence_ancestor(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            repo = root / "repo"
            rocky = repo / "host-kernel/rocky"
            rocky.mkdir(parents=True)
            external = root / "external-evidence"
            external.mkdir()
            (external / "hosted-runtime-review-external-v1.json").write_bytes(
                self.review_path.read_bytes()
            )
            (rocky / "evidence").symlink_to(external, target_is_directory=True)
            with self.assertRaisesRegex(reviewer.HostedRuntimeReviewError, "symlink"):
                reviewer.discover_review(repo)

    def test_safe_relative_paths_reject_escape_and_ambiguous_forms(self):
        for path in ("", "/absolute", "../escape", "a/../b", "a//b", "a\\b", "./a", "a/./b"):
            with self.subTest(path=path):
                with self.assertRaises(reviewer.HostedRuntimeReviewError):
                    reviewer.safe_relative_path(path, "path")

    def test_zip_closure_rejects_escape_duplicate_symlink_and_extra_fields(self):
        cases = ("escape", "duplicate", "symlink", "extra")
        for case in cases:
            with self.subTest(case=case), tempfile.TemporaryDirectory() as temporary:
                path = Path(temporary) / "bad.zip"
                with warnings.catch_warnings():
                    warnings.simplefilter("ignore", UserWarning)
                    with zipfile.ZipFile(str(path), "w") as archive:
                        if case == "escape":
                            archive.writestr(regular_zip_info("../escape"), b"x")
                        elif case == "duplicate":
                            archive.writestr(regular_zip_info("file"), b"x")
                            archive.writestr(regular_zip_info("file"), b"y")
                        elif case == "symlink":
                            info = zipfile.ZipInfo("link")
                            info.create_system = 3
                            info.external_attr = (stat.S_IFLNK | 0o777) << 16
                            archive.writestr(info, b"target")
                        else:
                            info = regular_zip_info("file")
                            info.extra = b"\x01\x00\x00\x00"
                            archive.writestr(info, b"x")
                with zipfile.ZipFile(str(path), "r") as archive:
                    with self.assertRaises(reviewer.HostedRuntimeReviewError):
                        reviewer.zip_entry_records(archive)

    def test_tar_closure_rejects_escape_duplicate_and_links(self):
        cases = (
            [(".", "directory", b""), ("./../escape", "file", b"x")],
            [(".", "directory", b""), ("./file", "file", b"x"), ("./file", "file", b"y")],
            [(".", "directory", b""), ("./link", "symlink", b"")],
        )
        for members in cases:
            with self.subTest(members=members):
                with self.assertRaises(reviewer.HostedRuntimeReviewError):
                    reviewer.tar_entry_records(make_tar(members))

    def test_checksum_manifest_requires_exact_order_closure_and_uniqueness(self):
        rows = ["{}  {}".format("0" * 64, name) for name in reviewer.EXPECTED_CHECKSUM_NAMES]
        data = ("\n".join(rows) + "\n").encode("ascii")
        self.assertEqual(tuple(reviewer.parse_sha256sums(data)), reviewer.EXPECTED_CHECKSUM_NAMES)
        bad_values = (
            ("\n".join(reversed(rows)) + "\n").encode("ascii"),
            ("\n".join(rows + [rows[0]]) + "\n").encode("ascii"),
            ("\n".join(rows[:-1]) + "\n").encode("ascii"),
            "\n".join(rows).encode("ascii"),
        )
        for bad in bad_values:
            with self.subTest(length=len(bad)):
                with self.assertRaises(reviewer.HostedRuntimeReviewError):
                    reviewer.parse_sha256sums(bad)

    def test_fatal_signature_policy_is_fail_closed(self):
        linux_signatures = (
            "BUG: unable to handle",
            "Oops: fault",
            "general protection fault",
            "Kernel panic",
            "panic - not syncing",
            "WARNING: CPU: 0 PID: 1",
            "Unable to handle kernel paging request",
        )
        mckernel_signatures = (
            "mcexec_v10: fatal state",
            " PANIC ",
            " panic: stopped",
            "BUG: failure",
            "Oops: fault",
            "general protection fault",
            "unhandled page fault",
            "assert failed",
            "assertion failed",
            "stack smashing",
            "stack corruption",
        )
        for signature in linux_signatures:
            with self.subTest(policy="linux", signature=signature):
                self.assertIsNotNone(reviewer.LINUX_FATAL_SIGNATURE.search(signature))
        for signature in mckernel_signatures:
            with self.subTest(policy="mckernel", signature=signature):
                self.assertIsNotNone(reviewer.MCKERNEL_FATAL_SIGNATURE.search(signature))
        self.assertIsNone(
            reviewer.LINUX_FATAL_SIGNATURE.search("hosted-post-validation: OK")
        )
        self.assertIsNone(
            reviewer.MCKERNEL_FATAL_SIGNATURE.search("hosted-post-validation: OK")
        )

    def test_pkcs8_encrypted_pkcs8_and_pgp_private_keys_are_rejected(self):
        signatures = (
            b"-----BEGIN PRIVATE KEY-----\nsecret\n-----END PRIVATE KEY-----\n",
            b"-----BEGIN ENCRYPTED PRIVATE KEY-----\nsecret\n-----END ENCRYPTED PRIVATE KEY-----\n",
            b"-----BEGIN PGP PRIVATE KEY BLOCK-----\nsecret\n-----END PGP PRIVATE KEY BLOCK-----\n",
        )
        for signature in signatures:
            with self.subTest(signature=signature.splitlines()[0]):
                with self.assertRaisesRegex(
                    reviewer.HostedRuntimeReviewError, "private-key material"
                ):
                    reviewer.reject_private_key_material(
                        {"qemu/guest-evidence/innocent.txt": signature}
                    )
        reviewer.reject_private_key_material(
            {"qemu/guest-evidence/innocent.txt": b"ordinary runtime evidence\n"}
        )

    def test_previously_omitted_fatal_log_mutations_fail_closed(self):
        cases = (
            (
                "linux_dmesg_delta",
                b"normal boot line\nWARNING: CPU: 0 PID: 1 at kernel/test.c:1\n",
                reviewer.LINUX_FATAL_SIGNATURE,
            ),
            (
                "mckernel_final",
                b"normal runtime line\nmcexec_v10: fatal dispatch state\n",
                reviewer.MCKERNEL_FATAL_SIGNATURE,
            ),
        )
        for label, payload, pattern in cases:
            with self.subTest(label=label):
                row = {
                    "fatal_signature_count": 0,
                    "line_count": len(payload.decode("ascii").splitlines()),
                    "prefix_chain_verified": True,
                    "sha256": hashlib.sha256(payload).hexdigest(),
                }
                with self.assertRaisesRegex(
                    reviewer.HostedRuntimeReviewError, "fatal scan"
                ):
                    reviewer.verify_fatal_scan(payload, row, pattern, label)

    def test_exact_artifact_closure_runtime_markers_and_cleanup(self):
        if self.artifact_path is None:
            self.skipTest(
                "expiring non-durable artifact not supplied in MCKERNEL_HOSTED_RUNTIME_ARTIFACT"
            )
        result = reviewer.verify_artifact(self.artifact_path, self.review)
        self.assertEqual(result["artifact_sha256"], reviewer.ARTIFACT_SHA256)
        self.assertEqual(result["entry_count"], 33)
        self.assertEqual(result["tar_member_count"], 19)

    def test_exact_artifact_marker_mutations_fail_closed(self):
        if self.artifact_path is None:
            self.skipTest(
                "expiring non-durable artifact not supplied in MCKERNEL_HOSTED_RUNTIME_ARTIFACT"
            )
        prefix = reviewer.ZIP_PREFIX
        with zipfile.ZipFile(str(self.artifact_path), "r") as archive:
            command = archive.read(prefix + "qemu/guest-command.log")
            tar_data = archive.read(prefix + "qemu/guest-evidence.tar")
        _, files = reviewer.tar_entry_records(tar_data)
        markers = copy.deepcopy(self.review["verified_facts"]["marker_review"])
        markers["ordered_exact_lines"][0]["count"] += 1
        with self.assertRaises(reviewer.HostedRuntimeReviewError):
            reviewer.verify_markers(command, files["mckernel-workload-delta.kmsg"], markers)
        delta = files["mckernel-workload-delta.kmsg"].replace(
            b"generic_forwarding owner=rust", b"generic_forwarding owner=c", 1
        )
        with self.assertRaises(reviewer.HostedRuntimeReviewError):
            reviewer.verify_markers(command, delta, self.review["verified_facts"]["marker_review"])

    def test_marker_positions_are_one_based_line_numbers(self):
        markers = self.review["verified_facts"]["marker_review"]["ordered_exact_lines"]
        self.assertEqual(markers[0]["first_line"], 3)
        self.assertEqual(markers[-1]["first_line"], 4036)

    def test_artifact_byte_mutation_fails_before_semantic_review(self):
        if self.artifact_path is None:
            self.skipTest(
                "expiring non-durable artifact not supplied in MCKERNEL_HOSTED_RUNTIME_ARTIFACT"
            )
        data = bytearray(self.artifact_path.read_bytes())
        data[len(data) // 2] ^= 1
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "mutated.zip"
            path.write_bytes(bytes(data))
            with self.assertRaisesRegex(reviewer.HostedRuntimeReviewError, "artifact digest"):
                reviewer.verify_artifact(path, self.review)

    def test_cli_git_authority_ignores_inherited_path_and_repository_overrides(self):
        with tempfile.TemporaryDirectory() as temporary:
            temporary = Path(temporary)
            marker = temporary / "fake-git-ran"
            fake_git = temporary / "git"
            fake_git.write_text(
                "#!/bin/sh\n: > {!r}\nexit 99\n".format(str(marker)),
                encoding="utf-8",
            )
            fake_git.chmod(0o755)
            environment = os.environ.copy()
            environment.update(
                {
                    "GIT_DIR": str(temporary / "fake-git-dir"),
                    "GIT_INDEX_FILE": str(temporary / "fake-index"),
                    "GIT_OBJECT_DIRECTORY": str(temporary / "fake-objects"),
                    "GIT_REPLACE_REF_BASE": "refs/hostile/replace/",
                    "GIT_WORK_TREE": str(temporary / "fake-worktree"),
                    "PATH": str(temporary),
                    "PYTHONDONTWRITEBYTECODE": "1",
                }
            )
            result = subprocess.run(
                [
                    sys.executable,
                    "-B",
                    str(MODULE_PATH),
                    "--repo",
                    str(REPO_ROOT),
                    "--check",
                ],
                env=environment,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertFalse(marker.exists())
            self.assertIn(
                "current descendant applicability: false (stale-input-drift)",
                result.stdout,
            )

    def test_cli_check_is_non_crediting_and_reports_expiration(self):
        result = subprocess.run(
            [sys.executable, "-B", str(MODULE_PATH), "--repo", str(REPO_ROOT), "--check"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("hosted runtime review: bounded historical PASS", result.stdout)
        self.assertIn(
            "current descendant applicability: false (stale-input-drift)",
            result.stdout,
        )
        self.assertIn(
            "current bound-input drift: .github/workflows/rust-x86_64-validation.yml",
            result.stdout,
        )
        self.assertIn("current runtime equivalence claimed: false", result.stdout)
        self.assertIn("gate/tracker/broad-runtime credit: false", result.stdout)
        self.assertIn(reviewer.ARTIFACT_EXPIRES_AT, result.stdout)

    def test_python_36_syntax_and_api_surface(self):
        source = MODULE_PATH.read_text(encoding="utf-8")
        if sys.version_info >= (3, 8):
            ast.parse(source, filename=str(MODULE_PATH), feature_version=(3, 6))
        else:
            ast.parse(source, filename=str(MODULE_PATH))
        self.assertNotIn("from __future__ import annotations", source)
        self.assertNotIn("capture_output=", source)
        self.assertNotIn("text=", source)


if __name__ == "__main__":
    unittest.main()
