#!/usr/bin/env python3
"""Fail-closed tests for the bounded RK-007 exact-build review."""

from __future__ import print_function

import ast
import copy
import hashlib
import importlib.util
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
MODULE_PATH = REPO_ROOT / "scripts/rocky_kernel_rk007_build_review.py"
SPEC = importlib.util.spec_from_file_location("rocky_kernel_rk007_build_review", str(MODULE_PATH))
reviewer = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(reviewer)


def set_path(value, path, replacement):
    cursor = value
    for key in path[:-1]:
        cursor = cursor[key]
    cursor[path[-1]] = replacement


def parse_python_36(source, filename):
    try:
        return ast.parse(source, filename=filename, feature_version=(3, 6))
    except TypeError:
        return ast.parse(source, filename=filename)


def zip_info(name, mode=stat.S_IFREG | 0o644, extra=b"", comment=b""):
    info = zipfile.ZipInfo(name)
    info.create_system = 3
    info.external_attr = mode << 16
    info.compress_type = zipfile.ZIP_STORED
    info.extra = extra
    info.comment = comment
    return info


def build_zip(files, metadata=None, duplicate=None, archive_comment=b""):
    output = io.BytesIO()
    metadata = metadata or {}
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_STORED) as archive:
        archive.comment = archive_comment
        for name in sorted(files):
            values = metadata.get(name, {})
            archive.writestr(
                zip_info(
                    name,
                    mode=values.get("mode", stat.S_IFREG | 0o644),
                    extra=values.get("extra", b""),
                    comment=values.get("comment", b""),
                ),
                files[name],
            )
        if duplicate is not None:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", UserWarning)
                archive.writestr(zip_info(duplicate), files[duplicate])
    return output.getvalue()


def checksum_bytes(files, names):
    return "".join(
        "{}  {}\n".format(hashlib.sha256(files[name]).hexdigest(), name)
        for name in sorted(names)
    ).encode("ascii")


def aligned_artifact(files, review, metadata=None):
    files = dict(files)
    files["PRECHECK_SHA256SUMS"] = checksum_bytes(files, reviewer.EXPECTED_PRECHECK_NAMES)
    files["SHA256SUMS"] = checksum_bytes(
        files, set(reviewer.EXPECTED_ZIP_PATHS) - {"SHA256SUMS"}
    )
    data = build_zip(files, metadata=metadata)
    mutated = copy.deepcopy(review)
    inner = mutated["inner_closure"]
    inner["precheck_manifest_sha256"] = hashlib.sha256(
        files["PRECHECK_SHA256SUMS"]
    ).hexdigest()
    inner["final_manifest_sha256"] = hashlib.sha256(files["SHA256SUMS"]).hexdigest()
    inner["precheck_records"] = [
        {"path": name, "sha256": hashlib.sha256(files[name]).hexdigest(), "size": len(files[name])}
        for name in reviewer.EXPECTED_PRECHECK_NAMES
    ]
    inner["final_records"] = [
        {"path": name, "sha256": hashlib.sha256(files[name]).hexdigest(), "size": len(files[name])}
        for name in sorted(set(reviewer.EXPECTED_ZIP_PATHS) - {"SHA256SUMS"})
    ]
    with zipfile.ZipFile(io.BytesIO(data), "r") as archive:
        index = []
        for info in archive.infolist():
            index.append(
                {
                    "compressed_size": info.compress_size,
                    "crc32": "{:08x}".format(info.CRC),
                    "mode": "100644",
                    "path": info.filename,
                    "size": info.file_size,
                }
            )
        index.sort(key=lambda row: row["path"])
    mutated["zip_closure"]["stored_payload_size"] = sum(row["size"] for row in index)
    mutated["zip_closure"]["compressed_payload_size"] = sum(
        row["compressed_size"] for row in index
    )
    mutated["zip_closure"]["entry_index_sha256"] = hashlib.sha256(
        reviewer.canonical_json_bytes(index)
    ).hexdigest()
    return data, mutated


def rebound_cmd_records(path, data, legacy_unicode_splitlines=False):
    """Rebind byte oracles so a test reaches independent semantic checks."""
    records = copy.deepcopy(reviewer.EXPECTED_CMD_RECORDS)
    expected = next(row for row in records if row["path"] == path)
    if legacy_unicode_splitlines:
        text = data.decode("utf-8")
        lines = text.splitlines()
        command = lines[0].split(" := ", 1)[1]
    else:
        _, command, text = reviewer.parse_saved_command(path, data)
        lines = text[:-1].split("\n")
    tokens = reviewer.shlex.split(command, posix=True)
    expected["sha256"] = hashlib.sha256(data).hexdigest()
    expected["savedcmd_line_sha256"] = hashlib.sha256(lines[0].encode("utf-8")).hexdigest()
    expected["trailing_lines_sha256"] = hashlib.sha256(
        reviewer.canonical_json_bytes(lines[1:])
    ).hexdigest()
    expected["structure_sha256"] = hashlib.sha256(
        reviewer.canonical_json_bytes(lines)
    ).hexdigest()
    expected["token_sha256"] = hashlib.sha256(
        reviewer.canonical_json_bytes(tokens)
    ).hexdigest()
    return records


def rebound_module_facts(binary_name, data):
    """Refresh only the exact binary identity so direct ELF checks are isolated."""
    facts = copy.deepcopy(reviewer.EXPECTED_MODULE_FACTS)
    fact = next(row for row in facts if row["binary"] == binary_name)
    fact["binary_sha256"] = hashlib.sha256(data).hexdigest()
    fact["binary_size"] = len(data)
    return facts


