import ast
import os
import re
import shutil
import subprocess
import tempfile
import unittest


REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
RUST_PATH = os.path.join(
    REPO_ROOT, "host-kernel", "native-rust", "smp_resource.rs")
FIXTURE_PATH = os.path.join(
    REPO_ROOT, "scripts", "tests", "fixtures", "ihk_smp_resource_compile.rs")
ALIAS_FIXTURE_PATH = os.path.join(
    REPO_ROOT, "scripts", "tests", "fixtures",
    "ihk_smp_resource_workspace_alias_compile_fail.rs")

REQUIRED_INVARIANTS = (
    "pub(crate) const SMP_MAX_CPUS: usize = 512;",
    "pub(crate) const OS_TOKEN_CAPACITY: u32 = 64;",
    "pub(crate) const OS_TOKEN_MAX_GENERATION: u64 = (1_u64 << 41) - 1;",
    "pub(crate) const X86_64_PAGE_SIZE: u64 = 4096;",
    "self.slot >= OS_TOKEN_CAPACITY",
    "self.generation > OS_TOKEN_MAX_GENERATION",
    "if cpu >= N || cpu >= SMP_MAX_CPUS",
    "if cpus[..position].contains(&cpu)",
    "owner.validate()?;",
    "checked_add(length)",
    "checked_add(extent.length)",
    "workspace: &'workspace mut [CpuChange]",
    "impl<const N: usize> Drop for CpuTransaction<'_, '_, N>",
    "external_effects_started: bool",
    "pub(crate) fn begin_external_effects",
    "pub(crate) fn compensated_rollback",
    "CpuState::Quarantined",
    "if self.external_effects_started {",
    "self.quarantine();",
    "self.restore();",
    "pub(crate) struct MemoryWorkspace<'storage>",
    "if workspace.capacity() < N",
    "workspace.validate()?;",
    "pub(crate) struct MemoryTransaction<",
    "impl<const N: usize> Drop for MemoryTransaction<'_, '_, '_, N>",
    "poisoned: bool",
    "if self.poisoned {",
    "pub(crate) fn prepare_insert_free",
    "pub(crate) fn prepare_remove_free",
    "start % X86_64_PAGE_SIZE != 0",
    "if output.len() < needed",
    "prior_end > extent.start",
    "prior_end == extent.start && prior.same_class(extent)",
)

FORBIDDEN_PRODUCTION_TOKENS = (
    "std::",
    "alloc::",
    "Vec<",
    "Box<",
    "HashMap<",
    "unsafe ",
    'extern "C"',
    "kernel::",
    "panic!",
    ".unwrap()",
    ".expect(",
    "let mut candidate = Self::new();",
)


def read_text(path):
    with open(path, "r", encoding="utf-8") as stream:
        return stream.read()


def production_source(source):
    marker = "#[cfg(test)]\nmod tests"
    if marker not in source:
        raise AssertionError("Rust source lacks its exhaustive in-file test module")
    return source.split(marker, 1)[0]


def assert_source_invariants(source):
    for invariant in REQUIRED_INVARIANTS:
        if invariant not in source:
            raise AssertionError("missing resource invariant: {0}".format(invariant))
    production = production_source(source)
    for token in FORBIDDEN_PRODUCTION_TOKENS:
        if token in production:
            raise AssertionError("forbidden production token: {0}".format(token))
    token_impl = production.split("impl OsToken {", 1)[1].split(
        "/// Internal CPU lifecycle states", 1)[0]
    if "pub(crate) fn new(" in token_impl or "pub(crate) fn next(" in token_impl:
        raise AssertionError("production OsToken constructor is forbidden")
    if '#[cfg(test)]\n    pub(crate) fn test_only' not in token_impl:
        raise AssertionError("OsToken test construction is not cfg(test)-only")
    if '#[cfg(test)]\n    pub(crate) fn commit_policy_only' not in production:
        raise AssertionError("CPU policy-only commit is not cfg(test)-only")
    cpu_transaction = production.split(
        "impl<const N: usize> CpuTransaction<'_, '_, N> {", 1)[1].split(
            "impl<const N: usize> Drop for CpuTransaction", 1)[0]
    if "if !self.external_effects_started {" not in cpu_transaction:
        raise AssertionError("production CPU commit does not require effect preflight")
    for name in ("insert_free", "assign", "release", "release_all", "remove_free"):
        pattern = r"#\[cfg\(test\)\]\n\s+pub\(crate\) fn {0}\(".format(name)
        if re.search(pattern, production) is None:
            raise AssertionError(
                "production memory convenience method is not test-gated: {0}".format(name))
    if production.count("self.length += 1;") != 1:
        raise AssertionError("workspace push must advance length exactly once")
    memory_transaction = production.split(
        "impl<const N: usize> MemoryTransaction<'_, '_, '_, N> {", 1)[1].split(
            "impl<const N: usize> Drop for MemoryTransaction", 1)[0]
    for contract in (
            "pub(crate) fn begin_external_effects",
            "pub(crate) fn compensated_rollback",
            "self.poison();",
            "Err(ResourceError::ExternalEffectsNotStarted)"):
        if contract not in memory_transaction:
            raise AssertionError("missing memory effect contract: {0}".format(contract))


class IhkSmpResourceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = read_text(RUST_PATH)
        cls.fixture = read_text(FIXTURE_PATH)
        cls.alias_fixture = read_text(ALIAS_FIXTURE_PATH)

    def rejected_mutation(self, old, new):
        self.assertIn(old, self.source)
        mutated = self.source.replace(old, new)
        with self.assertRaises(AssertionError):
            assert_source_invariants(mutated)

    def test_source_is_no_std_allocation_ffi_and_unsafe_free(self):
        assert_source_invariants(self.source)
        self.assertTrue(self.source.startswith("// SPDX-License-Identifier: GPL-2.0"))

    def test_cpu_bound_and_duplicate_mutations_are_rejected(self):
        self.rejected_mutation(
            "if cpu >= N || cpu >= SMP_MAX_CPUS",
            "if cpu > N || cpu > SMP_MAX_CPUS")
        self.rejected_mutation(
            "if cpus[..position].contains(&cpu)",
            "if false && cpus[..position].contains(&cpu)")

    def test_generation_and_arithmetic_mutations_are_rejected(self):
        self.rejected_mutation(
            "self.slot >= OS_TOKEN_CAPACITY", "self.slot > OS_TOKEN_CAPACITY")
        self.rejected_mutation(
            "self.generation > OS_TOKEN_MAX_GENERATION",
            "self.generation >= OS_TOKEN_MAX_GENERATION")
        self.rejected_mutation("checked_add(length)", "wrapping_add(length)")
        self.rejected_mutation(
            "checked_add(extent.length)", "wrapping_add(extent.length)")

    def test_rollback_mutation_is_rejected(self):
        self.rejected_mutation(
            "impl<const N: usize> Drop for CpuTransaction<'_, '_, N>",
            "impl<const N: usize> Drop for AbandonedCpuTransaction<'_, '_, N>")
        self.rejected_mutation("self.restore();", "self.active = false;")
        self.rejected_mutation(
            "if self.external_effects_started {",
            "if false && self.external_effects_started {")
        self.rejected_mutation(
            "self.quarantine();", "self.restore();")

    def test_memory_atomicity_overlap_and_coalesce_mutations_are_rejected(self):
        self.rejected_mutation("workspace.validate()?;", "let _ = workspace.validate();")
        self.rejected_mutation(
            "if workspace.capacity() < N", "if workspace.capacity() > N")
        self.rejected_mutation("prior_end > extent.start", "prior_end >= extent.start")
        self.rejected_mutation(
            "prior_end == extent.start && prior.same_class(extent)",
            "false && prior.same_class(extent)")
        self.rejected_mutation(
            "start % X86_64_PAGE_SIZE != 0",
            "start % X86_64_PAGE_SIZE == 0")
        self.rejected_mutation("if self.poisoned {", "if false && self.poisoned {")
        self.rejected_mutation("self.length += 1;", "self.length += 2;")

    def test_queries_retain_count_before_copy_contract(self):
        self.rejected_mutation("if output.len() < needed", "if output.len() > needed")

    def test_test_and_fixture_surface_is_broad(self):
        self.assertEqual(24, self.source.count("#[test]"))
        self.assertEqual(5, self.fixture.count("#[test]"))
        self.assertEqual(29, self.source.count("#[test]") + self.fixture.count("#[test]"))
        self.assertIn(
            '#[path = "../../../host-kernel/native-rust/smp_resource.rs"]',
            self.fixture)
        for scenario in (
                "cpu_ownership_and_ikc_round_trip",
                "dropped_transaction_and_memory_capacity_failure_are_atomic",
                "memory_owner_generation_is_part_of_release_authority"):
            self.assertIn(scenario, self.fixture)
        self.assertIn("&mut memory", self.alias_fixture)
        self.assertIn("MemoryMap::<4>::new()", self.alias_fixture)
        self.assertIn("forge_os_token", self.alias_fixture)

    def test_python_test_parses_as_python_3_6(self):
        source = read_text(__file__)
        try:
            ast.parse(source, filename=__file__, feature_version=(3, 6))
        except TypeError:
            try:
                ast.parse(source, filename=__file__, feature_version=6)
            except TypeError:
                ast.parse(source, filename=__file__)

    def test_standalone_no_std_compile_and_tests_when_rustc_is_available(self):
        configured = os.environ.get("MCKERNEL_RUSTC_1_92")
        rustc = configured or shutil.which("rustc")
        if rustc is None:
            self.skipTest("rustc is not installed in this workspace")
        if configured:
            version = subprocess.check_output([rustc, "--version"]).decode("utf-8")
            self.assertIn("rustc 1.92.0", version)
        with tempfile.TemporaryDirectory(prefix="ihk-smp-resource-rust-") as temporary:
            library = os.path.join(temporary, "smp-resource.rlib")
            tests = os.path.join(temporary, "smp-resource-tests")
            commands = (
                [rustc, "--edition=2021", "-Dwarnings", "-C",
                 "overflow-checks=yes", "--crate-type", "lib", FIXTURE_PATH,
                 "-o", library],
                [rustc, "--edition=2021", "-Dwarnings", "-C",
                 "overflow-checks=yes", "--test", FIXTURE_PATH, "-o", tests],
                [tests, "--test-threads=1"],
            )
            for command in commands:
                if command[0] == tests:
                    listing = subprocess.check_output(
                        [tests, "--list"], cwd=REPO_ROOT).decode("utf-8")
                    self.assertEqual(
                        29,
                        len([line for line in listing.splitlines()
                             if line.endswith(": test")]))
                subprocess.check_call(command, cwd=REPO_ROOT)
            negative = subprocess.run(
                [rustc, "--edition=2021", "-Dwarnings", ALIAS_FIXTURE_PATH,
                 "-o", os.path.join(temporary, "must-not-build")],
                cwd=REPO_ROOT,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True)
            self.assertNotEqual(0, negative.returncode)
            self.assertIn("private", negative.stderr, negative.stderr)
            self.assertTrue(
                "mismatched types" in negative.stderr
                or "cannot borrow" in negative.stderr,
                negative.stderr)


if __name__ == "__main__":
    unittest.main()
