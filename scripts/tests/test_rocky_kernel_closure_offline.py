#!/usr/bin/env python3
"""Fail-closed tests for RK-003 closure and offline replay evidence."""

import ast
import copy
import gzip
import hashlib
import json
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
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
        self.assertTrue(contract["gate_claims"])
        self.assertFalse(any(contract["gate_claims"].values()))
        self.assertEqual(len(contract["success_blockers"]), 9)
        self.assertIn(
            "marks closure-offline unimplemented", contract["success_blockers"][-2]
        )
        self.assertEqual(
            contract["success_blockers"][-1], closure.LLVM_OWNER_AUTHORITY_BLOCKER
        )
        self.assertIn(
            "not kernel-level network isolation",
            contract["network_contract"]["scope"],
        )
        self.assertIn(
            "configured network sources",
            contract["network_contract"]["acquisition"],
        )

    def test_contract_is_bound_to_historical_review_and_current_toolchain(self):
        contract = closure.validate_contract(REPO_ROOT)
        self.assertEqual(
            contract["direct_phase"]["outer_zip_sha256"],
            "a88e8a35c13dbd5b7a4e6524595d5cec31450f83c136b4cf64030e517d208eef",
        )
        lock_path = REPO_ROOT / contract["toolchain_lock"]["path"]
        self.assertEqual(
            hashlib.sha256(lock_path.read_bytes()).hexdigest(),
            contract["toolchain_lock"]["sha256"],
        )

    def test_gate_promotion_and_network_overclaim_fail_closed(self):
        contract = closure.validate_contract(REPO_ROOT)
        promoted = copy.deepcopy(contract)
        promoted["gate_claims"]["RK-003"] = True
        with self.assertRaisesRegex(closure.ClosureError, "gate claims"):
            closure.require_exact(
                promoted["gate_claims"], contract["gate_claims"], "gate claims"
            )
        overclaim = copy.deepcopy(contract)
        overclaim["network_contract"]["scope"] = "network isolated"
        self.assertNotIn(
            "not kernel-level network isolation",
            overclaim["network_contract"]["scope"],
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
            "host-kernel/rocky/**",
            "scripts/rocky_kernel_platform_evidence.py",
            "scripts/rocky_kernel_platform_lock.py",
            "scripts/rocky_kernel_source_lock.py",
            "scripts.tests.test_rocky_kernel_closure_offline",
        ):
            self.assertIn(fragment, text)


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
        contract = closure.validate_contract(REPO_ROOT)
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
        contract = closure.validate_contract(REPO_ROOT)
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
        contract = closure.validate_contract(REPO_ROOT)
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
        contract = closure.validate_contract(REPO_ROOT)
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

    def test_llvm_config_uses_actual_owner_and_retains_wrong_authority_blocker(self):
        self.assertEqual(
            closure.expected_probe_owner(
                "llvm", "llvm-0:21.1.8-1.el10.x86_64"
            ),
            "llvm-devel-0:21.1.8-1.el10.x86_64",
        )
        self.assertEqual(
            closure.expected_probe_owner(
                "clang", "clang-0:21.1.8-1.el10.x86_64"
            ),
            "clang-0:21.1.8-1.el10.x86_64",
        )
        with self.assertRaisesRegex(closure.ClosureError, "authority mapping"):
            closure.expected_probe_owner(
                "llvm", "llvm-devel-0:21.1.8-1.el10.x86_64"
            )
        contract = closure.validate_contract(REPO_ROOT)
        self.assertIn("before credit or review ingestion", contract["success_blockers"][-1])

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
