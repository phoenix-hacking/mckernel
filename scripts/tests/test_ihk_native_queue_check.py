import contextlib
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

from scripts import ihk_native_queue_check as queue_check


class IhkNativeQueueCheckTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory(prefix="ihk-native-queue-check-")
        self.repo = Path(self.temporary.name) / "repo"
        self.contract = json.loads(
            (REPO_ROOT / queue_check.DEFAULT_CONTRACT).read_text(encoding="utf-8")
        )
        relative_paths = {
            queue_check.DEFAULT_CONTRACT.as_posix(),
            self.contract["canonical_abi"]["path"],
            self.contract["production_source"]["path"],
            self.contract["compile_fixture"]["path"],
        }
        for relative in relative_paths:
            target = self.repo / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(REPO_ROOT / relative, target)

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def mutate_text(self, relative: str, old: str, new: str) -> None:
        path = self.repo / relative
        text = path.read_text(encoding="utf-8")
        self.assertIn(old, text)
        path.write_text(text.replace(old, new, 1), encoding="utf-8")

    def write_contract(self, value: object) -> None:
        (self.repo / queue_check.DEFAULT_CONTRACT).write_text(
            json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )

    def fake_rustc(
        self,
        version: str = (
            "rustc 1.92.0 (ded5c06cf 2025-12-08) (Red Hat 1.92.0-1.el10)"
        ),
        passed: int = 5,
        compile_exit: int = 0,
    ) -> Path:
        compiler = Path(self.temporary.name) / "rustc"
        compiler.write_text(
            "#!/usr/bin/env python3\n"
            "import os\n"
            "import sys\n"
            f"VERSION = {version!r}\n"
            f"PASSED = {passed!r}\n"
            f"COMPILE_EXIT = {compile_exit!r}\n"
            "if sys.argv[1:] == ['--version']:\n"
            "    print(VERSION)\n"
            "    raise SystemExit(0)\n"
            "if COMPILE_EXIT:\n"
            "    print('synthetic compile failure', file=sys.stderr)\n"
            "    raise SystemExit(COMPILE_EXIT)\n"
            "output = sys.argv[sys.argv.index('-o') + 1]\n"
            "body = (\n"
            "    '#!/usr/bin/env python3\\n'\n"
            "    \"print('test result: ok. %d passed; 0 failed; 0 ignored; \"\n"
            "    \"0 measured; 0 filtered out')\\n\" % PASSED\n"
            ")\n"
            "with open(output, 'w', encoding='utf-8') as stream:\n"
            "    stream.write(body)\n"
            "os.chmod(output, 0o755)\n",
            encoding="utf-8",
        )
        compiler.chmod(0o755)
        return compiler

    def test_source_contract_is_verified_without_gate_credit(self) -> None:
        summary = queue_check.validate_repository(REPO_ROOT)
        self.assertEqual("IHK-008", summary["gate_id"])
        self.assertTrue(summary["source_contract_validated"])
        self.assertFalse(summary["gate_credit_eligible"])
        self.assertFalse(summary["built_into_ihk_validated"])
        self.assertFalse(summary["exact_kernel_compile_validated"])
        self.assertFalse(summary["rocky_runtime_validated"])
        self.assertFalse(summary["teardown_validated"])
        self.assertFalse(summary["performance_parity_validated"])

    def test_cli_reports_honest_compiler_skip_without_pass_or_credit(self) -> None:
        output = io.StringIO()
        with mock.patch.dict(os.environ, {"IHK_NATIVE_QUEUE_RUSTC": ""}), mock.patch.object(
            queue_check.shutil, "which", return_value=None
        ), contextlib.redirect_stdout(output):
            result = queue_check.main(["--repo", str(REPO_ROOT)])
        self.assertEqual(0, result)
        rendered = output.getvalue()
        self.assertIn("SOURCE-CONTRACT-VERIFIED", rendered)
        self.assertIn("fixture=SKIPPED_NO_CONFIGURED_RUSTC", rendered)
        self.assertIn("rocky_runtime=NOT_PROVEN", rendered)
        self.assertIn("gate_credit=FORBIDDEN", rendered)
        self.assertNotIn("PASS", rendered)

    def test_require_rustc_rejects_absence(self) -> None:
        with mock.patch.dict(os.environ, {"IHK_NATIVE_QUEUE_RUSTC": ""}), mock.patch.object(
            queue_check.shutil, "which", return_value=None
        ), self.assertRaisesRegex(queue_check.ValidationError, "required but absent"):
            queue_check.validate_configured_fixture(REPO_ROOT, require_rustc=True)

    def test_unconfigured_path_rustc_is_not_used_opportunistically(self) -> None:
        compiler = self.fake_rustc(version="rustc 1.92.0 (wrong PATH compiler)")
        with mock.patch.dict(
            os.environ,
            {"IHK_NATIVE_QUEUE_RUSTC": "", "PATH": str(compiler.parent)},
        ), mock.patch.object(
            queue_check.shutil, "which", wraps=queue_check.shutil.which
        ) as which:
            result = queue_check.validate_configured_fixture(REPO_ROOT)
        self.assertEqual("SKIPPED_NO_CONFIGURED_RUSTC", result["fixture_status"])
        which.assert_not_called()

    def test_exact_configured_rustc_compiles_and_runs_five_tests(self) -> None:
        compiler = self.fake_rustc()
        result = queue_check.validate_configured_fixture(
            REPO_ROOT, rustc=str(compiler), require_rustc=True
        )
        self.assertEqual("EXACT_ROCKY_RUSTC_FIXTURE_VERIFIED", result["fixture_status"])
        self.assertEqual(
            "rustc 1.92.0 (ded5c06cf 2025-12-08) (Red Hat 1.92.0-1.el10)",
            result["compiler_version"],
        )

    def test_configured_rustc_version_drift_is_rejected(self) -> None:
        compiler = self.fake_rustc(version="rustc 1.92.0 (unlocked)")
        with self.assertRaisesRegex(queue_check.ValidationError, "version differs"):
            queue_check.validate_configured_fixture(REPO_ROOT, rustc=str(compiler))

    def test_configured_rustc_compile_failure_is_not_skipped(self) -> None:
        compiler = self.fake_rustc(compile_exit=2)
        with self.assertRaisesRegex(queue_check.ValidationError, "compilation failed"):
            queue_check.validate_configured_fixture(REPO_ROOT, rustc=str(compiler))

    def test_fixture_test_count_drift_is_rejected(self) -> None:
        compiler = self.fake_rustc(passed=4)
        with self.assertRaisesRegex(queue_check.ValidationError, "exact contracted test count"):
            queue_check.validate_configured_fixture(REPO_ROOT, rustc=str(compiler))

    def test_contract_cannot_claim_gate_credit_or_runtime_evidence(self) -> None:
        for field in self.contract["evidence_policy"]:
            with self.subTest(field=field):
                mutated = json.loads(json.dumps(self.contract))
                mutated["evidence_policy"][field] = True
                self.write_contract(mutated)
                with self.assertRaisesRegex(queue_check.ValidationError, "cannot claim"):
                    queue_check.validate_repository(self.repo)

    def test_explicit_remote_dequeue_exclusion_is_mandatory(self) -> None:
        mutated = json.loads(json.dumps(self.contract))
        mutated["safety_contract"]["remote_dequeue_owner_forbidden"] = False
        self.write_contract(mutated)
        with self.assertRaisesRegex(queue_check.ValidationError, "precondition"):
            queue_check.validate_repository(self.repo)

    def test_source_remote_owner_precondition_is_mandatory(self) -> None:
        self.mutate_text(
            self.contract["production_source"]["path"],
            "no remote endpoint may consume and",
            "a remote endpoint may also consume and",
        )
        with self.assertRaisesRegex(queue_check.ValidationError, "safety/ABI"):
            queue_check.validate_repository(self.repo)

    def test_packet_alignment_checks_are_mandatory_at_init_and_attach(self) -> None:
        source = self.contract["production_source"]["path"]
        original = (self.repo / source).read_text(encoding="utf-8")
        for fragment in (
            "packet_bytes % size_of::<u64>() != 0",
            "packet_size % size_of::<u64>() != 0",
        ):
            with self.subTest(fragment=fragment):
                (self.repo / source).write_text(
                    original.replace(fragment, "false", 1), encoding="utf-8"
                )
                with self.assertRaisesRegex(queue_check.ValidationError, "alignment"):
                    queue_check.validate_repository(self.repo)
        (self.repo / source).write_text(original, encoding="utf-8")

    def test_legacy_full_retry_drift_is_rejected(self) -> None:
        self.mutate_text(
            self.contract["production_source"]["path"],
            "const LEGACY_WRITE_QUEUE_RETRY: usize = 128;",
            "const LEGACY_WRITE_QUEUE_RETRY: usize = 127;",
        )
        with self.assertRaisesRegex(queue_check.ValidationError, "retry constant"):
            queue_check.validate_repository(self.repo)

    def test_reservation_ordering_drift_is_rejected(self) -> None:
        self.mutate_text(
            self.contract["production_source"]["path"],
            "Ordering::AcqRel,\n                    Ordering::Acquire,",
            "Ordering::Relaxed,\n                    Ordering::Acquire,",
        )
        with self.assertRaisesRegex(queue_check.ValidationError, "acqrel reservation"):
            queue_check.validate_repository(self.repo)

    def test_publication_ordering_drift_is_rejected(self) -> None:
        self.mutate_text(
            self.contract["production_source"]["path"],
            "current.wrapping_add(1),\n                            Ordering::Release,",
            "current.wrapping_add(1),\n                            Ordering::Relaxed,",
        )
        with self.assertRaisesRegex(queue_check.ValidationError, "release publication"):
            queue_check.validate_repository(self.repo)

    def test_read_release_ordering_drift_is_rejected(self) -> None:
        self.mutate_text(
            self.contract["production_source"]["path"],
            "state.read.wrapping_add(1),\n                    Ordering::Release,",
            "state.read.wrapping_add(1),\n                    Ordering::Relaxed,",
        )
        with self.assertRaisesRegex(queue_check.ValidationError, "release read-offset"):
            queue_check.validate_repository(self.repo)

    def test_mapping_overlap_guards_are_mandatory_on_both_paths(self) -> None:
        source = self.contract["production_source"]["path"]
        original = (self.repo / source).read_text(encoding="utf-8")
        guard = "self.overlaps_mapping(packet.as_ptr(), state.packet_size)"
        self.assertEqual(2, original.count(guard))
        for occurrence in (1, 2):
            with self.subTest(occurrence=occurrence):
                parts = original.split(guard)
                parts[occurrence] = "false" + parts[occurrence]
                mutated = guard.join(parts[:occurrence]) + parts[occurrence]
                if occurrence == 1:
                    mutated += guard + parts[2]
                (self.repo / source).write_text(mutated, encoding="utf-8")
                with self.assertRaisesRegex(queue_check.ValidationError, "overlap guard"):
                    queue_check.validate_repository(self.repo)
        (self.repo / source).write_text(original, encoding="utf-8")

    def test_consumer_claim_cannot_be_removed(self) -> None:
        self.mutate_text(
            self.contract["production_source"]["path"],
            ".compare_exchange(false, true, Ordering::Acquire, Ordering::Relaxed)",
            ".compare_exchange(false, true, Ordering::Relaxed, Ordering::Relaxed)",
        )
        with self.assertRaisesRegex(queue_check.ValidationError, "consumer claim ordering"):
            queue_check.validate_repository(self.repo)

    def test_counter_corruption_bounds_are_mandatory(self) -> None:
        self.mutate_text(
            self.contract["production_source"]["path"],
            "reserved_distance >= packet_count",
            "reserved_distance > packet_count",
        )
        with self.assertRaisesRegex(queue_check.ValidationError, "capacity corruption"):
            queue_check.validate_repository(self.repo)

    def test_copy_nonoverlapping_regression_is_rejected(self) -> None:
        source = self.repo / self.contract["production_source"]["path"]
        with source.open("a", encoding="utf-8") as stream:
            stream.write("\n// copy_nonoverlapping must remain forbidden.\n")
        with self.assertRaisesRegex(queue_check.ValidationError, "forbidden boundary"):
            queue_check.validate_repository(self.repo)

    def test_fixture_concurrency_inventory_drift_is_rejected(self) -> None:
        self.mutate_text(
            self.contract["compile_fixture"]["path"],
            "const CONSUMERS: usize = 4;",
            "const CONSUMERS: usize = 1;",
        )
        with self.assertRaisesRegex(queue_check.ValidationError, "four consumers"):
            queue_check.validate_repository(self.repo)

    def test_fixture_cannot_duplicate_the_canonical_queue_header(self) -> None:
        fixture = self.repo / self.contract["compile_fixture"]["path"]
        with fixture.open("a", encoding="utf-8") as stream:
            stream.write("\nstruct IhkIkcQueueHead;\n")
        with self.assertRaisesRegex(queue_check.ValidationError, "duplicates"):
            queue_check.validate_repository(self.repo)

    def test_source_and_fixture_digest_drift_fail_closed(self) -> None:
        for relative, expected in (
            (self.contract["production_source"]["path"], "source digest"),
            (self.contract["compile_fixture"]["path"], "fixture digest"),
        ):
            with self.subTest(relative=relative):
                path = self.repo / relative
                original = path.read_text(encoding="utf-8")
                path.write_text(original + "\n", encoding="utf-8")
                with self.assertRaisesRegex(queue_check.ValidationError, expected):
                    queue_check.validate_repository(self.repo)
                path.write_text(original, encoding="utf-8")

    def test_canonical_abi_digest_drift_fails_closed(self) -> None:
        path = self.repo / self.contract["canonical_abi"]["path"]
        original = path.read_text(encoding="utf-8")
        path.write_text(original + "\n", encoding="utf-8")
        with self.assertRaisesRegex(queue_check.ValidationError, "ABI digest"):
            queue_check.validate_repository(self.repo)


if __name__ == "__main__":
    unittest.main()
