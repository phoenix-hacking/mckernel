#!/usr/bin/env python3
"""Focused tests for the non-crediting RK-006 source/build capture."""

from __future__ import print_function

import copy
import hashlib
import io
import json
import os
from pathlib import Path
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

    def _build_evidence(self, directory, head="a" * 40):
        contents = {}
        for name in capture.REQUIRED_BUILD_MEMBERS:
            if name == "SHA256SUMS":
                continue
            contents[name] = (name + "\n").encode("ascii")
        contents["commit.sha"] = (head + "\n").encode("ascii")
        contents["build.phase"] = b"complete\n"
        contents["build.exit-code"] = b"0\n"
        contents["build-log.exit-code"] = b"0\n"
        contents["workflow-state"] = b"bootstrap-complete\n"
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

    def test_contract_and_all_frozen_inputs_validate(self):
        contract_value, authority = capture.validate_contract(REPO_ROOT)
        self.assertEqual("rk-006-full-source-build-capture-v1", contract_value["capture_contract_id"])
        self.assertEqual(25, len(authority["patches"]))

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
            "patch_authority": "ebc3e4c69ecbdb3891f92018a89f5fc3dae43fa070628fda8b22f881f02c67a1",
            "patch_authority_checker": "c23969ba2716db96f02a0564d6815b7342036a58c258ce22319b0185693cfddd",
            "patch_authority_tests": "719d1e87b4d66944abf3bad0c03dc7cc86dddb97fa36e3fe32736c29ea549b39",
            "source_lock": "707ee40466ac0bb0cd0600383bba0b13fc1146e7080034786bf5668a95b27682",
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

    def test_fixture_replays_all_25_patches_and_rejects_every_second_apply(self):
        with tempfile.TemporaryDirectory() as directory:
            source = self._fixture_source(Path(directory))
            replay = capture._replay_patch_series(
                REPO_ROOT, source, self.authority, enforce_parent_hashes=False
            )
        self.assertEqual(25, len(replay["patch_records"]))
        self.assertEqual(list(range(1, 26)), [row["order"] for row in replay["patch_records"]])
        second = [json.loads(line) for line in replay["second_log"].splitlines()]
        self.assertEqual(25, len(second))
        self.assertTrue(all(row["returncode"] != 0 for row in second))
        self.assertNotEqual(
            self.authority["source_binding"]["fixture_preimage_closure_sha256"],
            replay["external_initial_closure"]["sha256"],
            "the external closure must not be assumed to equal the authority fixture closure",
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

    def test_build_binding_rejects_checksum_status_and_extra_member_mutations(self):
        document = {
            "github": {"head_sha": "a" * 40, "run_id": 123, "run_attempt": 2}
        }
        mutations = ("checksum", "status", "extra")
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
                else:
                    (root / "extra").write_bytes(b"extra")
                    (root / "extra").chmod(0o644)
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
        self.assertEqual(25, sum(path.endswith(".patch") for path in paths))
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