class Rk007BuildReviewTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.review_path = reviewer.discover_review(REPO_ROOT)
        cls.review = reviewer.load_review(cls.review_path)
        artifact = os.environ.get("MCKERNEL_RK007_BUILD_ARTIFACT")
        cls.artifact_path = Path(artifact) if artifact else None
        cls.artifact_bytes = None
        cls.artifact_files = None
        if cls.artifact_path is not None:
            cls.artifact_bytes = cls.artifact_path.read_bytes()
            with zipfile.ZipFile(io.BytesIO(cls.artifact_bytes), "r") as archive:
                cls.artifact_files = {info.filename: archive.read(info) for info in archive.infolist()}

    def require_artifact(self):
        if self.artifact_bytes is None:
            self.skipTest("set MCKERNEL_RK007_BUILD_ARTIFACT for exact artifact mutations")

    def make_port_fixture(self, root):
        def git(*arguments):
            return subprocess.run(
                ["git", "-C", str(root)] + list(arguments),
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            ).stdout.decode("ascii").strip()

        git("init", "-q")
        git("config", "user.name", "RK007 fixture")
        git("config", "user.email", "rk007-fixture@example.invalid")
        paths = ("bound-one", "bound-two")
        for path in paths:
            (root / path).write_bytes(("runtime-{}\n".format(path)).encode("ascii"))
            (root / path).chmod(0o644)
        git("add", "--", *paths)
        git("commit", "-q", "-m", "runtime")
        runtime_head = git("rev-parse", "HEAD")
        runtime_tree = git("rev-parse", "HEAD^{tree}")
        runtime_rows = []
        for path in paths:
            data = (root / path).read_bytes()
            runtime_rows.append(
                {
                    "git_blob_sha1": git("rev-parse", "HEAD:{}".format(path)),
                    "mode": "100644",
                    "path": path,
                    "sha256": hashlib.sha256(data).hexdigest(),
                    "size": len(data),
                }
            )
        for path in paths:
            (root / path).write_bytes(("current-{}\n".format(path)).encode("ascii"))
        git("add", "--", *paths)
        git("commit", "-q", "-m", "current")
        current_head = git("rev-parse", "HEAD")
        overrides = []
        for runtime_row in runtime_rows:
            path = runtime_row["path"]
            data = (root / path).read_bytes()
            overrides.append(
                {
                    "current_git_blob_sha1": git("rev-parse", "HEAD:{}".format(path)),
                    "current_sha256": hashlib.sha256(data).hexdigest(),
                    "current_size": len(data),
                    "mode": "100644",
                    "path": path,
                    "runtime_git_blob_sha1": runtime_row["git_blob_sha1"],
                    "runtime_sha256": runtime_row["sha256"],
                    "runtime_size": runtime_row["size"],
                }
            )
        review = {
            "current_repository_input_policy": {"current_overrides": overrides},
            "runtime_candidate": {"committed_inputs": runtime_rows},
        }
        return git, runtime_head, runtime_tree, current_head, review

    def test_checked_in_review_is_bounded_no_credit_and_valid(self):
        checked = reviewer.validate_review_object(copy.deepcopy(self.review))
        self.assertEqual(checked["claims"], reviewer.EXPECTED_CLAIMS)
        self.assertFalse(checked["source_artifact"]["durable_archive"])
        self.assertFalse(checked["claims"]["gate_claims"]["RK-007"])

    def test_manifest_is_canonical_and_digest_locked(self):
        data = self.review_path.read_bytes()
        self.assertEqual(hashlib.sha256(data).hexdigest(), reviewer.REVIEW_SHA256)
        self.assertEqual(data, reviewer.canonical_json_bytes(self.review))
        with tempfile.TemporaryDirectory() as temporary:
            mutated = copy.deepcopy(self.review)
            mutated["source_artifact"]["artifact"]["id"] = 1
            path = Path(temporary) / "review.json"
            path.write_bytes(reviewer.canonical_json_bytes(mutated))
            with self.assertRaisesRegex(reviewer.BuildReviewError, "manifest digest"):
                reviewer.load_review(path)

    def test_historical_projection_rejects_coherently_rehashed_retargeting(self):
        mutations = (
            (("source_artifact", "artifact", "sha256"), "0" * 64),
            (("runtime_candidate", "committed_inputs", 0, "sha256"), "0" * 64),
            (("verified_facts", "stage_lock", "manifest_sha256"), "0" * 64),
            (("inner_closure", "final_manifest_sha256"), "0" * 64),
        )
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "review.json"
            for target, replacement in mutations:
                with self.subTest(target=target):
                    mutated = copy.deepcopy(self.review)
                    set_path(mutated, target, replacement)
                    data = reviewer.canonical_json_bytes(mutated)
                    path.write_bytes(data)
                    coherent_digest = hashlib.sha256(data).hexdigest()
                    with mock.patch.object(
                        reviewer, "REVIEW_SHA256", coherent_digest
                    ):
                        with self.assertRaisesRegex(
                            reviewer.BuildReviewError,
                            "historical review projection digest",
                        ):
                            reviewer.load_review(path)

    def test_historical_projection_excludes_only_the_checked_port_policy(self):
        mutated = copy.deepcopy(self.review)
        mutated["current_repository_input_policy"]["current_override_count"] = 4
        data = reviewer.canonical_json_bytes(mutated)
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "review.json"
            path.write_bytes(data)
            with mock.patch.object(
                reviewer, "REVIEW_SHA256", hashlib.sha256(data).hexdigest()
            ):
                loaded = reviewer.load_review(path)
        with self.assertRaisesRegex(reviewer.BuildReviewError, "current override count"):
            reviewer.validate_review_object(loaded)

    def test_duplicate_json_keys_are_rejected(self):
        with self.assertRaisesRegex(reviewer.BuildReviewError, "duplicate JSON key"):
            reviewer.read_json_bytes(b'{"a":1,"a":2}\n', "duplicate")

    def test_every_credit_runtime_and_gate_claim_must_remain_false(self):
        for name in sorted(set(reviewer.EXPECTED_CLAIMS) - {"gate_claims"}):
            with self.subTest(name=name):
                mutated = copy.deepcopy(self.review)
                mutated["claims"][name] = True
                with self.assertRaisesRegex(reviewer.BuildReviewError, "bounded claims"):
                    reviewer.validate_review_object(mutated)
        for name in sorted(reviewer.EXPECTED_GATE_CLAIMS):
            with self.subTest(gate=name):
                mutated = copy.deepcopy(self.review)
                mutated["claims"]["gate_claims"][name] = True
                with self.assertRaisesRegex(reviewer.BuildReviewError, "bounded claims"):
                    reviewer.validate_review_object(mutated)

    def test_added_claim_is_rejected(self):
        mutated = copy.deepcopy(self.review)
        mutated["claims"]["invented_authority"] = False
        with self.assertRaises(reviewer.BuildReviewError):
            reviewer.validate_review_object(mutated)

    def test_run_job_artifact_head_and_tree_identities_are_pinned(self):
        mutations = (
            (("source_artifact", "artifact", "id"), 1),
            (("source_artifact", "artifact", "name"), "retargeted"),
            (("source_artifact", "artifact", "sha256"), "0" * 64),
            (("source_artifact", "artifact", "size"), 1),
            (("source_artifact", "github", "run_id"), 1),
            (("source_artifact", "github", "job_id"), 1),
            (("source_artifact", "github", "runtime_head_sha"), "0" * 40),
            (("source_artifact", "github", "runtime_tree_sha"), "0" * 40),
            (("runtime_candidate", "head_sha"), "0" * 40),
            (("runtime_candidate", "tree_sha"), "0" * 40),
        )
        for path, replacement in mutations:
            with self.subTest(path=".".join(path)):
                mutated = copy.deepcopy(self.review)
                set_path(mutated, path, replacement)
                with self.assertRaises(reviewer.BuildReviewError):
                    reviewer.validate_review_object(mutated)

    def test_boolean_as_integer_identities_are_rejected(self):
        for path in (
            ("source_artifact", "artifact", "id"),
            ("source_artifact", "artifact", "size"),
            ("source_artifact", "github", "run_id"),
            ("source_artifact", "github", "job_id"),
            ("zip_closure", "entry_count"),
        ):
            with self.subTest(path=".".join(path)):
                mutated = copy.deepcopy(self.review)
                set_path(mutated, path, True)
                with self.assertRaises(reviewer.BuildReviewError):
                    reviewer.validate_review_object(mutated)

    def test_expiry_and_durability_are_immutable(self):
        for path, replacement in (
            (("source_artifact", "expires_at"), "2099-01-01T00:00:00Z"),
            (("source_artifact", "retention_days"), 3650),
            (("source_artifact", "durable_archive"), True),
            (("claims", "durable_archive"), True),
            (("caveats", "artifact_retention_is_durable"), True),
        ):
            with self.subTest(path=".".join(path)):
                mutated = copy.deepcopy(self.review)
                set_path(mutated, path, replacement)
                with self.assertRaises(reviewer.BuildReviewError):
                    reviewer.validate_review_object(mutated)

    def test_remaining_prerequisites_are_exact_and_ordered(self):
        mutations = []
        reversed_review = copy.deepcopy(self.review)
        reversed_review["remaining_prerequisites"].reverse()
        mutations.append(reversed_review)
        removed = copy.deepcopy(self.review)
        removed["remaining_prerequisites"].pop()
        mutations.append(removed)
        added = copy.deepcopy(self.review)
        added["remaining_prerequisites"].append("invented authority")
        mutations.append(added)
        for mutated in mutations:
            with self.assertRaisesRegex(reviewer.BuildReviewError, "remaining prerequisites"):
                reviewer.validate_review_object(mutated)

    def test_unknown_top_and_nested_keys_are_rejected(self):
        mutations = []
        top = copy.deepcopy(self.review)
        top["unknown"] = False
        mutations.append(top)
        nested = copy.deepcopy(self.review)
        nested["verified_facts"]["configuration"]["unknown"] = False
        mutations.append(nested)
        record = copy.deepcopy(self.review)
        record["inner_closure"]["final_records"][0]["unknown"] = False
        mutations.append(record)
        for mutated in mutations:
            with self.assertRaises(reviewer.BuildReviewError):
                reviewer.validate_review_object(mutated)

    def test_committed_input_order_modes_and_values_are_exact(self):
        mutated = copy.deepcopy(self.review)
        mutated["runtime_candidate"]["committed_inputs"].reverse()
        with self.assertRaisesRegex(reviewer.BuildReviewError, "committed inputs"):
            reviewer.validate_review_object(mutated)
        mutated = copy.deepcopy(self.review)
        mutated["runtime_candidate"]["committed_inputs"][0]["mode"] = "100755"
        with self.assertRaises(reviewer.BuildReviewError):
            reviewer.validate_review_object(mutated)

    def test_current_repository_rejects_unreviewed_active_workflow_descendant(self):
        with self.assertRaisesRegex(
            reviewer.BuildReviewError,
            r"committed input 0 (?:current blob|worktree (?:size|digest)) differs",
        ):
            reviewer.validate_repository(
                REPO_ROOT, reviewer.validate_review_object(copy.deepcopy(self.review))
            )

    def test_descendant_port_requires_exact_old_to_new_records(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            unused_git, runtime_head, runtime_tree, current_head, review = self.make_port_fixture(root)
            with mock.patch.multiple(
                reviewer,
                RUNTIME_HEAD_SHA=runtime_head,
                RUNTIME_TREE_SHA=runtime_tree,
            ):
                self.assertEqual(reviewer.validate_repository(root, review), current_head)

                missing = copy.deepcopy(review)
                missing["current_repository_input_policy"]["current_overrides"].pop()
                with self.assertRaisesRegex(reviewer.BuildReviewError, "current blob"):
                    reviewer.validate_repository(root, missing)

                wrong_old = copy.deepcopy(review)
                wrong_old["current_repository_input_policy"]["current_overrides"][0][
                    "runtime_git_blob_sha1"
                ] = "0" * 40
                with self.assertRaisesRegex(reviewer.BuildReviewError, "override runtime blob"):
                    reviewer.validate_repository(root, wrong_old)

                wrong_new = copy.deepcopy(review)
                wrong_new["current_repository_input_policy"]["current_overrides"][0][
                    "current_git_blob_sha1"
                ] = "0" * 40
                with self.assertRaisesRegex(reviewer.BuildReviewError, "current blob"):
                    reviewer.validate_repository(root, wrong_new)

                for field, value, error in (
                    ("runtime_sha256", "0" * 64, "override runtime digest"),
                    ("runtime_size", 1, "override runtime size"),
                    ("current_sha256", "0" * 64, "current digest"),
                    ("current_size", 1, "current size"),
                ):
                    with self.subTest(field=field):
                        wrong = copy.deepcopy(review)
                        wrong["current_repository_input_policy"]["current_overrides"][0][
                            field
                        ] = value
                        with self.assertRaisesRegex(reviewer.BuildReviewError, error):
                            reviewer.validate_repository(root, wrong)

                extra = copy.deepcopy(review)
                extra_row = copy.deepcopy(
                    extra["current_repository_input_policy"]["current_overrides"][0]
                )
                extra_row["path"] = "not-reviewed"
                extra["current_repository_input_policy"]["current_overrides"].append(extra_row)
                with self.assertRaisesRegex(reviewer.BuildReviewError, "unreviewed"):
                    reviewer.validate_repository(root, extra)

    def test_descendant_port_rejects_dirty_index_and_worktree(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            git, runtime_head, runtime_tree, unused_current, review = self.make_port_fixture(root)
            with mock.patch.multiple(
                reviewer,
                RUNTIME_HEAD_SHA=runtime_head,
                RUNTIME_TREE_SHA=runtime_tree,
            ):
                (root / "bound-one").write_bytes(b"dirty-worktree\n")
                with self.assertRaisesRegex(reviewer.BuildReviewError, "worktree"):
                    reviewer.validate_repository(root, review)

                (root / "bound-one").write_bytes(b"current-bound-one\n")
                git("add", "--", "bound-one")
                (root / "bound-one").write_bytes(b"different-index\n")
                git("add", "--", "bound-one")
                (root / "bound-one").write_bytes(b"current-bound-one\n")
                with self.assertRaisesRegex(reviewer.BuildReviewError, "index"):
                    reviewer.validate_repository(root, review)

    def test_descendant_port_rejects_non_descendant_head(self):
        real_run_git = reviewer.run_git

        def no_ancestry(repo, arguments, allow_failure=False):
            if arguments[:2] == ["merge-base", "--is-ancestor"]:
                return subprocess.CompletedProcess(arguments, 1, stdout=b"", stderr=b"")
            return real_run_git(repo, arguments, allow_failure=allow_failure)

        with mock.patch.object(reviewer, "run_git", side_effect=no_ancestry):
            with self.assertRaisesRegex(reviewer.BuildReviewError, "not a descendant"):
                reviewer.validate_repository(REPO_ROOT, copy.deepcopy(self.review))

    def test_descendant_port_requires_current_head_to_be_a_commit(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            git, runtime_head, runtime_tree, current_head, review = self.make_port_fixture(root)
            git("tag", "-a", "review-tag", "-m", "review tag", current_head)
            tag_object = git("rev-parse", "refs/tags/review-tag")
            (root / ".git" / "HEAD").write_text(tag_object + "\n")
            self.assertEqual("tag", git("cat-file", "-t", "HEAD"))
            with mock.patch.multiple(
                reviewer,
                RUNTIME_HEAD_SHA=runtime_head,
                RUNTIME_TREE_SHA=runtime_tree,
            ):
                with self.assertRaisesRegex(reviewer.BuildReviewError, "current HEAD Git object type"):
                    reviewer.validate_repository(root, review)

    def test_descendant_port_ignores_git_replace_ancestry(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            git, runtime_head, runtime_tree, current_head, review = self.make_port_fixture(root)
            current_tree = git("rev-parse", "{}^{{tree}}".format(current_head))
            unrelated = subprocess.run(
                ["git", "-C", str(root), "commit-tree", current_tree],
                input=b"unrelated\n",
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            ).stdout.decode("ascii").strip()
            git("checkout", "-q", "--detach", unrelated)
            git("replace", unrelated, current_head)
            self.assertEqual(
                0,
                subprocess.run(
                    ["git", "-C", str(root), "merge-base", "--is-ancestor", runtime_head, unrelated],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                ).returncode,
            )
            with mock.patch.multiple(
                reviewer,
                RUNTIME_HEAD_SHA=runtime_head,
                RUNTIME_TREE_SHA=runtime_tree,
            ):
                with self.assertRaisesRegex(reviewer.BuildReviewError, "not a descendant"):
                    reviewer.validate_repository(root, review)

            git("replace", "-d", unrelated)
            grafts = root / ".git" / "info" / "grafts"
            grafts.write_text("{} {}\n".format(unrelated, current_head))
            self.assertEqual(
                0,
                subprocess.run(
                    ["git", "-C", str(root), "merge-base", "--is-ancestor", runtime_head, unrelated],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                ).returncode,
            )
            with mock.patch.multiple(
                reviewer,
                RUNTIME_HEAD_SHA=runtime_head,
                RUNTIME_TREE_SHA=runtime_tree,
            ):
                with self.assertRaisesRegex(reviewer.BuildReviewError, "not a descendant"):
                    reviewer.validate_repository(root, review)

    def test_git_subprocess_ignores_repository_redirect_environment(self):
        redirected = {
            "GIT_CONFIG_COUNT": "1",
            "GIT_CONFIG_KEY_0": "core.useReplaceRefs",
            "GIT_CONFIG_VALUE_0": "true",
            "GIT_DIR": "/definitely/not/the/reviewed/repository",
            "GIT_INDEX_FILE": "/definitely/not/the/reviewed/index",
            "GIT_NO_REPLACE_OBJECTS": "0",
            "GIT_WORK_TREE": "/definitely/not/the/reviewed/worktree",
        }
        with mock.patch.dict(os.environ, redirected, clear=False):
            with self.assertRaisesRegex(reviewer.BuildReviewError, "committed input 0"):
                reviewer.validate_repository(
                    REPO_ROOT, reviewer.validate_review_object(copy.deepcopy(self.review))
                )
            for name, value in redirected.items():
                self.assertEqual(os.environ.get(name), value)

    def test_checked_policy_rejects_unreviewed_port_records(self):
        base = copy.deepcopy(self.review)
        policy = base["current_repository_input_policy"]
        self.assertEqual(policy["current_override_count"], 5)
        self.assertEqual(policy["current_overrides"], reviewer.EXPECTED_CURRENT_OVERRIDES)
        self.assertEqual(
            [row["path"] for row in policy["current_overrides"]],
            [
                ".github/workflows/native-rust-host-modules-exact-build.yml",
                "host-kernel/kbuild/Kconfig",
                "host-kernel/kbuild/stage-manifest.json",
                "host-kernel/rocky/configs/native-rust-evidence.config",
                "scripts/rocky_rust_staging.py",
            ],
        )
        self.assertTrue(policy["historical_runtime_inputs_immutable"])
        mutations = []
        added = copy.deepcopy(base)
        added["current_repository_input_policy"]["current_override_count"] = 1
        added["current_repository_input_policy"]["current_overrides"] = [
            {
                "current_git_blob_sha1": "1" * 40,
                "current_sha256": "1" * 64,
                "current_size": 1,
                "mode": "100644",
                "path": reviewer.EXPECTED_COMMITTED_INPUTS[0]["path"],
                "runtime_git_blob_sha1": reviewer.EXPECTED_COMMITTED_INPUTS[0][
                    "git_blob_sha1"
                ],
                "runtime_sha256": reviewer.EXPECTED_COMMITTED_INPUTS[0]["sha256"],
                "runtime_size": reviewer.EXPECTED_COMMITTED_INPUTS[0]["size"],
            }
        ]
        mutations.append(added)
        weakened = copy.deepcopy(base)
        weakened["current_repository_input_policy"][
            "historical_runtime_inputs_immutable"
        ] = False
        mutations.append(weakened)
        for mutated in mutations:
            with self.assertRaises(reviewer.BuildReviewError):
                reviewer.validate_review_object(mutated)

    def test_repository_file_rejects_symlink_ancestors(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            target = root / "target"
            target.mkdir()
            (target / "file").write_text("x")
            (root / "linked").symlink_to(target, target_is_directory=True)
            with self.assertRaisesRegex(reviewer.BuildReviewError, "symlink"):
                reviewer.repository_file(root, "linked/file", "fixture")

    def test_regular_file_rejects_explicit_symlink_and_symlink_ancestor(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            target = root / "target"
            target.mkdir()
            real = target / "artifact.zip"
            real.write_bytes(b"zip")
            leaf = root / "leaf.zip"
            leaf.symlink_to(real)
            ancestor = root / "ancestor"
            ancestor.symlink_to(target, target_is_directory=True)
            for path in (leaf, ancestor / "artifact.zip"):
                with self.subTest(path=str(path)):
                    with self.assertRaisesRegex(reviewer.BuildReviewError, "symlink"):
                        reviewer.read_regular_file_once(path, "artifact")

    def test_regular_file_read_uses_anchored_nofollow_openat_walk(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "artifact.zip"
            path.write_bytes(b"zip")
            calls = []
            real_open = os.open

            def recording_open(name, flags, *args, **kwargs):
                calls.append((name, flags, kwargs.get("dir_fd")))
                return real_open(name, flags, *args, **kwargs)

            with mock.patch.object(reviewer.os, "open", side_effect=recording_open):
                self.assertEqual(reviewer.read_regular_file_once(path, "artifact"), b"zip")
            self.assertGreaterEqual(len(calls), 3)
            self.assertIsNotNone(calls[-1][2])
            if hasattr(os, "O_NOFOLLOW"):
                self.assertTrue(all(flags & os.O_NOFOLLOW for unused, flags, unused_fd in calls))

    def test_regular_file_rejects_raw_dot_dotdot_and_empty_components(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "artifact.zip"
            path.write_bytes(b"zip")
            cases = (
                ".",
                "..",
                str(Path(temporary)) + "/./artifact.zip",
                str(Path(temporary)) + "/child/../artifact.zip",
                str(Path(temporary)) + "//artifact.zip",
            )
            for raw in cases:
                with self.subTest(raw=raw):
                    with self.assertRaisesRegex(reviewer.BuildReviewError, "path is unsafe"):
                        reviewer.read_regular_file_once(raw, "artifact")

    def test_bound_worktree_input_must_be_mode_0644(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "input"
            path.write_bytes(b"bound")
            path.chmod(0o755)
            with self.assertRaisesRegex(reviewer.BuildReviewError, "mode is not 0644"):
                reviewer.read_regular_file_once(path, "worktree", expected_mode=0o644)

    def test_repository_snapshot_end_rechecks_head(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            unused_git, runtime_head, runtime_tree, unused_current, review = self.make_port_fixture(root)
            real_run_git = reviewer.run_git
            rev_parse_count = [0]

            def moving_head(repo, arguments, allow_failure=False):
                completed = real_run_git(repo, arguments, allow_failure=allow_failure)
                if arguments == ["rev-parse", "HEAD"]:
                    rev_parse_count[0] += 1
                    if rev_parse_count[0] == 2:
                        return subprocess.CompletedProcess(
                            completed.args, 0, stdout=("0" * 40 + "\n").encode("ascii"), stderr=b""
                        )
                return completed

            with mock.patch.multiple(
                reviewer,
                RUNTIME_HEAD_SHA=runtime_head,
                RUNTIME_TREE_SHA=runtime_tree,
            ), mock.patch.object(reviewer, "run_git", side_effect=moving_head):
                with self.assertRaisesRegex(reviewer.BuildReviewError, "snapshot end"):
                    reviewer.validate_repository(root, review)

    def test_repository_snapshot_rechecks_head_after_all_inputs(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            unused_git, runtime_head, runtime_tree, unused_current, review = self.make_port_fixture(root)
            real_run_git = reviewer.run_git
            rev_parse_count = [0]

            def moving_head(repo, arguments, allow_failure=False):
                completed = real_run_git(repo, arguments, allow_failure=allow_failure)
                if arguments == ["rev-parse", "HEAD"]:
                    rev_parse_count[0] += 1
                    if rev_parse_count[0] == 3:
                        return subprocess.CompletedProcess(
                            completed.args,
                            0,
                            stdout=("0" * 40 + "\n").encode("ascii"),
                            stderr=b"",
                        )
                return completed

            with mock.patch.multiple(
                reviewer,
                RUNTIME_HEAD_SHA=runtime_head,
                RUNTIME_TREE_SHA=runtime_tree,
            ), mock.patch.object(reviewer, "run_git", side_effect=moving_head):
                with self.assertRaisesRegex(reviewer.BuildReviewError, "after repository snapshot"):
                    reviewer.validate_repository(root, review)

    def test_repository_snapshot_end_rechecks_every_worktree_input(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            unused_git, runtime_head, runtime_tree, unused_current, review = self.make_port_fixture(root)
            real_read = reviewer.read_regular_file_once

            def changing_input(path, label, expected_mode=None):
                data = real_read(path, label, expected_mode=expected_mode)
                if label == "committed input 0 snapshot end worktree":
                    return data + b"changed"
                return data

            with mock.patch.multiple(
                reviewer,
                RUNTIME_HEAD_SHA=runtime_head,
                RUNTIME_TREE_SHA=runtime_tree,
            ), mock.patch.object(
                reviewer, "read_regular_file_once", side_effect=changing_input
            ):
                with self.assertRaisesRegex(reviewer.BuildReviewError, "snapshot end worktree size"):
                    reviewer.validate_repository(root, review)

    def test_repository_snapshot_end_rehashes_runtime_and_current_git_blobs(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            unused_git, runtime_head, runtime_tree, unused_current, review = self.make_port_fixture(root)
            targets = (
                (
                    review["runtime_candidate"]["committed_inputs"][0]["git_blob_sha1"],
                    "snapshot end runtime size",
                ),
                (
                    review["current_repository_input_policy"]["current_overrides"][0][
                        "current_git_blob_sha1"
                    ],
                    "snapshot end current size",
                ),
            )
            real_run_git = reviewer.run_git
            for target, error in targets:
                with self.subTest(error=error):
                    calls = [0]

                    def disappearing_blob(repo, arguments, allow_failure=False):
                        completed = real_run_git(
                            repo, arguments, allow_failure=allow_failure
                        )
                        if arguments == ["cat-file", "blob", target]:
                            calls[0] += 1
                            if calls[0] == 2:
                                return subprocess.CompletedProcess(
                                    completed.args,
                                    0,
                                    stdout=b"",
                                    stderr=b"",
                                )
                        return completed

                    with mock.patch.multiple(
                        reviewer,
                        RUNTIME_HEAD_SHA=runtime_head,
                        RUNTIME_TREE_SHA=runtime_tree,
                    ), mock.patch.object(
                        reviewer, "run_git", side_effect=disappearing_blob
                    ):
                        with self.assertRaisesRegex(reviewer.BuildReviewError, error):
                            reviewer.validate_repository(root, review)

    def test_config_parser_rejects_duplicate_symbols(self):
        with self.assertRaisesRegex(reviewer.BuildReviewError, "repeats CONFIG_MODULES"):
            reviewer.parse_config(b"CONFIG_MODULES=y\n# CONFIG_MODULES is not set\n")

    def test_config_parser_records_set_and_unset_values(self):
        values = reviewer.parse_config(b"CONFIG_MODULES=y\n# CONFIG_OTHER is not set\n")
        self.assertEqual(values, {"CONFIG_MODULES": "y", "CONFIG_OTHER": "n"})

    def test_checksum_parser_rejects_malformed_duplicate_and_unsorted_rows(self):
        cases = (
            b"bad  file\n",
            (("0" * 64 + "  a\n") * 2).encode("ascii"),
            (("0" * 64 + "  b\n") + ("1" * 64 + "  a\n")).encode("ascii"),
        )
        for data in cases:
            with self.subTest(data=data[:10]):
                with self.assertRaises(reviewer.BuildReviewError):
                    reviewer.parse_sum_manifest(data, "fixture")

    def test_command_record_set_covers_all_thirteen_link_and_compile_records(self):
        records = reviewer.EXPECTED_CMD_RECORDS
        self.assertEqual(len(records), 13)
        self.assertEqual(len({row["path"] for row in records}), 13)
        self.assertEqual(
            {row["kind"] for row in records},
            {"aggregate-link", "final-link", "generated-mod-c-compile", "object-list", "rust-compile"},
        )
        self.assertTrue(all(len(row["sha256"]) == 64 for row in records))
        self.assertTrue(all(len(row["token_sha256"]) == 64 for row in records))
        self.assertTrue(all(len(row["structure_sha256"]) == 64 for row in records))
        self.assertTrue(all(len(row["savedcmd_line_sha256"]) == 64 for row in records))
        self.assertTrue(all(len(row["trailing_lines_sha256"]) == 64 for row in records))
        self.assertEqual(
            {row["path"]: row["token_sha256"] for row in records},
            reviewer.EXACT_CMD_TOKEN_VECTOR_SHA256,
        )

    def test_empty_saved_command_fails_with_review_error(self):
        for payload in (b"", b"\n"):
            with self.subTest(payload=payload):
                with self.assertRaises(reviewer.BuildReviewError):
                    reviewer.parse_saved_command("empty.cmd", payload)

    def test_saved_command_rejects_non_lf_controls_and_unicode_separators(self):
        markers = (
            b"\x00", b"\x09", b"\x0b", b"\x0c", b"\x0d", b"\x1f", b"\x7f",
            "\u0085".encode("utf-8"), "\u2028".encode("utf-8"), "\u2029".encode("utf-8"),
        )
        for marker in markers:
            with self.subTest(marker=marker):
                payload = b"savedcmd_x := true" + marker + b"\n"
                with self.assertRaises(reviewer.BuildReviewError):
                    reviewer.parse_saved_command("control.cmd", payload)

    def test_command_records_have_only_rust_project_sources(self):
        sources = [source for row in reviewer.EXPECTED_CMD_RECORDS for source in row["project_sources"]]
        self.assertTrue(sources)
        self.assertTrue(all(source.endswith(".rs") for source in sources))
        self.assertEqual(
            sorted(sources),
            sorted(row["path"] for row in reviewer.EXPECTED_STAGE_FILES if row["path"].endswith(".rs")),
        )

    def test_module_graph_is_provider_first_and_namespace_closed(self):
        facts = reviewer.EXPECTED_MODULE_FACTS
        self.assertEqual(facts[0]["name"], "ihk")
        self.assertEqual(facts[0]["production_namespace"], "MCKERNEL_IHK_V1")
        for consumer in facts[1:]:
            self.assertEqual(consumer["depends"], ["ihk"])
            self.assertEqual(consumer["import_namespaces"], ["MCKERNEL_IHK_V1"])

    def test_python_source_parses_as_python_3_6(self):
        parse_python_36(MODULE_PATH.read_text(encoding="utf-8"), str(MODULE_PATH))

    def test_python_36_ast_parse_typeerror_falls_back_without_feature_version(self):
        parsed = ast.Module(body=[])
        with mock.patch.object(ast, "parse", side_effect=[TypeError("unsupported"), parsed]) as patched:
            self.assertIs(parse_python_36("x = 1\n", "fixture.py"), parsed)
        self.assertEqual(patched.call_count, 2)
        self.assertIn("feature_version", patched.call_args_list[0][1])
        self.assertNotIn("feature_version", patched.call_args_list[1][1])

    def test_cli_check_mode_fails_closed_on_unreviewed_active_workflow(self):
        completed = subprocess.run(
            [sys.executable, str(MODULE_PATH), "--repo", str(REPO_ROOT), "--check"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        self.assertEqual(completed.returncode, 1)
        self.assertEqual(completed.stdout, b"")
        self.assertIn(
            "committed input 0",
            completed.stderr.decode("utf-8", errors="replace"),
        )

    def test_exact_artifact_verifies_when_available(self):
        self.require_artifact()
        result = reviewer.verify_artifact(self.artifact_path, copy.deepcopy(self.review))
        self.assertEqual(result["cmd_record_count"], 13)
        self.assertEqual(result["module_count"], 3)
        self.assertEqual(result["zip_entry_count"], 43)

    def test_cli_exact_artifact_verifies_when_available(self):
        self.require_artifact()
        completed = subprocess.run(
            [
                sys.executable,
                str(MODULE_PATH),
                "--repo",
                str(REPO_ROOT),
                "--check",
                "--verify-artifact",
                str(self.artifact_path),
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr.decode("utf-8", errors="replace"))
        self.assertTrue(json.loads(completed.stdout.decode("ascii"))["artifact_verified"])

    def test_outer_artifact_digest_and_size_are_exact(self):
        self.require_artifact()
        with self.assertRaisesRegex(reviewer.BuildReviewError, "artifact (size|digest)"):
            reviewer.verify_artifact_bytes(self.artifact_bytes + b"x", copy.deepcopy(self.review))

    def test_zip_duplicate_path_is_rejected(self):
        self.require_artifact()
        data = build_zip(self.artifact_files, duplicate="commit.sha")
        with self.assertRaisesRegex(reviewer.BuildReviewError, "duplicate"):
            reviewer.verify_artifact_bytes(data, copy.deepcopy(self.review), require_outer_identity=False)

    def test_zip_traversal_and_absolute_paths_are_rejected(self):
        self.require_artifact()
        for bad in ("../escape", "/absolute", "a//b", "a\\b"):
            with self.subTest(path=bad):
                files = dict(self.artifact_files)
                files[bad] = files.pop("commit.sha")
                data = build_zip(files)
                with self.assertRaises(reviewer.BuildReviewError):
                    reviewer.verify_artifact_bytes(data, copy.deepcopy(self.review), require_outer_identity=False)

    def test_zip_symlink_mode_is_rejected(self):
        self.require_artifact()
        data = build_zip(
            self.artifact_files,
            metadata={"commit.sha": {"mode": stat.S_IFLNK | 0o777}},
        )
        with self.assertRaisesRegex(reviewer.BuildReviewError, "mode 100644"):
            reviewer.verify_artifact_bytes(data, copy.deepcopy(self.review), require_outer_identity=False)

    def test_zip_executable_mode_is_rejected(self):
        self.require_artifact()
        data = build_zip(
            self.artifact_files,
            metadata={"commit.sha": {"mode": stat.S_IFREG | 0o755}},
        )
        with self.assertRaisesRegex(reviewer.BuildReviewError, "mode 100644"):
            reviewer.verify_artifact_bytes(data, copy.deepcopy(self.review), require_outer_identity=False)

    def test_zip_extra_member_comment_and_archive_comment_are_rejected(self):
        self.require_artifact()
        cases = (
            build_zip(self.artifact_files, metadata={"commit.sha": {"extra": b"\x01\x00\x00\x00"}}),
            build_zip(self.artifact_files, metadata={"commit.sha": {"comment": b"comment"}}),
            build_zip(self.artifact_files, archive_comment=b"comment"),
        )
        for data in cases:
            with self.assertRaises(reviewer.BuildReviewError):
                reviewer.verify_artifact_bytes(data, copy.deepcopy(self.review), require_outer_identity=False)

    def test_inner_checksum_mutation_is_rejected(self):
        self.require_artifact()
        files = dict(self.artifact_files)
        line = files["SHA256SUMS"].splitlines()[0]
        files["SHA256SUMS"] = line.replace(line[:1], b"0" if line[:1] != b"0" else b"1", 1) + b"\n" + b"\n".join(files["SHA256SUMS"].splitlines()[1:]) + b"\n"
        data = build_zip(files)
        with self.assertRaises(reviewer.BuildReviewError):
            reviewer.verify_artifact_bytes(data, copy.deepcopy(self.review), require_outer_identity=False)

    def test_commit_identity_mutation_survives_rehash_but_is_rejected(self):
        self.require_artifact()
        files = dict(self.artifact_files)
        files["commit.sha"] = ("0" * 40 + "\n").encode("ascii")
        data, review = aligned_artifact(files, self.review)
        with self.assertRaisesRegex(reviewer.BuildReviewError, "commit.sha"):
            reviewer.verify_artifact_bytes(data, review, require_outer_identity=False)

    def test_config_symbol_mutation_survives_rehash_but_is_rejected(self):
        self.require_artifact()
        files = dict(self.artifact_files)
        files["resolved.config"] = files["resolved.config"].replace(
            b"CONFIG_MCKERNEL_MCCTRL_RUST=m\n", b"# CONFIG_MCKERNEL_MCCTRL_RUST is not set\n", 1
        )
        data, review = aligned_artifact(files, self.review)
        with self.assertRaisesRegex(reviewer.BuildReviewError, "CONFIG_MCKERNEL_MCCTRL_RUST"):
            reviewer.verify_artifact_bytes(data, review, require_outer_identity=False)

    def test_module_target_order_mutation_survives_rehash_but_is_rejected(self):
        self.require_artifact()
        files = dict(self.artifact_files)
        lines = files["module-targets.txt"].splitlines()
        files["module-targets.txt"] = b"\n".join(reversed(lines)) + b"\n"
        data, review = aligned_artifact(files, self.review)
        with self.assertRaisesRegex(reviewer.BuildReviewError, "module target order"):
            reviewer.verify_artifact_bytes(data, review, require_outer_identity=False)

    def test_rust_command_project_c_injection_survives_rehash_but_is_rejected(self):
        self.require_artifact()
        files = dict(self.artifact_files)
        marker = b" /__w/_temp/native-rust-source/linux-6.12.0-211.44.1.el10_2/drivers/misc/mckernel/injected.c"
        files[".ihk.o.cmd"] = files[".ihk.o.cmd"].replace(b"  ; ./tools/objtool", marker + b"  ; ./tools/objtool", 1)
        data, review = aligned_artifact(files, self.review)
        with self.assertRaisesRegex(
            reviewer.BuildReviewError, "(final Rust source token|forbidden project input)"
        ):
            reviewer.verify_artifact_bytes(data, review, require_outer_identity=False)

    def test_rust_crate_name_mutation_survives_rehash_but_is_rejected(self):
        self.require_artifact()
        files = dict(self.artifact_files)
        files[".ihk.o.cmd"] = files[".ihk.o.cmd"].replace(
            b"--crate-name ihk ", b"--crate-name bad ", 1
        )
        data, review = aligned_artifact(files, self.review)
        with self.assertRaisesRegex(reviewer.BuildReviewError, "crate name"):
            reviewer.verify_artifact_bytes(data, review, require_outer_identity=False)

    def test_rust_root_source_mutation_survives_rehash_but_is_rejected(self):
        self.require_artifact()
        files = dict(self.artifact_files)
        root = b"/__w/_temp/native-rust-source/linux-6.12.0-211.44.1.el10_2/drivers/misc/mckernel/"
        files[".ihk.o.cmd"] = files[".ihk.o.cmd"].replace(
            root + b"ihk.rs", root + b"mcctrl.rs"
        )
        data, review = aligned_artifact(files, self.review)
        with self.assertRaisesRegex(reviewer.BuildReviewError, "primary Rust source"):
            reviewer.verify_artifact_bytes(data, review, require_outer_identity=False)

    def test_object_list_extra_input_survives_rehash_but_is_rejected(self):
        self.require_artifact()
        files = dict(self.artifact_files)
        files[".ihk.mod.cmd"] = files[".ihk.mod.cmd"].replace(
            b"  ihk.o | awk", b"  ihk.o injected.o | awk", 1
        )
        data, review = aligned_artifact(files, self.review)
        with self.assertRaisesRegex(reviewer.BuildReviewError, "object-list tokens"):
            reviewer.verify_artifact_bytes(data, review, require_outer_identity=False)

    def test_aggregate_link_extra_input_survives_rehash_but_is_rejected(self):
        self.require_artifact()
        files = dict(self.artifact_files)
        files[".ihk-smp-x86_64.o.cmd"] = files[".ihk-smp-x86_64.o.cmd"].replace(
            b"@drivers/misc/mckernel/ihk-smp-x86_64.mod  ;",
            b"@drivers/misc/mckernel/ihk-smp-x86_64.mod drivers/misc/mckernel/injected.o  ;",
            1,
        )
        data, review = aligned_artifact(files, self.review)
        with self.assertRaisesRegex(reviewer.BuildReviewError, "aggregate-link tokens"):
            reviewer.verify_artifact_bytes(data, review, require_outer_identity=False)

    def test_final_link_extra_input_before_output_survives_rehash_but_is_rejected(self):
        self.require_artifact()
        files = dict(self.artifact_files)
        files[".ihk.ko.cmd"] = files[".ihk.ko.cmd"].replace(
            b"-T scripts/module.lds -o",
            b"-T scripts/module.lds drivers/misc/mckernel/injected.o -o",
            1,
        )
        data, review = aligned_artifact(files, self.review)
        with self.assertRaisesRegex(reviewer.BuildReviewError, "final-link tokens"):
            reviewer.verify_artifact_bytes(data, review, require_outer_identity=False)

    def test_generated_mod_compile_relative_c_survives_rehash_but_is_rejected(self):
        self.require_artifact()
        files = dict(self.artifact_files)
        files[".ihk.mod.o.cmd"] = files[".ihk.mod.o.cmd"].replace(
            b" drivers/misc/mckernel/ihk.mod.c\n",
            b" drivers/misc/mckernel/injected.c drivers/misc/mckernel/ihk.mod.c\n",
            1,
        )
        data, review = aligned_artifact(files, self.review)
        with self.assertRaisesRegex(reviewer.BuildReviewError, "generated compile inputs"):
            reviewer.verify_artifact_bytes(data, review, require_outer_identity=False)

    def test_rust_shell_suffix_survives_rehash_but_is_rejected(self):
        self.require_artifact()
        files = dict(self.artifact_files)
        command = files[".ihk.o.cmd"]
        line_end = command.index(b"\n")
        files[".ihk.o.cmd"] = (
            command[:line_end] + b" ; /bin/echo injected" + command[line_end:]
        )
        data, review = aligned_artifact(files, self.review)
        with self.assertRaisesRegex(reviewer.BuildReviewError, "Rust shell pipeline"):
            reviewer.verify_artifact_bytes(data, review, require_outer_identity=False)

    def test_generated_mod_shell_splice_survives_rehash_but_is_rejected(self):
        self.require_artifact()
        files = dict(self.artifact_files)
        files[".ihk.mod.o.cmd"] = files[".ihk.mod.o.cmd"].replace(
            b" drivers/misc/mckernel/ihk.mod.c\n",
            b" ; /bin/echo injected ; drivers/misc/mckernel/ihk.mod.c\n",
            1,
        )
        data, review = aligned_artifact(files, self.review)
        with self.assertRaisesRegex(reviewer.BuildReviewError, "shell (expansion/)?control"):
            reviewer.verify_artifact_bytes(data, review, require_outer_identity=False)

    def test_rust_response_and_prebuilt_inputs_survive_rehash_but_are_rejected(self):
        self.require_artifact()
        root = b"/__w/_temp/native-rust-source/linux-6.12.0-211.44.1.el10_2/drivers/misc/mckernel/ihk.rs"
        cases = (
            (b"@drivers/misc/mckernel/injected.rsp", "Rust response inputs"),
            (b"drivers/misc/mckernel/injected.rlib", "forbidden project input"),
            (b"drivers/misc/mckernel/injected.rmeta", "forbidden project input"),
            (b"drivers/misc/mckernel/injected.bc", "forbidden project input"),
        )
        for injected, message in cases:
            with self.subTest(injected=injected):
                files = dict(self.artifact_files)
                files[".ihk.o.cmd"] = files[".ihk.o.cmd"].replace(
                    root, injected + b" " + root, 1
                )
                data, review = aligned_artifact(files, self.review)
                with self.assertRaisesRegex(reviewer.BuildReviewError, message):
                    reviewer.verify_artifact_bytes(data, review, require_outer_identity=False)

    def test_appended_make_shell_line_survives_rehash_but_is_rejected(self):
        self.require_artifact()
        for path in (".ihk.ko.cmd", ".ihk.o.cmd"):
            with self.subTest(path=path):
                files = dict(self.artifact_files)
                files[path] = files[path] + b"probe := $(shell /bin/echo injected)\n"
                data, review = aligned_artifact(files, self.review)
                with self.assertRaisesRegex(reviewer.BuildReviewError, "shell evaluation"):
                    reviewer.verify_artifact_bytes(data, review, require_outer_identity=False)

    def test_trailing_make_shell_assignment_fails_immutable_oracle_after_rebind(self):
        self.require_artifact()
        path = ".ihk.o.cmd"
        data = self.artifact_files[path] + b"probe != /bin/echo injected\n"
        with mock.patch.object(reviewer, "EXPECTED_CMD_RECORDS", rebound_cmd_records(path, data)):
            with self.assertRaisesRegex(
                reviewer.BuildReviewError, "immutable exact trailing-line grammar"
            ):
                reviewer.summarize_cmd(path, data)

    def test_quoted_shell_operators_are_semantically_rejected_after_oracle_rebind(self):
        self.require_artifact()
        mutations = (
            (".ihk.o.cmd", b"  ; ./tools/objtool", b"  ';' ./tools/objtool"),
            (".ihk-smp-x86_64.o.cmd", b"  ; ./tools/objtool", b"  ';' ./tools/objtool"),
            (".ihk.mod.cmd", b" | awk", b" '|' awk"),
            (".ihk.mod.cmd", b" > drivers/misc/mckernel/ihk.mod", b" '>' drivers/misc/mckernel/ihk.mod"),
        )
        for path, before, after in mutations:
            with self.subTest(path=path, operator=before):
                data = self.artifact_files[path].replace(before, after, 1)
                with mock.patch.object(
                    reviewer, "EXPECTED_CMD_RECORDS", rebound_cmd_records(path, data)
                ):
                    with self.assertRaisesRegex(
                        reviewer.BuildReviewError,
                        "(Rust|aggregate-link|object-list) shell (pipeline|grammar) differs",
                    ):
                        reviewer.summarize_cmd(path, data)

    def test_rust_simple_environment_expansion_survives_rehash_but_is_rejected(self):
        self.require_artifact()
        files = dict(self.artifact_files)
        root = b"/__w/_temp/native-rust-source/linux-6.12.0-211.44.1.el10_2/drivers/misc/mckernel/ihk.rs"
        files[".ihk.o.cmd"] = files[".ihk.o.cmd"].replace(
            root, b"$MCKERNEL_INJECT " + root, 1
        )
        data, review = aligned_artifact(files, self.review)
        with self.assertRaisesRegex(reviewer.BuildReviewError, "raw shell expansion"):
            reviewer.verify_artifact_bytes(data, review, require_outer_identity=False)

    def test_generated_mod_attached_redirection_survives_rehash_but_is_rejected(self):
        self.require_artifact()
        files = dict(self.artifact_files)
        files[".ihk.mod.o.cmd"] = files[".ihk.mod.o.cmd"].replace(
            b" drivers/misc/mckernel/ihk.mod.c\n",
            b" x>/tmp/rk007-splice drivers/misc/mckernel/ihk.mod.c\n",
            1,
        )
        data, review = aligned_artifact(files, self.review)
        with self.assertRaisesRegex(reviewer.BuildReviewError, "raw shell expansion"):
            reviewer.verify_artifact_bytes(data, review, require_outer_identity=False)

    def test_rust_attached_semicolon_is_semantically_rejected_after_oracle_rebind(self):
        self.require_artifact()
        path = ".ihk.o.cmd"
        root = b"/__w/_temp/native-rust-source/linux-6.12.0-211.44.1.el10_2/drivers/misc/mckernel/ihk.rs"
        data = self.artifact_files[path].replace(root, b"injected;true " + root, 1)
        with mock.patch.object(reviewer, "EXPECTED_CMD_RECORDS", rebound_cmd_records(path, data)):
            with self.assertRaisesRegex(reviewer.BuildReviewError, "Rust shell pipeline"):
                reviewer.summarize_cmd(path, data)

    def test_rust_project_glob_is_semantically_rejected_after_oracle_rebind(self):
        self.require_artifact()
        path = ".ihk.o.cmd"
        root = b"/__w/_temp/native-rust-source/linux-6.12.0-211.44.1.el10_2/drivers/misc/mckernel/ihk.rs"
        data = self.artifact_files[path].replace(
            root, b"drivers/misc/mckernel/* " + root, 1
        )
        with mock.patch.object(reviewer, "EXPECTED_CMD_RECORDS", rebound_cmd_records(path, data)):
            with self.assertRaisesRegex(reviewer.BuildReviewError, "raw shell expansion/control"):
                reviewer.summarize_cmd(path, data)

    def test_rust_extra_extern_is_semantically_rejected_after_oracle_rebind(self):
        self.require_artifact()
        path = ".ihk.o.cmd"
        root = b"/__w/_temp/native-rust-source/linux-6.12.0-211.44.1.el10_2/drivers/misc/mckernel/ihk.rs"
        data = self.artifact_files[path].replace(root, b"--extern injected " + root, 1)
        with mock.patch.object(reviewer, "EXPECTED_CMD_RECORDS", rebound_cmd_records(path, data)):
            with self.assertRaisesRegex(reviewer.BuildReviewError, "exact Rust extern inputs"):
                reviewer.summarize_cmd(path, data)

    def test_generated_extra_include_is_semantically_rejected_after_oracle_rebind(self):
        self.require_artifact()
        path = ".ihk.mod.o.cmd"
        source = b"drivers/misc/mckernel/ihk.mod.c\n"
        data = self.artifact_files[path].replace(
            source, b"-include drivers/misc/mckernel/injected.h " + source, 1
        )
        with mock.patch.object(reviewer, "EXPECTED_CMD_RECORDS", rebound_cmd_records(path, data)):
            with self.assertRaisesRegex(reviewer.BuildReviewError, "exact generated include inputs"):
                reviewer.summarize_cmd(path, data)

    def test_critical_compiler_option_injections_fail_immutable_token_oracle(self):
        self.require_artifact()
        rust_root = b"/__w/_temp/native-rust-source/linux-6.12.0-211.44.1.el10_2/drivers/misc/mckernel/ihk.rs"
        generated_source = b"drivers/misc/mckernel/ihk.mod.c\n"
        cases = (
            (".ihk.o.cmd", rust_root, b"--cfg injected " + rust_root),
            (".ihk.mod.o.cmd", generated_source, b"-DINJECTED=1 " + generated_source),
            (
                ".ihk.mod.o.cmd",
                generated_source,
                b"-imacros drivers/misc/mckernel/injected.h " + generated_source,
            ),
            (
                ".ihk.mod.o.cmd",
                generated_source,
                b"-Xclang -load -Xclang /tmp/injected-plugin " + generated_source,
            ),
        )
        for path, before, after in cases:
            with self.subTest(path=path, injection=after[:24]):
                data = self.artifact_files[path].replace(before, after, 1)
                with mock.patch.object(
                    reviewer, "EXPECTED_CMD_RECORDS", rebound_cmd_records(path, data)
                ):
                    with self.assertRaisesRegex(
                        reviewer.BuildReviewError, "immutable exact command token vector"
                    ):
                        reviewer.summarize_cmd(path, data)

    def test_unicode_line_separator_is_rejected_after_five_oracle_rebind(self):
        self.require_artifact()
        path = ".ihk.o.cmd"
        original = self.artifact_files[path]
        line_end = original.index(b"\n")
        data = original[:line_end] + "\u2028; /bin/echo injected".encode("utf-8") + original[line_end:]
        records = rebound_cmd_records(path, data, legacy_unicode_splitlines=True)
        with mock.patch.object(reviewer, "EXPECTED_CMD_RECORDS", records):
            with self.assertRaisesRegex(reviewer.BuildReviewError, "strict ASCII"):
                reviewer.summarize_cmd(path, data)

    def test_final_link_extra_object_survives_rehash_but_is_rejected(self):
        self.require_artifact()
        files = dict(self.artifact_files)
        files[".ihk.ko.cmd"] = files[".ihk.ko.cmd"].replace(
            b" .module-common.o\n", b" injected.o .module-common.o\n", 1
        )
        data, review = aligned_artifact(files, self.review)
        with self.assertRaisesRegex(reviewer.BuildReviewError, "final-link tokens"):
            reviewer.verify_artifact_bytes(data, review, require_outer_identity=False)

    def test_stage_lock_prebuilt_input_survives_rehash_but_is_rejected(self):
        self.require_artifact()
        files = dict(self.artifact_files)
        stage = reviewer.read_json_bytes(files["stage-lock.json"], "stage")
        stage["files"][-1]["path"] = "prebuilt.o"
        files["stage-lock.json"] = reviewer.canonical_json_bytes(stage)
        data, review = aligned_artifact(files, self.review)
        with self.assertRaises(reviewer.BuildReviewError):
            reviewer.verify_artifact_bytes(data, review, require_outer_identity=False)

    def test_consumer_dependency_mutation_survives_rehash_but_is_rejected(self):
        self.require_artifact()
        files = dict(self.artifact_files)
        files["mcctrl.ko.modinfo"] = files["mcctrl.ko.modinfo"].replace(b"depends:        ihk", b"depends:        ", 1)
        data, review = aligned_artifact(files, self.review)
        with self.assertRaisesRegex(reviewer.BuildReviewError, "sidecar depends"):
            reviewer.verify_artifact_bytes(data, review, require_outer_identity=False)

    def test_consumer_namespace_mutation_survives_rehash_but_is_rejected(self):
        self.require_artifact()
        files = dict(self.artifact_files)
        files["mcctrl.ko.modinfo"] = files["mcctrl.ko.modinfo"].replace(
            b"import_ns:      MCKERNEL_IHK_V1\n", b"", 1
        )
        data, review = aligned_artifact(files, self.review)
        with self.assertRaisesRegex(reviewer.BuildReviewError, "sidecar (field closure|import_ns)"):
            reviewer.verify_artifact_bytes(data, review, require_outer_identity=False)

    def test_provider_export_mutation_survives_rehash_but_is_rejected(self):
        self.require_artifact()
        files = dict(self.artifact_files)
        files["ihk.ko.nm"] = files["ihk.ko.nm"].replace(
            b"__kstrtabns_ihk_provider_lifecycle_v1", b"__kstrtabns_removed_provider_symbol", 1
        )
        data, review = aligned_artifact(files, self.review)
        with self.assertRaisesRegex(reviewer.BuildReviewError, "provider export"):
            reviewer.verify_artifact_bytes(data, review, require_outer_identity=False)

    def test_binary_modinfo_license_mutation_survives_rehash_but_is_rejected(self):
        self.require_artifact()
        files = dict(self.artifact_files)
        self.assertEqual(files["ihk.ko"].count(b"license=GPL v2\0"), 1)
        files["ihk.ko"] = files["ihk.ko"].replace(
            b"license=GPL v2\0", b"license=GPL xx\0", 1
        )
        data, review = aligned_artifact(files, self.review)
        with self.assertRaisesRegex(reviewer.BuildReviewError, "direct modinfo records"):
            reviewer.verify_artifact_bytes(data, review, require_outer_identity=False)

    def test_binary_provider_symbol_mutation_survives_rehash_but_is_rejected(self):
        self.require_artifact()
        files = dict(self.artifact_files)
        self.assertGreater(files["ihk.ko"].count(b"ihk_provider_lifecycle_v1"), 0)
        files["ihk.ko"] = files["ihk.ko"].replace(
            b"ihk_provider_lifecycle_v1", b"ihk_provider_lifecycle_v2"
        )
        data, review = aligned_artifact(files, self.review)
        with self.assertRaisesRegex(reviewer.BuildReviewError, "provider relocation closure"):
            reviewer.verify_artifact_bytes(data, review, require_outer_identity=False)

    def test_binary_elf_machine_mutation_survives_rehash_but_is_rejected(self):
        self.require_artifact()
        files = dict(self.artifact_files)
        module = bytearray(files["ihk.ko"])
        self.assertEqual(module[18:20], b"\x3e\x00")
        module[18:20] = b"\xb7\x00"
        files["ihk.ko"] = bytes(module)
        data, review = aligned_artifact(files, self.review)
        with self.assertRaisesRegex(reviewer.BuildReviewError, "x86-64 ET_REL"):
            reviewer.verify_artifact_bytes(data, review, require_outer_identity=False)

    def test_consumer_provider_relocations_disconnected_after_rehash_are_rejected(self):
        self.require_artifact()
        files = dict(self.artifact_files)
        module = bytearray(files["mcctrl.ko"])
        parsed = reviewer.parse_elf_module(bytes(module), "mcctrl.ko")
        for relocation_name in (".rela.text", ".rela.init.text"):
            records = [
                row for row in parsed["relocations"][relocation_name]["records"]
                if row["symbol"] == "ihk_provider_lifecycle_v1"
            ]
            self.assertEqual(len(records), 1)
            row = records[0]
            section = parsed["sections"][relocation_name]
            struct.pack_into(
                "<Q", module, section["offset"] + row["index"] * 24 + 8, row["type"]
            )
        files["mcctrl.ko"] = bytes(module)
        data, review = aligned_artifact(files, self.review)
        with self.assertRaisesRegex(reviewer.BuildReviewError, "provider relocation closure"):
            reviewer.verify_artifact_bytes(data, review, require_outer_identity=False)

    def test_provider_export_relocation_symbol_indices_zeroed_after_rehash_are_rejected(self):
        self.require_artifact()
        files = dict(self.artifact_files)
        module = bytearray(files["ihk.ko"])
        parsed = reviewer.parse_elf_module(bytes(module), "ihk.ko")
        section = parsed["sections"][".rela__ksymtab_gpl"]
        records = parsed["relocations"][".rela__ksymtab_gpl"]["records"]
        self.assertEqual(len(records), 3)
        for row in records:
            struct.pack_into(
                "<Q", module, section["offset"] + row["index"] * 24 + 8, row["type"]
            )
        files["ihk.ko"] = bytes(module)
        data, review = aligned_artifact(files, self.review)
        with self.assertRaisesRegex(reviewer.BuildReviewError, "provider relocation closure"):
            reviewer.verify_artifact_bytes(data, review, require_outer_identity=False)

    def test_provider_alloc_section_flags_cleared_after_rehash_are_rejected(self):
        self.require_artifact()
        files = dict(self.artifact_files)
        module = bytearray(files["ihk.ko"])
        parsed = reviewer.parse_elf_module(bytes(module), "ihk.ko")
        section_table = struct.unpack_from("<Q", module, 40)[0]
        for section_name in (".modinfo", "__ksymtab_gpl", "__ksymtab_strings"):
            section = parsed["sections"][section_name]
            flags_offset = section_table + section["index"] * 64 + 8
            flags = struct.unpack_from("<Q", module, flags_offset)[0]
            struct.pack_into("<Q", module, flags_offset, flags & ~0x2)
        files["ihk.ko"] = bytes(module)
        data, review = aligned_artifact(files, self.review)
        with self.assertRaisesRegex(reviewer.BuildReviewError, "shape"):
            reviewer.verify_artifact_bytes(data, review, require_outer_identity=False)

    def test_consumer_code_relocation_target_must_remain_alloc(self):
        self.require_artifact()
        files = dict(self.artifact_files)
        module = bytearray(files["mcctrl.ko"])
        parsed = reviewer.parse_elf_module(bytes(module), "mcctrl.ko")
        section_table = struct.unpack_from("<Q", module, 40)[0]
        section = parsed["sections"][".text"]
        flags_offset = section_table + section["index"] * 64 + 8
        flags = struct.unpack_from("<Q", module, flags_offset)[0]
        struct.pack_into("<Q", module, flags_offset, flags & ~0x2)
        files["mcctrl.ko"] = bytes(module)
        data, review = aligned_artifact(files, self.review)
        with self.assertRaisesRegex(reviewer.BuildReviewError, "(shape|alloc|PROGBITS)"):
            reviewer.verify_artifact_bytes(data, review, require_outer_identity=False)

    def test_consumer_code_relocation_target_must_remain_executable(self):
        self.require_artifact()
        files = dict(self.artifact_files)
        module = bytearray(files["mcctrl.ko"])
        parsed = reviewer.parse_elf_module(bytes(module), "mcctrl.ko")
        section_table = struct.unpack_from("<Q", module, 40)[0]
        section = parsed["sections"][".text"]
        flags_offset = section_table + section["index"] * 64 + 8
        flags = struct.unpack_from("<Q", module, flags_offset)[0]
        struct.pack_into("<Q", module, flags_offset, flags & ~0x4)
        files["mcctrl.ko"] = bytes(module)
        data, review = aligned_artifact(files, self.review)
        with self.assertRaisesRegex(reviewer.BuildReviewError, r"(shape|alloc\+exec)"):
            reviewer.verify_artifact_bytes(data, review, require_outer_identity=False)

    def test_consumer_code_relocation_target_must_remain_progbits(self):
        self.require_artifact()
        files = dict(self.artifact_files)
        module = bytearray(files["mcctrl.ko"])
        parsed = reviewer.parse_elf_module(bytes(module), "mcctrl.ko")
        section_table = struct.unpack_from("<Q", module, 40)[0]
        section = parsed["sections"][".text"]
        type_offset = section_table + section["index"] * 64 + 4
        struct.pack_into("<I", module, type_offset, 8)
        files["mcctrl.ko"] = bytes(module)
        data, review = aligned_artifact(files, self.review)
        with self.assertRaisesRegex(reviewer.BuildReviewError, "(shape|PROGBITS)"):
            reviewer.verify_artifact_bytes(data, review, require_outer_identity=False)

    def test_consumer_pc32_relocation_write_must_fit_target(self):
        self.require_artifact()
        files = dict(self.artifact_files)
        module = bytearray(files["mcctrl.ko"])
        parsed = reviewer.parse_elf_module(bytes(module), "mcctrl.ko")
        section_table = struct.unpack_from("<Q", module, 40)[0]
        relocation = [
            row for row in parsed["relocations"][".rela.init.text"]["records"]
            if row["symbol"] == "ihk_provider_lifecycle_v1"
        ][0]
        section = parsed["sections"][".init.text"]
        size_offset = section_table + section["index"] * 64 + 32
        struct.pack_into("<Q", module, size_offset, relocation["offset"] + 1)
        files["mcctrl.ko"] = bytes(module)
        data, review = aligned_artifact(files, self.review)
        with self.assertRaisesRegex(reviewer.BuildReviewError, "(shape|write exceeds)"):
            reviewer.verify_artifact_bytes(data, review, require_outer_identity=False)

    def test_consumer_provider_relocation_in_unexpected_alloc_section_is_rejected(self):
        self.require_artifact()
        files = dict(self.artifact_files)
        module = bytearray(files["mcctrl.ko"])
        parsed = reviewer.parse_elf_module(bytes(module), "mcctrl.ko")
        relocation = parsed["sections"][".rela.init.data"]
        info_offset = relocation["offset"] + 8
        old_info = struct.unpack_from("<Q", module, info_offset)[0]
        provider_index = parsed["symbols"]["ihk_provider_lifecycle_v1"][0]["index"]
        struct.pack_into(
            "<Q", module, info_offset, (provider_index << 32) | (old_info & 0xffffffff)
        )
        files["mcctrl.ko"] = bytes(module)
        data, review = aligned_artifact(files, self.review)
        with self.assertRaisesRegex(reviewer.BuildReviewError, "provider relocation closure"):
            reviewer.verify_artifact_bytes(data, review, require_outer_identity=False)

    def test_provider_hidden_and_absolute_symbol_mutations_are_rejected(self):
        self.require_artifact()
        original = self.artifact_files["ihk.ko"]
        parsed = reviewer.parse_elf_module(original, "ihk.ko")
        symbol = parsed["symbols"]["ihk_provider_lifecycle_v1"][0]
        symtab = parsed["sections"][".symtab"]
        symbol_offset = symtab["offset"] + symbol["index"] * 24
        cases = (
            ("hidden", 5, b"\x02", "(visibility|st_other)"),
            ("absolute", 6, b"\xf1\xff", "provider (relocation closure|section)"),
        )
        for label, field_offset, replacement, message in cases:
            with self.subTest(label=label):
                files = dict(self.artifact_files)
                module = bytearray(original)
                module[symbol_offset + field_offset:symbol_offset + field_offset + len(replacement)] = replacement
                files["ihk.ko"] = bytes(module)
                data, review = aligned_artifact(files, self.review)
                with self.assertRaisesRegex(reviewer.BuildReviewError, message):
                    reviewer.verify_artifact_bytes(data, review, require_outer_identity=False)

    def test_provider_export_string_symbol_offset_mutation_is_rejected(self):
        self.require_artifact()
        files = dict(self.artifact_files)
        module = bytearray(files["ihk.ko"])
        parsed = reviewer.parse_elf_module(bytes(module), "ihk.ko")
        symbol = parsed["symbols"]["__kstrtabns_ihk_provider_lifecycle_v1"][0]
        symtab = parsed["sections"][".symtab"]
        struct.pack_into("<Q", module, symtab["offset"] + symbol["index"] * 24 + 8, 0)
        files["ihk.ko"] = bytes(module)
        data, review = aligned_artifact(files, self.review)
        with self.assertRaisesRegex(reviewer.BuildReviewError, "__kstrtabns_.* value"):
            reviewer.verify_artifact_bytes(data, review, require_outer_identity=False)

    def test_provider_export_relocation_section_symbol_value_is_exact(self):
        self.require_artifact()
        files = dict(self.artifact_files)
        module = bytearray(files["ihk.ko"])
        parsed = reviewer.parse_elf_module(bytes(module), "ihk.ko")
        symtab = parsed["sections"][".symtab"]
        section_symbol_index = 64
        name, symbol = parsed["symbols_by_index"][section_symbol_index]
        self.assertEqual(name, "")
        self.assertEqual(symbol["type"], 3)
        struct.pack_into(
            "<Q", module, symtab["offset"] + section_symbol_index * 24 + 8, 1
        )
        files["ihk.ko"] = bytes(module)
        data, review = aligned_artifact(files, self.review)
        with self.assertRaisesRegex(reviewer.BuildReviewError, "section-symbol shape"):
            reviewer.verify_artifact_bytes(data, review, require_outer_identity=False)

    def test_provider_object_value_mutation_is_rejected_after_binary_oracle_rebind(self):
        self.require_artifact()
        name = "ihk.ko"
        files = dict(self.artifact_files)
        module = bytearray(files[name])
        parsed = reviewer.parse_elf_module(bytes(module), name)
        symbol_name = reviewer.EXPECTED_PROVIDER_OBJECT["symbol"]
        symbol = parsed["symbols"][symbol_name][0]
        section = parsed["sections"][reviewer.EXPECTED_PROVIDER_OBJECT["section"]]
        object_offset = section["offset"] + symbol["value"]
        self.assertEqual(symbol["size"], 1)
        self.assertEqual(module[object_offset:object_offset + 1], b"\x01")
        original_structure = parsed["structure_sha256"]
        module[object_offset] = 0
        files[name] = bytes(module)
        self.assertEqual(
            reviewer.parse_elf_module(files[name], name)["structure_sha256"],
            original_structure,
        )
        with mock.patch.object(
            reviewer, "EXPECTED_MODULE_FACTS", rebound_module_facts(name, files[name])
        ):
            with self.assertRaisesRegex(
                reviewer.BuildReviewError, "direct provider object content"
            ):
                reviewer.verify_modules(files)

    def test_nonzero_x86_elf_flags_are_rejected(self):
        self.require_artifact()
        files = dict(self.artifact_files)
        module = bytearray(files["mcctrl.ko"])
        struct.pack_into("<I", module, 48, 1)
        files["mcctrl.ko"] = bytes(module)
        data, review = aligned_artifact(files, self.review)
        with self.assertRaisesRegex(reviewer.BuildReviewError, "header fields"):
            reviewer.verify_artifact_bytes(data, review, require_outer_identity=False)

    def test_nonnull_elf_section_zero_is_rejected_after_binary_oracle_rebind(self):
        self.require_artifact()
        name = "mcctrl.ko"
        files = dict(self.artifact_files)
        module = bytearray(files[name])
        section_table = struct.unpack_from("<Q", module, 40)[0]
        struct.pack_into(
            "<IIQQQQIIQQ",
            module,
            section_table,
            0, 1, 0x2, 0, 64, 1, 0, 0, 1, 0,
        )
        files[name] = bytes(module)
        with mock.patch.object(
            reviewer, "EXPECTED_MODULE_FACTS", rebound_module_facts(name, files[name])
        ):
            with self.assertRaisesRegex(reviewer.BuildReviewError, "canonical null section header"):
                reviewer.verify_modules(files)

    def test_nonzero_elf_symbol_zero_is_rejected_after_binary_oracle_rebind(self):
        self.require_artifact()
        name = "mcctrl.ko"
        files = dict(self.artifact_files)
        module = bytearray(files[name])
        parsed = reviewer.parse_elf_module(bytes(module), name)
        symtab = parsed["sections"][".symtab"]
        module[symtab["offset"] + 4] = 0x11
        struct.pack_into("<Q", module, symtab["offset"] + 16, 1)
        files[name] = bytes(module)
        with mock.patch.object(
            reviewer, "EXPECTED_MODULE_FACTS", rebound_module_facts(name, files[name])
        ):
            with self.assertRaisesRegex(reviewer.BuildReviewError, "canonical null symbol"):
                reviewer.verify_modules(files)

    def test_symtab_local_boundary_is_rejected_after_binary_oracle_rebind(self):
        self.require_artifact()
        name = "mcctrl.ko"
        files = dict(self.artifact_files)
        module = bytearray(files[name])
        parsed = reviewer.parse_elf_module(bytes(module), name)
        symtab = parsed["sections"][".symtab"]
        section_table = struct.unpack_from("<Q", module, 40)[0]
        struct.pack_into("<I", module, section_table + symtab["index"] * 64 + 44, 0)
        files[name] = bytes(module)
        with mock.patch.object(
            reviewer, "EXPECTED_MODULE_FACTS", rebound_module_facts(name, files[name])
        ):
            with self.assertRaisesRegex(reviewer.BuildReviewError, "local boundary"):
                reviewer.verify_modules(files)

    def test_non_power_of_two_section_alignment_is_rejected_after_binary_oracle_rebind(self):
        self.require_artifact()
        name = "mcctrl.ko"
        files = dict(self.artifact_files)
        module = bytearray(files[name])
        parsed = reviewer.parse_elf_module(bytes(module), name)
        symtab = parsed["sections"][".symtab"]
        section_table = struct.unpack_from("<Q", module, 40)[0]
        struct.pack_into("<Q", module, section_table + symtab["index"] * 64 + 48, 3)
        files[name] = bytes(module)
        with mock.patch.object(
            reviewer, "EXPECTED_MODULE_FACTS", rebound_module_facts(name, files[name])
        ):
            with self.assertRaisesRegex(reviewer.BuildReviewError, "alignment is not a power of two"):
                reviewer.verify_modules(files)

    def test_nonzero_et_rel_section_address_is_rejected_after_binary_oracle_rebind(self):
        self.require_artifact()
        name = "mcctrl.ko"
        files = dict(self.artifact_files)
        module = bytearray(files[name])
        parsed = reviewer.parse_elf_module(bytes(module), name)
        text_section = parsed["sections"][".text"]
        section_table = struct.unpack_from("<Q", module, 40)[0]
        struct.pack_into("<Q", module, section_table + text_section["index"] * 64 + 16, 1)
        files[name] = bytes(module)
        with mock.patch.object(
            reviewer, "EXPECTED_MODULE_FACTS", rebound_module_facts(name, files[name])
        ):
            with self.assertRaisesRegex(reviewer.BuildReviewError, "nonzero address"):
                reviewer.verify_modules(files)

    def test_unbacked_symbol_xindex_is_rejected_after_binary_oracle_rebind(self):
        self.require_artifact()
        name = "mcctrl.ko"
        files = dict(self.artifact_files)
        module = bytearray(files[name])
        parsed = reviewer.parse_elf_module(bytes(module), name)
        symtab = parsed["sections"][".symtab"]
        symbol_index = 52
        struct.pack_into("<H", module, symtab["offset"] + symbol_index * 24 + 6, 0xffff)
        files[name] = bytes(module)
        with mock.patch.object(
            reviewer, "EXPECTED_MODULE_FACTS", rebound_module_facts(name, files[name])
        ):
            with self.assertRaisesRegex(reviewer.BuildReviewError, "unsupported SHN_XINDEX"):
                reviewer.verify_modules(files)

    def test_every_relocation_write_is_bounded_after_binary_oracle_rebind(self):
        self.require_artifact()
        name = "mcctrl.ko"
        files = dict(self.artifact_files)
        module = bytearray(files[name])
        parsed = reviewer.parse_elf_module(bytes(module), name)
        relocation = parsed["sections"][".rela.text"]
        target = parsed["sections"][".text"]
        struct.pack_into("<Q", module, relocation["offset"] + 24, target["size"] + 8)
        files[name] = bytes(module)
        with mock.patch.object(
            reviewer, "EXPECTED_MODULE_FACTS", rebound_module_facts(name, files[name])
        ):
            with self.assertRaisesRegex(reviewer.BuildReviewError, "write exceeds its target"):
                reviewer.verify_modules(files)

    def test_unrelated_valid_elf_shape_drift_fails_immutable_structure_oracle(self):
        self.require_artifact()
        name = "mcctrl.ko"
        files = dict(self.artifact_files)
        module = bytearray(files[name])
        parsed = reviewer.parse_elf_module(bytes(module), name)
        debug_info = parsed["sections"][".debug_info"]
        section_table = struct.unpack_from("<Q", module, 40)[0]
        flags_offset = section_table + debug_info["index"] * 64 + 8
        flags = struct.unpack_from("<Q", module, flags_offset)[0]
        struct.pack_into("<Q", module, flags_offset, flags | 0x2)
        files[name] = bytes(module)
        with mock.patch.object(
            reviewer, "EXPECTED_MODULE_FACTS", rebound_module_facts(name, files[name])
        ):
            with self.assertRaisesRegex(reviewer.BuildReviewError, "immutable exact ELF structure"):
                reviewer.verify_modules(files)

    def test_inline_this_module_name_mismatch_is_rejected_after_binary_oracle_rebind(self):
        self.require_artifact()
        name = "mcctrl.ko"
        files = dict(self.artifact_files)
        module = bytearray(files[name])
        parsed = reviewer.parse_elf_module(bytes(module), name)
        this_section = parsed["sections"][".gnu.linkonce.this_module"]
        name_offset = this_section["offset"] + 24
        self.assertEqual(module[name_offset:name_offset + 7], b"mcctrl\0")
        module[name_offset:name_offset + 7] = b"badctl\0"
        files[name] = bytes(module)
        with mock.patch.object(
            reviewer, "EXPECTED_MODULE_FACTS", rebound_module_facts(name, files[name])
        ):
            with self.assertRaisesRegex(reviewer.BuildReviewError, "inline this_module name field"):
                reviewer.verify_modules(files)

    def test_all_loader_note_payloads_are_rejected_after_binary_oracle_rebind(self):
        self.require_artifact()
        name = "ihk.ko"
        original = self.artifact_files[name]
        parsed = reviewer.parse_elf_module(original, name)
        for section_name in (".note.gnu.build-id", ".note.Linux", ".note.gnu.property"):
            with self.subTest(section=section_name):
                files = dict(self.artifact_files)
                module = bytearray(original)
                section = parsed["sections"][section_name]
                name_size = struct.unpack_from("<I", module, section["offset"])[0]
                description_offset = section["offset"] + 12 + ((name_size + 3) & ~3)
                module[description_offset] ^= 1
                files[name] = bytes(module)
                with mock.patch.object(
                    reviewer, "EXPECTED_MODULE_FACTS", rebound_module_facts(name, files[name])
                ):
                    with self.assertRaisesRegex(
                        reviewer.BuildReviewError, r"\.note\..* exact records"
                    ):
                        reviewer.verify_modules(files)

    def test_provider_export_relocation_target_section_mutation_is_rejected(self):
        self.require_artifact()
        files = dict(self.artifact_files)
        module = bytearray(files["ihk.ko"])
        parsed = reviewer.parse_elf_module(bytes(module), "ihk.ko")
        section_table = struct.unpack_from("<Q", module, 40)[0]
        relocation = parsed["sections"][".rela__ksymtab_gpl"]
        info_offset = section_table + relocation["index"] * 64 + 44
        struct.pack_into("<I", module, info_offset, parsed["sections"][".text"]["index"])
        files["ihk.ko"] = bytes(module)
        data, review = aligned_artifact(files, self.review)
        with self.assertRaisesRegex(reviewer.BuildReviewError, "provider relocation closure"):
            reviewer.verify_artifact_bytes(data, review, require_outer_identity=False)

    def test_provider_export_relocation_symbol_table_link_mutation_is_rejected(self):
        self.require_artifact()
        files = dict(self.artifact_files)
        module = bytearray(files["ihk.ko"])
        parsed = reviewer.parse_elf_module(bytes(module), "ihk.ko")
        section_table = struct.unpack_from("<Q", module, 40)[0]
        relocation = parsed["sections"][".rela__ksymtab_gpl"]
        link_offset = section_table + relocation["index"] * 64 + 40
        struct.pack_into("<I", module, link_offset, parsed["sections"][".strtab"]["index"])
        files["ihk.ko"] = bytes(module)
        data, review = aligned_artifact(files, self.review)
        with self.assertRaisesRegex(reviewer.BuildReviewError, "relocation section shape"):
            reviewer.verify_artifact_bytes(data, review, require_outer_identity=False)

    def test_direct_smp_parameter_type_mutation_survives_rehash_but_is_rejected(self):
        self.require_artifact()
        files = dict(self.artifact_files)
        self.assertEqual(files["ihk-smp-x86_64.ko"].count(b"parmtype=ihk_mem:ulong\0"), 1)
        files["ihk-smp-x86_64.ko"] = files["ihk-smp-x86_64.ko"].replace(
            b"parmtype=ihk_mem:ulong\0", b"parmtype=ihk_mem:xxxxx\0", 1
        )
        data, review = aligned_artifact(files, self.review)
        with self.assertRaisesRegex(reviewer.BuildReviewError, "exact direct modinfo records"):
            reviewer.verify_artifact_bytes(data, review, require_outer_identity=False)

    def test_loader_parameter_name_mismatch_is_rejected_after_binary_oracle_rebind(self):
        self.require_artifact()
        name = "ihk-smp-x86_64.ko"
        files = dict(self.artifact_files)
        module = bytearray(files[name])
        parsed = reviewer.parse_elf_module(bytes(module), name)
        rodata = parsed["sections"][".rodata"]
        name_offset = rodata["offset"] + 86
        self.assertEqual(module[name_offset:name_offset + 8], b"ihk_mem\0")
        module[name_offset:name_offset + 8] = b"bad_mem\0"
        files[name] = bytes(module)
        with mock.patch.object(
            reviewer, "EXPECTED_MODULE_FACTS", rebound_module_facts(name, files[name])
        ):
            with self.assertRaisesRegex(
                reviewer.BuildReviewError, "(parameter-name rodata content|loader name)"
            ):
                reviewer.verify_modules(files)

    def test_bzimage_header_mutation_survives_rehash_but_is_rejected(self):
        self.require_artifact()
        files = dict(self.artifact_files)
        image = bytearray(files["bzImage"])
        image[0x202:0x206] = b"BAD!"
        files["bzImage"] = bytes(image)
        data, review = aligned_artifact(files, self.review)
        with self.assertRaisesRegex(reviewer.BuildReviewError, "boot header"):
            reviewer.verify_artifact_bytes(data, review, require_outer_identity=False)


if __name__ == "__main__":
    unittest.main()
