import ast
import json
import os
import subprocess
import sys
import tempfile
import unittest


REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from scripts import ihk_os_registry_check as registry


def read_bytes(relative):
    with open(os.path.join(REPO_ROOT, relative), "rb") as stream:
        return stream.read()


class IhkOsRegistryContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rust = read_bytes(registry.RUST_PATH)
        cls.abi = read_bytes(registry.ABI_PATH)
        cls.fixture = read_bytes(registry.FIXTURE_PATH)
        cls.contract = read_bytes(registry.CONTRACT_PATH)
        cls.legacy = registry.load_legacy_sources(REPO_ROOT)

    def rejected_rust_mutation(self, old, new):
        self.assertIn(old, self.rust)
        mutated = self.rust.replace(old, new, 1)
        with self.assertRaises(registry.ContractError):
            registry.check(REPO_ROOT, rust_override=mutated)

    def test_repository_contract_is_todo_and_fail_closed(self):
        contract = registry.check(REPO_ROOT)
        self.assertEqual("IHK-005-foundation", contract["gate_id"])
        self.assertEqual(64, contract["implementation"]["capacity"])
        self.assertEqual(41, contract["implementation"]["generation_bits"])
        self.assertTrue(contract["implementation"]["allocation_free"])
        self.assertTrue(contract["implementation"]["ffi_free"])
        self.assertEqual(8, contract["fixture"]["test_count"])
        self.assertEqual("TODO", contract["readiness"]["status"])
        self.assertFalse(contract["readiness"]["credit_eligible"])
        self.assertEqual(registry.READINESS_BLOCKERS,
                         tuple(contract["readiness"]["blockers"]))

    def test_checker_and_tests_parse_as_python_3_6(self):
        for relative in (
                "scripts/ihk_os_registry_check.py",
                "scripts/tests/test_ihk_os_registry_check.py"):
            source = read_bytes(relative).decode("utf-8")
            try:
                ast.parse(source, filename=relative, feature_version=(3, 6))
            except TypeError:
                ast.parse(source, filename=relative, feature_version=6)

    def test_every_frozen_legacy_source_mutation_is_rejected(self):
        for source_id in sorted(self.legacy):
            with self.subTest(source_id=source_id):
                source = self.legacy[source_id]
                mutated = source[:-1] + bytes(bytearray([source[-1] ^ 1]))
                with self.assertRaisesRegex(registry.ContractError, "source lock mismatch"):
                    registry.derive_contract(
                        REPO_ROOT, legacy_overrides={source_id: mutated})

    def test_capacity_and_first_free_contract_mutations_are_rejected(self):
        self.rejected_rust_mutation(
            b"pub(crate) const OS_CAPACITY: usize = 64;",
            b"pub(crate) const OS_CAPACITY: usize = 63;")
        self.rejected_rust_mutation(
            b"for minor in 0..OS_CAPACITY {",
            b"for minor in (0..OS_CAPACITY).rev() {")

    def test_generation_or_stale_check_mutation_is_rejected(self):
        self.rejected_rust_mutation(
            b"const GENERATION_SHIFT: u32 = 23;",
            b"const GENERATION_SHIFT: u32 = 22;")
        self.rejected_rust_mutation(
            b"generation(current) != handle.generation",
            b"generation(current) == handle.generation")
        self.rejected_rust_mutation(
            b"old_generation == MAX_GENERATION",
            b"old_generation > MAX_GENERATION")

    def test_transition_graph_mutation_is_rejected(self):
        self.rejected_rust_mutation(
            b"(1 << 1) | (1 << 2),",
            b"(1 << 1) | (1 << 2) | (1 << 5),")

    def test_allocation_ffi_and_unsafe_escape_hatches_are_rejected(self):
        for suffix in (
                b'\nextern "C" { fn legacy_create(); }\n',
                b"\nfn allocate() { let _ = Box::new(1); }\n",
                b"\nunsafe fn bypass_registry() {}\n"):
            with self.subTest(suffix=suffix):
                with self.assertRaisesRegex(registry.ContractError, "forbidden"):
                    registry.derive_contract(REPO_ROOT, rust_override=self.rust + suffix)

    def test_canonical_abi_status_drift_is_rejected(self):
        old = b"pub const IHK_OS_STATUS_RUNNING: i32 = 5;"
        self.assertIn(old, self.abi)
        mutated = self.abi.replace(
            old, b"pub const IHK_OS_STATUS_RUNNING: i32 = 6;", 1)
        with self.assertRaisesRegex(registry.ContractError, "canonical ABI"):
            registry.derive_contract(REPO_ROOT, abi_override=mutated)

    def test_fixture_drift_is_rejected(self):
        old = b"concurrent_churn_never_revives_an_old_handle"
        self.assertIn(old, self.fixture)
        mutated = self.fixture.replace(old, b"weakened_churn_test", 1)
        with self.assertRaisesRegex(registry.ContractError, "fixture lacks"):
            registry.derive_contract(REPO_ROOT, fixture_override=mutated)

    def test_contract_cannot_self_attest_credit_or_pass(self):
        contract = json.loads(self.contract.decode("utf-8"))
        contract["readiness"] = {
            "blockers": [],
            "credit_eligible": True,
            "status": "PASS",
        }
        with self.assertRaises(registry.ContractError):
            registry.check(
                REPO_ROOT,
                contract_override=registry.render_contract(contract))

    def test_exact_rust_1_92_fixture_when_configured(self):
        rustc = os.environ.get("MCKERNEL_RUSTC_1_92")
        if not rustc:
            self.skipTest("set MCKERNEL_RUSTC_1_92 for exact compiler replay")
        version = subprocess.check_output([rustc, "--version"]).decode("utf-8")
        self.assertIn("rustc 1.92.0", version)
        with tempfile.TemporaryDirectory(prefix="ihk-os-registry-rust-") as temporary:
            library = os.path.join(temporary, "registry.rlib")
            tests = os.path.join(temporary, "registry-tests")
            commands = (
                [rustc, "--edition=2021", "-Dwarnings", "--crate-type", "lib",
                 registry.FIXTURE_PATH, "-o", library],
                [rustc, "--edition=2021", "-Dwarnings", "--test",
                 registry.FIXTURE_PATH, "-o", tests],
                [tests, "--test-threads=1"],
            )
            for command in commands:
                subprocess.check_call(command, cwd=REPO_ROOT)


if __name__ == "__main__":
    unittest.main()
