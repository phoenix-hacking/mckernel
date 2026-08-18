#!/usr/bin/env python3
"""Focused fail-closed tests for the RK-006 layered patch authority."""

from __future__ import print_function

import copy
import ast
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest


REPO_ROOT = Path(__file__).resolve().parents[2]
MANIFEST_PATH = REPO_ROOT / "host-kernel/rocky/rk006-patch-authority-v1.json"


class Rk006PatchAuthorityTests(unittest.TestCase):
    def setUp(self):
        from scripts import rocky_kernel_rk006_patch_authority as authority

        self.authority = authority
        self.manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))

    def assert_manifest_rejected(self, mutation):
        candidate = copy.deepcopy(self.manifest)
        mutation(candidate)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "authority.json"
            path.write_text(
                json.dumps(candidate, sort_keys=True, separators=(",", ":")),
                encoding="utf-8",
            )
            with self.assertRaises(self.authority.AuthorityError):
                self.authority.validate(REPO_ROOT, path, replay=False)

    @staticmethod
    def copy_minimal_authority_repo(destination):
        files = (
            "host-kernel/rocky/rk006-patch-authority-v1.json",
            "host-kernel/rocky/source-lock.json",
            "host-kernel/kbuild/parent-integration-v1.json",
        )
        directories = (
            "host-kernel/rocky/patches",
            "host-kernel/kbuild/patches",
            "scripts/tests/fixtures",
        )
        for relative in files:
            target = destination / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(str(REPO_ROOT / relative), str(target))
        for relative in directories:
            target = destination / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copytree(str(REPO_ROOT / relative), str(target))

    @staticmethod
    def synthetic_patch(path, added, new_file=False, old_path=None, new_path=None):
        old_path = old_path or path
        new_path = new_path or path
        lines = ["diff --git a/{} b/{}".format(old_path, new_path)]
        if new_file:
            lines.extend(
                [
                    "new file mode 100644",
                    "--- /dev/null",
                    "+++ b/{}".format(new_path),
                    "@@ -0,0 +1 @@",
                ]
            )
        else:
            lines.extend(
                [
                    "--- a/{}".format(old_path),
                    "+++ b/{}".format(new_path),
                    "@@ -1 +1,2 @@",
                    " context",
                ]
            )
        lines.extend("+{}".format(line) for line in added)
        return ("\n".join(lines) + "\n").encode("utf-8")

    def test_canonical_authority_replays_all_layers_and_second_apply_fails(self):
        report = self.authority.validate(REPO_ROOT)
        self.assertEqual(25, report["patch_count"])
        self.assertEqual(37, report["touched_path_count"])
        self.assertEqual(
            {"compatibility": 21, "generic": 3, "parent": 1},
            report["layer_counts"],
        )
        self.assertFalse(report["credit_eligible"])

    def test_direct_cli_reports_explicit_non_crediting_validation(self):
        result = subprocess.run(
            [
                sys.executable,
                str(REPO_ROOT / "scripts/rocky_kernel_rk006_patch_authority.py"),
                "--repo",
                str(REPO_ROOT),
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True,
        )
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertIn("VALID (non-crediting; 25 patches; 21/3/1 layers; 37 touched paths)", result.stdout)
        self.assertNotIn("RK-006: PASS", result.stdout)

    def test_exact_order_counts_and_touched_path_closure_are_bound(self):
        expected_ids = [
            "compat-{:03d}".format(index) for index in range(1, 19)
        ] + [
            "generic-001", "generic-002", "compat-019", "compat-020",
            "compat-021", "parent-001", "generic-003",
        ]
        self.assertEqual(expected_ids, [row["id"] for row in self.manifest["patches"]])
        self.assertEqual(list(range(1, 26)), [row["order"] for row in self.manifest["patches"]])
        self.assertEqual(
            [21, 3, 1],
            [layer["patch_count"] for layer in self.manifest["layers"]],
        )
        created = []
        for row in self.manifest["patches"]:
            patch = REPO_ROOT / row["path"]
            result = self.authority.inspect_patch_bytes(
                patch.read_bytes(), row["layer"], row["touched_paths"]
            )
            created.extend(result["created_paths"])
        self.assertEqual(["rust/kernel/miscdevice.rs"], created)

    def test_manifest_rejects_reorder_duplicate_retarget_and_touched_path_mutations(self):
        mutations = [
            lambda value: value["patches"].__setitem__(slice(0, 2), list(reversed(value["patches"][:2]))),
            lambda value: value["patches"].__setitem__(1, copy.deepcopy(value["patches"][0])),
            lambda value: value["patches"][0].__setitem__("path", "host-kernel/rocky/patches/0002-rust-support-rust-1.91-target-spec.patch"),
            lambda value: value["patches"][0]["touched_paths"].append("rust/kernel/lib.rs"),
            lambda value: value["patches"][0].__setitem__("order", 2),
        ]
        for index, mutation in enumerate(mutations):
            with self.subTest(case=index):
                self.assert_manifest_rejected(mutation)

    def test_manifest_rejects_digest_postimage_origin_license_and_provenance_mutations(self):
        mutations = [
            lambda value: value["patches"][0].__setitem__("sha256", "0" * 64),
            lambda value: value["patches"][0].__setitem__("postimage_closure_sha256", "0" * 64),
            lambda value: value["patches"][0].__setitem__("origin", "local"),
            lambda value: value["patches"][0].__setitem__("license_expression", "MIT"),
            lambda value: value["patches"][0].__setitem__("license_basis", "asserted"),
            lambda value: value["patches"][0].__setitem__("provenance", "linux-commit:" + "0" * 40),
        ]
        for index, mutation in enumerate(mutations):
            with self.subTest(case=index):
                self.assert_manifest_rejected(mutation)

    def test_manifest_rejects_false_credit_review_and_build_archive_claims(self):
        mutations = [
            lambda value: value["gate"].__setitem__("credit_eligible", True),
            lambda value: value["gate"].__setitem__("tracker_credit", True),
            lambda value: value["gate"].__setitem__("gate_status_claimed", "PASS"),
            lambda value: value["review"].__setitem__("independent_review_complete", True),
            lambda value: value["review"].__setitem__("durable_archive_complete", True),
            lambda value: value["replay"].__setitem__("external_current_head_build_proof", True),
            lambda value: value["replay"].__setitem__("full_external_parent_preimage_execution_proof", True),
            lambda value: value.__setitem__("remaining_blockers", value["remaining_blockers"][:-1]),
        ]
        for index, mutation in enumerate(mutations):
            with self.subTest(case=index):
                self.assert_manifest_rejected(mutation)

    def test_manifest_rejects_bool_as_int_and_open_schema(self):
        mutations = [
            lambda value: value["gate"].__setitem__("credit_eligible", 0),
            lambda value: value.__setitem__("schema_version", True),
            lambda value: value.__setitem__("unexpected", False),
            lambda value: value["patches"][0].__setitem__("unexpected", False),
            lambda value: value["layers"][0].__setitem__("patch_count", True),
        ]
        for index, mutation in enumerate(mutations):
            with self.subTest(case=index):
                self.assert_manifest_rejected(mutation)

    def test_duplicate_json_keys_are_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "duplicate.json"
            path.write_text('{"schema_version":1,"schema_version":1}', encoding="utf-8")
            with self.assertRaises(self.authority.AuthorityError):
                self.authority.load_json(path)

    def test_manifest_symlink_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            target = root / "target.json"
            target.write_text(MANIFEST_PATH.read_text(encoding="utf-8"), encoding="utf-8")
            link = root / "authority.json"
            link.symlink_to(target)
            with self.assertRaises(self.authority.AuthorityError):
                self.authority.validate(REPO_ROOT, link, replay=False)

    def test_manifest_intermediate_directory_symlink_is_rejected_by_validate_and_cli(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            real = root / "real"
            real.mkdir()
            target = real / "authority.json"
            target.write_text(MANIFEST_PATH.read_text(encoding="utf-8"), encoding="utf-8")
            alias = root / "alias"
            alias.symlink_to(real, target_is_directory=True)
            manifest = alias / "authority.json"
            with self.assertRaises(self.authority.AuthorityError):
                self.authority.validate(REPO_ROOT, manifest, replay=False)
            result = subprocess.run(
                [
                    sys.executable,
                    str(REPO_ROOT / "scripts/rocky_kernel_rk006_patch_authority.py"),
                    "--repo",
                    str(REPO_ROOT),
                    "--manifest",
                    str(manifest),
                    "--no-replay",
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True,
            )
            self.assertEqual(1, result.returncode)
            self.assertIn("traverses a symlink", result.stderr)

    def test_fixture_intermediate_directory_symlink_is_rejected_by_validate(self):
        with tempfile.TemporaryDirectory() as directory:
            repo = Path(directory) / "repo"
            repo.mkdir()
            self.copy_minimal_authority_repo(repo)
            fixtures = repo / "scripts/tests/fixtures"
            real_fixtures = repo / "real-fixtures"
            fixtures.rename(real_fixtures)
            fixtures.symlink_to(real_fixtures, target_is_directory=True)
            with self.assertRaisesRegex(
                self.authority.AuthorityError, "traverses a symlink"
            ):
                self.authority.validate(repo, replay=False)

    def test_repository_path_symlink_traversal_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            outside = root / "outside"
            outside.mkdir()
            (outside / "patch").write_text("data", encoding="utf-8")
            (root / "link").symlink_to(outside, target_is_directory=True)
            with self.assertRaises(self.authority.AuthorityError):
                self.authority.safe_repository_file(root, "link/patch", "mutant")

    def test_unsafe_absolute_parent_and_backslash_paths_are_rejected(self):
        unsafe = ["/tmp/escape", "../escape", "a/../escape", "a\\escape", "./escape"]
        for path in unsafe:
            with self.subTest(path=path):
                with self.assertRaises(self.authority.AuthorityError):
                    self.authority.safe_relative_path(path, "mutant")

    def test_generic_and_compatibility_hunks_reject_project_policy_tokens(self):
        for token in (
            "CONFIG_MCKERNEL_HELPER",
            "ihk_helper",
            "mcctrl_ioctl",
            "mcexec_call",
        ):
            patch = self.synthetic_patch("rust/kernel/example.rs", ["let {} = 1;".format(token)])
            with self.subTest(token=token):
                with self.assertRaises(self.authority.AuthorityError):
                    self.authority.inspect_patch_bytes(
                        patch, "generic-rust-abstraction-binding"
                    )

    def test_checker_and_tests_parse_as_python_3_6(self):
        for relative in (
            "scripts/rocky_kernel_rk006_patch_authority.py",
            "scripts/tests/test_rocky_kernel_rk006_patch_authority.py",
        ):
            source = (REPO_ROOT / relative).read_text(encoding="utf-8")
            try:
                ast.parse(source, filename=relative, feature_version=(3, 6))
            except TypeError:
                ast.parse(source, filename=relative, feature_version=6)

    def test_added_hunks_reject_export_symbol_injection(self):
        for symbol in (
            "EXPORT_SYMBOL(project_helper);",
            "EXPORT_SYMBOL_GPL(project_helper);",
            "EXPORT_SYMBOL_NS(project_helper, PROJECT);",
            "EXPORT_SYMBOL_NS_GPL(project_helper, PROJECT);",
            "EXPORT_SYMBOL_RUST_GPL(project_helper);",
            "EXPORT_UNUSED_SYMBOL(project_helper);",
            "EXPORT_UNUSED_SYMBOL_GPL(project_helper);",
            "EXPORT_SYMBOL_GPL /* comment */ (project_helper);",
            "__EXPORT_SYMBOL(project_helper);",
            "#define PROJECT_EXPORT(symbol) EXPORT_SYMBOL_NS(symbol, PROJECT)",
            "EXPORT_ ## SYMBOL(project_helper);",
        ):
            patch = self.synthetic_patch("kernel/example.c", [symbol])
            with self.subTest(symbol=symbol):
                with self.assertRaises(self.authority.AuthorityError):
                    self.authority.inspect_patch_bytes(
                        patch, "compiler-kernel-compatibility"
                    )

    def test_policy_tokens_reject_line_splicing_string_concatenation_and_token_paste(self):
        mutants = [
            ["int value = mcke\\", "rnel_policy;"],
            ['const char *value = "mc" "kernel";'],
            ["int value = mck ## ernel_policy;"],
        ]
        for index, lines in enumerate(mutants):
            patch = self.synthetic_patch("kernel/example.c", lines)
            with self.subTest(case=index):
                with self.assertRaises(self.authority.AuthorityError):
                    self.authority.inspect_patch_bytes(
                        patch, "compiler-kernel-compatibility"
                    )

    def test_existing_c_files_reject_new_functions_prototypes_and_macro_helpers(self):
        mutants = [
            ["static int project_helper(void) { return 0; }"],
            ["int", "project_helper(void)", "{"],
            ["extern long project_helper(unsigned long value);"],
            ["#define project_helper(value) ((value) + 1)"],
            ["#define HELPER static int project_helper(void) { return 0; }", "HELPER"],
            ["SYSCALL_DEFINE0(project_helper)", "{", "return 0;", "}"],
            ["DEFINE_SHOW_ATTRIBUTE(project_helper);"],
        ]
        for index, lines in enumerate(mutants):
            patch = self.synthetic_patch("kernel/existing.c", lines)
            with self.subTest(case=index):
                with self.assertRaises(self.authority.AuthorityError):
                    self.authority.inspect_patch_bytes(
                        patch, "compiler-kernel-compatibility"
                    )

    def test_audited_c_hunk_table_is_exact_and_mutation_is_rejected(self):
        table = self.manifest["semantic_policy"]["audited_c_hunk_digests"]
        self.assertEqual(11, len(table))
        self.assertEqual(11, len({(row["patch_id"], row["path"]) for row in table}))
        self.assert_manifest_rejected(
            lambda value: value["semantic_policy"]["audited_c_hunk_digests"][0].__setitem__(
                "sha256", "0" * 64
            )
        )

    def test_new_c_cpp_and_header_helpers_are_rejected(self):
        for path in ("drivers/misc/helper.c", "drivers/misc/helper.cc", "include/linux/helper.h"):
            patch = self.synthetic_patch(path, ["int helper;"], new_file=True)
            with self.subTest(path=path):
                with self.assertRaises(self.authority.AuthorityError):
                    self.authority.inspect_patch_bytes(
                        patch, "generic-rust-abstraction-binding"
                    )

    def test_only_exact_generic_miscdevice_new_source_is_allowed(self):
        accepted = self.synthetic_patch(
            "rust/kernel/miscdevice.rs", ["// generic abstraction"], new_file=True
        )
        result = self.authority.inspect_patch_bytes(
            accepted, "generic-rust-abstraction-binding"
        )
        self.assertEqual(["rust/kernel/miscdevice.rs"], result["created_paths"])
        rejected = self.synthetic_patch(
            "rust/kernel/project.rs", ["// generic abstraction"], new_file=True
        )
        with self.assertRaises(self.authority.AuthorityError):
            self.authority.inspect_patch_bytes(
                rejected, "generic-rust-abstraction-binding"
            )

    def test_zero_preimage_hunk_without_new_file_metadata_is_rejected(self):
        for old_range in ("0,0", "1,0"):
            mutant = (
                "diff --git a/drivers/misc/project.rs b/drivers/misc/project.rs\n"
                "--- a/drivers/misc/project.rs\n"
                "+++ b/drivers/misc/project.rs\n"
                "@@ -{} +1 @@\n"
                "+pub struct Project;\n"
            ).format(old_range).encode("utf-8")
            with self.subTest(old_range=old_range):
                with self.assertRaisesRegex(
                    self.authority.AuthorityError, "zero-preimage"
                ):
                    self.authority.inspect_patch_bytes(
                        mutant, "generic-rust-abstraction-binding"
                    )

    def test_new_file_mode_requires_dev_null_preimage(self):
        mutant = (
            "diff --git a/rust/kernel/miscdevice.rs b/rust/kernel/miscdevice.rs\n"
            "new file mode 100644\n"
            "--- a/rust/kernel/miscdevice.rs\n"
            "+++ b/rust/kernel/miscdevice.rs\n"
            "@@ -0,0 +1 @@\n"
            "+// generic abstraction\n"
        ).encode("utf-8")
        with self.assertRaisesRegex(
            self.authority.AuthorityError, "/dev/null preimage"
        ):
            self.authority.inspect_patch_bytes(
                mutant, "generic-rust-abstraction-binding"
            )

    def test_patch_header_retarget_duplicate_and_unsafe_paths_are_rejected(self):
        retarget = self.synthetic_patch(
            "rust/kernel/a.rs", ["safe"], old_path="rust/kernel/a.rs", new_path="rust/kernel/b.rs"
        )
        duplicate = self.synthetic_patch("rust/kernel/a.rs", ["safe"]) * 2
        unsafe = self.synthetic_patch("../escape", ["safe"])
        for name, patch in (("retarget", retarget), ("duplicate", duplicate), ("unsafe", unsafe)):
            with self.subTest(case=name):
                with self.assertRaises(self.authority.AuthorityError):
                    self.authority.inspect_patch_bytes(
                        patch, "generic-rust-abstraction-binding"
                    )

    def test_symlink_mode_binary_and_deletion_metadata_are_rejected(self):
        base = self.synthetic_patch("rust/kernel/example.rs", ["safe"], new_file=True)
        mutants = [
            base.replace(b"new file mode 100644", b"new file mode 120000"),
            base.replace(b"new file mode 100644", b"new file mode 100644\nGIT binary patch"),
            base.replace(b"new file mode 100644", b"deleted file mode 100644"),
        ]
        for index, patch in enumerate(mutants):
            with self.subTest(case=index):
                with self.assertRaises(self.authority.AuthorityError):
                    self.authority.inspect_patch_bytes(
                        patch, "generic-rust-abstraction-binding"
                    )

    def test_parent_integration_exception_is_exact_and_cannot_grow_policy(self):
        row = self.manifest["patches"][23]
        canonical = (REPO_ROOT / row["path"]).read_bytes()
        result = self.authority.inspect_patch_bytes(
            canonical, row["layer"], row["touched_paths"]
        )
        self.assertEqual(2, len(result["added_lines"]))
        mutant = canonical.replace(
            b'+source "drivers/misc/mckernel/Kconfig"\n',
            b'+source "drivers/misc/mckernel/Kconfig"\n+obj-y += mckernel_helper.o\n',
        )
        with self.assertRaises(self.authority.AuthorityError):
            self.authority.inspect_patch_bytes(mutant, row["layer"])

    def test_parent_integration_lines_cannot_move_between_target_files(self):
        row = self.manifest["patches"][23]
        canonical = (REPO_ROOT / row["path"]).read_bytes()
        source_line = b'source "drivers/misc/mckernel/Kconfig"'
        mutant = canonical.replace(b"+" + source_line, b" " + source_line)
        insertion = b"+obj-$(CONFIG_MCKERNEL_IHK_RUST)\t+= mckernel/\n"
        mutant = mutant.replace(insertion, insertion + b"+" + source_line + b"\n")
        with self.assertRaisesRegex(
            self.authority.AuthorityError, "parent integration additions"
        ):
            self.authority.inspect_patch_bytes(
                mutant, row["layer"], row["touched_paths"]
            )

    def test_parent_integration_cannot_delete_existing_parent_content(self):
        row = self.manifest["patches"][23]
        canonical = (REPO_ROOT / row["path"]).read_bytes()
        anchor = b" obj-$(CONFIG_NSM)\t\t+= nsm.o\n"
        mutant = canonical.replace(
            anchor,
            anchor + b"-obj-$(CONFIG_NSM)\t\t+= nsm.o\n",
            1,
        )
        with self.assertRaisesRegex(
            self.authority.AuthorityError, "parent integration additions"
        ):
            self.authority.inspect_patch_bytes(
                mutant, row["layer"], row["touched_paths"]
            )

    def test_closure_digest_binds_regular_file_mode(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = root / "script"
            path.write_bytes(b"same bytes\n")
            path.chmod(0o644)
            regular = self.authority._closure_digest(root, ["script"])
            path.chmod(0o755)
            executable = self.authority._closure_digest(root, ["script"])
            self.assertNotEqual(regular, executable)

    def test_provenance_and_license_schemes_are_exhaustive_and_evidence_backed(self):
        parent = json.loads(
            (REPO_ROOT / "host-kernel/kbuild/parent-integration-v1.json").read_text(
                encoding="utf-8"
            )
        )
        fixture = REPO_ROOT / "scripts/tests/fixtures/rust-core-rocky-6.12"

        for index in (23, 24):
            row = self.manifest["patches"][index]
            patch = (REPO_ROOT / row["path"]).read_bytes()
            inspection = self.authority.inspect_patch_bytes(
                patch, row["layer"], row["touched_paths"]
            )
            with self.subTest(empty_overlay=row["id"]):
                with self.assertRaises(self.authority.AuthorityError):
                    self.authority._verify_provenance(
                        row, "", parent, fixture, inspection
                    )

        parent_row = copy.deepcopy(self.manifest["patches"][23])
        parent_patch = (REPO_ROOT / parent_row["path"]).read_text(encoding="utf-8")
        parent_inspection = self.authority.inspect_patch_bytes(
            parent_patch.encode("utf-8"), parent_row["layer"], parent_row["touched_paths"]
        )
        bad_parent = copy.deepcopy(parent)
        bad_parent["patch"]["sha256"] = "0" * 64
        with self.assertRaises(self.authority.AuthorityError):
            self.authority._verify_provenance(
                parent_row, parent_patch, bad_parent, fixture, parent_inspection
            )

        overlay_row = copy.deepcopy(self.manifest["patches"][24])
        overlay_patch = (REPO_ROOT / overlay_row["path"]).read_text(encoding="utf-8")
        overlay_inspection = self.authority.inspect_patch_bytes(
            overlay_patch.encode("utf-8"), overlay_row["layer"], overlay_row["touched_paths"]
        )
        overlay_row["provenance"] = "repository-overlay:" + "0" * 64
        with self.assertRaises(self.authority.AuthorityError):
            self.authority._verify_provenance(
                overlay_row, overlay_patch, parent, fixture, overlay_inspection
            )

        unknown = copy.deepcopy(self.manifest["patches"][0])
        canonical_text = (REPO_ROOT / unknown["path"]).read_text(encoding="utf-8")
        canonical_inspection = self.authority.inspect_patch_bytes(
            canonical_text.encode("utf-8"), unknown["layer"], unknown["touched_paths"]
        )
        unknown["provenance"] = "unknown:value"
        with self.assertRaises(self.authority.AuthorityError):
            self.authority._verify_provenance(
                unknown, canonical_text, parent, fixture, canonical_inspection
            )
        unknown = copy.deepcopy(self.manifest["patches"][0])
        unknown["license_basis"] = "asserted"
        with self.assertRaises(self.authority.AuthorityError):
            self.authority._verify_provenance(
                unknown, canonical_text, parent, fixture, canonical_inspection
            )

        header_row = self.manifest["patches"][0]
        header_without_license = canonical_text.replace(
            "License: GPL-2.0-only\n", ""
        )
        with self.assertRaises(self.authority.AuthorityError):
            self.authority._verify_provenance(
                header_row, header_without_license, parent, fixture, canonical_inspection
            )

        generic_row = self.manifest["patches"][18]
        generic_text = (REPO_ROOT / generic_row["path"]).read_text(encoding="utf-8")
        generic_inspection = self.authority.inspect_patch_bytes(
            generic_text.encode("utf-8"), generic_row["layer"], generic_row["touched_paths"]
        )
        with tempfile.TemporaryDirectory() as directory:
            altered_fixture = Path(directory) / "fixture"
            shutil.copytree(str(fixture), str(altered_fixture))
            target = altered_fixture / "rust/kernel/types.rs"
            target.write_text(
                target.read_text(encoding="utf-8").replace(
                    "// SPDX-License-Identifier: GPL-2.0\n", ""
                ),
                encoding="utf-8",
            )
            with self.assertRaises(self.authority.AuthorityError):
                self.authority._verify_provenance(
                    generic_row, generic_text, parent, altered_fixture, generic_inspection
                )

        new_row = self.manifest["patches"][19]
        new_text = (REPO_ROOT / new_row["path"]).read_text(encoding="utf-8")
        new_inspection = self.authority.inspect_patch_bytes(
            new_text.encode("utf-8"), new_row["layer"], new_row["touched_paths"]
        )
        new_inspection["added_by_path"]["rust/kernel/miscdevice.rs"] = [
            line for line in new_inspection["added_by_path"]["rust/kernel/miscdevice.rs"]
            if "SPDX-License-Identifier" not in line
        ]
        with self.assertRaises(self.authority.AuthorityError):
            self.authority._verify_provenance(
                new_row, new_text, parent, fixture, new_inspection
            )

        self.assertIsNone(parent_row["license_expression"])
        self.assertEqual(
            "unreviewed-bound-linux-parent-targets", parent_row["license_basis"]
        )


if __name__ == "__main__":
    unittest.main()
