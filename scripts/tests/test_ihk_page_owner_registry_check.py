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

from scripts import ihk_page_owner_registry_check as registry_check


class IhkPageOwnerRegistryCheckTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="ihk-page-owner-check-")
        self.repo = Path(self.temporary.name) / "repo"
        self.contract = json.loads(
            (REPO_ROOT / registry_check.DEFAULT_CONTRACT).read_text(encoding="utf-8")
        )
        paths = {
            registry_check.DEFAULT_CONTRACT.as_posix(),
            self.contract["production_source"]["path"],
            self.contract["allocator_dependency"]["source_path"],
            self.contract["allocator_dependency"]["contract_path"],
            self.contract["compile_fixture"]["path"],
            self.contract["lifetime_probe"]["path"],
            self.contract["sync_probe"]["path"],
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
        (self.repo / registry_check.DEFAULT_CONTRACT).write_text(
            json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )

    def mutate_and_resign(self, relative, old, new, owner, field="sha256"):
        path = self.repo / relative
        source = path.read_text(encoding="utf-8")
        self.assertIn(old, source)
        path.write_text(source.replace(old, new, 1), encoding="utf-8")
        owner[field] = hashlib.sha256(path.read_bytes()).hexdigest()
        self.write_contract()

    def fake_rustc(
        self,
        version=registry_check.EXPECTED_COMPILER,
        passed=15,
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
            "if any('lifetime_compile_fail' in item for item in sys.argv):\n"
            "    print('error[E0515]: cannot return value referencing local variable `allocator`', file=sys.stderr)\n"
            "    print('error[E0515]: cannot return value referencing local variable `slots`', file=sys.stderr)\n"
            "    raise SystemExit(1)\n"
            "if any('sync_compile_fail' in item for item in sys.argv):\n"
            "    print('error[E0277]: `Cell<()>` cannot be shared between threads safely', file=sys.stderr)\n"
            "    print('required by a bound in `assert_sync`', file=sys.stderr)\n"
            "    raise SystemExit(1)\n"
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
        result = registry_check.validate_repository(REPO_ROOT)
        self.assertEqual("IHK-006", result["gate_id"])
        self.assertTrue(result["source_contract_validated"])
        for field in (
            "gate_credit_eligible",
            "built_into_ihk_validated",
            "exact_kernel_compile_validated",
            "rocky_runtime_validated",
            "legacy_adapters_validated",
            "failure_injection_validated",
        ):
            self.assertFalse(result[field])

    def test_cli_reports_explicit_skip_without_pass_or_credit(self):
        output = io.StringIO()
        with mock.patch.dict(
            os.environ, {"IHK_PAGE_OWNER_REGISTRY_RUSTC": ""}
        ), mock.patch.object(registry_check.shutil, "which", return_value=None), contextlib.redirect_stdout(
            output
        ):
            result = registry_check.main(["--repo", str(REPO_ROOT)])
        self.assertEqual(0, result)
        rendered = output.getvalue()
        self.assertIn("SOURCE-CONTRACT-VERIFIED", rendered)
        self.assertIn("fixture=SKIPPED_NO_CONFIGURED_RUSTC", rendered)
        self.assertIn("gate_credit=FORBIDDEN", rendered)
        self.assertNotIn("PASS", rendered)

    def test_required_compiler_absence_fails(self):
        with mock.patch.dict(
            os.environ, {"IHK_PAGE_OWNER_REGISTRY_RUSTC": ""}
        ), self.assertRaisesRegex(registry_check.ValidationError, "required but absent"):
            registry_check.validate_configured_fixture(REPO_ROOT, require_rustc=True)

    def test_unconfigured_path_rustc_is_never_used(self):
        with mock.patch.dict(
            os.environ, {"IHK_PAGE_OWNER_REGISTRY_RUSTC": ""}
        ), mock.patch.object(registry_check.shutil, "which") as which:
            result = registry_check.validate_configured_fixture(REPO_ROOT)
        self.assertEqual("SKIPPED_NO_CONFIGURED_RUSTC", result["fixture_status"])
        which.assert_not_called()

    def test_exact_compiler_runs_fifteen_tests_and_compile_fail_probes(self):
        result = registry_check.validate_configured_fixture(
            REPO_ROOT, rustc=str(self.fake_rustc()), require_rustc=True
        )
        self.assertEqual(
            "EXACT_ROCKY_RUSTC_FIXTURE_VERIFIED", result["fixture_status"]
        )
        self.assertEqual(registry_check.EXPECTED_COMPILER, result["compiler_version"])

    def test_compiler_version_drift_fails(self):
        with self.assertRaisesRegex(registry_check.ValidationError, "version differs"):
            registry_check.validate_configured_fixture(
                REPO_ROOT, rustc=str(self.fake_rustc(version="rustc 1.92.0 unlocked"))
            )

    def test_configured_compiler_failure_is_not_skipped(self):
        with self.assertRaisesRegex(registry_check.ValidationError, "compilation failed"):
            registry_check.validate_configured_fixture(
                REPO_ROOT, rustc=str(self.fake_rustc(compile_exit=2))
            )

    def test_fixture_count_drift_fails(self):
        with self.assertRaisesRegex(
            registry_check.ValidationError, "exact contracted test count"
        ):
            registry_check.validate_configured_fixture(
                REPO_ROOT, rustc=str(self.fake_rustc(passed=14))
            )

    def test_direct_fixture_validation_checks_repository_first(self):
        source = self.repo / self.contract["production_source"]["path"]
        source.write_text(source.read_text(encoding="utf-8") + "\n", encoding="utf-8")
        with self.assertRaisesRegex(registry_check.ValidationError, "source digest differs"):
            registry_check.validate_configured_fixture(
                self.repo, rustc=str(self.fake_rustc()), require_rustc=True
            )

    def test_contract_cannot_self_award_any_evidence(self):
        for field in self.contract["evidence_policy"]:
            with self.subTest(field=field):
                mutated = json.loads(json.dumps(self.contract))
                mutated["evidence_policy"][field] = True
                self.write_contract(mutated)
                with self.assertRaisesRegex(registry_check.ValidationError, "cannot claim"):
                    registry_check.validate_repository(self.repo)

    def test_resigned_heap_or_unsafe_implementation_fails(self):
        for addition, expected in (
            ("\nunsafe fn bypass() {}\n", "forbidden registry implementation"),
            ("\ntype Hidden = alloc::vec::Vec<u64>;\n", "forbidden registry implementation"),
            ("\ntype Erased = core::mem::ManuallyDrop<u64>;\n", "forbidden registry implementation"),
        ):
            with self.subTest(addition=addition):
                source = self.repo / self.contract["production_source"]["path"]
                original = source.read_text(encoding="utf-8")
                source.write_text(original + addition, encoding="utf-8")
                self.contract["production_source"]["sha256"] = hashlib.sha256(
                    source.read_bytes()
                ).hexdigest()
                self.write_contract()
                with self.assertRaisesRegex(registry_check.ValidationError, expected):
                    registry_check.validate_repository(self.repo)
                source.write_text(original, encoding="utf-8")

    def test_resigned_lease_slot_erasure_fails(self):
        self.mutate_and_resign(
            self.contract["production_source"]["path"],
            "allocation: Option<PageAllocation<'allocator, 'storage>>",
            "allocation: Option<PageRange>",
            self.contract["production_source"],
        )
        with self.assertRaisesRegex(registry_check.ValidationError, "retained lease slots"):
            registry_check.validate_repository(self.repo)

    def test_resigned_inline_slot_array_fails(self):
        self.mutate_and_resign(
            self.contract["production_source"]["path"],
            "slots: &'slots mut [RawPageOwnerSlot<'allocator, 'storage>]",
            "slots: [RawPageOwnerSlot<'allocator, 'storage>; 64]",
            self.contract["production_source"],
        )
        with self.assertRaisesRegex(registry_check.ValidationError, "caller-owned slot slice"):
            registry_check.validate_repository(self.repo)

    def test_resigned_identity_wrap_mutation_fails(self):
        self.mutate_and_resign(
            self.contract["production_source"]["path"],
            "let next = current\n            .checked_add(1)",
            "let next = current\n            .wrapping_add(1)",
            self.contract["production_source"],
        )
        with self.assertRaisesRegex(registry_check.ValidationError, "non-wrapping registry identity"):
            registry_check.validate_repository(self.repo)

    def test_resigned_generation_wrap_mutation_fails(self):
        self.mutate_and_resign(
            self.contract["production_source"]["path"],
            "slot.generation.checked_add(1)",
            "slot.generation.wrapping_add(1)",
            self.contract["production_source"],
        )
        with self.assertRaisesRegex(registry_check.ValidationError, "free-slot selection"):
            registry_check.validate_repository(self.repo)

    def test_resigned_allocate_before_slot_selection_fails(self):
        self.mutate_and_resign(
            self.contract["production_source"]["path"],
            "        let (slot, generation) = self.next_slot()?;\n        let allocator: &'allocator BitmapPageAllocator<'storage> = self.allocator;\n        let allocation = allocator.allocate(blocks)?;",
            "        let allocator: &'allocator BitmapPageAllocator<'storage> = self.allocator;\n        let allocation = allocator.allocate(blocks)?;\n        let (slot, generation) = self.next_slot()?;",
            self.contract["production_source"],
        )
        with self.assertRaisesRegex(registry_check.ValidationError, "slot-before-allocator"):
            registry_check.validate_repository(self.repo)

    def test_resigned_identity_or_generation_check_removal_fails(self):
        for old, new, expected in (
            (
                "handle.registry_id != self.registry_id || handle.generation == 0",
                "handle.generation == 0",
                "registry identity check",
            ),
            (
                "slot.generation != handle.generation",
                "false",
                "slot generation check",
            ),
        ):
            with self.subTest(expected=expected):
                source = self.repo / self.contract["production_source"]["path"]
                original = source.read_text(encoding="utf-8")
                self.assertIn(old, original)
                source.write_text(original.replace(old, new, 1), encoding="utf-8")
                self.contract["production_source"]["sha256"] = hashlib.sha256(
                    source.read_bytes()
                ).hexdigest()
                self.write_contract()
                with self.assertRaisesRegex(registry_check.ValidationError, expected):
                    registry_check.validate_repository(self.repo)
                source.write_text(original, encoding="utf-8")

    def test_resigned_exact_handle_metadata_check_removal_fails(self):
        for old, new, expected in (
            ("range.address() != handle.address()", "false", "address ownership check"),
            ("range.blocks() != handle.blocks()", "false", "block ownership check"),
            ("range.bytes() != handle.bytes()", "false", "byte ownership check"),
        ):
            with self.subTest(expected=expected):
                source = self.repo / self.contract["production_source"]["path"]
                original = source.read_text(encoding="utf-8")
                source.write_text(original.replace(old, new, 1), encoding="utf-8")
                self.contract["production_source"]["sha256"] = hashlib.sha256(
                    source.read_bytes()
                ).hexdigest()
                self.write_contract()
                with self.assertRaisesRegex(registry_check.ValidationError, expected):
                    registry_check.validate_repository(self.repo)
                source.write_text(original, encoding="utf-8")

    def test_resigned_release_clear_before_try_release_fails(self):
        self.mutate_and_resign(
            self.contract["production_source"]["path"],
            "        allocation.try_release()?;\n        let released = slot.allocation.take();",
            "        let released = slot.allocation.take();\n        allocation.try_release()?;",
            self.contract["production_source"],
        )
        with self.assertRaisesRegex(registry_check.ValidationError, "validate-release-before-slot-clear"):
            registry_check.validate_repository(self.repo)

    def test_resigned_release_exclusive_receiver_removal_fails(self):
        for old, new, expected in (
            (
                "pub(crate) fn release(\n        &mut self,",
                "pub(crate) fn release(\n        &self,",
                "typed release must require exclusive",
            ),
            (
                "pub(crate) fn release_address(\n        &mut self,",
                "pub(crate) fn release_address(\n        &self,",
                "raw release must require exclusive",
            ),
        ):
            with self.subTest(expected=expected):
                source = self.repo / self.contract["production_source"]["path"]
                original = source.read_text(encoding="utf-8")
                self.assertIn(old, original)
                source.write_text(original.replace(old, new, 1), encoding="utf-8")
                self.contract["production_source"]["sha256"] = hashlib.sha256(
                    source.read_bytes()
                ).hexdigest()
                self.write_contract()
                with self.assertRaisesRegex(registry_check.ValidationError, expected):
                    registry_check.validate_repository(self.repo)
                source.write_text(original, encoding="utf-8")

    def test_resigned_raw_size_check_removal_fails(self):
        self.mutate_and_resign(
            self.contract["production_source"]["path"],
            "if range.blocks() != blocks || found.is_some()",
            "if found.is_some()",
            self.contract["production_source"],
        )
        with self.assertRaisesRegex(registry_check.ValidationError, "exact current-address release"):
            registry_check.validate_repository(self.repo)

    def test_resigned_allocator_retry_clear_reordering_fails(self):
        dependency = self.contract["allocator_dependency"]
        self.mutate_and_resign(
            dependency["source_path"],
            "        self.allocator\n            .release_owned(self.range, OwnershipKind::Allocated)?;\n        self.owned = false;",
            "        self.owned = false;\n        self.allocator\n            .release_owned(self.range, OwnershipKind::Allocated)?;",
            dependency,
            "source_sha256",
        )
        with self.assertRaisesRegex(registry_check.ValidationError, "release failure retains"):
            registry_check.validate_repository(self.repo)

    def test_resigned_fixture_contention_or_aba_reduction_fails(self):
        for old, new, expected in (
            ("const THREADS: usize = 8;", "const THREADS: usize = 1;", "eight-thread"),
            (
                "A generation-free legacy request cannot distinguish these owners.",
                "ABA coverage removed.",
                "raw ABA oracle",
            ),
        ):
            with self.subTest(expected=expected):
                fixture = self.repo / self.contract["compile_fixture"]["path"]
                original = fixture.read_text(encoding="utf-8")
                fixture.write_text(original.replace(old, new, 1), encoding="utf-8")
                self.contract["compile_fixture"]["sha256"] = hashlib.sha256(
                    fixture.read_bytes()
                ).hexdigest()
                self.write_contract()
                with self.assertRaisesRegex(registry_check.ValidationError, expected):
                    registry_check.validate_repository(self.repo)
                fixture.write_text(original, encoding="utf-8")

    def test_all_bound_file_digest_drift_fails_closed(self):
        cases = (
            (self.contract["production_source"]["path"], "source digest differs"),
            (self.contract["allocator_dependency"]["source_path"], "allocator source digest differs"),
            (self.contract["allocator_dependency"]["contract_path"], "allocator contract digest differs"),
            (self.contract["compile_fixture"]["path"], "fixture digest differs"),
            (self.contract["lifetime_probe"]["path"], "lifetime probe digest differs"),
            (self.contract["sync_probe"]["path"], "sync probe digest differs"),
        )
        for relative, expected in cases:
            with self.subTest(relative=relative):
                path = self.repo / relative
                original = path.read_text(encoding="utf-8")
                path.write_text(original + "\n", encoding="utf-8")
                with self.assertRaisesRegex(registry_check.ValidationError, expected):
                    registry_check.validate_repository(self.repo)
                path.write_text(original, encoding="utf-8")

    def test_duplicate_contract_key_fails_closed(self):
        contract_path = self.repo / registry_check.DEFAULT_CONTRACT
        text = contract_path.read_text(encoding="utf-8")
        contract_path.write_text(
            text.replace("{\n", '{\n  "schema_version": 1,\n', 1),
            encoding="utf-8",
        )
        with self.assertRaisesRegex(registry_check.ValidationError, "duplicate JSON key"):
            registry_check.validate_repository(self.repo)


if __name__ == "__main__":
    unittest.main()
