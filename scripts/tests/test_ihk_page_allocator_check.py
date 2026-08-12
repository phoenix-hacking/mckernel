import contextlib
import hashlib
import io
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
from unittest import mock


REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts import ihk_page_allocator_check as allocator_check


class IhkPageAllocatorCheckTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="ihk-page-allocator-check-")
        self.repo = Path(self.temporary.name) / "repo"
        self.contract = json.loads(
            (REPO_ROOT / allocator_check.DEFAULT_CONTRACT).read_text(encoding="utf-8")
        )
        paths = {
            allocator_check.DEFAULT_CONTRACT.as_posix(),
            self.contract["production_source"]["path"],
            self.contract["compile_fixture"]["path"],
            self.contract["legacy_oracle"]["source_path"],
            self.contract["legacy_oracle"]["header_path"],
        }
        for relative in paths:
            target = self.repo / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(REPO_ROOT / relative, target)

    def tearDown(self):
        self.temporary.cleanup()

    def write_contract(self, value=None):
        if value is None:
            value = self.contract
        (self.repo / allocator_check.DEFAULT_CONTRACT).write_text(
            json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )

    def mutate_and_resign(self, relative, old, new, digest_owner, digest_field):
        path = self.repo / relative
        text = path.read_text(encoding="utf-8")
        self.assertIn(old, text)
        path.write_text(text.replace(old, new, 1), encoding="utf-8")
        digest_owner[digest_field] = hashlib.sha256(path.read_bytes()).hexdigest()
        self.write_contract()

    def fake_rustc(
        self,
        version=allocator_check.EXPECTED_COMPILER,
        passed=7,
        compile_exit=0,
    ):
        compiler = Path(self.temporary.name) / "rustc"
        compiler.write_text(
            "#!/usr/bin/env python3\n"
            "import os\n"
            "import sys\n"
            "VERSION = {0!r}\n".format(version)
            + "PASSED = {0!r}\n".format(passed)
            + "COMPILE_EXIT = {0!r}\n".format(compile_exit)
            + "if sys.argv[1:] == ['--version']:\n"
            "    print(VERSION)\n"
            "    raise SystemExit(0)\n"
            "if COMPILE_EXIT:\n"
            "    print('synthetic compile failure', file=sys.stderr)\n"
            "    raise SystemExit(COMPILE_EXIT)\n"
            "output = sys.argv[sys.argv.index('-o') + 1]\n"
            "body = (\n"
            "    '#!/usr/bin/env python3\\n'\n"
            "    + \"print('test result: ok. {0} passed; 0 failed; 0 ignored; \"\n"
            "    + \"0 measured; 0 filtered out')\\n\"\n"
            ").format(PASSED)\n"
            "with open(output, 'w', encoding='utf-8') as stream:\n"
            "    stream.write(body)\n"
            "os.chmod(output, 0o755)\n",
            encoding="utf-8",
        )
        compiler.chmod(0o755)
        return compiler

    def test_source_contract_is_valid_but_credit_forbidden(self):
        result = allocator_check.validate_repository(REPO_ROOT)
        self.assertEqual("IHK-006", result["gate_id"])
        self.assertTrue(result["source_contract_validated"])
        for field in (
            "gate_credit_eligible",
            "built_into_ihk_validated",
            "exact_kernel_compile_validated",
            "rocky_runtime_validated",
            "differential_legacy_parity_validated",
            "failure_injection_validated",
        ):
            self.assertFalse(result[field])

    def test_cli_reports_skip_without_pass_or_credit(self):
        output = io.StringIO()
        with mock.patch.dict(os.environ, {"IHK_PAGE_ALLOCATOR_RUSTC": ""}), mock.patch.object(
            allocator_check.shutil, "which", return_value=None
        ), contextlib.redirect_stdout(output):
            result = allocator_check.main(["--repo", str(REPO_ROOT)])
        self.assertEqual(0, result)
        rendered = output.getvalue()
        self.assertIn("SOURCE-CONTRACT-VERIFIED", rendered)
        self.assertIn("fixture=SKIPPED_NO_CONFIGURED_RUSTC", rendered)
        self.assertIn("gate_credit=FORBIDDEN", rendered)
        self.assertNotIn("PASS", rendered)

    def test_required_compiler_absence_fails(self):
        with mock.patch.dict(os.environ, {"IHK_PAGE_ALLOCATOR_RUSTC": ""}), mock.patch.object(
            allocator_check.shutil, "which", return_value=None
        ), self.assertRaisesRegex(allocator_check.ValidationError, "required but absent"):
            allocator_check.validate_configured_fixture(REPO_ROOT, require_rustc=True)

    def test_exact_compiler_executes_seven_tests(self):
        result = allocator_check.validate_configured_fixture(
            REPO_ROOT, rustc=str(self.fake_rustc()), require_rustc=True
        )
        self.assertEqual("EXACT_ROCKY_RUSTC_FIXTURE_VERIFIED", result["fixture_status"])
        self.assertEqual(allocator_check.EXPECTED_COMPILER, result["compiler_version"])

    def test_compiler_version_drift_fails(self):
        with self.assertRaisesRegex(allocator_check.ValidationError, "version differs"):
            allocator_check.validate_configured_fixture(
                REPO_ROOT, rustc=str(self.fake_rustc(version="rustc 1.92.0 unlocked"))
            )

    def test_configured_compiler_failure_is_not_skipped(self):
        with self.assertRaisesRegex(allocator_check.ValidationError, "compilation failed"):
            allocator_check.validate_configured_fixture(
                REPO_ROOT, rustc=str(self.fake_rustc(compile_exit=2))
            )

    def test_fixture_test_count_drift_fails(self):
        with self.assertRaisesRegex(allocator_check.ValidationError, "exact contracted test count"):
            allocator_check.validate_configured_fixture(
                REPO_ROOT, rustc=str(self.fake_rustc(passed=6))
            )

    def test_contract_cannot_self_award_any_evidence(self):
        for field in self.contract["evidence_policy"]:
            with self.subTest(field=field):
                mutated = json.loads(json.dumps(self.contract))
                mutated["evidence_policy"][field] = True
                self.write_contract(mutated)
                with self.assertRaisesRegex(allocator_check.ValidationError, "cannot claim"):
                    allocator_check.validate_repository(self.repo)

    def test_resigned_unit_validation_mutation_fails_semantically(self):
        self.mutate_and_resign(
            self.contract["production_source"]["path"],
            "|| !unit_bytes.is_power_of_two()",
            "|| false",
            self.contract["production_source"],
            "sha256",
        )
        with self.assertRaisesRegex(allocator_check.ValidationError, "power-of-two unit"):
            allocator_check.validate_repository(self.repo)

    def test_resigned_checked_end_mutation_fails_semantically(self):
        self.mutate_and_resign(
            self.contract["production_source"]["path"],
            ".checked_add(size_bytes)",
            ".wrapping_add(size_bytes)",
            self.contract["production_source"],
            "sha256",
        )
        with self.assertRaisesRegex(allocator_check.ValidationError, "checked physical end"):
            allocator_check.validate_repository(self.repo)

    def test_resigned_separate_reservation_map_mutation_fails(self):
        self.mutate_and_resign(
            self.contract["production_source"]["path"],
            "reserved: &'storage [AtomicU64]",
            "held: &'storage [AtomicU64]",
            self.contract["production_source"],
            "sha256",
        )
        with self.assertRaisesRegex(allocator_check.ValidationError, "reservation map"):
            allocator_check.validate_repository(self.repo)

    def test_resigned_allocation_drop_removal_fails(self):
        self.mutate_and_resign(
            self.contract["production_source"]["path"],
            "impl Drop for PageAllocation<'_, '_>",
            "impl PageAllocation<'_, '_>",
            self.contract["production_source"],
            "sha256",
        )
        with self.assertRaisesRegex(allocator_check.ValidationError, "allocation Drop"):
            allocator_check.validate_repository(self.repo)

    def test_resigned_alignment_mutation_fails(self):
        self.mutate_and_resign(
            self.contract["production_source"]["path"],
            "!alignment_blocks.is_power_of_two()",
            "false",
            self.contract["production_source"],
            "sha256",
        )
        with self.assertRaisesRegex(allocator_check.ValidationError, "alignment validation"):
            allocator_check.validate_repository(self.repo)

    def test_resigned_unsafe_or_ffi_boundary_fails(self):
        source = self.repo / self.contract["production_source"]["path"]
        with source.open("a", encoding="utf-8") as stream:
            stream.write('\nextern "C" { fn project_c_fallback(); }\n')
        self.contract["production_source"]["sha256"] = hashlib.sha256(
            source.read_bytes()
        ).hexdigest()
        self.write_contract()
        with self.assertRaisesRegex(allocator_check.ValidationError, "forbidden implementation"):
            allocator_check.validate_repository(self.repo)

    def test_resigned_fixture_contention_reduction_fails(self):
        self.mutate_and_resign(
            self.contract["compile_fixture"]["path"],
            "const THREADS: usize = 8;",
            "const THREADS: usize = 1;",
            self.contract["compile_fixture"],
            "sha256",
        )
        with self.assertRaisesRegex(allocator_check.ValidationError, "eight-thread"):
            allocator_check.validate_repository(self.repo)

    def test_resigned_legacy_export_removal_fails(self):
        oracle = self.contract["legacy_oracle"]
        self.mutate_and_resign(
            oracle["source_path"],
            "EXPORT_SYMBOL(ihk_pagealloc_alloc);",
            "/* export removed */",
            oracle,
            "source_sha256",
        )
        with self.assertRaisesRegex(allocator_check.ValidationError, "frozen legacy allocator oracle"):
            allocator_check.validate_repository(self.repo)

    def test_raw_source_and_fixture_digest_drift_fail_closed(self):
        for relative, expected in (
            (self.contract["production_source"]["path"], "source digest differs"),
            (self.contract["compile_fixture"]["path"], "fixture digest differs"),
        ):
            with self.subTest(relative=relative):
                path = self.repo / relative
                original = path.read_text(encoding="utf-8")
                path.write_text(original + "\n", encoding="utf-8")
                with self.assertRaisesRegex(allocator_check.ValidationError, expected):
                    allocator_check.validate_repository(self.repo)
                path.write_text(original, encoding="utf-8")

    def test_duplicate_contract_key_fails_closed(self):
        contract_path = self.repo / allocator_check.DEFAULT_CONTRACT
        text = contract_path.read_text(encoding="utf-8")
        contract_path.write_text(text.replace("{\n", '{\n  "schema_version": 1,\n', 1), encoding="utf-8")
        with self.assertRaisesRegex(allocator_check.ValidationError, "duplicate JSON key"):
            allocator_check.validate_repository(self.repo)


if __name__ == "__main__":
    unittest.main()
