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

from scripts import ihk_ioctl_dispatch_check as dispatch


def read_bytes(relative):
    with open(os.path.join(REPO_ROOT, relative), "rb") as stream:
        return stream.read()


class IhkIoctlDispatchContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rust = read_bytes(dispatch.RUST_PATH)
        cls.abi = read_bytes(dispatch.ABI_PATH)
        cls.registry = read_bytes(dispatch.REGISTRY_PATH)
        cls.fixture = read_bytes(dispatch.FIXTURE_PATH)
        cls.crate_root = read_bytes(dispatch.CRATE_ROOT_PATH)
        cls.contract = read_bytes(dispatch.CONTRACT_PATH)
        cls.legacy = dispatch.load_legacy_sources(REPO_ROOT)
        cls.rocky = {}
        for source_id, path, _size, _digest in dispatch.ROCKY_RUST_SOURCES:
            cls.rocky[source_id] = read_bytes(dispatch.ROCKY_FIXTURE_ROOT + "/" + path)

    def rejected_rust_mutation(self, old, new):
        self.assertIn(old, self.rust)
        mutated = self.rust.replace(old, new, 1)
        with self.assertRaises(dispatch.ContractError):
            dispatch.check(REPO_ROOT, rust_override=mutated)

    def test_repository_contract_is_todo_and_registration_blocked(self):
        contract = dispatch.check(REPO_ROOT)
        self.assertEqual("IHK-005-ioctl-dispatch-foundation", contract["gate_id"])
        self.assertEqual(64, contract["behavior"]["capacity"])
        self.assertEqual(10, contract["fixture"]["test_count"])
        self.assertTrue(contract["implementation"]["allocation_free"])
        self.assertTrue(contract["implementation"]["ffi_free"])
        self.assertFalse(contract["implementation"]["registration_supported"])
        self.assertFalse(contract["implementation"]["user_copy_reachable"])
        self.assertEqual("TODO", contract["readiness"]["status"])
        self.assertFalse(contract["readiness"]["credit_eligible"])
        self.assertEqual(dispatch.READINESS_BLOCKERS,
                         tuple(contract["readiness"]["blockers"]))

    def test_checker_and_tests_parse_as_python_3_6(self):
        for relative in (
                "scripts/ihk_ioctl_dispatch_check.py",
                "scripts/tests/test_ihk_ioctl_dispatch_check.py"):
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
                with self.assertRaisesRegex(dispatch.ContractError, "source lock mismatch"):
                    dispatch.derive_contract(
                        REPO_ROOT, legacy_overrides={source_id: mutated})

    def test_exact_commands_are_bound_to_canonical_abi(self):
        old = b"pub const IHK_DEVICE_DESTROY_OS: u32 = 0x0011_2901;"
        self.assertIn(old, self.abi)
        mutated = self.abi.replace(
            old, b"pub const IHK_DEVICE_DESTROY_OS: u32 = 0x0011_2902;", 1)
        with self.assertRaisesRegex(dispatch.ContractError, "canonical ABI value"):
            dispatch.derive_contract(REPO_ROOT, abi_override=mutated)

    def test_unsupported_registration_or_copy_markers_cannot_flip(self):
        for name in (
                b"NATIVE_DEVICE_REGISTRATION_SUPPORTED",
                b"NATIVE_FILE_OPERATIONS_SUPPORTED",
                b"NATIVE_IOCTL_CALLBACK_SUPPORTED",
                b"USER_COPY_REACHABLE_FROM_IOCTL"):
            old = b"pub(crate) const " + name + b": bool = false;"
            new = b"pub(crate) const " + name + b": bool = true;"
            with self.subTest(name=name):
                self.rejected_rust_mutation(old, new)

    def test_unsafe_ffi_allocation_registration_and_copy_escape_hatches_are_rejected(self):
        for suffix in (
                b'\nextern "C" { fn legacy_ioctl(); }\n',
                b"\nunsafe fn raw_file_operations() {}\n",
                b"\nfn allocate() { let _ = Box::new(1); }\n",
                b"\nfn bypass() { misc_register(); }\n",
                b"\nfn copy() { kernel::uaccess::UserSlice::new(0, 0); }\n"):
            with self.subTest(suffix=suffix):
                with self.assertRaisesRegex(dispatch.ContractError, "forbidden"):
                    dispatch.derive_contract(REPO_ROOT, rust_override=self.rust + suffix)

    def test_minor_range_and_two_phase_transaction_mutations_are_rejected(self):
        self.rejected_rust_mutation(
            b"argument >= OS_CAPACITY as u64",
            b"argument > OS_CAPACITY as u64")
        self.rejected_rust_mutation(
            b"commit_after_external_success",
            b"publish_without_external_success")
        self.rejected_rust_mutation(
            b"abort_external_failure",
            b"forget_external_failure")

    def test_status_alias_or_generation_snapshot_mutation_is_rejected(self):
        self.rejected_rust_mutation(
            b"IHK_OS_QUERY_STATUS | IHK_OS_STATUS",
            b"IHK_OS_QUERY_STATUS")
        self.rejected_rust_mutation(
            b".snapshot(handle)",
            b".resolve_minor(handle.minor())")

    def test_private_attachment_and_queue_registry_edges_are_required(self):
        for old, new in (
                (b"mod ihk_ioctl;", b"mod missing_ioctl;"),
                (b"mod ikc_queue;", b"mod missing_queue;"),
                (b"mod ikc_master;", b"mod missing_master;"),
                (b"mod os_registry;", b"mod missing_registry;")):
            with self.subTest(old=old):
                self.assertIn(old, self.crate_root)
                mutated = self.crate_root.replace(old, new, 1)
                with self.assertRaises(dispatch.ContractError):
                    dispatch.check(REPO_ROOT, crate_root_override=mutated)

    def test_fixture_concurrency_or_property_coverage_drift_is_rejected(self):
        for marker in (
                b"concurrent_create_transactions_publish_unique_minors",
                b"deterministic_operation_property_preserves_registry_invariants"):
            with self.subTest(marker=marker):
                self.assertIn(marker, self.fixture)
                mutated = self.fixture.replace(marker, b"weakened_coverage", 1)
                with self.assertRaisesRegex(dispatch.ContractError, "fixture lacks"):
                    dispatch.derive_contract(REPO_ROOT, fixture_override=mutated)

    def test_exact_rocky_api_semantics_reject_weakened_key_sources(self):
        values = dict(self.rocky)
        values["crate_exports"] = values["crate_exports"].replace(
            b"pub mod uaccess;", b"pub mod inaccessible;", 1)
        with self.assertRaisesRegex(dispatch.ContractError, "user-access module"):
            dispatch._validate_rocky_key_sources(values)

        values = dict(self.rocky)
        values["ioctl_numbers"] = values["ioctl_numbers"].replace(
            b"pub const fn _IOWR", b"pub const fn missing_IOWR", 1)
        with self.assertRaisesRegex(dispatch.ContractError, "ioctl helper"):
            dispatch._validate_rocky_key_sources(values)

        values = dict(self.rocky)
        values["user_access"] = values["user_access"].replace(
            b"bindings::copy_to_user", b"bindings::missing_copy_to_user", 1)
        with self.assertRaisesRegex(dispatch.ContractError, "copy-to-user"):
            dispatch._validate_rocky_key_sources(values)

    def test_contract_cannot_self_attest_registration_credit_or_pass(self):
        contract = json.loads(self.contract.decode("utf-8"))
        contract["implementation"]["registration_supported"] = True
        contract["readiness"] = {
            "blockers": [],
            "credit_eligible": True,
            "status": "PASS",
        }
        with self.assertRaises(dispatch.ContractError):
            dispatch.check(
                REPO_ROOT,
                contract_override=dispatch.render_contract(contract))

    def test_exact_rocky_source_tree_audit_when_configured(self):
        kernel_source = os.environ.get("MCKERNEL_ROCKY_SOURCE_6_12")
        if not kernel_source:
            self.skipTest("set MCKERNEL_ROCKY_SOURCE_6_12 for full Rust API audit")
        count = dispatch.audit_rocky_source(kernel_source)
        self.assertGreaterEqual(count, 50)

    def test_exact_rust_1_92_fixture_when_configured(self):
        rustc = os.environ.get("MCKERNEL_RUSTC_1_92")
        if not rustc:
            self.skipTest("set MCKERNEL_RUSTC_1_92 for exact compiler replay")
        version = subprocess.check_output([rustc, "--version"]).decode("utf-8").strip()
        self.assertEqual(dispatch.EXPECTED_RUSTC, version)
        environment = os.environ.copy()
        with tempfile.TemporaryDirectory(prefix="ihk-ioctl-dispatch-rust-") as temporary:
            library = os.path.join(temporary, "dispatch.rlib")
            tests = os.path.join(temporary, "dispatch-tests")
            commands = (
                [rustc, "--edition=2021", "-Dwarnings", "--crate-type", "lib",
                 dispatch.FIXTURE_PATH, "-o", library],
                [rustc, "--edition=2021", "-Dwarnings", "--test",
                 dispatch.FIXTURE_PATH, "-o", tests],
                [tests, "--test-threads=1"],
            )
            for command in commands:
                subprocess.check_call(command, cwd=REPO_ROOT, env=environment)


if __name__ == "__main__":
    unittest.main()
