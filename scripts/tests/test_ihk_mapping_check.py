#!/usr/bin/env python3
"""Fail-closed tests for the unattached IHK-007 mapping foundation."""

from __future__ import print_function

import ast
import contextlib
import copy
import hashlib
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
if str(REPO_ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "scripts"))

import ihk_mapping_check as mapping_check  # noqa: E402


class IhkMappingCheckTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="ihk-mapping-check-")
        self.repo = Path(self.temporary.name) / "repo"
        self.repo.mkdir()
        self.contract = json.loads(
            (REPO_ROOT / mapping_check.DEFAULT_CONTRACT).read_text(encoding="utf-8")
        )
        paths = {
            mapping_check.DEFAULT_CONTRACT.as_posix(),
            self.contract["checker"]["path"],
            self.contract["production_source"]["path"],
            self.contract["compile_fixture"]["path"],
            self.contract["must_use_probe"]["path"],
            "host-kernel/native-rust/ihk.rs",
            "host-kernel/kbuild/Kbuild.in",
            "host-kernel/kbuild/stage-manifest.json",
            "host-kernel/contracts/native-rust-unsafe-ffi-ledger-v1.json",
            ".github/workflows/native-rust-host-modules-exact-build.yml",
            ".github/workflows/rocky-kernel-source-evidence.yml",
        }
        paths.update(row["path"] for row in self.contract["legacy_oracle"]["inputs"])
        for relative in paths:
            target = self.repo / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(REPO_ROOT / relative, target)
        subprocess.run(
            ["git", "init", "-q", str(self.repo)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True,
        )
        subprocess.run(
            [
                "git",
                "-C",
                str(self.repo),
                "update-index",
                "--add",
                "--cacheinfo",
                "160000,{0},ihk".format(mapping_check.EXPECTED_GITLINK),
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True,
        )

    def tearDown(self):
        self.temporary.cleanup()

    def write_contract(self, value=None):
        if value is None:
            value = self.contract
        (self.repo / mapping_check.DEFAULT_CONTRACT).write_text(
            json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )

    def mutate_and_resign(self, relative, old, new, binding):
        path = self.repo / relative
        text = path.read_text(encoding="utf-8")
        self.assertIn(old, text)
        path.write_text(text.replace(old, new, 1), encoding="utf-8")
        binding["sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
        if "size" in binding:
            binding["size"] = path.stat().st_size
        self.write_contract()

    def fake_rustc(
        self,
        version=mapping_check.EXPECTED_COMPILER,
        passed=len(mapping_check.EXPECTED_TESTS),
        compile_exit=0,
        probe_exit=1,
    ):
        compiler = Path(self.temporary.name) / "rustc"
        compiler.write_text(
            "#!/usr/bin/env python3\n"
            "import os\n"
            "import sys\n"
            "VERSION = {0!r}\n".format(version)
            + "PASSED = {0!r}\n".format(passed)
            + "COMPILE_EXIT = {0!r}\n".format(compile_exit)
            + "PROBE_EXIT = {0!r}\n".format(probe_exit)
            + "TESTS = {0!r}\n".format(mapping_check.EXPECTED_TESTS)
            + "if sys.argv[1:] == ['--version']:\n"
            "    print(VERSION)\n"
            "    raise SystemExit(0)\n"
            "if any('must_use_compile_fail' in item for item in sys.argv):\n"
            "    if PROBE_EXIT:\n"
            "        print('error: unused `MmapTransaction` that must be used', file=sys.stderr)\n"
            "        print('mapping transactions must reach rollback, live, or close', file=sys.stderr)\n"
            "        print('error: unused `RollbackPlan` that must be used', file=sys.stderr)\n"
            "        print('mapping cleanup plans must be executed by the Linux adapter', file=sys.stderr)\n"
            "        raise SystemExit(PROBE_EXIT)\n"
            "if COMPILE_EXIT:\n"
            "    print('synthetic compilation failure', file=sys.stderr)\n"
            "    raise SystemExit(COMPILE_EXIT)\n"
            "output = sys.argv[sys.argv.index('-o') + 1]\n"
            "lines = ['#!/usr/bin/env python3']\n"
            "for name in TESTS:\n"
            "    lines.append(\"print('test {0} ... ok')\".format(name))\n"
            "lines.append(\"print('test result: ok. {0} passed; 0 failed; 0 ignored; 0 measured; 0 filtered out')\".format(PASSED))\n"
            "with open(output, 'w', encoding='utf-8') as stream:\n"
            "    stream.write('\\n'.join(lines) + '\\n')\n"
            "os.chmod(output, 0o755)\n",
            encoding="utf-8",
        )
        compiler.chmod(0o755)
        return compiler

    def test_repository_contract_is_valid_unattached_and_credit_forbidden(self):
        contract = mapping_check.validate_contract(REPO_ROOT)
        self.assertEqual(contract["gate_id"], "IHK-007")
        self.assertFalse(any(contract["attachment_status"].values()))
        self.assertFalse(any(contract["evidence_policy"].values()))
        self.assertIn("IHK-007 completion", contract["unproven"][-1])

    def test_cli_source_only_result_never_says_pass(self):
        output = io.StringIO()
        with mock.patch.dict(os.environ, {"IHK_MAPPING_RUSTC": ""}), contextlib.redirect_stdout(output):
            result = mapping_check.main(["--repo", str(REPO_ROOT)])
        self.assertEqual(result, 0)
        rendered = output.getvalue()
        self.assertIn("SOURCE-CONTRACT-VERIFIED", rendered)
        self.assertIn("fixture=SKIPPED_NO_CONFIGURED_RUSTC", rendered)
        self.assertIn("attachment=ABSENT", rendered)
        self.assertIn("gate_credit=FORBIDDEN", rendered)
        self.assertNotIn("PASS", rendered)

    def test_required_compiler_absence_fails(self):
        with mock.patch.dict(os.environ, {"IHK_MAPPING_RUSTC": ""}), self.assertRaisesRegex(
            mapping_check.ValidationError, "required but absent"
        ):
            mapping_check.validate_configured_fixture(
                REPO_ROOT, require_rustc=True
            )

    def test_exact_compiler_executes_bound_tests_and_must_use_probe(self):
        result = mapping_check.validate_configured_fixture(
            REPO_ROOT, rustc=str(self.fake_rustc()), require_rustc=True
        )
        self.assertEqual(
            result["fixture_status"], "EXACT_ROCKY_RUSTC_FIXTURE_VERIFIED"
        )
        self.assertEqual(result["compiler_version"], mapping_check.EXPECTED_COMPILER)

    def test_compiler_version_and_test_count_drift_fail(self):
        with self.assertRaisesRegex(mapping_check.ValidationError, "version output"):
            mapping_check.validate_configured_fixture(
                REPO_ROOT,
                rustc=str(self.fake_rustc(version="rustc 1.92.0 unlocked")),
                require_rustc=True,
            )
        with self.assertRaisesRegex(mapping_check.ValidationError, "result summary"):
            mapping_check.validate_configured_fixture(
                REPO_ROOT,
                rustc=str(self.fake_rustc(passed=len(mapping_check.EXPECTED_TESTS) - 1)),
                require_rustc=True,
            )

    def test_configured_compile_failure_and_probe_success_fail(self):
        with self.assertRaisesRegex(mapping_check.ValidationError, "compilation failed"):
            mapping_check.validate_configured_fixture(
                REPO_ROOT,
                rustc=str(self.fake_rustc(compile_exit=2)),
                require_rustc=True,
            )
        with self.assertRaisesRegex(mapping_check.ValidationError, "unexpectedly compiled"):
            mapping_check.validate_configured_fixture(
                REPO_ROOT,
                rustc=str(self.fake_rustc(probe_exit=0)),
                require_rustc=True,
            )

    def test_source_digest_drift_fails_closed(self):
        source = self.repo / self.contract["production_source"]["path"]
        source.write_text(source.read_text(encoding="utf-8") + "\n", encoding="utf-8")
        with self.assertRaisesRegex(mapping_check.ValidationError, "source size"):
            mapping_check.validate_contract(self.repo)

    def test_checker_digest_drift_fails_closed(self):
        checker = self.repo / self.contract["checker"]["path"]
        checker.write_text(
            checker.read_text(encoding="utf-8") + "\n", encoding="utf-8"
        )
        with self.assertRaisesRegex(mapping_check.ValidationError, "checker size"):
            mapping_check.validate_contract(self.repo)

    def test_resigned_checked_arithmetic_mutation_fails_semantically(self):
        self.mutate_and_resign(
            self.contract["production_source"]["path"],
            "pfn.checked_mul(self.size)",
            "pfn.wrapping_mul(self.size)",
            self.contract["production_source"],
        )
        with self.assertRaisesRegex(mapping_check.ValidationError, "forbidden construct"):
            mapping_check.validate_contract(self.repo)

    def test_resigned_full_mapped_extent_mutation_fails_semantically(self):
        self.mutate_and_resign(
            self.contract["production_source"]["path"],
            "base.checked_add(mapped.length())",
            "base.checked_add(requested.length())",
            self.contract["production_source"],
        )
        with self.assertRaisesRegex(mapping_check.ValidationError, "invariant marker"):
            mapping_check.validate_contract(self.repo)

    def test_resigned_cleanup_order_mutation_fails_semantically(self):
        source = self.contract["production_source"]
        self.mutate_and_resign(
            source["path"],
            "Some(CleanupStep::UnmapUser {\n                    user_start: request.user_start(),\n                    length: request.length(),\n                }),\n                Some(CleanupStep::UnmapDevice { local }),",
            "Some(CleanupStep::UnmapDevice { local }),\n                Some(CleanupStep::UnmapUser {\n                    user_start: request.user_start(),\n                    length: request.length(),\n                }),",
            source,
        )
        with self.assertRaisesRegex(mapping_check.ValidationError, "cleanup order"):
            mapping_check.validate_contract(self.repo)

    def test_contract_cannot_claim_attachment_evidence_or_credit(self):
        for section in ("attachment_status", "evidence_policy"):
            for field in self.contract[section]:
                with self.subTest(section=section, field=field):
                    mutated = copy.deepcopy(self.contract)
                    mutated[section][field] = True
                    self.write_contract(mutated)
                    with self.assertRaisesRegex(mapping_check.ValidationError, "differs"):
                        mapping_check.validate_contract(self.repo)

    def test_legacy_bytes_and_resigned_authority_mutation_fail(self):
        row = self.contract["legacy_oracle"]["inputs"][0]
        path = self.repo / row["path"]
        path.write_text(
            path.read_text(encoding="utf-8").replace("return -ENOSYS;", "return -EINVAL;", 1),
            encoding="utf-8",
        )
        with self.assertRaisesRegex(mapping_check.ValidationError, "legacy input digest"):
            mapping_check.validate_contract(self.repo)
        row["sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
        row["size"] = path.stat().st_size
        self.write_contract()
        with self.assertRaisesRegex(mapping_check.ValidationError, "legacy input authority"):
            mapping_check.validate_contract(self.repo)

    def test_gitlink_commit_mismatch_fails_closed(self):
        subprocess.run(
            [
                "git",
                "-C",
                str(self.repo),
                "update-index",
                "--add",
                "--cacheinfo",
                "160000,{0},ihk".format("1" * 40),
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True,
        )
        with self.assertRaisesRegex(mapping_check.ValidationError, "gitlink index"):
            mapping_check.validate_contract(self.repo)

    def test_ihk_source_stage_ledger_and_workflow_attachment_fail(self):
        surfaces = [
            "host-kernel/native-rust/ihk.rs",
            "host-kernel/kbuild/Kbuild.in",
            "host-kernel/kbuild/stage-manifest.json",
            "host-kernel/contracts/native-rust-unsafe-ffi-ledger-v1.json",
            ".github/workflows/native-rust-host-modules-exact-build.yml",
            ".github/workflows/rocky-kernel-source-evidence.yml",
        ]
        for relative in surfaces:
            with self.subTest(relative=relative):
                path = self.repo / relative
                original = path.read_text(encoding="utf-8")
                path.write_text(original + "\nihk_mapping\n", encoding="utf-8")
                with self.assertRaisesRegex(mapping_check.ValidationError, "production surface"):
                    mapping_check.validate_contract(self.repo)
                path.write_text(original, encoding="utf-8")

    def test_fixture_and_probe_digest_drift_fail_closed(self):
        for section in ("compile_fixture", "must_use_probe"):
            with self.subTest(section=section):
                path = self.repo / self.contract[section]["path"]
                original = path.read_text(encoding="utf-8")
                path.write_text(original + "\n", encoding="utf-8")
                with self.assertRaisesRegex(mapping_check.ValidationError, "digest"):
                    mapping_check.validate_contract(self.repo)
                path.write_text(original, encoding="utf-8")

    def test_duplicate_json_key_and_symlinked_source_fail_closed(self):
        contract_path = self.repo / mapping_check.DEFAULT_CONTRACT
        contract_path.write_text('{"schema_version":1,"schema_version":1}\n', encoding="utf-8")
        with self.assertRaisesRegex(mapping_check.ValidationError, "duplicate JSON key"):
            mapping_check.validate_contract(self.repo)

        self.write_contract()
        source = self.repo / self.contract["production_source"]["path"]
        original = source.read_bytes()
        source.unlink()
        target = source.with_suffix(".target")
        target.write_bytes(original)
        source.symlink_to(target.name)
        with self.assertRaisesRegex(mapping_check.ValidationError, "canonical regular file"):
            mapping_check.validate_contract(self.repo)

    def test_script_tests_and_source_parse_or_compile_at_supported_boundaries(self):
        for relative in (
            "scripts/ihk_mapping_check.py",
            "scripts/tests/test_ihk_mapping_check.py",
        ):
            source = (REPO_ROOT / relative).read_text(encoding="utf-8")
            try:
                tree = ast.parse(source, filename=relative, feature_version=(3, 6))
            except TypeError:
                tree = ast.parse(source, filename=relative, feature_version=6)
            self.assertIsNotNone(tree)
            self.assertNotRegex(source, r"\b(?:list|dict|set|tuple)\[[^\]]")
            self.assertNotRegex(source, r"\s\|\sNone\b")
        rust = (REPO_ROOT / self.contract["production_source"]["path"]).read_text(
            encoding="utf-8"
        )
        self.assertNotIn("unsafe", rust)
        self.assertNotIn("std::", rust)
        self.assertNotIn("alloc::", rust)


if __name__ == "__main__":
    unittest.main()
