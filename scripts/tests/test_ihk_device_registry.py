import os
import re
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
SOURCE = REPO_ROOT / "host-kernel/native-rust/device_registry.rs"
FIXTURE = REPO_ROOT / "scripts/tests/fixtures/ihk_device_registry_compile.rs"


class IhkDeviceRegistryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = SOURCE.read_text(encoding="utf-8")
        cls.fixture = FIXTURE.read_text(encoding="utf-8")
        marker = "#[cfg(test)]\nmod tests {"
        if marker not in cls.source:
            raise AssertionError("device registry lacks in-file Rust unit tests")
        cls.production = cls.source.split(marker, 1)[0]

    def test_production_is_allocation_free_no_std_core(self):
        self.assertIn("use core::sync::atomic::{AtomicU64, Ordering};", self.production)
        forbidden = (
            r"\bunsafe\b",
            r"extern\s+\"C\"",
            r"\b(?:alloc|std|kernel)::",
            r"\b(?:Box|Vec|String|Arc|Rc)\b",
            r"\binclude(?:_bytes)?!\s*\(",
            r"\b(?:global_asm|asm)!\s*\(",
        )
        for pattern in forbidden:
            with self.subTest(pattern=pattern):
                self.assertIsNone(re.search(pattern, self.production))

    def test_exact_fixed_slot_and_nonwrapping_identity_layout(self):
        required = (
            "pub(crate) const DEVICE_CAPACITY: usize = 64;",
            "slots: [Slot; DEVICE_CAPACITY]",
            "const PROVIDER_REFERENCE_SHIFT: u32 = 4;",
            "const OS_REFERENCE_SHIFT: u32 = 20;",
            "const GENERATION_SHIFT: u32 = 36;",
            "const MAX_GENERATION: u64 = u64::MAX >> GENERATION_SHIFT;",
            "const PROVIDER_TOKEN_MAGIC: u64 = 0x49_48_4b;",
            "const PROVIDER_TOKEN_VERSION: u64 = 1;",
            "old_generation == MAX_GENERATION",
            ".checked_add(1)",
            "handle.registry_id != self.registry_id",
            "const fn production() -> Self",
            "pub(crate) static IHK_DEVICE_REGISTRY: DeviceRegistry = DeviceRegistry::production();",
            "pub(crate) fn encode_provider_token(",
            "pub(crate) fn decode_provider_token(",
        )
        for token in required:
            with self.subTest(token=token):
                self.assertIn(token, self.production)

    def test_atomic_transactions_and_rollback_guards_are_present(self):
        self.assertGreaterEqual(self.production.count("compare_exchange("), 10)
        self.assertIn("PHASE_PUBLISHING", self.production)
        self.assertIn("PHASE_LIVE", self.production)
        self.assertIn("PHASE_UNPUBLISHING", self.production)
        self.assertIn("impl Drop for ReservationGuard", self.production)
        self.assertIn("pub(crate) fn abort", self.production)
        self.assertIn("impl Drop for UnregisterGuard", self.production)
        self.assertIn("pub(crate) fn rollback", self.production)
        self.assertRegex(
            self.production,
            r"provider_references\(current\) != 0\s*\|\|\s*os_references\(current\) != 0",
        )

    def test_sharing_and_both_reference_overflows_fail_closed(self):
        self.assertIn(
            "share_policy(current) == SharePolicy::Exclusive && references != 0",
            self.production,
        )
        self.assertIn("references == MAX_REFERENCES", self.production)
        self.assertIn("ProviderReferenceOverflow", self.production)
        self.assertIn("os_references(current) == MAX_REFERENCES", self.production)
        self.assertIn("OsReferenceOverflow", self.production)
        self.assertIn(
            "share_policy(word) == SharePolicy::Shared", self.production
        )
        self.assertIn("provider_references <= 1", self.production)
        self.assertIn(
            "fn live_count(&self) -> Result<usize, DeviceRegistryError>",
            self.production,
        )
        self.assertIn(
            "fn active_count(&self) -> Result<usize, DeviceRegistryError>",
            self.production,
        )
        self.assertNotIn("wrapping_add", self.production)

    def test_in_file_unit_suite_is_large_and_covers_required_boundaries(self):
        self.assertEqual(31, self.source.count("#[test]"))
        required_tests = (
            "exact_capacity_first_fit_generation_reuse_and_stale_rejection",
            "dropping_reservation_aborts_and_consumes_generation",
            "exclusive_provider_allows_only_one_open",
            "os_references_drain_while_unpublishing",
            "provider_reference_overflow_fails_without_field_carry",
            "os_reference_overflow_fails_without_generation_carry",
            "dropping_unregister_guard_restores_live_state",
            "premature_unregister_commit_fails_and_rolls_back",
            "foreign_registry_handle_is_always_stale",
            "registry_identity_exhaustion_is_nonwrapping",
            "generation_exhaustion_retires_without_wrapping",
            "malformed_packed_words_fail_closed_as_corrupt",
            "lease_drop_does_not_rewrite_corrupt_slot_words",
            "concurrent_publications_claim_unique_slots",
            "production_registry_token_round_trip_is_positive_and_exact",
            "provider_open_tokens_count_shared_files_and_release_once_each",
            "owned_open_token_release_fails_stop_on_unbalanced_receipt",
            "provider_token_header_version_and_generation_fail_closed",
            "provider_token_is_stale_after_unregister_and_slot_reuse",
            "dynamic_registry_cannot_issue_or_accept_production_tokens",
            "concurrent_provider_attaches_publish_exactly_one_minor_zero_lease",
            "concurrent_duplicate_detach_has_one_winner_and_no_live_slot",
        )
        for name in required_tests:
            with self.subTest(name=name):
                self.assertIn("fn " + name, self.source)

    def test_fixture_has_deterministic_success_rollback_and_interleavings(self):
        self.assertEqual(8, self.fixture.count("#[test]"))
        required_tests = (
            "success_path_publishes_counts_and_unregisters",
            "failed_external_publication_aborts_without_reusing_handle",
            "registry_state_rollback_restores_live_before_external_commit",
            "deterministic_open_first_interleaving_blocks_unregister",
            "deterministic_unregister_first_interleaving_blocks_references",
            "simultaneous_publishers_get_unique_generation_tagged_slots",
            "production_token_adapter_round_trips_and_detaches",
            "malformed_and_replayed_production_tokens_fail_closed",
        )
        for name in required_tests:
            with self.subTest(name=name):
                self.assertIn("fn " + name, self.fixture)
        self.assertIn("Barrier::new(2)", self.fixture)

    def test_standalone_fixture_compiles_and_runs_when_rustc_is_available(self):
        rustc = os.environ.get("MCKERNEL_RUSTC_1_92") or shutil.which("rustc")
        if rustc is None:
            self.skipTest("rustc is unavailable")
        environment = dict(os.environ)
        environment["RUST_BACKTRACE"] = "1"
        with tempfile.TemporaryDirectory(prefix="ihk-device-registry-") as temporary:
            library = os.path.join(temporary, "device-registry.rlib")
            tests = os.path.join(temporary, "device-registry-tests")
            compile_commands = (
                [rustc, "--edition=2021", "-Dwarnings", "-C", "overflow-checks=yes",
                 "--crate-type", "lib", str(FIXTURE), "-o", library],
                [rustc, "--edition=2021", "-Dwarnings", "-C", "overflow-checks=yes",
                 "--test", str(FIXTURE), "-o", tests],
            )
            for command in compile_commands:
                subprocess.check_call(command, cwd=str(REPO_ROOT), env=environment)
            listed = subprocess.check_output(
                [tests, "--list"], cwd=str(REPO_ROOT), env=environment
            ).decode("utf-8")
            discovered = [line for line in listed.splitlines() if line.endswith(": test")]
            self.assertEqual(37, len(discovered))
            subprocess.check_call(
                [tests, "--test-threads=1"], cwd=str(REPO_ROOT), env=environment
            )


if __name__ == "__main__":
    unittest.main()
