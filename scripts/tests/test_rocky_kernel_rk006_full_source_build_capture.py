#!/usr/bin/env python3
"""Focused tests for the non-crediting RK-006 source/build capture."""

from __future__ import print_function

import copy
import hashlib
import io
import json
import os
from pathlib import Path
import re
import shutil
import stat
import subprocess
import sys
import tarfile
import tempfile
import unittest
from unittest import mock

from scripts import rocky_kernel_rk006_full_source_build_capture as capture


REPO_ROOT = Path(__file__).resolve().parents[2]
CONTRACT = REPO_ROOT / capture.CONTRACT_PATH


class Rk006FullSourceBuildCaptureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
        cls.authority = json.loads(
            (REPO_ROOT / capture.AUTHORITY_PATH).read_text(encoding="utf-8")
        )

    def _fixture_source(self, parent):
        source = parent / "linux"
        shutil.copytree(
            str(REPO_ROOT / "scripts/tests/fixtures/rust-core-rocky-6.12"),
            str(source),
        )
        generator = source / "scripts/generate_rust_target.rs"
        generator.write_bytes(
            (REPO_ROOT / "scripts/tests/fixtures/generate-rust-target-rocky-6.12.rs").read_bytes()
        )
        misc = source / "drivers/misc"
        misc.mkdir(parents=True, exist_ok=True)
        (misc / "Makefile").write_text(
            "obj-$(CONFIG_NSM)\t\t+= nsm.o\n"
            "obj-$(CONFIG_MARVELL_CN10K_DPI)\t+= mrvl_cn10k_dpi.o\n"
            "obj-y\t\t\t\t+= keba/\n",
            encoding="utf-8",
        )
        (misc / "Kconfig").write_text(
            'source "drivers/misc/pvpanic/Kconfig"\n'
            'source "drivers/misc/mchp_pci1xxxx/Kconfig"\n'
            'source "drivers/misc/keba/Kconfig"\n'
            "endmenu\n",
            encoding="utf-8",
        )
        return source

    def test_git_identity_ignores_inherited_repository_and_loader_overrides(self):
        with tempfile.TemporaryDirectory(prefix="rk006-git-identity-") as raw:
            root = Path(raw)
            repositories = []
            heads = []
            for name in ("a", "b"):
                repo = root / name
                repo.mkdir()
                subprocess.run(
                    ["/usr/bin/git", "init", "-q", str(repo)], check=True
                )
                (repo / "tracked").write_text(name + "\n", encoding="ascii")
                subprocess.run(
                    ["/usr/bin/git", "-C", str(repo), "add", "tracked"],
                    check=True,
                )
                subprocess.run(
                    [
                        "/usr/bin/git",
                        "-c",
                        "user.name=RK006 Test",
                        "-c",
                        "user.email=rk006@example.invalid",
                        "-C",
                        str(repo),
                        "commit",
                        "-q",
                        "-m",
                        name,
                    ],
                    check=True,
                )
                head = subprocess.run(
                    ["/usr/bin/git", "-C", str(repo), "rev-parse", "HEAD"],
                    check=True,
                    stdout=subprocess.PIPE,
                    text=True,
                ).stdout.strip()
                repositories.append(repo)
                heads.append(head)
            hostile = {
                "GIT_DIR": str(repositories[1] / ".git"),
                "GIT_WORK_TREE": str(repositories[1]),
                "LD_AUDIT": str(root / "attacker-audit.so"),
                "LD_PRELOAD": str(root / "attacker-preload.so"),
                "PATH": str(root),
            }
            with mock.patch.dict(os.environ, hostile, clear=False):
                capture._check_git_identity(repositories[0], heads[0])
                with self.assertRaisesRegex(
                    capture.CaptureError, "checked-out HEAD differs"
                ):
                    capture._check_git_identity(repositories[0], heads[1])

    def _build_evidence(self, directory, head="a" * 40):
        contents = {}
        names = sorted(
            set(capture.REQUIRED_BUILD_MEMBERS)
            | set(capture.PRECHECK_BUILD_MEMBERS)
        )
        for name in names:
            if name in ("PRECHECK_SHA256SUMS", "SHA256SUMS"):
                continue
            contents[name] = (name + "\n").encode("ascii")
        contents["commit.sha"] = (head + "\n").encode("ascii")
        contents["build.phase"] = b"complete\n"
        contents["build.exit-code"] = b"0\n"
        contents["build-log.exit-code"] = b"0\n"
        contents["build.environment"] = capture.REPRODUCIBLE_BUILD_ENVIRONMENT_BYTES
        contents["workflow-state"] = b"bootstrap-complete\n"
        contents["PRECHECK_SHA256SUMS"] = "".join(
            "{}  {}\n".format(hashlib.sha256(contents[name]).hexdigest(), name)
            for name in capture.PRECHECK_BUILD_MEMBERS
        ).encode("ascii")
        for name, data in contents.items():
            path = directory / name
            path.write_bytes(data)
            path.chmod(0o644)
        manifest = "".join(
            "{}  {}\n".format(hashlib.sha256(contents[name]).hexdigest(), name)
            for name in sorted(contents)
        )
        (directory / "SHA256SUMS").write_text(manifest, encoding="ascii")
        (directory / "SHA256SUMS").chmod(0o644)

    def _synthetic_tool_probes(self):
        probes = {}
        owner_prefix = [
            "rpm",
            "-qf",
            "--qf",
            "%{NAME}-%{EPOCHNUM}:%{VERSION}-%{RELEASE}.%{ARCH}\\n",
        ]
        empty_digest = hashlib.sha256(b"").hexdigest()
        for probe_id, identity in sorted(capture.LOCKED_PROBES.items()):
            probes[probe_id] = {
                "binary_path": identity["path"],
                "binary_sha256": identity["sha256"],
                "command": identity["command"],
                "owner_command": owner_prefix + [identity["path"]],
                "package_nevra": identity["owner"],
                "stderr_sha256": empty_digest,
                "stdout_sha256": identity["stdout_sha256"],
                "text": probe_id + " locked version\n",
            }
        probes["rust_src_core"] = {
            "command": ["rustc", "--print", "sysroot"],
            "file_path": capture.RUST_SRC_CORE["path"],
            "file_sha256": capture.RUST_SRC_CORE["sha256"],
            "owner_command": owner_prefix + [capture.RUST_SRC_CORE["path"]],
            "package_nevra": capture.RUST_SRC_CORE["owner"],
            "stderr_sha256": empty_digest,
            "stdout_sha256": capture.RUST_SRC_CORE["stdout_sha256"],
        }
        versions = {
            "patch": "GNU patch 2.7.6\n",
            "python3": "Python 3.12.13\n",
        }
        owners = {
            "patch": "patch-0:2.7.6-26.el10.x86_64",
            "python3": "python3-0:3.12.13-2.el10_2.1.x86_64",
        }
        for probe_id, identity in sorted(capture.CAPTURE_TOOL_PROBES.items()):
            text = versions[probe_id]
            probes[probe_id] = {
                "binary_path": identity["path"],
                "binary_resolved_path": identity["resolved_path"],
                "binary_sha256": "0" * 64,
                "command": identity["command"],
                "owner_command": owner_prefix + [identity["path"]],
                "package_nevra": owners[probe_id],
                "stderr_sha256": empty_digest,
                "stdout_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
                "text": text,
            }
        return {
            "claims": dict(capture.FALSE_CLAIMS),
            "environment": dict(capture.CAPTURE_ENV),
            "probe_count": len(probes),
            "probes": probes,
            "schema_version": 1,
        }

    def _two_hop_probe_fixture(self, root):
        logical_parent = root / "bin"
        intermediate_parent = root / "alternatives"
        target_parent = root / "llvm21-bin"
        logical_parent.mkdir()
        intermediate_parent.mkdir()
        target_parent.mkdir()
        target = target_parent / "llvm-config"
        target_bytes = b"#!/bin/sh\nprintf '21.1.8\\n'\n"
        target.write_bytes(target_bytes)
        target.chmod(0o755)
        intermediate = intermediate_parent / "llvm-config"
        intermediate.symlink_to(str(target))
        logical = logical_parent / "llvm-config"
        logical.symlink_to(str(intermediate))
        expected = {
            "command": ["llvm-config", "--version"],
            "symlink_hops": [
                {"path": str(logical), "target": str(intermediate)},
                {"path": str(intermediate), "target": str(target)},
            ],
        }
        return {
            "expected": expected,
            "intermediate": intermediate,
            "intermediate_parent": intermediate_parent,
            "logical": logical,
            "logical_parent": logical_parent,
            "target": target,
            "target_bytes": target_bytes,
            "target_parent": target_parent,
        }

    def test_contract_and_all_frozen_inputs_validate(self):
        contract_value, authority = capture.validate_contract(REPO_ROOT)
        self.assertEqual("rk-006-full-source-build-capture-v1", contract_value["capture_contract_id"])
        self.assertEqual(26, len(authority["patches"]))

    def test_contract_cli_is_noncrediting(self):
        completed = subprocess.run(
            [
                sys.executable,
                str(REPO_ROOT / capture.CAPTURE_SCRIPT_PATH),
                "check-contract",
                "--repo",
                str(REPO_ROOT),
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True,
        )
        self.assertEqual(0, completed.returncode, completed.stderr)
        self.assertIn("non-crediting", completed.stdout)
        self.assertNotIn("RK-006: PASS", completed.stdout)

    def test_every_credit_review_and_durability_claim_is_false(self):
        self.assertEqual(capture.FALSE_CLAIMS, self.contract["claims"])
        self.assertEqual(capture.FALSE_GATE, self.contract["gate"])
        self.assertFalse(self.contract["artifact_policy"]["artifact_is_durable"])
        self.assertFalse(self.contract["build_binding_policy"]["build_artifact_is_durable"])
        self.assertEqual(0, self.contract["gate"]["points_awarded"])

    def test_contract_binds_authority_locks_and_full_parent_hashes(self):
        expected = {
            "patch_authority": "0c40d8079b3c5f6b90e44f1067f89f27c5c7ac50c67a127609a34a10c224475b",
            "patch_authority_checker": "ee0ef72baf560c1a4412ff0140b950f0f8456d4291154186af339320a1ec21da",
            "patch_authority_tests": "bb829109b32b2474b0edeb06e2121b42aff4edb4a3103ea80cf6a9520e775b3b",
            "source_lock": "b70df1e475072dbfa31fdc712900ac59d30eeb139219c7076aacaa19abf0fded",
            "toolchain_lock": "fd3d7a13e1b8b5d103f7e59d22f17c9e4b99cc937637decaa66749acfae6c802",
        }
        for key, digest in expected.items():
            self.assertEqual(digest, self.contract["inputs"][key]["sha256"])
        self.assertEqual(capture.PARENT_FILES, self.contract["parent_files"])
        self.assertEqual(
            {"drivers/misc/Kconfig", "drivers/misc/Makefile"},
            {row["path"] for row in self.contract["parent_files"]},
        )

    def test_contract_rejects_every_frozen_policy_and_blocker_mutation(self):
        mutations = (
            (("artifact_policy", "member_mode"), "0444"),
            (("build_binding_policy", "build_evidence_checksum_manifest"), "SUMS"),
            (("capture_policy", "external_closure_algorithm"), "other"),
            (("capture_policy", "full_source_closure_algorithm"), "other"),
            (("capture_policy", "patch_order_source"), "other.json"),
            (("capture_policy", "snapshot_archive_format"), "tar"),
            (("capture_policy", "snapshot_member_mode"), "0644"),
            (("capture_policy", "snapshot_mtime"), False),
            (("capture_policy", "source_archive_extraction_owned_by_capture"), False),
        )
        for path, value in mutations:
            with self.subTest(path=path):
                contract = copy.deepcopy(self.contract)
                contract[path[0]][path[1]] = value
                with self.assertRaises(capture.CaptureError):
                    capture._validate_contract_structure(contract)
        contract = copy.deepcopy(self.contract)
        contract["remaining_blockers"][0] = "weakened"
        with self.assertRaises(capture.CaptureError):
            capture._validate_contract_structure(contract)
        self.assertEqual("0644", self.contract["artifact_policy"]["member_mode"])
        self.assertEqual("0444", self.contract["capture_policy"]["snapshot_member_mode"])
        with tempfile.TemporaryDirectory() as directory:
            capture._write_atomic(Path(directory), "member", b"transported\n")
            self.assertEqual(
                0o644, stat.S_IMODE((Path(directory) / "member").stat().st_mode)
            )

    def test_fixture_replays_all_26_patches_and_rejects_every_second_apply(self):
        with tempfile.TemporaryDirectory() as directory:
            source = self._fixture_source(Path(directory))
            replay = capture._replay_patch_series(
                REPO_ROOT, source, self.authority, enforce_parent_hashes=False
            )
        self.assertEqual(26, len(replay["patch_records"]))
        self.assertEqual(list(range(1, 27)), [row["order"] for row in replay["patch_records"]])
        second = [json.loads(line) for line in replay["second_log"].splitlines()]
        self.assertEqual(26, len(second))
        self.assertTrue(all(row["returncode"] != 0 for row in second))
        self.assertNotEqual(
            self.authority["source_binding"]["fixture_preimage_closure_sha256"],
            replay["external_initial_closure"]["sha256"],
            "the external closure must not be assumed to equal the authority fixture closure",
        )

    def test_patch_log_cardinality_binds_vendor_plus_every_authority_patch(self):
        apply_rows = [{"kind": "vendor-apply"}] + [
            {"id": row["id"]} for row in self.authority["patches"]
        ]
        second_rows = [
            {"id": row["id"], "returncode": 1}
            for row in self.authority["patches"]
        ]
        self.assertEqual(27, len(apply_rows))
        self.assertEqual(26, len(second_rows))
        capture._validate_patch_log_cardinality(
            apply_rows, second_rows, self.authority
        )

        mutations = (
            ("missing-apply", apply_rows[:-1], second_rows),
            ("extra-apply", apply_rows + [dict(apply_rows[-1])], second_rows),
            (
                "wrong-vendor-kind",
                [dict(apply_rows[0], kind="apply")] + apply_rows[1:],
                second_rows,
            ),
            ("missing-second", apply_rows, second_rows[:-1]),
            ("extra-second", apply_rows, second_rows + [dict(second_rows[-1])]),
            (
                "successful-second",
                apply_rows,
                [dict(second_rows[0], returncode=0)] + second_rows[1:],
            ),
        )
        for label, mutated_apply, mutated_second in mutations:
            with self.subTest(label=label):
                with self.assertRaises(capture.CaptureError):
                    capture._validate_patch_log_cardinality(
                        mutated_apply, mutated_second, self.authority
                    )

    def test_replay_relationships_bind_closures_continuity_and_parent_bytes(self):
        with tempfile.TemporaryDirectory() as directory:
            source = self._fixture_source(Path(directory))
            replay = capture._replay_patch_series(
                REPO_ROOT, source, self.authority, enforce_parent_hashes=False
            )
        document = {
            "external_final_closure": replay["external_final_closure"],
            "external_initial_closure": replay["external_initial_closure"],
            "patch_replay": replay["patch_records"],
            "touched_path_count": replay["touched_path_count"],
        }
        capture._validate_replay_relationships(
            document, self.authority, enforce_parent_hashes=False
        )
        closure_mutation = copy.deepcopy(document)
        closure_mutation["patch_replay"][0]["before"]["sha256"] = "0" * 64
        with self.assertRaisesRegex(capture.CaptureError, "preimage closure"):
            capture._validate_replay_relationships(
                closure_mutation, self.authority, enforce_parent_hashes=False
            )
        global_mutation = copy.deepcopy(document)
        global_mutation["external_final_closure"]["sha256"] = "0" * 64
        with self.assertRaisesRegex(capture.CaptureError, "external final closure"):
            capture._validate_replay_relationships(
                global_mutation, self.authority, enforce_parent_hashes=False
            )
        with self.assertRaisesRegex(capture.CaptureError, "full parent bytes"):
            capture._validate_replay_relationships(
                document, self.authority, enforce_parent_hashes=True
            )

    def test_fixture_snapshots_are_safe_regular_deterministic_members(self):
        with tempfile.TemporaryDirectory() as directory:
            source = self._fixture_source(Path(directory))
            replay = capture._replay_patch_series(
                REPO_ROOT, source, self.authority, enforce_parent_hashes=False
            )
        pre = capture._inspect_tar(replay["preimages"], "preimages")
        post = capture._inspect_tar(replay["postimages"], "postimages")
        self.assertTrue(pre)
        self.assertTrue(post)
        self.assertEqual(sorted(row["path"] for row in pre), [row["path"] for row in pre])
        self.assertTrue(any("parent-001/drivers/misc/Makefile" in row["path"] for row in pre))
        self.assertTrue(any("parent-001/drivers/misc/Kconfig" in row["path"] for row in post))

    def test_full_parent_hash_check_rejects_repository_fixture_parent_bytes(self):
        with tempfile.TemporaryDirectory() as directory:
            source = self._fixture_source(Path(directory))
            with self.assertRaisesRegex(capture.CaptureError, "full parent preimage"):
                capture._replay_patch_series(
                    REPO_ROOT, source, self.authority, enforce_parent_hashes=True
                )

    def test_external_file_binding_rejects_wrong_bytes_and_filename(self):
        record = self.contract["inputs"]["vendor_patch"]
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            wrong = root / record["filename"]
            wrong.write_bytes(b"not the locked vendor patch")
            with self.assertRaisesRegex(capture.CaptureError, "bytes differ"):
                capture._verify_exact_external(wrong, record, "vendor patch")
            renamed = root / "renamed.patch"
            renamed.write_bytes(b"not the locked vendor patch")
            with self.assertRaisesRegex(capture.CaptureError, "filename differs"):
                capture._verify_exact_external(renamed, record, "vendor patch")

    def test_rooted_reads_reject_symlinks_and_hardlinks(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            original = root / "original"
            original.write_bytes(b"value")
            symlink = root / "symlink"
            symlink.symlink_to(original.name)
            with self.assertRaises(capture.CaptureError):
                capture._read_rooted(root, "symlink", "symlink")
            hardlink = root / "hardlink"
            os.link(str(original), str(hardlink))
            with self.assertRaisesRegex(capture.CaptureError, "hard-linked"):
                capture._read_rooted(root, "hardlink", "hardlink")

    def test_locked_probe_symlink_preserves_logical_owner_and_target_digest(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            target = root / "clang-21"
            target_bytes = b"#!/bin/sh\nprintf 'clang version 21.1.8\\n'\n"
            target.write_bytes(target_bytes)
            target.chmod(0o755)
            logical = root / "clang"
            logical.symlink_to(target.name)
            version = b"clang version 21.1.8\n"
            owner = "clang-0:21.1.8-1.el10.x86_64"
            identity = {
                "command": ["clang", "--version"],
                "owner": owner,
                "path": str(logical),
                "sha256": hashlib.sha256(target_bytes).hexdigest(),
                "stdout_sha256": hashlib.sha256(version).hexdigest(),
                "symlink_hops": [
                    {"path": str(logical), "target": target.name},
                ],
            }
            core = root / "lib/rustlib/src/rust/library/core/src/lib.rs"
            core.parent.mkdir(parents=True)
            core_bytes = b"#![no_std]\n"
            core.write_bytes(core_bytes)
            core_owner = "rust-src-0:1.92.0-1.el10.noarch"
            core_stdout = (str(root) + "\n").encode("utf-8")

            def run(command, cwd=None, env=None, allow_failure=False):
                del cwd, env, allow_failure
                if command == ["rustc", "--print", "sysroot"]:
                    return subprocess.CompletedProcess(command, 0, core_stdout, b"")
                raise AssertionError("unexpected command: {!r}".format(command))

            def rpm_owner(path):
                path = str(path)
                package = owner if path == str(logical) else core_owner
                command = [
                    "rpm",
                    "-qf",
                    "--qf",
                    "%{NAME}-%{EPOCHNUM}:%{VERSION}-%{RELEASE}.%{ARCH}\\n",
                    path,
                ]
                return package, command

            rust_src = {
                "owner": core_owner,
                "path": str(core),
                "sha256": hashlib.sha256(core_bytes).hexdigest(),
                "stdout_sha256": hashlib.sha256(core_stdout).hexdigest(),
            }
            with mock.patch.object(capture, "LOCKED_PROBES", {"clang": identity}), \
                    mock.patch.object(capture, "CAPTURE_TOOL_PROBES", {}), \
                    mock.patch.object(capture, "RUST_SRC_CORE", rust_src), \
                    mock.patch.object(capture.shutil, "which", return_value=str(logical)), \
                    mock.patch.object(capture, "_rpm_owner", side_effect=rpm_owner), \
                    mock.patch.object(capture, "_run", side_effect=run):
                document = capture._probe_tools()

            probe = document["probes"]["clang"]
            self.assertEqual(str(logical), probe["binary_path"])
            self.assertEqual(owner, probe["package_nevra"])
            self.assertEqual(
                [
                    "rpm",
                    "-qf",
                    "--qf",
                    "%{NAME}-%{EPOCHNUM}:%{VERSION}-%{RELEASE}.%{ARCH}\\n",
                    str(logical),
                ],
                probe["owner_command"],
            )
            self.assertEqual(hashlib.sha256(target_bytes).hexdigest(), probe["binary_sha256"])

    def test_locked_probe_table_binds_exact_rocky_regular_and_symlink_shapes(self):
        expected_hops = {
            "clang": [
                {"path": "/usr/bin/clang", "target": "clang-21"},
            ],
            "lld": [
                {"path": "/usr/bin/ld.lld", "target": "lld"},
            ],
            "llvm": [
                {
                    "path": "/usr/bin/llvm-config",
                    "target": "/etc/alternatives/llvm-config",
                },
                {
                    "path": "/etc/alternatives/llvm-config",
                    "target": "/usr/lib64/llvm21/bin/llvm-config",
                },
            ],
        }
        self.assertEqual(
            expected_hops,
            {
                probe_id: capture.LOCKED_PROBES[probe_id]["symlink_hops"]
                for probe_id in sorted(expected_hops)
            },
        )
        for probe_id in ("bindgen", "pahole", "rustc"):
            self.assertNotIn("symlink_hops", capture.LOCKED_PROBES[probe_id])

    def test_locked_probe_lld_and_llvm_alternatives_bind_logical_owner_and_target(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            binary_parent = root / "bin"
            binary_parent.mkdir()

            lld_target = binary_parent / "lld"
            lld_bytes = b"#!/bin/sh\nprintf 'LLD 21.1.8\\n'\n"
            lld_target.write_bytes(lld_bytes)
            lld_target.chmod(0o755)
            lld_logical = binary_parent / "ld.lld"
            lld_logical.symlink_to(lld_target.name)

            llvm_target_parent = root / "llvm21-bin"
            llvm_target_parent.mkdir()
            llvm_target = llvm_target_parent / "llvm-config"
            llvm_bytes = b"#!/bin/sh\nprintf '21.1.8\\n'\n"
            llvm_target.write_bytes(llvm_bytes)
            llvm_target.chmod(0o755)
            alternatives = root / "alternatives"
            alternatives.mkdir()
            llvm_intermediate = alternatives / "llvm-config"
            llvm_intermediate.symlink_to(str(llvm_target))
            llvm_logical = binary_parent / "llvm-config"
            llvm_logical.symlink_to(str(llvm_intermediate))

            cases = (
                (
                    "lld",
                    lld_logical,
                    lld_bytes,
                    b"LLD 21.1.8\n",
                    "lld-0:21.1.8-1.el10.x86_64",
                    [
                        {"path": str(lld_logical), "target": lld_target.name},
                    ],
                ),
                (
                    "llvm",
                    llvm_logical,
                    llvm_bytes,
                    b"21.1.8\n",
                    "llvm-devel-0:21.1.8-1.el10.x86_64",
                    [
                        {
                            "path": str(llvm_logical),
                            "target": str(llvm_intermediate),
                        },
                        {
                            "path": str(llvm_intermediate),
                            "target": str(llvm_target),
                        },
                    ],
                ),
            )
            for probe_id, logical, target_bytes, stdout, owner, hops in cases:
                with self.subTest(probe_id=probe_id):
                    command = [logical.name, "--version"]
                    expected = {"command": command, "symlink_hops": hops}
                    owner_command = ["rpm", "-qf", str(logical)]
                    rpm_owner = mock.Mock(return_value=(owner, owner_command))
                    with mock.patch.dict(
                        capture.CAPTURE_ENV, {"PATH": str(binary_parent)}
                    ), mock.patch.object(capture, "_rpm_owner", rpm_owner):
                        result = capture._capture_locked_probe(
                            logical, expected, probe_id + " binary"
                        )
                    rpm_owner.assert_called_once_with(logical)
                    self.assertEqual(target_bytes, result["binary_data"])
                    self.assertEqual(stdout, result["completed"].stdout)
                    self.assertEqual(owner, result["owner"])
                    self.assertEqual(owner_command, result["owner_command"])

    def test_locked_probe_symlink_rejects_loop_and_static_retarget(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            logical = root / "clang"
            target = root / "clang-21"
            target.symlink_to(target.name)
            logical.symlink_to(target.name)
            expected = {
                "command": ["clang", "--version"],
                "symlink_hops": [
                    {"path": str(logical), "target": target.name},
                ],
            }
            with self.assertRaisesRegex(capture.CaptureError, "unlisted symlink hop"):
                capture._open_locked_probe(logical, expected, "clang binary")

            logical.unlink()
            target.unlink()
            target.write_bytes(b"exact target\n")
            logical.symlink_to("clang-22")
            with self.assertRaisesRegex(capture.CaptureError, "target differs"):
                capture._open_locked_probe(logical, expected, "clang binary")

            loop = {
                "command": ["clang", "--version"],
                "symlink_hops": [
                    {"path": str(logical), "target": logical.name},
                ],
            }
            with self.assertRaisesRegex(capture.CaptureError, "forms a loop"):
                capture._open_locked_probe(logical, loop, "clang binary")

            unsafe = {
                "command": ["clang", "--version"],
                "symlink_hops": [
                    {"path": str(logical), "target": "../clang-21"},
                ],
            }
            with self.assertRaisesRegex(capture.CaptureError, "safe basename"):
                capture._open_locked_probe(logical, unsafe, "clang binary")

    def test_locked_probe_rejects_post_return_and_path_hijack(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            trusted = root / "trusted"
            hostile = root / "hostile"
            trusted.mkdir()
            hostile.mkdir()
            logical = trusted / "probe"
            trusted_bytes = b"#!/bin/sh\nprintf 'trusted\\n'\n"
            hostile_bytes = b"#!/bin/sh\nprintf 'hostile\\n'\n"
            logical.write_bytes(trusted_bytes)
            logical.chmod(0o755)
            hijack = hostile / logical.name
            hijack.write_bytes(hostile_bytes)
            hijack.chmod(0o755)
            expected = {"command": [logical.name, "--version"]}
            owner_command = ["rpm", "-qf", str(logical)]
            rpm_owner = mock.Mock(return_value=("probe-0:1-1.x86_64", owner_command))
            run_locked = capture._run_locked_probe
            observed = []

            replacement = root / "replacement"
            replacement.write_bytes(trusted_bytes)
            replacement.chmod(0o755)

            def replace_after_return(session, command):
                completed = run_locked(session, command)
                observed.append(completed.stdout)
                os.replace(str(replacement), str(logical))
                return completed

            with mock.patch.dict(capture.CAPTURE_ENV, {"PATH": str(trusted)}), \
                    mock.patch.object(capture, "_rpm_owner", rpm_owner), \
                    mock.patch.object(
                        capture, "_run_locked_probe", side_effect=replace_after_return
                    ):
                with self.assertRaisesRegex(capture.CaptureError, "path identity changed"):
                    capture._capture_locked_probe(logical, expected, "regular probe")
            self.assertEqual([b"trusted\n"], observed)

            logical.write_bytes(trusted_bytes)
            logical.chmod(0o755)
            observed[:] = []

            def insert_path_hijack(session, command):
                capture.CAPTURE_ENV["PATH"] = (
                    str(hostile) + os.pathsep + str(trusted)
                )
                completed = run_locked(session, command)
                observed.append(completed.stdout)
                return completed

            with mock.patch.dict(capture.CAPTURE_ENV, {"PATH": str(trusted)}), \
                    mock.patch.object(capture, "_rpm_owner", rpm_owner), \
                    mock.patch.object(
                        capture, "_run_locked_probe", side_effect=insert_path_hijack
                    ):
                with self.assertRaisesRegex(capture.CaptureError, "PATH resolution changed"):
                    capture._capture_locked_probe(logical, expected, "regular probe")
            self.assertEqual([b"trusted\n"], observed)

    def test_locked_probe_rejects_parent_substitution_during_rpm_lookup(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            parent = root / "bin"
            parent.mkdir()
            logical = parent / "probe"
            logical.write_bytes(b"#!/bin/sh\nexit 0\n")
            logical.chmod(0o755)
            expected = {"command": [logical.name, "--version"]}
            moved = root / "bin-held"

            def substitute_parent(path):
                self.assertEqual(str(logical), str(path))
                parent.rename(moved)
                parent.mkdir()
                replacement = parent / logical.name
                replacement.write_bytes(b"#!/bin/sh\nexit 99\n")
                replacement.chmod(0o755)
                return "probe-0:1-1.x86_64", ["rpm", "-qf", str(path)]

            with mock.patch.dict(capture.CAPTURE_ENV, {"PATH": str(parent)}), \
                    mock.patch.object(
                        capture, "_rpm_owner", side_effect=substitute_parent
                    ), mock.patch.object(capture, "_run_locked_probe") as execute:
                with self.assertRaisesRegex(capture.CaptureError, "path identity changed"):
                    capture._capture_locked_probe(logical, expected, "regular probe")
            execute.assert_not_called()

    def test_locked_probe_rejects_retarget_in_rpm_exec_window(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            target = root / "clang-21"
            replacement = root / "clang-22"
            target.write_bytes(b"#!/bin/sh\nexit 0\n")
            replacement.write_bytes(target.read_bytes())
            target.chmod(0o755)
            replacement.chmod(0o755)
            logical = root / "clang"
            logical.symlink_to(target.name)
            expected = {
                "command": [logical.name, "--version"],
                "symlink_hops": [
                    {"path": str(logical), "target": target.name},
                ],
            }

            def retarget_after_rpm(path):
                self.assertEqual(str(logical), str(path))
                logical.unlink()
                logical.symlink_to(replacement.name)
                return "clang-0:21.1.8-1.el10.x86_64", [
                    "rpm", "-qf", str(path)
                ]

            with mock.patch.dict(capture.CAPTURE_ENV, {"PATH": str(root)}), \
                    mock.patch.object(
                        capture, "_rpm_owner", side_effect=retarget_after_rpm
                    ), mock.patch.object(capture, "_run_locked_probe") as execute:
                with self.assertRaisesRegex(capture.CaptureError, "path identity changed"):
                    capture._capture_locked_probe(logical, expected, "clang binary")
            execute.assert_not_called()

    def test_locked_probe_two_hop_rejects_retarget_at_every_hop_and_target(self):
        for mutation in ("logical-hop", "intermediate-hop", "target"):
            with self.subTest(mutation=mutation), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                fixture = self._two_hop_probe_fixture(root)
                other_intermediate_parent = root / "other-alternatives"
                other_intermediate_parent.mkdir()
                other_intermediate = other_intermediate_parent / "llvm-config"
                other_intermediate.symlink_to(str(fixture["target"]))
                other_target_parent = root / "other-llvm21-bin"
                other_target_parent.mkdir()
                other_target = other_target_parent / "llvm-config"
                other_target.write_bytes(fixture["target_bytes"])
                other_target.chmod(0o755)
                replacement = root / "replacement-target"
                replacement.write_bytes(fixture["target_bytes"])
                replacement.chmod(0o755)

                def retarget_after_rpm(path):
                    self.assertEqual(str(fixture["logical"]), str(path))
                    if mutation == "logical-hop":
                        fixture["logical"].unlink()
                        fixture["logical"].symlink_to(str(other_intermediate))
                    elif mutation == "intermediate-hop":
                        fixture["intermediate"].unlink()
                        fixture["intermediate"].symlink_to(str(other_target))
                    else:
                        os.replace(str(replacement), str(fixture["target"]))
                    return "llvm-devel-0:21.1.8-1.el10.x86_64", [
                        "rpm", "-qf", str(path)
                    ]

                with mock.patch.dict(
                    capture.CAPTURE_ENV, {"PATH": str(fixture["logical_parent"])}
                ), mock.patch.object(
                    capture, "_rpm_owner", side_effect=retarget_after_rpm
                ), mock.patch.object(capture, "_run_locked_probe") as execute:
                    with self.assertRaisesRegex(
                        capture.CaptureError, "path identity changed"
                    ):
                        capture._capture_locked_probe(
                            fixture["logical"], fixture["expected"], "llvm binary"
                        )
                execute.assert_not_called()

    def test_locked_probe_two_hop_rechecks_every_hop_and_target_after_execution(self):
        for mutation in ("logical-hop", "intermediate-hop", "target"):
            with self.subTest(mutation=mutation), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                fixture = self._two_hop_probe_fixture(root)
                other_intermediate_parent = root / "other-alternatives"
                other_intermediate_parent.mkdir()
                other_intermediate = other_intermediate_parent / "llvm-config"
                other_intermediate.symlink_to(str(fixture["target"]))
                other_target_parent = root / "other-llvm21-bin"
                other_target_parent.mkdir()
                other_target = other_target_parent / "llvm-config"
                other_target.write_bytes(fixture["target_bytes"])
                other_target.chmod(0o755)
                replacement = root / "replacement-target"
                replacement.write_bytes(fixture["target_bytes"])
                replacement.chmod(0o755)
                run_locked = capture._run_locked_probe
                observed = []

                def mutate_after_execution(session, command):
                    completed = run_locked(session, command)
                    observed.append(completed.stdout)
                    if mutation == "logical-hop":
                        fixture["logical"].unlink()
                        fixture["logical"].symlink_to(str(other_intermediate))
                    elif mutation == "intermediate-hop":
                        fixture["intermediate"].unlink()
                        fixture["intermediate"].symlink_to(str(other_target))
                    else:
                        os.replace(str(replacement), str(fixture["target"]))
                    return completed

                owner_command = ["rpm", "-qf", str(fixture["logical"])]
                rpm_owner = mock.Mock(
                    return_value=(
                        "llvm-devel-0:21.1.8-1.el10.x86_64",
                        owner_command,
                    )
                )
                with mock.patch.dict(
                    capture.CAPTURE_ENV, {"PATH": str(fixture["logical_parent"])}
                ), mock.patch.object(
                    capture, "_rpm_owner", rpm_owner
                ), mock.patch.object(
                    capture,
                    "_run_locked_probe",
                    side_effect=mutate_after_execution,
                ):
                    with self.assertRaisesRegex(
                        capture.CaptureError, "path identity changed"
                    ):
                        capture._capture_locked_probe(
                            fixture["logical"], fixture["expected"], "llvm binary"
                        )
                self.assertEqual([b"21.1.8\n"], observed)

    def test_locked_probe_two_hop_rejects_unlisted_third_hop(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            fixture = self._two_hop_probe_fixture(root)
            final_target = root / "final-target"
            final_target.write_bytes(fixture["target_bytes"])
            final_target.chmod(0o755)
            fixture["target"].unlink()
            fixture["target"].symlink_to(str(final_target))
            with self.assertRaisesRegex(capture.CaptureError, "unlisted symlink hop"):
                capture._open_locked_probe(
                    fixture["logical"], fixture["expected"], "llvm binary"
                )

    def test_locked_probe_two_hop_rejects_every_parent_substitution(self):
        parent_keys = (
            "logical_parent",
            "intermediate_parent",
            "target_parent",
        )
        for parent_key in parent_keys:
            with self.subTest(parent=parent_key), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                fixture = self._two_hop_probe_fixture(root)

                def substitute_parent(path):
                    self.assertEqual(str(fixture["logical"]), str(path))
                    parent = fixture[parent_key]
                    parent.rename(root / (parent.name + "-held"))
                    parent.mkdir()
                    if parent_key == "logical_parent":
                        fixture["logical"].symlink_to(str(fixture["intermediate"]))
                    elif parent_key == "intermediate_parent":
                        fixture["intermediate"].symlink_to(str(fixture["target"]))
                    else:
                        fixture["target"].write_bytes(fixture["target_bytes"])
                        fixture["target"].chmod(0o755)
                    return "llvm-devel-0:21.1.8-1.el10.x86_64", [
                        "rpm", "-qf", str(path)
                    ]

                with mock.patch.dict(
                    capture.CAPTURE_ENV, {"PATH": str(fixture["logical_parent"])}
                ), mock.patch.object(
                    capture, "_rpm_owner", side_effect=substitute_parent
                ), mock.patch.object(capture, "_run_locked_probe") as execute:
                    with self.assertRaisesRegex(
                        capture.CaptureError, "path identity changed"
                    ):
                        capture._capture_locked_probe(
                            fixture["logical"], fixture["expected"], "llvm binary"
                        )
                execute.assert_not_called()

    def test_tar_inspection_rejects_traversal_and_symlink_members(self):
        for name, member_type in (("../escape", tarfile.REGTYPE), ("link", tarfile.SYMTYPE)):
            output = io.BytesIO()
            with tarfile.open(fileobj=output, mode="w:xz") as archive:
                member = tarfile.TarInfo(name)
                member.type = member_type
                member.mode = 0o444
                member.mtime = 0
                member.uid = 0
                member.gid = 0
                if member_type == tarfile.SYMTYPE:
                    member.linkname = "target"
                archive.addfile(member, io.BytesIO(b""))
            with self.subTest(name=name, member_type=member_type):
                with self.assertRaises(capture.CaptureError):
                    capture._inspect_tar(output.getvalue(), "hostile archive")

    def test_locked_archive_is_safely_extracted_and_full_tree_bound(self):
        output = io.BytesIO()
        with tarfile.open(fileobj=output, mode="w:xz") as archive:
            for name in ("locked-root", "locked-root/dir"):
                member = tarfile.TarInfo(name)
                member.type = tarfile.DIRTYPE
                member.mode = 0o755
                archive.addfile(member)
            payload = b"locked source bytes\n"
            member = tarfile.TarInfo("locked-root/dir/file")
            member.mode = 0o644
            member.size = len(payload)
            archive.addfile(member, io.BytesIO(payload))
            member = tarfile.TarInfo("locked-root/link")
            member.type = tarfile.SYMTYPE
            member.mode = 0o777
            member.linkname = "dir/file"
            archive.addfile(member)
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "locked-root"
            closure = capture._extract_locked_source_archive(
                output.getvalue(), source, "locked-root"
            )
            self.assertEqual(payload, (source / "dir/file").read_bytes())
            self.assertTrue((source / "link").is_symlink())
            self.assertEqual("dir/file", os.readlink(str(source / "link")))
            self.assertEqual(capture.FULL_SOURCE_CLOSURE_ALGORITHM, closure["algorithm"])
            self.assertEqual(4, closure["row_count"])
            self.assertRegex(closure["sha256"], r"^[0-9a-f]{64}$")
            with self.assertRaisesRegex(capture.CaptureError, "must not preexist"):
                capture._extract_locked_source_archive(
                    output.getvalue(), source, "locked-root"
                )

    def test_locked_archive_rejects_traversal_and_hardlink_members(self):
        for name, member_type in (
            ("locked-root/../escape", tarfile.REGTYPE),
            ("locked-root/hardlink", tarfile.LNKTYPE),
        ):
            output = io.BytesIO()
            with tarfile.open(fileobj=output, mode="w:xz") as archive:
                root = tarfile.TarInfo("locked-root")
                root.type = tarfile.DIRTYPE
                root.mode = 0o755
                archive.addfile(root)
                member = tarfile.TarInfo(name)
                member.type = member_type
                member.mode = 0o644
                if member_type == tarfile.LNKTYPE:
                    member.linkname = "locked-root/target"
                archive.addfile(member, io.BytesIO(b""))
            with self.subTest(name=name), tempfile.TemporaryDirectory() as directory:
                with self.assertRaises(capture.CaptureError):
                    capture._extract_locked_source_archive(
                        output.getvalue(), Path(directory) / "locked-root", "locked-root"
                    )

    def test_build_binding_verifies_complete_exact_build_evidence(self):
        document = {
            "github": {"head_sha": "a" * 40, "run_id": 123, "run_attempt": 2}
        }
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self._build_evidence(root)
            binding = capture._build_binding(root, document)
        self.assertEqual("technical-build-bound-unreviewed", binding["status"])
        self.assertEqual(capture.FALSE_CLAIMS, binding["claims"])
        self.assertFalse(binding["build_artifact"]["durable"])
        self.assertIsNone(binding["build_artifact"]["outer_artifact_sha256"])
        self.assertEqual("native-rust-exact-build-123-2", binding["build_artifact"]["name"])
        capture._validate_final_build_evidence_rows(
            document, binding["build_evidence"], binding["build_artifact"]
        )

    def test_final_verifier_rejects_self_resealed_fixed_build_rows(self):
        document = {
            "github": {"head_sha": "a" * 40, "run_id": 123, "run_attempt": 2}
        }
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self._build_evidence(root)
            original = capture._build_binding(root, document)
        for name in (
            "build.environment",
            "build.phase",
            "build.exit-code",
            "build-log.exit-code",
            "workflow-state",
            "commit.sha",
        ):
            with self.subTest(name=name):
                binding = copy.deepcopy(original)
                for row in binding["build_evidence"]:
                    if row["path"] == name:
                        replacement = b"self-resealed\n"
                        row["sha256"] = hashlib.sha256(replacement).hexdigest()
                        row["size"] = len(replacement)
                        break
                rows = binding["build_evidence"]
                binding["build_artifact"]["content_closure_sha256"] = hashlib.sha256(
                    capture._canonical_json(rows)
                ).hexdigest()
                reconstructed = "".join(
                    "{}  {}\n".format(row["sha256"], row["path"])
                    for row in rows
                ).encode("ascii")
                binding["build_artifact"]["sha256sums_sha256"] = hashlib.sha256(
                    reconstructed
                ).hexdigest()
                with self.assertRaisesRegex(
                    capture.CaptureError, "fixed evidence differs"
                ):
                    capture._validate_final_build_evidence_rows(
                        document, rows, binding["build_artifact"]
                    )

        binding = copy.deepcopy(original)
        binding["build_artifact"]["sha256sums_sha256"] = "f" * 64
        with self.assertRaisesRegex(capture.CaptureError, "manifest digest"):
            capture._validate_final_build_evidence_rows(
                document, binding["build_evidence"], binding["build_artifact"]
            )

    def test_build_binding_rejects_checksum_status_and_extra_member_mutations(self):
        document = {
            "github": {"head_sha": "a" * 40, "run_id": 123, "run_attempt": 2}
        }
        mutations = ("checksum", "status", "missing-raw", "extra")
        for mutation in mutations:
            with self.subTest(mutation=mutation), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                self._build_evidence(root)
                if mutation == "checksum":
                    (root / "build.log").write_bytes(b"mutated")
                elif mutation == "status":
                    (root / "build.exit-code").write_bytes(b"1\n")
                    content = (root / "build.exit-code").read_bytes()
                    manifest = (root / "SHA256SUMS").read_text(encoding="ascii")
                    manifest = __import__("re").sub(
                        r"[0-9a-f]{64}  build\.exit-code",
                        hashlib.sha256(content).hexdigest() + "  build.exit-code",
                        manifest,
                    )
                    (root / "SHA256SUMS").write_text(manifest, encoding="ascii")
                elif mutation == "missing-raw":
                    (root / ".ihk.o.cmd").unlink()
                    manifest = (root / "SHA256SUMS").read_text(encoding="ascii")
                    manifest = "".join(
                        row for row in manifest.splitlines(True)
                        if not row.endswith("  .ihk.o.cmd\n")
                    )
                    (root / "SHA256SUMS").write_text(manifest, encoding="ascii")
                else:
                    (root / "extra").write_bytes(b"extra")
                    (root / "extra").chmod(0o644)
                with self.assertRaises(capture.CaptureError):
                    capture._build_binding(root, document)

    def test_build_binding_rejects_reproducible_environment_mutations(self):
        document = {
            "github": {"head_sha": "a" * 40, "run_id": 123, "run_attempt": 2}
        }
        mutations = (
            b"KBUILD_BUILD_USER=root\n",
            capture.REPRODUCIBLE_BUILD_ENVIRONMENT_BYTES.replace(
                b"KBUILD_BUILD_HOST=rocky-10.2-x86_64\n", b""
            ),
            capture.REPRODUCIBLE_BUILD_ENVIRONMENT_BYTES
            + b"KBUILD_BUILD_USER=attacker\n",
        )
        for mutation in mutations:
            with self.subTest(mutation=mutation), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                self._build_evidence(root)
                environment = root / "build.environment"
                environment.write_bytes(mutation)
                digest = hashlib.sha256(mutation).hexdigest()
                manifest = (root / "SHA256SUMS").read_text(encoding="ascii")
                manifest = __import__("re").sub(
                    r"[0-9a-f]{64}  build\.environment",
                    digest + "  build.environment",
                    manifest,
                )
                (root / "SHA256SUMS").write_text(manifest, encoding="ascii")
                with self.assertRaisesRegex(capture.CaptureError, r"build\.environment"):
                    capture._build_binding(root, document)

    def test_build_binding_rejects_self_resealed_precheck_mutations(self):
        document = {
            "github": {"head_sha": "a" * 40, "run_id": 123, "run_attempt": 2}
        }
        for mutation in ("missing", "extra", "duplicate", "reordered", "digest"):
            with self.subTest(mutation=mutation), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                self._build_evidence(root)
                precheck = root / "PRECHECK_SHA256SUMS"
                rows = precheck.read_text(encoding="ascii").splitlines(True)
                if mutation == "missing":
                    content = "".join(rows[1:])
                elif mutation == "extra":
                    content = "".join(rows) + "{}  unexpected\n".format("0" * 64)
                elif mutation == "duplicate":
                    content = "".join(rows) + rows[0]
                elif mutation == "reordered":
                    content = "".join(reversed(rows))
                else:
                    content = ("0" * 64) + rows[0][64:] + "".join(rows[1:])
                precheck.write_text(content, encoding="ascii")
                digest = hashlib.sha256(content.encode("ascii")).hexdigest()
                manifest = (root / "SHA256SUMS").read_text(encoding="ascii")
                manifest = re.sub(
                    r"[0-9a-f]{64}  PRECHECK_SHA256SUMS",
                    digest + "  PRECHECK_SHA256SUMS",
                    manifest,
                )
                (root / "SHA256SUMS").write_text(manifest, encoding="ascii")
                with self.assertRaises(capture.CaptureError):
                    capture._build_binding(root, document)

    def test_build_checksum_manifest_requires_stable_single_link_0644_identity(self):
        document = {
            "github": {"head_sha": "a" * 40, "run_attempt": 1, "run_id": 1}
        }
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self._build_evidence(root)
            (root / "SHA256SUMS").chmod(0o600)
            with self.assertRaisesRegex(capture.CaptureError, "manifest.*mode"):
                capture._build_binding(root, document)

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self._build_evidence(root)
            manifest = root / "SHA256SUMS"
            target = root / "SHA256SUMS.real"
            manifest.rename(target)
            manifest.symlink_to(target.name)
            with self.assertRaises(capture.CaptureError):
                capture._build_binding(root, document)

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self._build_evidence(root)
            manifest = root / "SHA256SUMS"
            os.link(str(manifest), str(root / "manifest-hardlink"))
            with self.assertRaisesRegex(capture.CaptureError, "hard-linked"):
                capture._build_binding(root, document)

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self._build_evidence(root)
            manifest = root / "SHA256SUMS"
            manifest_inode = manifest.stat().st_ino
            real_read = capture.os.read
            raced = [False]

            def read_then_change_mode(descriptor, size):
                data = real_read(descriptor, size)
                metadata = os.fstat(descriptor)
                if (
                    not data
                    and not raced[0]
                    and stat.S_ISREG(metadata.st_mode)
                    and metadata.st_ino == manifest_inode
                ):
                    manifest.chmod(0o600)
                    raced[0] = True
                return data

            with mock.patch.object(capture.os, "read", side_effect=read_then_change_mode):
                with self.assertRaisesRegex(capture.CaptureError, "changed while it was read"):
                    capture._build_binding(root, document)
            self.assertTrue(raced[0])

    def test_repository_inputs_require_the_exact_fixed_and_patch_membership(self):
        paths = capture._repository_input_paths(self.authority)
        rows = [{"path": path} for path in paths]
        capture._validate_repository_input_membership(rows, self.authority)
        self.assertEqual(26, sum(path.endswith(".patch") for path in paths))
        with self.assertRaisesRegex(capture.CaptureError, "membership"):
            capture._validate_repository_input_membership(rows[:-1], self.authority)

    def test_capture_tool_probes_reject_empty_schema_path_version_and_owner_drift(self):
        expected = self._synthetic_tool_probes()
        capture._validate_tool_probe_document(copy.deepcopy(expected), expected=expected)
        mutations = (
            ("empty", lambda value: value["probes"].__setitem__("patch", {})),
            (
                "path",
                lambda value: value["probes"]["patch"].__setitem__(
                    "binary_path", "/tmp/patch"
                ),
            ),
            (
                "version",
                lambda value: value["probes"]["python3"].__setitem__(
                    "text", "different\n"
                ),
            ),
            (
                "owner",
                lambda value: value["probes"]["python3"].__setitem__(
                    "package_nevra", "different"
                ),
            ),
        )
        for label, mutate in mutations:
            with self.subTest(label=label):
                value = copy.deepcopy(expected)
                mutate(value)
                with self.assertRaises(capture.CaptureError):
                    capture._validate_tool_probe_document(value, expected=expected)

        reviewer_document = {
            "claims": dict(capture.FALSE_CLAIMS),
            "environment": dict(capture.CAPTURE_ENV),
            "probe_count": 2,
            "probes": {
                probe_id: copy.deepcopy(expected["probes"][probe_id])
                for probe_id in ("patch", "python3")
            },
            "schema_version": 1,
        }
        for probe in reviewer_document["probes"].values():
            probe["text"] = ""
            probe["stdout_sha256"] = hashlib.sha256(b"").hexdigest()
        with self.assertRaises(capture.CaptureError):
            capture._validate_tool_probe_document(
                reviewer_document, expected=reviewer_document
            )

        def empty_version_streams(value):
            for probe_id in ("patch", "python3"):
                value["probes"][probe_id]["text"] = ""
                value["probes"][probe_id]["stdout_sha256"] = hashlib.sha256(
                    b""
                ).hexdigest()

        def unrecognized_version(value):
            text = "python3 version\n"
            value["probes"]["python3"]["text"] = text
            value["probes"]["python3"]["stdout_sha256"] = hashlib.sha256(
                text.encode("utf-8")
            ).hexdigest()

        self_oracle_mutations = (
            ("empty-version-streams", empty_version_streams),
            (
                "command",
                lambda value: value["probes"]["patch"].__setitem__(
                    "command", ["patch", "-v"]
                ),
            ),
            (
                "resolved-path",
                lambda value: value["probes"]["python3"].__setitem__(
                    "binary_resolved_path", "/usr/bin/python3.13"
                ),
            ),
            (
                "owner-command",
                lambda value: value["probes"]["patch"]["owner_command"].__setitem__(
                    -1, "/tmp/patch"
                ),
            ),
            (
                "owner-nevra",
                lambda value: value["probes"]["python3"].__setitem__(
                    "package_nevra", "python3-libs-0:3.12.13-2.el10_2.1.x86_64"
                ),
            ),
            ("unrecognized-version", unrecognized_version),
        )
        for label, mutate in self_oracle_mutations:
            with self.subTest(self_oracle=label):
                value = copy.deepcopy(expected)
                mutate(value)
                with self.assertRaises(capture.CaptureError):
                    capture._validate_tool_probe_document(value, expected=value)

    def test_patch_logs_bind_every_command_kind_exit_and_stream_digest(self):
        with tempfile.TemporaryDirectory() as directory:
            source = self._fixture_source(Path(directory))
            replay = capture._replay_patch_series(
                REPO_ROOT, source, self.authority, enforce_parent_hashes=False
            )
        patch_program = shutil.which("patch", path=capture.CAPTURE_ENV["PATH"])
        vendor_path = Path("/tmp") / self.contract["inputs"]["vendor_patch"]["filename"]
        vendor_command = capture._patch_command(patch_program, vendor_path)
        vendor_completed = subprocess.CompletedProcess(
            vendor_command, 0, stdout=b"vendor applied\n", stderr=b""
        )
        apply_rows = [
            capture._log_record(
                "vendor-apply", "rocky-vendor-1000", vendor_command, vendor_completed
            )
        ] + [json.loads(line) for line in replay["apply_log"].splitlines()]
        second_rows = [json.loads(line) for line in replay["second_log"].splitlines()]
        capture._validate_patch_logs(
            apply_rows,
            second_rows,
            self.authority,
            REPO_ROOT,
            vendor_path.name,
        )
        mutations = (
            ("minimal", lambda apply, second: apply.__setitem__(1, {})),
            ("kind", lambda apply, second: apply[1].__setitem__("kind", "other")),
            ("command", lambda apply, second: apply[1]["command"].append("--silent")),
            ("success", lambda apply, second: second[0].__setitem__("returncode", 0)),
            (
                "digest",
                lambda apply, second: second[0].__setitem__(
                    "stdout_sha256", "0" * 64
                ),
            ),
        )
        for label, mutate in mutations:
            with self.subTest(label=label):
                apply = copy.deepcopy(apply_rows)
                second = copy.deepcopy(second_rows)
                mutate(apply, second)
                with self.assertRaises(capture.CaptureError):
                    capture._validate_patch_logs(
                        apply,
                        second,
                        self.authority,
                        REPO_ROOT,
                        vendor_path.name,
                    )

    def test_checksum_parser_rejects_duplicate_nested_and_malformed_rows(self):
        values = (
            b"0" * 64 + b"  file\n" + b"1" * 64 + b"  file\n",
            b"0" * 64 + b"  nested/file\n",
            b"not-a-checksum  file\n",
        )
        for value in values:
            with self.subTest(value=value[:20]):
                with self.assertRaises(capture.CaptureError):
                    capture._parse_checksum_manifest(value, "manifest")

    def test_python36_source_avoids_newer_only_syntax(self):
        source = (REPO_ROOT / capture.CAPTURE_SCRIPT_PATH).read_text(encoding="utf-8")
        self.assertNotIn("missing_ok=", source)
        self.assertNotIn(" | None", source)
        self.assertNotRegex(source, r"\blist\[[^\]]+\]")
        self.assertNotRegex(source, r"\bdict\[[^\]]+\]")


if __name__ == "__main__":
    unittest.main()
