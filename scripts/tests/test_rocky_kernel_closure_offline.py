#!/usr/bin/env python3
"""Fail-closed tests for RK-003 closure and offline replay evidence."""

import ast
import copy
import gzip
import hashlib
import json
import os
import shutil
import stat
import sys
import tempfile
import unittest
from pathlib import Path, PurePosixPath
from unittest import mock


REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import rocky_kernel_closure_offline as closure  # noqa: E402


def canonical(value):
    return (json.dumps(value, separators=(",", ":"), sort_keys=True) + "\n").encode(
        "ascii"
    )


def write_checksums(root):
    rows = []
    for path in sorted(root.rglob("*")):
        if path.is_file() and path.name != "SHA256SUMS":
            rows.append(
                "{}  {}".format(
                    hashlib.sha256(path.read_bytes()).hexdigest(),
                    path.relative_to(root).as_posix(),
                )
            )
    (root / "SHA256SUMS").write_text("\n".join(rows) + "\n", encoding="ascii")


class ContractTests(unittest.TestCase):
    def test_repository_contract_and_workflow_are_valid_and_credit_forbidden(self):
        contract = closure.validate_contract(REPO_ROOT)
        closure.validate_workflow(REPO_ROOT)
        self.assertEqual(contract["phase_id"], "closure-offline")
        self.assertEqual(contract["schema_version"], 2)
        self.assertTrue(contract["gate_claims"])
        self.assertFalse(any(contract["gate_claims"].values()))
        self.assertEqual(len(contract["success_blockers"]), 7)
        self.assertNotIn(
            "marks closure-offline unimplemented",
            "\n".join(contract["success_blockers"]),
        )
        self.assertNotIn(
            "maps the llvm-config probe", "\n".join(contract["success_blockers"])
        )
        reconciliation = contract["metadata_reconciliation"]
        self.assertTrue(
            reconciliation["phase_plan"]["implementation_available"]
        )
        self.assertFalse(
            reconciliation["phase_plan"]["historical_implemented"]
        )
        self.assertFalse(any(reconciliation["claims"].values()))
        self.assertIn(
            "not kernel-level network isolation",
            contract["network_contract"]["scope"],
        )
        self.assertIn(
            "three exact",
            contract["network_contract"]["rpm_acquisition"],
        )
        self.assertEqual(
            contract["snapshot_authority"]["binary_repository_ids"],
            ["baseos", "appstream", "crb"],
        )
        self.assertEqual(
            contract["snapshot_authority"]["source_repository_id"],
            "source-baseos",
        )
        self.assertEqual(
            contract["snapshot_authority"]["git_authority"],
            closure.snapshot_v2.GIT_AUTHORITY_POLICY,
        )

    def test_contract_is_bound_to_historical_review_and_current_toolchain(self):
        contract = closure.validate_legacy_contract(REPO_ROOT)
        self.assertEqual(len(contract["success_blockers"]), 9)
        self.assertEqual(
            contract["success_blockers"][-1], closure.LLVM_OWNER_AUTHORITY_BLOCKER
        )
        self.assertEqual(
            contract["direct_phase"]["outer_zip_sha256"],
            "a88e8a35c13dbd5b7a4e6524595d5cec31450f83c136b4cf64030e517d208eef",
        )
        lock_path = REPO_ROOT / contract["toolchain_lock"]["path"]
        self.assertEqual(
            hashlib.sha256(lock_path.read_bytes()).hexdigest(),
            contract["toolchain_lock"]["sha256"],
        )

    def test_metadata_reconciliation_is_local_exact_and_fail_closed(self):
        contract = closure.validate_contract(REPO_ROOT)
        lock, _ = closure.read_json(
            REPO_ROOT / contract["toolchain_lock"]["path"], "toolchain fixture"
        )
        reconciliation = contract["metadata_reconciliation"]
        validated = closure.validate_metadata_reconciliation(
            REPO_ROOT, copy.deepcopy(reconciliation), lock
        )
        self.assertEqual(validated, reconciliation)
        historical_plan = json.loads(
            (REPO_ROOT / reconciliation["phase_plan"]["path"]).read_text(
                encoding="utf-8"
            )
        )
        phase = [
            item
            for item in historical_plan["phases"]
            if item["id"] == "closure-offline"
        ][0]
        self.assertFalse(phase["implemented"])
        self.assertTrue(reconciliation["phase_plan"]["implementation_available"])

        for claim in sorted(reconciliation["claims"]):
            for replacement in (True, 0):
                with self.subTest(claim=claim, replacement=replacement):
                    promoted = copy.deepcopy(reconciliation)
                    promoted["claims"][claim] = replacement
                    with self.assertRaisesRegex(
                        closure.ClosureError, "metadata reconciliation claim"
                    ):
                        closure.validate_metadata_reconciliation(
                            REPO_ROOT, promoted, lock
                        )

        mutations = (
            (
                ("phase_plan", "historical_implemented"),
                True,
                "historical closure implementation state",
            ),
            (
                ("phase_plan", "historical_implemented"),
                0,
                "historical closure implementation state",
            ),
            (
                ("phase_plan", "implementation_available"),
                False,
                "implementation availability",
            ),
            (
                ("phase_plan", "implementation_available"),
                1,
                "implementation availability",
            ),
            (("phase_plan", "sha256"), "0" * 64, "reconciliation digest"),
            (
                ("llvm_config_owner", "expected_package_nevra"),
                "llvm-0:21.1.8-1.el10.x86_64",
                "expected owner",
            ),
            (
                ("llvm_config_owner", "binary_path"),
                "/usr/local/bin/llvm-config",
                "binary path",
            ),
            (
                ("llvm_config_owner", "command"),
                ["llvm-config", "--bindir"],
                "command",
            ),
            (
                ("phase_plan", "scope"),
                ["no runtime capture is claimed"],
                "phase-plan reconciliation scope",
            ),
            (
                ("phase_plan", "scope"),
                {"no runtime capture is claimed": True},
                "phase-plan reconciliation scope",
            ),
            (
                ("phase_plan", "scope"),
                True,
                "phase-plan reconciliation scope",
            ),
            (
                ("llvm_config_owner", "scope"),
                ["does not prove"],
                "owner reconciliation scope",
            ),
            (
                ("llvm_config_owner", "scope"),
                {"does not prove": True},
                "owner reconciliation scope",
            ),
            (
                ("llvm_config_owner", "scope"),
                True,
                "owner reconciliation scope",
            ),
            (
                ("scope",),
                reconciliation["scope"]
                + "; runtime evidence captured and credit is now awarded.",
                "metadata reconciliation scope",
            ),
            (
                ("phase_plan", "scope"),
                reconciliation["phase_plan"]["scope"]
                + "; runtime capture is claimed and complete.",
                "phase-plan reconciliation scope",
            ),
            (
                ("llvm_config_owner", "scope"),
                reconciliation["llvm_config_owner"]["scope"]
                + "; nevertheless this does prove gate eligibility.",
                "owner reconciliation scope",
            ),
        )
        for path, replacement, message in mutations:
            with self.subTest(path=path):
                mutated = copy.deepcopy(reconciliation)
                if len(path) == 1:
                    mutated[path[0]] = replacement
                else:
                    mutated[path[0]][path[1]] = replacement
                with self.assertRaisesRegex(closure.ClosureError, message):
                    closure.validate_metadata_reconciliation(
                        REPO_ROOT, mutated, lock
                    )

    def test_success_blockers_are_exact_ordered_authority(self):
        contract = closure.validate_contract(REPO_ROOT)
        blockers = contract["success_blockers"]
        self.assertEqual(blockers, closure.V2_SUCCESS_BLOCKERS)
        self.assertEqual(
            closure.validate_v2_success_blockers(copy.deepcopy(blockers)), blockers
        )

        duplicate = list(blockers)
        duplicate[0] = duplicate[1]
        reordered = list(blockers)
        reordered[0], reordered[1] = reordered[1], reordered[0]
        deleted_and_replaced = list(blockers)
        del deleted_and_replaced[2]
        deleted_and_replaced.append("A replacement prerequisite remains open.")
        readiness_wording = list(blockers)
        readiness_wording[0] = "RK-003 READY: " + readiness_wording[0]
        credit_wording = list(blockers)
        credit_wording[-1] = credit_wording[-1].replace(
            "receives no credit", "receives credit"
        )

        for name, mutated in (
            ("duplicate", duplicate),
            ("reorder", reordered),
            ("deletion-and-replacement", deleted_and_replaced),
            ("readiness-wording", readiness_wording),
            ("credit-wording", credit_wording),
        ):
            with self.subTest(name=name):
                self.assertEqual(len(mutated), 7)
                self.assertTrue(all(isinstance(item, str) and item for item in mutated))
                with self.assertRaisesRegex(
                    closure.ClosureError, "v2 success blocker"
                ):
                    closure.validate_v2_success_blockers(mutated)

    def test_gate_promotion_and_network_overclaim_fail_closed(self):
        contract = closure.validate_contract(REPO_ROOT)
        promoted = copy.deepcopy(contract)
        promoted["gate_claims"]["RK-003"] = True
        with self.assertRaisesRegex(closure.ClosureError, "gate claims"):
            closure.require_exact(
                promoted["gate_claims"], contract["gate_claims"], "gate claims"
            )
        for replacement in (0, "false", None, [], {}):
            with self.subTest(replacement=replacement):
                aliased = copy.deepcopy(contract["gate_claims"])
                aliased["RK-003"] = replacement
                with self.assertRaisesRegex(closure.ClosureError, "gate claims"):
                    closure.validate_false_gate_claims(
                        aliased, contract["gate_claims"], "v2 gate claims"
                    )
        overclaim = copy.deepcopy(contract)
        overclaim["network_contract"]["scope"] = "network isolated"
        self.assertNotIn(
            "not kernel-level network isolation",
            overclaim["network_contract"]["scope"],
        )
        redirected_git = copy.deepcopy(contract)
        redirected_git["snapshot_authority"]["git_authority"][
            "executable"
        ] = "/tmp/git"
        with self.assertRaisesRegex(closure.ClosureError, "Git authority"):
            closure.require_exact(
                redirected_git["snapshot_authority"]["git_authority"],
                closure.snapshot_v2.GIT_AUTHORITY_POLICY,
                "snapshot Git authority policy",
            )

    def test_cli_check_passes_and_capture_arguments_are_rejected(self):
        self.assertEqual(closure.main(["--repo", str(REPO_ROOT), "--check"]), 0)
        self.assertEqual(
            closure.main(
                [
                    "--repo",
                    str(REPO_ROOT),
                    "--check",
                    "--phase",
                    "closure-offline",
                ]
            ),
            2,
        )

    def test_full_runtime_import_surface_is_python_3_6_parseable(self):
        runtime_paths = closure.python36_runtime_paths(REPO_ROOT)
        self.assertEqual(
            runtime_paths,
            [
                "scripts/rocky_kernel_closure_offline.py",
                "scripts/rocky_kernel_platform_evidence.py",
                "scripts/rocky_repository_snapshot_capture.py",
                "scripts/rocky_kernel_platform_lock.py",
            ],
        )
        for relative in runtime_paths + [
            "scripts/tests/test_rocky_kernel_closure_offline.py"
        ]:
            source = (REPO_ROOT / relative).read_text(encoding="utf-8")
            closure.parse_python36_source(source, relative)

    def test_python_3_6_guard_rejects_newer_annotation_forms(self):
        for source in (
            "value: " + "li" + "st[str] = []\n",
            "from __future__ import " + "annotations\n",
            "value: str " + "| None = None\n",
        ):
            with self.subTest(source=source):
                with self.assertRaises(closure.ClosureError):
                    closure.parse_python36_source(source, "fixture.py")

    def test_python_3_6_guard_follows_local_imports_fail_closed(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            scripts = root / "scripts"
            scripts.mkdir()
            (scripts / "entry.py").write_text("import imported\n", encoding="utf-8")
            (scripts / "imported.py").write_text(
                "from __future__ import " + "annotations\n", encoding="utf-8"
            )
            with mock.patch.object(
                closure, "PYTHON36_ENTRYPOINT_PATHS", ["scripts/entry.py"]
            ):
                with self.assertRaisesRegex(
                    closure.ClosureError, "Python 3.6-incompatible"
                ):
                    closure.validate_python36_runtime(root)

    def test_workflow_has_complete_triggers_and_runs_focused_tests(self):
        text = (REPO_ROOT / closure.WORKFLOW_PATH).read_text(encoding="utf-8")
        for fragment in (
            ".github/workflows/rocky-kernel-platform-evidence.yml",
            ".github/workflows/rocky-repository-snapshot-capture-v2.yml",
            "host-kernel/rocky/**",
            "scripts/rocky_kernel_platform_evidence.py",
            "scripts/rocky_kernel_platform_lock.py",
            "scripts/rocky_repository_snapshot_capture.py",
            "scripts/rocky_kernel_source_lock.py",
            "scripts.tests.test_rocky_kernel_closure_offline",
            "actions/download-artifact@d3f86a106a0bac45b974a628896c90dbdf5c8093",
            "--snapshot-sha256 \"$SNAPSHOT_TAR_SHA256\"",
            "run-id: ${{ inputs.snapshot_run_id }}",
            "actions: read",
        ):
            self.assertIn(fragment, text)
        self.assertNotIn("--direct-root", text)
        self.assertNotIn("--phase repository-direct", text)
        self.assertNotIn("latest", text.lower())


class SnapshotBridgeTests(unittest.TestCase):
    def contract_fixture(self):
        return json.loads(
            (REPO_ROOT / closure.CONTRACT_PATH).read_text(encoding="utf-8")
        )

    def runtime_fixture(self):
        identity = {
            "head_sha": "1" * 40,
            "repository": "phoenix-hacking/mckernel",
            "run_attempt": 9,
            "run_id": 10,
        }
        workflow_ref = (
            closure.snapshot_v2.WORKFLOW_REF_PREFIX + "refs/heads/development"
        )
        runtime = closure.validate_snapshot_runtime_identity(
            "a" * 64,
            identity["head_sha"],
            workflow_ref,
            "123",
            "4",
            identity,
        )
        return identity, runtime

    def manifest_fixture(self, contract, runtime):
        authority = contract["snapshot_authority"]
        return {
            "capture_id": authority["capture_id"],
            "claims": dict(closure.snapshot_v2.FALSE_CLAIMS),
            "execution_identity": dict(runtime["execution_identity"]),
            "release_key": dict(
                authority["release_key"],
                path="release-key/RPM-GPG-KEY-Rocky-10",
            ),
            "repositories": [dict(item) for item in authority["repositories"]],
            "repository_inputs": [
                dict(item) for item in authority["required_repository_inputs"]
            ],
            "schema_version": 2,
            "snapshot_identity": "b" * 64,
            "target": dict(closure.snapshot_v2.TARGET),
        }

    def test_runtime_and_manifest_bridge_require_exact_current_identity(self):
        contract = self.contract_fixture()
        identity, runtime = self.runtime_fixture()
        manifest = self.manifest_fixture(contract, runtime)
        closure.validate_snapshot_manifest_bridge(manifest, contract, runtime)

        for field, value in (
            ("digest", "A" * 64),
            ("commit", "2" * 40),
            ("run_id", "01"),
            ("attempt", "0"),
        ):
            arguments = [
                "a" * 64,
                identity["head_sha"],
                runtime["execution_identity"]["workflow_ref"],
                "123",
                "4",
                identity,
            ]
            if field == "digest":
                arguments[0] = value
            elif field == "commit":
                arguments[1] = value
            elif field == "run_id":
                arguments[3] = value
            else:
                arguments[4] = value
            with self.subTest(field=field), self.assertRaises(closure.ClosureError):
                closure.validate_snapshot_runtime_identity(*arguments)
        wrong_repository = dict(identity)
        wrong_repository["repository"] = "other/repository"
        with self.assertRaisesRegex(closure.ClosureError, "repository"):
            closure.validate_snapshot_runtime_identity(
                "a" * 64,
                identity["head_sha"],
                runtime["execution_identity"]["workflow_ref"],
                "123",
                "4",
                wrong_repository,
            )

        promoted = copy.deepcopy(manifest)
        promoted["claims"]["credit_eligible"] = True
        with self.assertRaisesRegex(closure.ClosureError, "claims"):
            closure.validate_snapshot_manifest_bridge(promoted, contract, runtime)
        reordered = copy.deepcopy(manifest)
        reordered["repositories"].reverse()
        with self.assertRaisesRegex(closure.ClosureError, "repository authority"):
            closure.validate_snapshot_manifest_bridge(reordered, contract, runtime)
        changed_input = copy.deepcopy(manifest)
        changed_input["repository_inputs"][0]["sha256"] = "0" * 64
        with self.assertRaisesRegex(closure.ClosureError, "input digest"):
            closure.validate_snapshot_manifest_bridge(changed_input, contract, runtime)
        changed_size = copy.deepcopy(manifest)
        changed_size["repository_inputs"][0]["size"] += 1
        with self.assertRaisesRegex(closure.ClosureError, "input size"):
            closure.validate_snapshot_manifest_bridge(changed_size, contract, runtime)

    def test_external_digest_and_byte_bound_precede_snapshot_verifier(self):
        contract = self.contract_fixture()
        _, runtime = self.runtime_fixture()
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            artifact = root / "snapshot.tar"
            artifact.write_bytes(b"not-the-pinned-artifact")
            snapshot_contract = {"limits": {"max_snapshot_tar_bytes": 1024}}
            with mock.patch.object(
                closure.snapshot_v2,
                "check_repository_inputs",
                return_value=(snapshot_contract, []),
            ), mock.patch.object(
                closure, "verify_and_extract_snapshot_descriptor"
            ) as verifier:
                work = root / "work"
                work.mkdir()
                with self.assertRaisesRegex(
                    closure.ClosureError, "snapshot artifact digest"
                ):
                    closure.stage_verify_and_extract_snapshot(
                        REPO_ROOT, artifact, runtime, contract, work
                    )
                verifier.assert_not_called()

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "oversized"
            source.write_bytes(b"12")
            output = root / "output"
            output.mkdir()
            with self.assertRaisesRegex(closure.ClosureError, "byte bound"):
                closure.copy_archive(source, output, Path("snapshot.tar"), 1)

    def held_snapshot_fixture(self, root):
        contract = self.contract_fixture()
        snapshot_contract, input_records = (
            closure.snapshot_v2.check_repository_inputs(REPO_ROOT)
        )
        canonical_repo = REPO_ROOT.resolve()
        head = closure.run_command(
            [
                "git",
                "-c",
                "safe.directory=" + str(canonical_repo),
                "-C",
                str(canonical_repo),
                "rev-parse",
                "HEAD",
            ]
        )[0].decode("ascii").strip()
        workflow_ref = (
            closure.snapshot_v2.WORKFLOW_REF_PREFIX
            + "refs/heads/development"
        )
        execution = {
            "source_commit": head,
            "workflow_ref": workflow_ref,
        }
        runtime_seed = {
            "artifact_sha256": "0" * 64,
            "execution_identity": execution,
            "repository": closure.snapshot_v2.WORKFLOW_REPOSITORY,
            "run_attempt": 4,
            "run_id": 123,
        }
        manifest = self.manifest_fixture(contract, runtime_seed)
        tree = root / "artifact-tree"
        tree.mkdir(mode=0o700)
        (tree / "capture-manifest.json").write_bytes(canonical(manifest))
        artifact = root / "snapshot.tar"
        closure.snapshot_v2.create_deterministic_tar(
            tree, artifact, snapshot_contract["limits"]
        )
        runtime = dict(
            runtime_seed,
            artifact_sha256=hashlib.sha256(artifact.read_bytes()).hexdigest(),
        )
        return (
            contract,
            snapshot_contract,
            input_records,
            manifest,
            artifact,
            runtime,
        )

    def swap_staged_snapshot(self, staged, replacement, restore=True):
        held = staged.with_name("snapshot.original")
        staged.rename(held)
        staged.write_bytes(replacement)
        staged.chmod(0o400)
        if restore:
            staged.unlink()
            held.rename(staged)
        return held

    def test_held_snapshot_descriptor_rejects_path_swap_restore_matrix(self):
        scenarios = (
            "before_hash",
            "during_extract",
            "after_extract",
            "unlink_recreate_restore",
            "in_place_restore",
            "same_bytes_new_inode",
        )
        for scenario in scenarios:
            with self.subTest(scenario=scenario), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                (
                    contract,
                    _,
                    _,
                    manifest,
                    artifact,
                    runtime,
                ) = self.held_snapshot_fixture(root)
                work = root / "work"
                work.mkdir(mode=0o700)
                staged = work / "snapshot-input" / "snapshot.tar"
                original_copy = closure.copy_snapshot_archive_held
                original_extract = closure.snapshot_v2.extract_canonical_tar_stream
                hooks = []

                def copy_then_swap(*args, **kwargs):
                    result = original_copy(*args, **kwargs)
                    if scenario == "before_hash":
                        self.swap_staged_snapshot(
                            staged, b"replacement-before-hash\n", True
                        )
                        hooks.append(scenario)
                    return result

                def extract_with_swap(stream, tree, limits):
                    if scenario in ("during_extract", "unlink_recreate_restore"):
                        self.swap_staged_snapshot(
                            staged, b"replacement-during-extract\n", False
                        )
                        try:
                            result = original_extract(stream, tree, limits)
                        finally:
                            replacement = staged
                            held = staged.with_name("snapshot.original")
                            replacement.unlink()
                            held.rename(staged)
                        hooks.append(scenario)
                        return result
                    if scenario == "in_place_restore":
                        original = os.pread(stream.fileno(), 1, 0)
                        os.pwrite(stream.fileno(), b"X", 0)
                        os.fsync(stream.fileno())
                        os.pwrite(stream.fileno(), original, 0)
                        os.fsync(stream.fileno())
                        hooks.append(scenario)
                    result = original_extract(stream, tree, limits)
                    if scenario == "after_extract":
                        self.swap_staged_snapshot(
                            staged, b"replacement-after-extract\n", True
                        )
                        hooks.append(scenario)
                    elif scenario == "same_bytes_new_inode":
                        exact = staged.read_bytes()
                        self.swap_staged_snapshot(staged, exact, False)
                        hooks.append(scenario)
                    return result

                with mock.patch.object(
                    closure.snapshot_v2,
                    "build_capture_manifest",
                    return_value=manifest,
                ), mock.patch.object(
                    closure.snapshot_v2,
                    "require_repository_head",
                    return_value=None,
                ), mock.patch.object(
                    closure,
                    "copy_snapshot_archive_held",
                    side_effect=copy_then_swap,
                ), mock.patch.object(
                    closure.snapshot_v2,
                    "extract_canonical_tar_stream",
                    side_effect=extract_with_swap,
                ):
                    with self.assertRaises(closure.ClosureError):
                        closure.stage_verify_and_extract_snapshot(
                            REPO_ROOT,
                            artifact,
                            runtime,
                            contract,
                            work,
                        )
                self.assertEqual(hooks, [scenario])

    def test_held_snapshot_descriptor_verifies_and_extracts_one_exact_stream(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (
                contract,
                _,
                _,
                manifest,
                artifact,
                runtime,
            ) = self.held_snapshot_fixture(root)
            work = root / "work"
            work.mkdir(mode=0o700)
            with mock.patch.object(
                closure.snapshot_v2,
                "build_capture_manifest",
                return_value=manifest,
            ), mock.patch.object(
                closure.snapshot_v2,
                "require_repository_head",
                return_value=None,
            ):
                tree, observed, snapshot_input = (
                    closure.stage_verify_and_extract_snapshot(
                        REPO_ROOT,
                        artifact,
                        runtime,
                        contract,
                        work,
                    )
                )
            self.assertEqual(observed, manifest)
            self.assertEqual(
                snapshot_input["artifact"]["sha256"],
                runtime["artifact_sha256"],
            )
            self.assertEqual(
                json.loads(
                    (tree / "capture-manifest.json").read_text(encoding="ascii")
                ),
                manifest,
            )

    def test_snapshot_checker_import_origin_and_source_are_exact(self):
        contract = self.contract_fixture()
        closure.validate_snapshot_checker_binding(REPO_ROOT, contract)
        self.assertEqual(
            closure.snapshot_v2.GIT_AUTHORITY_EXECUTABLE,
            "/usr/bin/git",
        )
        self.assertEqual(
            closure.snapshot_v2.git_authority_environment(),
            contract["snapshot_authority"]["git_authority"]["environment"],
        )
        self.assertFalse(
            contract["snapshot_authority"]["git_authority"][
                "inherit_environment"
            ]
        )
        with mock.patch.object(
            closure.snapshot_v2, "__file__", "/tmp/hostile-snapshot-checker.py"
        ):
            with self.assertRaisesRegex(closure.ClosureError, "import origin"):
                closure.validate_snapshot_checker_binding(REPO_ROOT, contract)

    def materialization_fixture(self, root):
        contract = self.contract_fixture()
        files = {"release-key/RPM-GPG-KEY-Rocky-10": b"key"}
        repositories = []
        for authority in contract["snapshot_authority"]["repositories"]:
            repository = dict(authority)
            repository["repomd"] = {
                "revision": "10.2",
                "sha256": "1" * 64,
                "size": 1,
            }
            repository["signature"] = {
                "hash_algorithm_id": 10,
                "primary_fingerprint": closure.snapshot_v2.RELEASE_FINGERPRINT,
                "public_key_algorithm_id": 1,
                "sha256": "2" * 64,
                "signature_fingerprint": closure.snapshot_v2.RELEASE_FINGERPRINT,
                "signature_timestamp": 1,
                "size": 1,
                "status": "valid",
            }
            if authority["kind"] == "binary":
                prefix = "repositories/{}/repodata/".format(authority["id"])
                files[prefix + "repomd.xml"] = b"repomd-" + authority["id"].encode("ascii")
                files[prefix + "repomd.xml.asc"] = b"signature"
                files[prefix + "signature.json"] = b"{}\n"
                primary = b"primary-" + authority["id"].encode("ascii")
                href = "repodata/primary.xml.gz"
                files["repositories/{}/{}".format(authority["id"], href)] = primary
                repository["objects"] = [
                    {
                        "compressed_sha256": hashlib.sha256(primary).hexdigest(),
                        "compressed_size": len(primary),
                        "compression": "gzip",
                        "href": href,
                        "open_checksum_declared": True,
                        "open_sha256": "3" * 64,
                        "open_size": 1,
                        "type": "primary",
                        "verified_open_sha256": "3" * 64,
                        "verified_open_size": 1,
                    }
                ]
            else:
                repository["objects"] = []
            repositories.append(repository)
        for relative, data in files.items():
            path = root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
        payload = [
            {
                "path": relative,
                "sha256": hashlib.sha256(data).hexdigest(),
                "size": len(data),
            }
            for relative, data in sorted(files.items())
        ]
        return contract, {"payload_files": payload, "repositories": repositories}

    def test_only_three_binary_repositories_are_materialized_from_verified_payload(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            tree = root / "tree"
            tree.mkdir()
            contract, manifest = self.materialization_fixture(tree)
            with closure.V2OutputTransaction(root / "output") as output:
                roots, rows, dnf_rows, release_key = (
                    closure.materialize_snapshot_v2_repositories(
                        tree, manifest, output, contract
                    )
                )
                self.assertEqual(sorted(roots), ["appstream", "baseos", "crb"])
                self.assertEqual(
                    [item["id"] for item in dnf_rows],
                    ["baseos", "appstream", "crb"],
                )
                self.assertEqual([item["kind"] for item in rows], ["binary"] * 3)
                self.assertEqual(release_key.read_bytes(), b"key")
                self.assertNotIn("source-baseos", roots)

            primary = tree / "repositories/baseos/repodata/primary.xml.gz"
            primary.write_bytes(b"x" * len(primary.read_bytes()))
            with closure.V2OutputTransaction(root / "second-output") as output:
                with self.assertRaisesRegex(closure.ClosureError, "payload digest"):
                    closure.materialize_snapshot_v2_repositories(
                        tree, manifest, output, contract
                    )

    def test_locked_direct_and_source_rpms_must_exist_in_signed_primary(self):
        toolchain = json.loads(
            (REPO_ROOT / "host-kernel/rocky/toolchain-lock.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(len(toolchain["direct_artifacts"]), 20)
        primary = {}
        for artifact in toolchain["direct_artifacts"]:
            primary[artifact["nevra"]] = {
                key: artifact[key]
                for key in (
                    "arch",
                    "nevra",
                    "repository_id",
                    "repository_location",
                    "sha256",
                    "size",
                )
            }
        closure.validate_locked_primary_membership(primary, toolchain)
        primary.pop(toolchain["direct_artifacts"][0]["nevra"])
        with self.assertRaisesRegex(closure.ClosureError, "absent"):
            closure.validate_locked_primary_membership(primary, toolchain)

        source = json.loads(
            (REPO_ROOT / "host-kernel/rocky/source-lock.json").read_text(
                encoding="utf-8"
            )
        )
        locked = source["source_rpm"]
        xml = (
            '<metadata xmlns="http://linux.duke.edu/metadata/common" packages="1">'
            '<package type="rpm"><name>{}</name><arch>{}</arch>'
            '<version epoch="{}" ver="{}" rel="{}"/>'
            '<checksum type="sha256" pkgid="YES">{}</checksum>'
            '<size package="{}" installed="1" archive="1"/>'
            '<location href="{}"/></package></metadata>'
        ).format(
            locked["name"],
            locked["arch"],
            locked["epoch"],
            locked["version"],
            locked["release"],
            locked["sha256"],
            locked["size"],
            locked["repository_location"],
        ).encode("ascii")
        with tempfile.TemporaryDirectory() as temporary:
            tree = Path(temporary)
            primary_path = (
                tree
                / "repositories/source-baseos/repodata/primary.xml.gz"
            )
            primary_path.parent.mkdir(parents=True)
            with gzip.open(str(primary_path), "wb") as stream:
                stream.write(xml)
            primary_bytes = primary_path.read_bytes()
            manifest = {
                "repositories": [
                    {
                        "id": "source-baseos",
                        "objects": [
                            {
                                "compressed_sha256": hashlib.sha256(
                                    primary_bytes
                                ).hexdigest(),
                                "compressed_size": len(primary_bytes),
                                "href": "repodata/primary.xml.gz",
                                "type": "primary",
                            }
                        ],
                    }
                ]
            }
            result = closure.validate_source_primary_membership(
                tree, manifest, source, self.contract_fixture()
            )
            self.assertTrue(result["verified"])
            self.assertEqual(result["source_rpm"]["nevra"], locked["nevra"])
            changed_source = copy.deepcopy(source)
            changed_source["source_rpm"]["sha256"] = "0" * 64
            with self.assertRaisesRegex(closure.ClosureError, "source RPM digest"):
                closure.validate_source_primary_membership(
                    tree, manifest, changed_source, self.contract_fixture()
                )

    def snapshot_input_fixture(self, contract):
        _, runtime = self.runtime_fixture()
        authority = contract["snapshot_authority"]
        return {
            "artifact": {
                "name": "rocky-repository-snapshot-v2-123-4",
                "repository": closure.snapshot_v2.WORKFLOW_REPOSITORY,
                "sha256": runtime["artifact_sha256"],
                "size": 1,
            },
            "bootstrap_checkpoint_id": closure.phase_one.CHECKPOINT_ID,
            "bootstrap_manifest": {"sha256": "c" * 64, "size": 1},
            "capture_id": authority["capture_id"],
            "claims": dict(closure.snapshot_v2.FALSE_CLAIMS),
            "credit_eligible": False,
            "execution_identity": dict(runtime["execution_identity"]),
            "gate_claims": dict(contract["gate_claims"]),
            "repository_ids": [item["id"] for item in authority["repositories"]],
            "repository_inputs": [
                dict(item) for item in authority["required_repository_inputs"]
            ],
            "run_attempt": 4,
            "run_id": 123,
            "schema_version": 2,
            "snapshot_identity": "d" * 64,
        }

    def test_snapshot_input_schema_rejects_credit_and_unbound_fields(self):
        contract = self.contract_fixture()
        value = self.snapshot_input_fixture(contract)
        closure.validate_snapshot_input_v2(value, contract)
        for mutation in ("credit", "input", "extra"):
            changed = copy.deepcopy(value)
            if mutation == "credit":
                changed["gate_claims"]["RK-003"] = True
            elif mutation == "input":
                changed["repository_inputs"][0]["sha256"] = "0" * 64
            else:
                changed["unexpected"] = True
            with self.subTest(mutation=mutation), self.assertRaises(
                closure.ClosureError
            ):
                closure.validate_snapshot_input_v2(changed, contract)

    def resolution_fixture(self):
        direct = ["direct-0:1-1.x86_64"]
        effective = ["alpha", "beta"]
        reviewed = ["rust"]
        roots = [
            {"kind": "rocky-effective-spec", "value": item}
            for item in effective
        ]
        roots.extend(
            {"kind": "reviewed-rocky-rust", "value": item}
            for item in reviewed
        )
        roots.extend(
            {"kind": "locked-direct-nevra", "value": item} for item in direct
        )
        spec_sha256 = "e" * 64
        semantic = {
            "direct_nevras": direct,
            "effective_buildrequires": effective,
            "kernel_spec_sha256": spec_sha256,
            "resolution_roots": roots,
            "reviewed_rocky_rust_additions": reviewed,
        }
        authority = {
            "direct_nevra_count": 1,
            "direct_nevras_sha256": hashlib.sha256(canonical(direct)).hexdigest(),
            "effective_buildrequires_count": 2,
            "kernel_spec": {
                "dist_git_commit": "1" * 40,
                "path": "SPECS/kernel.spec",
                "sha256": spec_sha256,
                "size": 12,
            },
            "resolution_inputs_sha256": hashlib.sha256(canonical(semantic)).hexdigest(),
            "resolution_root_count": 4,
            "reviewed_rocky_rust_additions": reviewed,
        }
        contract = {
            "gate_claims": {"RK-003": False},
            "resolution_authority": authority,
            "snapshot_authority": {"source_repository_id": "source-baseos"},
        }
        value = {
            "collector_http_sealed_before_derivation": True,
            "credit_eligible": False,
            "direct_nevras": direct,
            "effective_buildrequires": effective,
            "gate_claims": {"RK-003": False},
            "kernel_spec": {
                "archive_path": "inputs/kernel.spec",
                "download": {
                    "final_url": "https://git.rockylinux.org/staging/rpms/kernel/-/raw/{}/SPECS/kernel.spec".format(
                        "1" * 40
                    ),
                    "redirect_count": 0,
                    "sha256": spec_sha256,
                    "size": 12,
                },
                "sha256": spec_sha256,
                "size": 12,
            },
            "resolution_inputs_sha256": authority["resolution_inputs_sha256"],
            "resolution_roots": roots,
            "reviewed_rocky_rust_additions": reviewed,
            "rpm_showrc_sha256": "f" * 64,
            "rpmspec_output_sha256": "0" * 64,
            "schema_version": 2,
            "source_snapshot_membership": {
                "primary": {
                    "href": "repodata/primary.xml.gz",
                    "sha256": "1" * 64,
                    "size": 1,
                },
                "repository_id": "source-baseos",
                "source_rpm": {
                    "arch": "src",
                    "nevra": "kernel-0:1-1.src",
                    "repository_id": "source-baseos",
                    "repository_location": "Packages/k/kernel.src.rpm",
                    "sha256": "2" * 64,
                    "size": 1,
                },
                "verified": True,
            },
            "source_spec_condition": "fixture",
        }
        return contract, value

    def test_resolution_schema_binds_semantic_roots_and_source_membership(self):
        contract, value = self.resolution_fixture()
        closure.validate_resolution_input_v2(value, contract)
        changed = copy.deepcopy(value)
        changed["resolution_roots"][0]["value"] = "changed"
        with self.assertRaisesRegex(closure.ClosureError, "resolution roots"):
            closure.validate_resolution_input_v2(changed, contract)
        promoted = copy.deepcopy(value)
        promoted["credit_eligible"] = True
        with self.assertRaisesRegex(closure.ClosureError, "credit"):
            closure.validate_resolution_input_v2(promoted, contract)

    def test_v2_checkpoint_never_claims_credit_and_binds_current_snapshot(self):
        names = [
            "blockers.json",
            "closure.json",
            "environment.json",
            "offline-replay.json",
            "probes.json",
            "resolution-input.json",
            "rpm-macros.json",
            "snapshot-input.json",
        ]
        checkpoint = {
            "claims": dict(closure.snapshot_v2.FALSE_CLAIMS),
            "credit_eligible": False,
            "gate_claims": {"RK-003": False},
            "github": {
                "head_sha": "1" * 40,
                "repository": "phoenix-hacking/mckernel",
                "run_attempt": 1,
                "run_id": 2,
            },
            "manifests": [
                {"path": name, "sha256": "a" * 64, "size": 1}
                for name in names
            ],
            "phase": "closure-offline",
            "schema_version": 2,
            "snapshot_identity": "b" * 64,
            "snapshot_source_commit": "1" * 40,
            "snapshot_tar_sha256": "c" * 64,
            "successful_capture_requires_independent_review": True,
        }
        closure.validate_capture_checkpoint_v2(checkpoint)
        for mutation in ("accept", "credit", "commit"):
            changed = copy.deepcopy(checkpoint)
            if mutation == "accept":
                changed["claims"]["accepted_checkpoint"] = True
            elif mutation == "credit":
                changed["gate_claims"]["RK-003"] = True
            else:
                changed["snapshot_source_commit"] = "2" * 40
            with self.subTest(mutation=mutation), self.assertRaises(
                closure.ClosureError
            ):
                closure.validate_capture_checkpoint_v2(changed)


class V2OutputTransactionTests(unittest.TestCase):
    def replace_held_regular(self, directory_descriptor, name, data):
        os.unlink(name, dir_fd=directory_descriptor)
        descriptor = os.open(
            name,
            os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
            0o600,
            dir_fd=directory_descriptor,
        )
        try:
            closure.v2_write_all(descriptor, data, "test replacement")
            os.fchmod(descriptor, 0o400)
            os.fsync(descriptor)
        finally:
            os.close(descriptor)
        os.fsync(directory_descriptor)

    def test_existing_leaf_file_directory_and_symlink_fail_closed(self):
        for kind in ("file", "directory", "symlink"):
            with self.subTest(kind=kind), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                parent = root / "parent"
                outside = root / "outside"
                parent.mkdir()
                outside.mkdir()
                destination = parent / "bundle"
                if kind == "file":
                    destination.write_bytes(b"collision")
                    message = "regular file"
                elif kind == "directory":
                    destination.mkdir()
                    message = "directory"
                else:
                    destination.symlink_to(outside, target_is_directory=True)
                    message = "symlink"
                with self.assertRaisesRegex(closure.ClosureError, message):
                    closure.V2OutputTransaction(destination)
                self.assertEqual(list(outside.iterdir()), [])

    def test_cross_parent_copy_uses_same_parent_atomic_publication(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            parent = root / "parent"
            parent.mkdir()
            destination = parent / "bundle"
            original_copy = closure.v2_copy_output_tree
            original_rename = closure.v2_rename_noreplace
            with mock.patch.object(
                closure, "v2_copy_output_tree", wraps=original_copy
            ) as copy_tree, mock.patch.object(
                closure, "v2_rename_noreplace", wraps=original_rename
            ) as rename:
                with closure.V2OutputTransaction(destination) as output:
                    stage_root = output.stage_root
                    self.assertNotEqual(
                        closure.v2_directory_identity(
                            os.fstat(output.stage_parent_descriptor)
                        ),
                        closure.v2_directory_identity(
                            os.fstat(output.output_parent_descriptor)
                        ),
                    )
                    output.write_bytes(PurePosixPath("nested/value"), b"fixture")
                    output.write_json(PurePosixPath("metadata.json"), {"value": 1})
                    output.write_sha256sums()
                    output.verify_sha256sums(["metadata.json", "nested/value"])
                    output.publish()
                    copy_arguments = copy_tree.call_args_list[0][0]
                    self.assertNotEqual(copy_arguments[0], copy_arguments[1])
                    rename_arguments = rename.call_args[0]
                    self.assertEqual(rename_arguments[0], rename_arguments[2])
                self.assertFalse(stage_root.exists())
            self.assertEqual((destination / "nested/value").read_bytes(), b"fixture")
            self.assertEqual(
                (destination / "metadata.json").read_bytes(), b'{"value":1}\n'
            )
            self.assertEqual(
                stat.S_IMODE((destination / "nested/value").stat().st_mode), 0o400
            )
            self.assertEqual(
                stat.S_IMODE((destination / "nested").stat().st_mode), 0o700
            )

    def test_late_leaf_file_directory_and_symlink_collisions_are_not_replaced(self):
        for kind in ("file", "directory", "symlink"):
            with self.subTest(kind=kind), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                parent = root / "parent"
                outside = root / "outside"
                parent.mkdir()
                outside.mkdir()
                destination = parent / "bundle"
                original_copy = closure.v2_copy_output_tree
                injected = []

                def copy_then_collide(source_descriptor, destination_descriptor):
                    copied = original_copy(source_descriptor, destination_descriptor)
                    if injected:
                        return copied
                    injected.append(True)
                    if kind == "file":
                        destination.write_bytes(b"late collision")
                    elif kind == "directory":
                        destination.mkdir()
                    else:
                        destination.symlink_to(outside, target_is_directory=True)
                    return copied

                with closure.V2OutputTransaction(destination) as output:
                    output.write_bytes(PurePosixPath("value"), b"fixture")
                    output.write_sha256sums()
                    output.verify_sha256sums(["value"])
                    with mock.patch.object(
                        closure,
                        "v2_copy_output_tree",
                        side_effect=copy_then_collide,
                    ):
                        with self.assertRaisesRegex(
                            closure.ClosureError, "appeared before publication"
                        ):
                            output.publish()
                self.assertTrue(injected)
                self.assertTrue(destination.exists() or destination.is_symlink())
                self.assertEqual(list(outside.iterdir()), [])
                self.assertFalse(
                    any(".publish." in item.name for item in parent.iterdir())
                )

    def test_atomic_stage_unlink_recreate_after_verification_is_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            parent = root / "parent"
            parent.mkdir()
            destination = parent / "bundle"
            original_copy = closure.v2_copy_output_tree
            mutated = []

            def replace_then_copy(source_descriptor, destination_descriptor):
                if not mutated:
                    self.replace_held_regular(
                        source_descriptor,
                        "value",
                        b"hostile-post-verification-replacement\n",
                    )
                    mutated.append(True)
                return original_copy(source_descriptor, destination_descriptor)

            with closure.V2OutputTransaction(destination) as output:
                output.write_bytes(
                    PurePosixPath("value"), b"trusted-evidence\n"
                )
                output.write_sha256sums()
                output.verify_sha256sums(["value"])
                with mock.patch.object(
                    closure,
                    "v2_copy_output_tree",
                    side_effect=replace_then_copy,
                ):
                    with self.assertRaises(closure.ClosureError):
                        output.publish()
            self.assertTrue(mutated)
            self.assertFalse(destination.exists() or destination.is_symlink())
            self.assertFalse(any(".publish." in item.name for item in parent.iterdir()))

    def test_hidden_unlink_recreate_before_rename_is_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            parent = root / "parent"
            parent.mkdir()
            destination = parent / "bundle"
            original_rename = closure.v2_rename_noreplace
            mutated = []

            def replace_hidden_then_rename(
                source_directory,
                source_name,
                destination_directory,
                destination_name,
            ):
                hidden = os.open(
                    source_name,
                    os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW,
                    dir_fd=source_directory,
                )
                try:
                    self.replace_held_regular(hidden, "value", b"trusted-evidence\n")
                    mutated.append(True)
                finally:
                    os.close(hidden)
                return original_rename(
                    source_directory,
                    source_name,
                    destination_directory,
                    destination_name,
                )

            with closure.V2OutputTransaction(destination) as output:
                output.write_bytes(
                    PurePosixPath("value"), b"trusted-evidence\n"
                )
                output.write_sha256sums()
                output.verify_sha256sums(["value"])
                with mock.patch.object(
                    closure,
                    "v2_rename_noreplace",
                    side_effect=replace_hidden_then_rename,
                ):
                    with self.assertRaises(closure.ClosureError):
                        output.publish()
            self.assertTrue(mutated)
            self.assertFalse(destination.exists() or destination.is_symlink())
            self.assertEqual(list(parent.iterdir()), [])

    def test_sha256sums_mutation_after_verification_is_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            parent = root / "parent"
            parent.mkdir()
            destination = parent / "bundle"
            original_copy = closure.v2_copy_output_tree
            mutated = []

            def replace_manifest_then_copy(
                source_descriptor, destination_descriptor
            ):
                if not mutated:
                    self.replace_held_regular(
                        source_descriptor,
                        "SHA256SUMS",
                        ("0" * 64 + "  value\n").encode("ascii"),
                    )
                    mutated.append(True)
                return original_copy(source_descriptor, destination_descriptor)

            with closure.V2OutputTransaction(destination) as output:
                output.write_bytes(PurePosixPath("value"), b"trusted-evidence\n")
                output.write_sha256sums()
                output.verify_sha256sums(["value"])
                with mock.patch.object(
                    closure,
                    "v2_copy_output_tree",
                    side_effect=replace_manifest_then_copy,
                ):
                    with self.assertRaises(closure.ClosureError):
                        output.publish()
            self.assertTrue(mutated)
            self.assertFalse(destination.exists() or destination.is_symlink())
            self.assertEqual(list(parent.iterdir()), [])

    def test_final_descriptor_mutation_during_verification_is_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            parent = root / "parent"
            parent.mkdir()
            destination = parent / "bundle"
            original_verify = closure.v2_verify_checksum_directory
            mutated = []

            with closure.V2OutputTransaction(destination) as output:
                output.write_bytes(PurePosixPath("value"), b"trusted-evidence\n")
                output.write_sha256sums()
                output.verify_sha256sums(["value"])

                def verify_then_replace_final(descriptor, *args, **kwargs):
                    result = original_verify(descriptor, *args, **kwargs)
                    try:
                        final_metadata = os.stat(
                            destination.name,
                            dir_fd=output.output_parent_descriptor,
                            follow_symlinks=False,
                        )
                    except FileNotFoundError:
                        return result
                    if (
                        not mutated
                        and stat.S_ISDIR(final_metadata.st_mode)
                        and final_metadata.st_ino == os.fstat(descriptor).st_ino
                        and final_metadata.st_dev == os.fstat(descriptor).st_dev
                    ):
                        self.replace_held_regular(
                            descriptor, "value", b"trusted-evidence\n"
                        )
                        mutated.append(True)
                    return result

                with mock.patch.object(
                    closure,
                    "v2_verify_checksum_directory",
                    side_effect=verify_then_replace_final,
                ):
                    with self.assertRaises(closure.ClosureError):
                        output.publish()
            self.assertTrue(mutated)
            self.assertFalse(destination.exists() or destination.is_symlink())
            self.assertEqual(list(parent.iterdir()), [])

    def test_parent_swap_before_write_create_copy_or_rename_writes_nothing_outside(self):
        checkpoints = (
            "v2 output parent before staged output write",
            "v2 output parent before publication directory create",
            "v2 output parent before publication copy",
            "v2 output parent before publication rename",
        )
        for checkpoint in checkpoints:
            with self.subTest(checkpoint=checkpoint), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                parent = root / "safe-parent"
                moved = root / "held-parent"
                outside = root / "outside"
                parent.mkdir()
                outside.mkdir()
                destination = parent / "bundle"
                with closure.V2OutputTransaction(destination) as output:
                    output.write_bytes(PurePosixPath("seed"), b"fixture")
                    output.write_sha256sums()
                    output.verify_sha256sums(["seed"])
                    original_check = output.require_output_parent
                    swapped = []

                    def swap_then_check(label):
                        if label == checkpoint and not swapped:
                            parent.rename(moved)
                            parent.symlink_to(outside, target_is_directory=True)
                            swapped.append(True)
                        return original_check(label)

                    with mock.patch.object(
                        output,
                        "require_output_parent",
                        side_effect=swap_then_check,
                    ):
                        with self.assertRaises(closure.ClosureError):
                            if checkpoint.endswith("staged output write"):
                                output.write_bytes(
                                    PurePosixPath("must-not-exist"), b"blocked"
                                )
                            else:
                                output.publish()
                self.assertTrue(swapped)
                self.assertTrue(parent.is_symlink())
                self.assertEqual(list(outside.iterdir()), [])
                self.assertEqual(list(moved.iterdir()), [])

    def test_parent_swap_before_trusted_stage_create_writes_nothing_outside(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            parent = root / "safe-parent"
            moved = root / "held-parent"
            outside = root / "outside"
            parent.mkdir()
            outside.mkdir()
            destination = parent / "bundle"
            original_check = closure.v2_require_stable_directory
            swapped = []

            def swap_then_check(path, descriptor, expected, label):
                if label == "v2 output parent before trusted stage create" and not swapped:
                    parent.rename(moved)
                    parent.symlink_to(outside, target_is_directory=True)
                    swapped.append(True)
                return original_check(path, descriptor, expected, label)

            with mock.patch.object(
                closure,
                "v2_require_stable_directory",
                side_effect=swap_then_check,
            ):
                with self.assertRaises(closure.ClosureError):
                    closure.V2OutputTransaction(destination)
            self.assertTrue(swapped)
            self.assertEqual(list(outside.iterdir()), [])
            self.assertEqual(list(moved.iterdir()), [])

    def test_cleanup_unlinks_stage_symlink_without_traversal(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            parent = root / "parent"
            outside = root / "outside"
            parent.mkdir()
            outside.mkdir()
            sentinel = outside / "sentinel"
            sentinel.write_bytes(b"preserve")
            output = closure.V2OutputTransaction(parent / "bundle")
            stage_root = output.stage_root
            os.symlink(
                str(outside),
                "hostile-link",
                dir_fd=output.stage_descriptor,
            )
            output.close()
            self.assertFalse(stage_root.exists())
            self.assertEqual(sentinel.read_bytes(), b"preserve")

    def test_capture_has_no_inherited_path_based_output_publication(self):
        source = (REPO_ROOT / "scripts/rocky_kernel_closure_offline.py").read_text(
            encoding="utf-8"
        )
        capture_source = source.split("\ndef capture(\n", 1)[1].split(
            "\ndef validate_workflow", 1
        )[0]
        for forbidden in (
            "phase_one.prepare_output_dir",
            "phase_one.write_output_bytes",
            "phase_one.write_output_json",
            "phase_one.write_sha256sums",
            "copy_archive(",
        ):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, capture_source)
        self.assertIn("with V2OutputTransaction(output_dir) as output", capture_source)
        self.assertIn("output.publish()", capture_source)


class DirectInputTests(unittest.TestCase):
    def refresh_fixture(self, root):
        checkpoint = json.loads((root / "checkpoint.json").read_text(encoding="utf-8"))
        for row in checkpoint["manifests"]:
            data = (root / row["path"]).read_bytes()
            row["sha256"] = hashlib.sha256(data).hexdigest()
            row["size"] = len(data)
        (root / "checkpoint.json").write_bytes(canonical(checkpoint))
        write_checksums(root)

    def make_fixture(self, root, contract, identity=None):
        direct = contract["direct_phase"]
        github = identity or {
            "head_sha": direct["head_sha"],
            "repository": direct["github_repository"],
            "run_attempt": direct["run_attempt"],
            "run_id": direct["run_id"],
        }
        build = {
            "closure_complete": False,
            "collector_http_sealed_before_derivation": True,
            "direct_nevras": ["fixture-0:1-1.x86_64"],
            "effective_buildrequires": ["root-{}".format(i) for i in range(86)],
            "kernel_spec_sha256": "a" * 64,
            "network_isolation_claimed": False,
            "resolution_roots": [
                {"kind": "fixture", "value": "root-{}".format(i)}
                for i in range(109)
            ],
            "reviewed_rocky_rust_additions": ["bindgen", "rust", "rust-src"],
            "reviewed_source_change_applied": False,
            "rpmspec_output_sha256": "b" * 64,
            "rpm_showrc_sha256": "c" * 64,
            "schema_version": 1,
            "source_spec_condition": "fixture",
            "transitive_resolution_status": "required-missing",
        }
        build_bytes = canonical(build)
        (root / "build-requirements.json").write_bytes(build_bytes)
        for name in closure.DIRECT_MANIFEST_NAMES:
            path = root / name
            if not path.exists():
                path.write_bytes(canonical({"fixture": name}))
        manifests = []
        for name in closure.DIRECT_MANIFEST_NAMES:
            data = (root / name).read_bytes()
            manifests.append(
                {
                    "path": name,
                    "sha256": hashlib.sha256(data).hexdigest(),
                    "size": len(data),
                }
            )
        checkpoint = {
            "acquisition": {
                "collector_http_after_seal": False,
                "collector_http_downloaded_bytes": 1,
                "collector_http_sealed": True,
                "network_isolation_claimed": False,
                "scope": "fixture",
            },
            "checkpoint_id": closure.phase_one.CHECKPOINT_ID,
            "credit_eligible": False,
            "gate_claims": {"RK-003": False, "RK-005": False},
            "github": github,
            "manifests": manifests,
            "phase": "repository-direct",
            "schema_version": 1,
            "successful_capture_requires_review": True,
        }
        checkpoint_bytes = canonical(checkpoint)
        (root / "checkpoint.json").write_bytes(checkpoint_bytes)
        fixture_contract = copy.deepcopy(contract)
        fixture_contract["direct_phase"]["historical_checkpoint_sha256"] = hashlib.sha256(
            checkpoint_bytes
        ).hexdigest()
        fixture_contract["direct_phase"]["historical_build_requirements_sha256"] = hashlib.sha256(
            build_bytes
        ).hexdigest()
        resolution_inputs = {
            key: build[key]
            for key in (
                "direct_nevras",
                "effective_buildrequires",
                "kernel_spec_sha256",
                "resolution_roots",
                "reviewed_rocky_rust_additions",
            )
        }
        fixture_contract["direct_phase"]["resolution_inputs_sha256"] = hashlib.sha256(
            canonical(resolution_inputs)
        ).hexdigest()
        write_checksums(root)
        expected = sorted(closure.DIRECT_MANIFEST_NAMES + ["checkpoint.json"])
        return fixture_contract, expected

    def test_historical_and_current_exact_identity_modes(self):
        contract = closure.validate_legacy_contract(REPO_ROOT)
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            fixture, expected = self.make_fixture(root, contract)
            build = closure.validate_direct_root(root, fixture, expected_files=expected)
            self.assertEqual(len(build["resolution_roots"]), 109)

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            current = {
                "head_sha": "1" * 40,
                "repository": "phoenix-hacking/mckernel",
                "run_attempt": 2,
                "run_id": 99,
            }
            fixture, expected = self.make_fixture(root, contract, current)
            closure.validate_direct_root(root, fixture, current, expected)
            wrong = dict(current)
            wrong["head_sha"] = "2" * 40
            with self.assertRaisesRegex(closure.ClosureError, "identity"):
                closure.validate_direct_root(root, fixture, wrong, expected)

    def test_unlisted_file_and_checksum_mutation_fail_closed(self):
        contract = closure.validate_legacy_contract(REPO_ROOT)
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            fixture, expected = self.make_fixture(root, contract)
            (root / "unlisted").write_text("bad", encoding="utf-8")
            with self.assertRaisesRegex(closure.ClosureError, "closure"):
                closure.validate_direct_root(root, fixture, expected_files=expected)

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            fixture, expected = self.make_fixture(root, contract)
            (root / "arbitrary-reviewed-looking.json").write_text("{}\n", encoding="utf-8")
            write_checksums(root)
            with self.assertRaisesRegex(closure.ClosureError, "exact file set"):
                closure.validate_direct_root(root, fixture, expected_files=expected)

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            fixture, expected = self.make_fixture(root, contract)
            (root / "checkpoint.json").write_text("{}\n", encoding="utf-8")
            with self.assertRaisesRegex(closure.ClosureError, "checksum"):
                closure.validate_direct_root(root, fixture, expected_files=expected)

    def test_unexpected_checkpoint_and_build_fields_fail_closed(self):
        contract = closure.validate_legacy_contract(REPO_ROOT)
        current = {
            "head_sha": "1" * 40,
            "repository": "phoenix-hacking/mckernel",
            "run_attempt": 1,
            "run_id": 1,
        }
        for name in ("checkpoint.json", "build-requirements.json"):
            with self.subTest(name=name), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                fixture, expected = self.make_fixture(root, contract, current)
                value = json.loads((root / name).read_text(encoding="utf-8"))
                value["unexpected"] = True
                (root / name).write_bytes(canonical(value))
                self.refresh_fixture(root)
                with self.assertRaisesRegex(closure.ClosureError, "fields changed"):
                    closure.validate_direct_root(root, fixture, current, expected)

    def test_symlinked_direct_root_and_symlinked_member_fail_closed(self):
        contract = closure.validate_legacy_contract(REPO_ROOT)
        with tempfile.TemporaryDirectory() as temporary:
            parent = Path(temporary)
            root = parent / "direct"
            root.mkdir()
            fixture, expected = self.make_fixture(root, contract)
            link = parent / "direct-link"
            link.symlink_to(root, target_is_directory=True)
            with self.assertRaisesRegex(closure.ClosureError, "regular directory"):
                closure.validate_direct_root(link, fixture, expected_files=expected)

        with tempfile.TemporaryDirectory() as temporary:
            parent = Path(temporary)
            root = parent / "direct"
            root.mkdir()
            fixture, expected = self.make_fixture(root, contract)
            outside = parent / "outside"
            outside.write_text("outside", encoding="utf-8")
            (root / "member-link").symlink_to(outside)
            with self.assertRaisesRegex(closure.ClosureError, "symlink"):
                closure.validate_direct_root(root, fixture, expected_files=expected)

    def test_no_follow_reads_reject_symlink_ancestors_and_special_files(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            real = root / "real"
            real.mkdir()
            regular = real / "input"
            regular.write_bytes(b"fixture")
            link = root / "link"
            link.symlink_to(real, target_is_directory=True)
            with self.assertRaisesRegex(closure.ClosureError, "safely open"):
                closure.sha256_file(link / "input")
            with self.assertRaisesRegex(closure.ClosureError, "safely create"):
                closure.open_regular_create(link / "new", "fixture output")
            final_link = real / "final-link"
            final_link.symlink_to(regular)
            with self.assertRaisesRegex(closure.ClosureError, "safely open"):
                closure.sha256_file(final_link)
            fifo = real / "fifo"
            os.mkfifo(str(fifo))
            with self.assertRaisesRegex(closure.ClosureError, "regular file"):
                closure.sha256_file(fifo)

    def test_archive_copy_rejects_source_mutation(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "source"
            source.write_bytes(b"original")
            output = root / "output"
            output.mkdir()
            original_copy = shutil.copyfileobj

            def mutate_after_copy(input_stream, output_stream, length):
                original_copy(input_stream, output_stream, length)
                source.write_bytes(b"mutated-source")

            with mock.patch.object(
                closure.shutil, "copyfileobj", side_effect=mutate_after_copy
            ):
                with self.assertRaisesRegex(
                    closure.ClosureError, "changed while it was copied"
                ):
                    closure.copy_archive(source, output, Path("archive"))


class MetadataAndCommandTests(unittest.TestCase):
    def output_schema_fixtures(self):
        closure_manifest = {
            "all_archives_verified": True,
            "all_repomd_data_materialized": True,
            "all_signatures_verified": True,
            "configured_network_sources": [],
            "environment_manifest_sha256": "a" * 64,
            "exact_snapshot_root_solve_verified": True,
            "historical_direct_phase_checkpoint_sha256": "b" * 64,
            "network_isolation_claimed": False,
            "package_bytes": 0,
            "package_count": 0,
            "packages": [],
            "resolution_inputs_sha256": "c" * 64,
            "resolution_root_count": 0,
            "resolution_roots": [],
            "rpm_set_sha256": "d" * 64,
            "schema_version": 1,
            "snapshot_repositories": [],
            "unresolved_dependencies": [],
        }
        snapshot_solve = {
            "command": [],
            "empty_installroot_verified": True,
            "installed_package_count": 0,
            "installed_rpm_set_sha256": "d" * 64,
            "local_file_repositories_only": True,
            "transaction_exit_code": 0,
            "transaction_output_sha256": "e" * 64,
        }
        offline = {
            "all_repositories_disabled": True,
            "command": [],
            "empty_installroot_verified": True,
            "enabled_repository_count": 0,
            "environment_manifest_sha256": "a" * 64,
            "installed_package_count": 0,
            "installed_rpm_set_sha256": "d" * 64,
            "network_isolation_claimed": False,
            "network_scope": "bounded",
            "proxy_loopback_defense": True,
            "schema_version": 1,
            "snapshot_solve": snapshot_solve,
            "transaction_exit_code": 0,
            "transaction_output_sha256": "f" * 64,
        }
        probes = {
            "all_required_probes_verified": True,
            "environment_manifest_sha256": "a" * 64,
            "fixture_path": "/fixture",
            "fixture_sha256": "1" * 64,
            "fixture_size": 1,
            "network_isolation_claimed": False,
            "results": [],
            "schema_version": 1,
        }
        macros = {
            "command": ["rpm", "--showrc"],
            "output_sha256": "2" * 64,
            "output_size": 1,
            "schema_version": 1,
        }
        environment = {
            "architecture": "x86_64",
            "container_image": "fixture",
            "container_manifest_digest": "fixture",
            "container_platform": "linux/amd64",
            "direct_input": {},
            "github": {},
            "offline_installroot_package_count": 0,
            "offline_os_release": {},
            "offline_rpm_set_sha256": "d" * 64,
            "runtime_os_release": {},
            "schema_version": 1,
            "snapshot_solve_package_count": 0,
        }
        blockers = {
            "config_lock_blockers_at_capture": [],
            "gate_claims": {},
            "phase_success_blockers": [],
            "toolchain_lock_blockers_at_capture": [],
        }
        return closure_manifest, offline, probes, macros, environment, blockers

    def test_capture_output_schemas_reject_extra_fields(self):
        fixtures = self.output_schema_fixtures()
        closure.validate_capture_manifest_schemas(*fixtures)
        for index in range(len(fixtures)):
            mutated = list(copy.deepcopy(fixtures))
            mutated[index]["unexpected"] = True
            with self.subTest(index=index), self.assertRaisesRegex(
                closure.ClosureError, "fields changed"
            ):
                closure.validate_capture_manifest_schemas(*mutated)

    def output_schema_fixtures_v2(self):
        claims = {"RK-003": False}
        closure_manifest = {
            "all_archives_verified": True,
            "all_binary_repomd_data_materialized": True,
            "all_signatures_verified": True,
            "configured_network_sources": [],
            "credit_eligible": False,
            "environment_manifest_sha256": "a" * 64,
            "exact_snapshot_root_solve_verified": True,
            "gate_claims": dict(claims),
            "network_isolation_claimed": False,
            "package_bytes": 0,
            "package_count": 0,
            "packages": [],
            "resolution_inputs_sha256": "b" * 64,
            "resolution_root_count": 0,
            "resolution_roots": [],
            "rpm_set_sha256": "c" * 64,
            "schema_version": 2,
            "snapshot_input": {
                "artifact_sha256": "d" * 64,
                "capture_id": closure.snapshot_v2.CAPTURE_ID,
                "snapshot_identity": "e" * 64,
                "source_commit": "1" * 40,
            },
            "snapshot_repositories": [],
            "unresolved_dependencies": [],
        }
        snapshot_solve = {
            "command": [],
            "empty_installroot_verified": True,
            "installed_package_count": 0,
            "installed_rpm_set_sha256": "c" * 64,
            "local_file_repositories_only": True,
            "transaction_exit_code": 0,
            "transaction_output_sha256": "f" * 64,
        }
        offline = {
            "all_repositories_disabled": True,
            "command": [],
            "credit_eligible": False,
            "empty_installroot_verified": True,
            "enabled_repository_count": 0,
            "environment_manifest_sha256": "a" * 64,
            "gate_claims": dict(claims),
            "installed_package_count": 0,
            "installed_rpm_set_sha256": "c" * 64,
            "network_isolation_claimed": False,
            "network_scope": "bounded",
            "proxy_loopback_defense": True,
            "schema_version": 2,
            "snapshot_solve": snapshot_solve,
            "transaction_exit_code": 0,
            "transaction_output_sha256": "0" * 64,
        }
        probes = {
            "all_required_probes_verified": True,
            "credit_eligible": False,
            "environment_manifest_sha256": "a" * 64,
            "fixture_path": "/fixture",
            "fixture_sha256": "1" * 64,
            "fixture_size": 1,
            "gate_claims": dict(claims),
            "network_isolation_claimed": False,
            "results": [],
            "schema_version": 2,
        }
        macros = {
            "command": ["rpm", "--showrc"],
            "credit_eligible": False,
            "gate_claims": dict(claims),
            "output_sha256": "2" * 64,
            "output_size": 1,
            "schema_version": 2,
        }
        environment = {
            "architecture": "x86_64",
            "container_image": "fixture",
            "container_manifest_digest": "fixture",
            "container_platform": "linux/amd64",
            "credit_eligible": False,
            "gate_claims": dict(claims),
            "github": {},
            "offline_installroot_package_count": 0,
            "offline_os_release": {},
            "offline_rpm_set_sha256": "c" * 64,
            "resolution_inputs_sha256": "b" * 64,
            "runtime_os_release": {},
            "schema_version": 2,
            "snapshot_tar_sha256": "d" * 64,
            "snapshot_solve_package_count": 0,
        }
        blockers = {
            "config_lock_blockers_at_capture": [],
            "credit_eligible": False,
            "gate_claims": dict(claims),
            "phase_success_blockers": [],
            "schema_version": 2,
            "toolchain_lock_blockers_at_capture": [],
        }
        return closure_manifest, offline, probes, macros, environment, blockers

    def test_v2_capture_schemas_keep_every_credit_claim_false(self):
        fixtures = self.output_schema_fixtures_v2()
        closure.validate_capture_manifest_schemas_v2(*fixtures)
        expected_paths = closure.expected_capture_bundle_paths_v2(
            fixtures[0], fixtures[2]
        )
        self.assertIn("snapshot-input.json", expected_paths)
        self.assertIn("resolution-input.json", expected_paths)
        self.assertNotIn("snapshot.tar", expected_paths)
        self.assertFalse(any("repository-direct" in item for item in expected_paths))
        for index in range(len(fixtures)):
            mutated = list(copy.deepcopy(fixtures))
            mutated[index]["unexpected"] = True
            with self.subTest(index=index), self.assertRaisesRegex(
                closure.ClosureError, "fields changed"
            ):
                closure.validate_capture_manifest_schemas_v2(*mutated)
        promoted = list(copy.deepcopy(fixtures))
        promoted[3]["gate_claims"]["RK-003"] = True
        with self.assertRaisesRegex(closure.ClosureError, "gate claims"):
            closure.validate_capture_manifest_schemas_v2(*promoted)

    def test_checkpoint_schema_and_capture_file_closure_fail_closed(self):
        names = [
            "blockers.json",
            "closure.json",
            "environment.json",
            "offline-replay.json",
            "probes.json",
            "rpm-macros.json",
        ]
        checkpoint = {
            "credit_eligible": False,
            "direct_phase_head_sha": "1" * 40,
            "gate_claims": {"RK-003": False},
            "github": {
                "head_sha": "2" * 40,
                "repository": "phoenix-hacking/mckernel",
                "run_attempt": 1,
                "run_id": 1,
            },
            "manifests": [
                {"path": name, "sha256": "a" * 64, "size": 1}
                for name in names
            ],
            "phase": "closure-offline",
            "schema_version": 1,
            "successful_capture_requires_independent_review": True,
        }
        closure.validate_capture_checkpoint(checkpoint)
        for mutation in ("unexpected", "credit"):
            value = copy.deepcopy(checkpoint)
            if mutation == "unexpected":
                value["unexpected"] = True
            else:
                value["gate_claims"]["RK-003"] = True
            with self.subTest(mutation=mutation), self.assertRaises(
                closure.ClosureError
            ):
                closure.validate_capture_checkpoint(value)

        closure_manifest, _, probes, _, _, _ = self.output_schema_fixtures()
        expected = closure.expected_capture_bundle_paths(closure_manifest, probes)
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            for relative in expected:
                path = root / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(b"fixture")
            write_checksums(root)
            closure.verify_sha256sums(root, expected, "capture fixture")
            (root / "unexpected").write_bytes(b"unexpected")
            write_checksums(root)
            with self.assertRaisesRegex(closure.ClosureError, "exact file set"):
                closure.verify_sha256sums(root, expected, "capture fixture")

    def primary_fixture(self, path, packages):
        rows = []
        for package in packages:
            rows.append(
                """<package type="rpm"><name>{name}</name><arch>{arch}</arch>
                <version epoch="{epoch}" ver="{version}" rel="{release}"/>
                <checksum type="sha256" pkgid="YES">{sha256}</checksum>
                <size package="{size}" installed="1" archive="1"/>
                <location href="{location}"/></package>""".format(**package)
            )
        xml = (
            '<metadata xmlns="http://linux.duke.edu/metadata/common" packages="{}">'.format(
                len(rows)
            )
            + "".join(rows)
            + "</metadata>"
        ).encode("utf-8")
        with gzip.open(str(path), "wb") as stream:
            stream.write(xml)

    def test_primary_index_is_exact_and_rejects_ambiguous_nevra(self):
        package = {
            "arch": "x86_64",
            "epoch": "0",
            "location": "Packages/r/rust-1.92.0-1.el10.x86_64.rpm",
            "name": "rust",
            "release": "1.el10",
            "sha256": "a" * 64,
            "size": "123",
            "version": "1.92.0",
        }
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "primary.xml.gz"
            self.primary_fixture(path, [package])
            index = closure.primary_index(path, "appstream")
            row = index["rust-0:1.92.0-1.el10.x86_64"]
            self.assertEqual(row["sha256"], "a" * 64)
            self.assertEqual(row["arch"], "x86_64")
            conflicting = dict(package)
            conflicting["sha256"] = "b" * 64
            self.primary_fixture(path, [package, conflicting])
            with self.assertRaisesRegex(closure.ClosureError, "ambiguous"):
                closure.primary_index(path, "appstream")

    def test_offline_command_has_no_repository_and_online_has_exact_three(self):
        roots = ["bash", "rust >= 1.92"]
        repositories = [
            {"id": "baseos", "base_url": "https://example/baseos/"},
            {"id": "appstream", "base_url": "https://example/appstream/"},
            {"id": "crb", "base_url": "https://example/crb/"},
        ]
        with tempfile.TemporaryDirectory() as temporary:
            snapshot_roots = {}
            for repository in repositories:
                path = Path(temporary) / repository["id"]
                path.mkdir()
                snapshot_roots[repository["id"]] = path
            online = closure.online_command(
                Path("/tmp/online"), repositories, snapshot_roots, roots
            )
            snapshot = closure.snapshot_solve_command(
                Path("/tmp/snapshot"), repositories, snapshot_roots, roots
            )
        self.assertEqual(sum(item.startswith("--repofrompath=") for item in online), 3)
        self.assertEqual(sum(item.startswith("--enablerepo=") for item in online), 3)
        for repository in repositories:
            command_id = "rk003-snapshot-" + repository["id"]
            self.assertTrue(
                any(item.startswith("--repofrompath=" + command_id + ",") for item in online)
            )
            self.assertIn("--enablerepo=" + command_id, online)
        self.assertEqual(sum(".baseurl=file://" in item for item in online), 3)
        self.assertIn("--downloadonly", online)
        self.assertIn("--noplugins", online)
        self.assertIn("--config=/dev/null", online)
        self.assertIn("--setopt=reposdir=/dev/null", online)
        self.assertEqual(sum(item.startswith("--repofrompath=") for item in snapshot), 3)
        self.assertTrue(
            all(
                any(
                    item.startswith("--repofrompath=rk003-snapshot-" + repository["id"] + ",")
                    for item in snapshot
                )
                for repository in repositories
            )
        )
        self.assertFalse(any("https://" in item or "http://" in item for item in snapshot))
        self.assertNotIn("--downloadonly", snapshot)
        self.assertEqual(snapshot[-len(roots) :], roots)
        offline = closure.offline_command(
            Path("/tmp/offline"), [Path("/evidence/a.rpm")]
        )
        self.assertIn("--disablerepo=*", offline)
        self.assertIn("--cacheonly", offline)
        self.assertIn("--noplugins", offline)
        self.assertIn("--config=/dev/null", offline)
        self.assertFalse(any("repofrompath" in item for item in offline))
        self.assertFalse(any(item.startswith("--enablerepo") for item in offline))
        self.assertIn("/evidence/a.rpm", offline)
        self.assertFalse(any(root in offline for root in roots))

    def test_package_count_and_primary_membership_are_bounded(self):
        self.assertEqual(closure.MAX_CAPTURED_RPMS, 4096)
        self.assertEqual(closure.MAX_CAPTURED_BYTES, 8 * 1024 * 1024 * 1024)
        self.assertEqual(closure.MAX_PRIMARY_PACKAGES, 100000)
        self.assertEqual(closure.MAX_REPOMD_OBJECTS, 64)
        self.assertEqual(closure.MAX_METADATA_OBJECT_BYTES, 512 * 1024 * 1024)

    def test_repomd_rows_require_unique_safe_signed_objects(self):
        repository = {
            "repomd": {"revision": "10.2"},
            "primary": {
                "href": "repodata/primary.xml.gz",
                "open_sha256": "b" * 64,
                "open_size": 9,
                "sha256": "a" * 64,
                "size": 7,
            },
        }
        row = (
            '<data type="primary"><checksum type="sha256">{}</checksum>'
            '<open-checksum type="sha256">{}</open-checksum><location href="{}"/>'
            '<size>{}</size><open-size>{}</open-size></data>'
        ).format("a" * 64, "b" * 64, "repodata/primary.xml.gz", 7, 9)
        filelists = (
            '<data type="filelists"><checksum type="sha256">{}</checksum>'
            '<open-checksum type="sha256">{}</open-checksum><location href="{}"/>'
            '<size>{}</size><open-size>{}</open-size></data>'
        ).format("c" * 64, "d" * 64, "repodata/filelists.xml.gz", 11, 13)
        xml = (
            '<repomd xmlns="http://linux.duke.edu/metadata/repo"><revision>10.2</revision>'
            + row
            + filelists
            + "</repomd>"
        ).encode("ascii")
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "repomd.xml"
            path.write_bytes(xml)
            rows = closure.repomd_data_rows(path, repository)
            self.assertEqual(
                [item["type"] for item in rows], ["primary", "filelists"]
            )
            for broken in (
                xml.replace(b"repodata/primary.xml.gz", b"../primary.xml.gz"),
                xml.replace(b"</repomd>", filelists.encode("ascii") + b"</repomd>"),
                xml.replace(b"<size>7</size>", b"<size>9999999999</size>"),
            ):
                path.write_bytes(broken)
                with self.assertRaises(closure.ClosureError):
                    closure.repomd_data_rows(path, repository)

    def test_cached_repomd_requires_exact_signed_set(self):
        repositories = [
            {"repomd": {"sha256": hashlib.sha256(value).hexdigest()}}
            for value in (b"one", b"two", b"three")
        ]
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            for index, value in enumerate((b"one", b"two", b"three")):
                path = root / str(index) / "repomd.xml"
                path.parent.mkdir()
                path.write_bytes(value)
            closure.verify_cached_repomd(root, repositories)
            (root / "0/repomd.xml").write_bytes(b"wrong")
            with self.assertRaisesRegex(closure.ClosureError, "identities"):
                closure.verify_cached_repomd(root, repositories)

    def test_closure_requires_every_direct_nevra_and_transitive_packages(self):
        closure.verify_transitive_inventory(
            ["direct-a", "direct-b", "transitive"], ["direct-a", "direct-b"]
        )
        with self.assertRaisesRegex(closure.ClosureError, "omits"):
            closure.verify_transitive_inventory(
                ["direct-a", "transitive"], ["direct-a", "direct-b"]
            )
        with self.assertRaisesRegex(closure.ClosureError, "no transitive"):
            closure.verify_transitive_inventory(
                ["direct-a", "direct-b"], ["direct-a", "direct-b"]
            )

    def test_version_checks_require_exact_bounded_output_and_owner(self):
        closure.verify_expected_version(
            "rustc",
            "1.92.0",
            b"rustc 1.92.0 (fixture)\nrelease: 1.92.0\n",
            "rust-0:1.92.0-1.el10.x86_64",
        )
        for output, owner in (
            (b"rustc 1.92.1 mentions 1.92.0rc1\n", "rust-0:1.92.0-1.el10.x86_64"),
            (b"rustc 1.92.0\n", "rust-0:1.92.1-1.el10.x86_64"),
        ):
            with self.subTest(output=output, owner=owner):
                with self.assertRaises(closure.ClosureError):
                    closure.verify_expected_version(
                        "rustc", "1.92.0", output, owner
                    )

        for probe_id, output, owner in (
            ("clippy", b"clippy 0.1.92 (fixture)\n", "clippy-0:1.92.0-1.el10.x86_64"),
            ("rustfmt", b"rustfmt 1.8.0-stable (fixture)\n", "rustfmt-0:1.92.0-1.el10.x86_64"),
        ):
            closure.verify_expected_version(probe_id, "1.92.0", output, owner)
            with self.assertRaises(closure.ClosureError):
                closure.verify_expected_version(
                    probe_id, "1.92.0", output, owner.replace("1.92.0", "1.92.1")
                )
            with self.assertRaises(closure.ClosureError):
                closure.verify_expected_version(
                    probe_id, "1.92.0", b"unexpected tool\n", owner
                )

    def test_llvm_config_owner_is_derived_from_reconciled_contract(self):
        contract = closure.validate_contract(REPO_ROOT)
        owner_policy = contract["metadata_reconciliation"]["llvm_config_owner"]
        self.assertEqual(
            closure.expected_probe_owner(
                "llvm", "llvm-0:21.1.8-1.el10.x86_64", owner_policy
            ),
            "llvm-devel-0:21.1.8-1.el10.x86_64",
        )
        self.assertEqual(
            closure.expected_probe_owner(
                "clang", "clang-0:21.1.8-1.el10.x86_64", owner_policy
            ),
            "clang-0:21.1.8-1.el10.x86_64",
        )
        with self.assertRaisesRegex(closure.ClosureError, "authority mapping"):
            closure.expected_probe_owner(
                "llvm", "llvm-devel-0:21.1.8-1.el10.x86_64", owner_policy
            )
        closure.validate_probe_binary_path("llvm", "/usr/bin/llvm-config", owner_policy)
        closure.validate_probe_binary_path("clang", "/usr/local/bin/clang", owner_policy)
        with self.assertRaisesRegex(closure.ClosureError, "resolved binary path"):
            closure.validate_probe_binary_path(
                "llvm", "/usr/local/bin/llvm-config", owner_policy
            )
        legacy = closure.validate_legacy_contract(REPO_ROOT)
        self.assertIn("before credit or review ingestion", legacy["success_blockers"][-1])

    def test_dynamic_loader_must_identify_one_exact_libclang(self):
        stderr = (
            b"      42:\tcalling init: /usr/lib64/libc.so.6\n"
            b"      42:\tcalling init: /usr/lib64/libclang.so.21.1\n"
        )
        self.assertEqual(
            closure.loaded_libclang_path(stderr), "/usr/lib64/libclang.so.21.1"
        )
        for broken in (
            b"calling init: /usr/lib64/libc.so.6\n",
            stderr + b"calling init: /tmp/libclang.so.bad\n",
            b"\xff",
        ):
            with self.subTest(broken=broken):
                with self.assertRaises(closure.ClosureError):
                    closure.loaded_libclang_path(broken)

    def test_probe_schema_matches_platform_review_fields(self):
        self.assertEqual(
            closure.PROBE_RESULT_FIELDS,
            {
                "binary_path",
                "binary_sha256",
                "command",
                "exit_code",
                "id",
                "loaded_library_path",
                "loaded_library_sha256",
                "package_nevra",
                "parsed_version",
                "required_file_path",
                "required_file_sha256",
                "stderr_sha256",
                "stdout_sha256",
            },
        )
        self.assertEqual(
            hashlib.sha256(closure.LIBCLANG_PROBE_BYTES).hexdigest(),
            closure.LIBCLANG_PROBE_SHA256,
        )

    def test_acquisition_removes_proxies_and_offline_is_loopback_only(self):
        base = {"HTTP_PROXY": "https://proxy.example.invalid", "KEEP": "yes"}
        online = closure.acquisition_environment(base)
        self.assertNotIn("HTTP_PROXY", online)
        self.assertEqual(online["KEEP"], "yes")
        offline = closure.private_environment(base)
        self.assertEqual(offline["HTTP_PROXY"], "http://127.0.0.1:9")
        self.assertEqual(offline["HTTPS_PROXY"], "http://127.0.0.1:9")
        self.assertEqual(offline["NO_PROXY"], "")
        self.assertEqual(offline["LANG"], "C")

    def test_chroot_file_resolution_handles_absolute_symlinks_fail_closed(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            target = root / "usr/libexec/tool"
            target.parent.mkdir(parents=True)
            target.write_bytes(b"tool")
            link = root / "usr/bin/tool"
            link.parent.mkdir(parents=True)
            link.symlink_to("/usr/libexec/tool")
            with mock.patch.object(
                closure,
                "run_command",
                return_value=(b"/usr/libexec/tool\n", b""),
            ):
                self.assertEqual(
                    closure.chroot_regular_file(root, "/usr/bin/tool", "fixture"),
                    target,
                )
            with mock.patch.object(
                closure,
                "run_command",
                return_value=(b"/../../outside\n", b""),
            ):
                with self.assertRaisesRegex(closure.ClosureError, "unsafe"):
                    closure.chroot_regular_file(root, "/usr/bin/tool", "fixture")


if __name__ == "__main__":
    unittest.main()
