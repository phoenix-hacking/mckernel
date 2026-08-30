import ast
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest


REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from scripts import ihk_device_registry_check as registry


def read_bytes(relative):
    with open(os.path.join(REPO_ROOT, relative), "rb") as stream:
        return stream.read()


def sha256(data):
    return hashlib.sha256(data).hexdigest()


class IhkDeviceRegistryContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rust = read_bytes(registry.RUST_PATH)
        cls.fixture = read_bytes(registry.FIXTURE_PATH)
        cls.crate_root = read_bytes(registry.CRATE_ROOT_PATH)
        cls.ioctl_contract = read_bytes(registry.IOCTL_CONTRACT_PATH)
        cls.reference_inventory = read_bytes(registry.REFERENCE_INVENTORY_PATH)
        cls.contract = read_bytes(registry.CONTRACT_PATH)
        cls.legacy = registry.load_legacy_sources(REPO_ROOT)

    def rejected_rust_semantic_mutation(self, old, new):
        self.assertIn(old, self.rust)
        mutated = self.rust.replace(old, new, 1)
        with self.assertRaises(registry.ContractError):
            registry.derive_contract(REPO_ROOT, rust_override=mutated)

    def rejected_legacy_semantic_mutation(self, source_id, old, new):
        source = self.legacy[source_id]
        self.assertIn(old, source)
        mutated = dict(self.legacy)
        mutated[source_id] = source.replace(old, new, 1)
        with self.assertRaises(registry.ContractError):
            registry._validate_legacy(mutated)

    def rejected_legacy_function_mutation(self, source_id, signature, old, new):
        source = self.legacy[source_id]
        start = source.find(signature)
        self.assertGreaterEqual(start, 0)
        position = source.find(old, start)
        self.assertGreaterEqual(position, 0)
        mutated_source = source[:position] + new + source[position + len(old):]
        mutated = dict(self.legacy)
        mutated[source_id] = mutated_source
        with self.assertRaises(registry.ContractError):
            registry._validate_legacy(mutated)

    def test_repository_contract_is_todo_noncrediting_and_exact(self):
        contract = registry.check(REPO_ROOT)
        self.assertEqual("IHK-004-device-registry-foundation", contract["gate_id"])
        self.assertEqual(64, contract["behavior"]["capacity"])
        self.assertEqual(28, contract["behavior"]["generation_bits"])
        self.assertEqual(16, contract["behavior"]["reference_bits"]["provider_open"])
        self.assertEqual(16, contract["behavior"]["reference_bits"]["os"])
        self.assertEqual(23, contract["fixture"]["expected_in_file_tests"])
        self.assertEqual(6, contract["fixture"]["expected_fixture_tests"])
        self.assertEqual(29, contract["fixture"]["expected_total_tests"])
        self.assertEqual("TODO", contract["readiness"]["status"])
        self.assertFalse(contract["readiness"]["credit_eligible"])
        self.assertFalse(contract["evidence_policy"]["credit_eligible"])
        self.assertFalse(contract["ioctl_boundary"]["registration_supported"])
        self.assertFalse(contract["ioctl_boundary"]["user_copy_reachable"])
        self.assertEqual(registry.READINESS_BLOCKERS,
                         tuple(contract["readiness"]["blockers"]))

    def test_checker_and_test_parse_as_python_3_6(self):
        for relative in (
                "scripts/ihk_device_registry_check.py",
                "scripts/tests/test_ihk_device_registry_check.py"):
            source = read_bytes(relative).decode("utf-8")
            try:
                ast.parse(source, filename=relative, feature_version=(3, 6))
            except TypeError:
                try:
                    ast.parse(source, filename=relative, feature_version=6)
                except TypeError:
                    ast.parse(source, filename=relative)

    def test_contract_is_canonical_and_print_contract_is_identical(self):
        decoded = json.loads(self.contract.decode("utf-8"))
        self.assertEqual(self.contract, registry.render_contract(decoded))
        output = subprocess.check_output(
            [sys.executable, "-E", "-s", registry.__file__,
             "--repo", REPO_ROOT, "--print-contract"],
            cwd=REPO_ROOT)
        self.assertEqual(self.contract, output)
        noncanonical = json.dumps(decoded).encode("utf-8")
        with self.assertRaisesRegex(registry.ContractError, "deterministic capture"):
            registry.check(REPO_ROOT, contract_override=noncanonical)

    def test_duplicate_contract_keys_are_rejected_before_byte_comparison(self):
        duplicate = self.contract.replace(
            b'{\n  "attachment_boundary": {',
            b'{\n  "schema_version": 1,\n  "attachment_boundary": {',
            1)
        with self.assertRaisesRegex(registry.ContractError, "duplicate JSON key"):
            registry.check(REPO_ROOT, contract_override=duplicate)

    def test_every_frozen_legacy_source_mutation_is_rejected(self):
        self.assertEqual(
            {"host_driver", "public_header", "linux_private_header", "smp_provider"},
            set(self.legacy))
        for source_id in sorted(self.legacy):
            with self.subTest(source_id=source_id):
                source = self.legacy[source_id]
                mutated = source[:-1] + bytes(bytearray([source[-1] ^ 1]))
                with self.assertRaisesRegex(registry.ContractError, "source lock mismatch"):
                    registry.derive_contract(
                        REPO_ROOT, legacy_overrides={source_id: mutated})
        mutated = self.reference_inventory[:-1] + b" "
        with self.assertRaisesRegex(registry.ContractError, "reference inventory lock"):
            registry.derive_contract(
                REPO_ROOT, reference_inventory_override=mutated)

    def test_legacy_registration_oracle_cannot_be_resigned_weaker(self):
        self.rejected_legacy_semantic_mutation(
            "host_driver", b"#define DEV_MAX_MINOR 64",
            b"#define DEV_MAX_MINOR 63")
        mutations = (
            (b"spin_lock_irqsave(&dev_data_lock, flags);",
             b"spin_lock(&dev_data_lock);"),
            (b"if (minor + 1 == os_max_minor)",
             b"if (minor + 1 == dev_max_minor)"),
            (b"if (cdev_add(&data->cdev, data->dev_num, 1) < 0) {\n"
             b"\t\tdev_data[minor] = NULL;\n\t\treturn NULL;\n\t}",
             b"if (cdev_add(&data->cdev, data->dev_num, 1) < 0) {\n"
             b"\t\tkfree(data);\n\t\tdev_data[minor] = NULL;\n\t\treturn NULL;\n\t}"),
        )
        for old, new in mutations:
            with self.subTest(old=old):
                self.rejected_legacy_function_mutation(
                    "host_driver", b"ihk_device_t ihk_register_device(", old, new)

    def test_legacy_open_release_and_unregister_oracle_cannot_drift(self):
        mutations = (
            (b"atomic_inc(&data->refcount);", b"atomic_dec(&data->refcount);"),
            (b"atomic_cmpxchg(&data->refcount, 0, 1)",
             b"atomic_cmpxchg(&data->refcount, 1, 2)"),
            (b"if (__destroy_all_os(data) != 0)",
             b"if (__destroy_all_os(data) == 0)"),
            (b"cdev_del(&data->cdev);", b"/* cdev removal omitted */"),
        )
        for old, new in mutations:
            with self.subTest(old=old):
                signature = (b"static int ihk_host_device_open("
                             if old.startswith(b"atomic_")
                             else b"int ihk_unregister_device(")
                self.rejected_legacy_function_mutation(
                    "host_driver", signature, old, new)
        self.rejected_legacy_function_mutation(
            "host_driver", b"int ihk_unregister_device(",
            b"unsigned long flags;",
            b"unsigned long flags;\n\ttry_module_get(NULL);")

    def test_legacy_separate_provider_and_unchecked_unload_are_bound(self):
        self.rejected_legacy_semantic_mutation(
            "smp_provider",
            b".ops = &smp_ihk_device_ops,",
            b".ops = NULL,")
        self.rejected_legacy_semantic_mutation(
            "smp_provider",
            b"ihk_unregister_device(builtin_data.ihk_dev);",
            b"/* unchecked unregister omitted */")

    def test_reserve_generation_retirement_and_publication_are_function_local(self):
        mutations = (
            (b"for minor in 0..DEVICE_CAPACITY {",
             b"for minor in (0..DEVICE_CAPACITY).rev() {"),
            (b"if old_generation == MAX_GENERATION {",
             b"if old_generation > MAX_GENERATION {"),
            (b"let next_generation = old_generation + 1;",
             b"let next_generation = old_generation;"),
            (b"current,\n                                publishing,",
             b"current,\n                                retired,"),
        )
        for old, new in mutations:
            with self.subTest(old=old):
                self.rejected_rust_semantic_mutation(old, new)

    def test_publish_abort_and_live_resolution_are_function_local(self):
        mutations = (
            (b"let live = (self.publishing & !PHASE_MASK) | PHASE_LIVE;",
             b"let live = self.publishing;"),
            (b"self.publishing,\n                vacant,",
             b"vacant,\n                self.publishing,"),
            (b"PHASE_LIVE => Ok(DeviceHandle {",
             b"PHASE_PUBLISHING => Ok(DeviceHandle {"),
        )
        for old, new in mutations:
            with self.subTest(old=old):
                self.rejected_rust_semantic_mutation(old, new)

    def test_open_sharing_and_overflow_are_checked_before_add(self):
        mutations = (
            (b"share_policy(current) == SharePolicy::Exclusive && references != 0",
             b"share_policy(current) == SharePolicy::Shared && references != 0"),
            (b"if references == MAX_REFERENCES {",
             b"if references > MAX_REFERENCES {"),
            (b"current + PROVIDER_REFERENCE_ONE,",
             b"current + OS_REFERENCE_ONE,"),
        )
        for old, new in mutations:
            with self.subTest(old=old):
                self.rejected_rust_semantic_mutation(old, new)

    def test_os_reference_overflow_and_release_are_function_local(self):
        mutations = (
            (b"if os_references(current) == MAX_REFERENCES {",
             b"if os_references(current) > MAX_REFERENCES {"),
            (b"current + OS_REFERENCE_ONE,",
             b"current + PROVIDER_REFERENCE_ONE,"),
            (b"!matches!(phase(current), PHASE_LIVE | PHASE_UNPUBLISHING)",
             b"phase(current) != PHASE_LIVE"),
            (b"current - OS_REFERENCE_ONE,",
             b"current - PROVIDER_REFERENCE_ONE,"),
        )
        for old, new in mutations:
            with self.subTest(old=old):
                self.rejected_rust_semantic_mutation(old, new)

    def test_unregister_exclusion_commit_and_rollback_are_function_local(self):
        mutations = (
            (b"if provider_references(current) != 0 {",
             b"if provider_references(current) == 0 {"),
            (b"provider_references(current) != 0 || os_references(current) != 0",
             b"provider_references(current) != 0 && os_references(current) != 0"),
            (b"let live = (current & !PHASE_MASK) | PHASE_LIVE;",
             b"let live = current;"),
            (b"current - PROVIDER_REFERENCE_ONE,",
             b"current + PROVIDER_REFERENCE_ONE,"),
        )
        for old, new in mutations:
            with self.subTest(old=old):
                self.rejected_rust_semantic_mutation(old, new)

    def test_drop_cleanup_stale_handles_and_identity_cannot_be_resigned_away(self):
        mutations = (
            (b"let _ = self.abort_inner();", b"let _ = Ok::<(), ()>(());"),
            (b"self.registry.release_open(self.handle);", b"return;"),
            (b"self.registry.release_os(self.handle);", b"return;"),
            (b"let _ = self.rollback_inner();", b"let _ = Ok::<(), ()>(());"),
            (b"handle.registry_id != self.registry_id || handle.generation == 0",
             b"handle.registry_id == self.registry_id || handle.generation == 0"),
            (b"generation(current) != handle.generation",
             b"generation(current) == handle.generation"),
            (b".checked_add(1)", b".wrapping_add(1)"),
        )
        for old, new in mutations:
            with self.subTest(old=old):
                self.rejected_rust_semantic_mutation(old, new)

    def test_slot_invariants_and_errno_mapping_cannot_drift(self):
        mutations = (
            (b"PHASE_UNPUBLISHING if generation != 0 && provider_references == 0",
             b"PHASE_UNPUBLISHING if generation != 0"),
            (b"Self::Capacity => -ENOMEM,", b"Self::Capacity => -EBUSY,"),
            (b"Self::StaleHandle => -ESTALE,", b"Self::StaleHandle => -ENOENT,"),
        )
        for old, new in mutations:
            with self.subTest(old=old):
                self.rejected_rust_semantic_mutation(old, new)

    def test_allocation_ffi_unsafe_and_textual_escape_hatches_are_rejected(self):
        for suffix in (
                b'\nextern "C" { fn legacy_register(); }\n',
                b'\nextern { fn legacy_register(); }\n',
                b'\nextern "system" { fn legacy_register(); }\n',
                b"\nfn allocate() { let _ = Box::new(1); }\n",
                b"\nunsafe fn bypass_registry() {}\n",
                b'\ninclude!("unreviewed.rs");\n',
                b'\ninclude ! ("unreviewed.rs");\n',
                b'\ninclude /* split token */ ! ("unreviewed.rs");\n',
                b'\ninclude_bytes ! ("unreviewed.bin");\n',
                b'\nasm ! ("nop");\n',
                b'\nglobal_asm /* split token */ ! ("nop");\n'):
            with self.subTest(suffix=suffix):
                with self.assertRaisesRegex(registry.ContractError, "forbidden"):
                    marker = b"#[cfg(test)]\nmod tests {"
                    mutated = self.rust.replace(marker, suffix + marker, 1)
                    registry.derive_contract(REPO_ROOT, rust_override=mutated)

    def test_forbidden_words_inside_rust_comments_and_strings_are_ignored(self):
        marker = b"#[cfg(test)]\nmod tests {"
        decoys = (
            b'\nconst DECOY: &str = "extern include ! global_asm ! unsafe";\n'
            b'const RAW_DECOY: &str = r###"device_registry::DeviceRegistry '
            b'extern { include ! }"###;\n'
            b'// extern "C" { include ! ("comment.rs"); }\n'
            b'/* outer device_registry /* nested extern */ global_asm ! */\n'
        )
        mutated = self.rust.replace(marker, decoys + marker, 1)
        registry._validate_rust(mutated)

    def test_fixture_and_exact_test_inventory_cannot_drift(self):
        old = b"simultaneous_publishers_get_unique_generation_tagged_slots"
        self.assertIn(old, self.fixture)
        mutated = self.fixture.replace(old, b"weakened_publishers_test", 1)
        with self.assertRaisesRegex(registry.ContractError, "fixture test closure"):
            registry.derive_contract(REPO_ROOT, fixture_override=mutated)
        old = b"errno_mapping_and_minor_bounds_fail_closed"
        self.assertIn(old, self.rust)
        mutated = self.rust.replace(old, b"weakened_errno_test", 1)
        with self.assertRaisesRegex(registry.ContractError, "in-file test closure"):
            registry.derive_contract(REPO_ROOT, rust_override=mutated)

    def test_crate_root_boundary_is_hash_bound_and_alias_resistant(self):
        contract = registry.derive_contract(REPO_ROOT)
        boundary = contract["attachment_boundary"]
        self.assertEqual(sha256(self.crate_root), boundary["crate_root_sha256"])
        self.assertEqual(len(self.crate_root), boundary["crate_root_size"])
        self.assertFalse(boundary["crate_root_constructs_registry_instance"])
        alias = self.crate_root + b"\nuse self::device_registry as hidden_registry;\n"
        with self.assertRaisesRegex(registry.ContractError, "unexpectedly uses"):
            registry.derive_contract(REPO_ROOT, crate_root_override=alias)
        string_comment_evasion = (
            self.crate_root
            + b'\nconst MASK: &str = "//"; fn hidden_registry_use() {'
              b' let _ = device_registry::DEVICE_CAPACITY; }\n'
        )
        with self.assertRaisesRegex(registry.ContractError, "unexpectedly uses"):
            registry.derive_contract(
                REPO_ROOT, crate_root_override=string_comment_evasion
            )
        harmless_decoys = (
            self.crate_root
            + b'\nconst DEVICE_REGISTRY_DOC: &str = "device_registry::DeviceRegistry";\n'
              b'const RAW_DEVICE_REGISTRY_DOC: &str = r#"device_registry"#;\n'
              b'// device_registry::DeviceRegistry\n'
              b'/* device_registry /* nested DeviceRegistry */ device_registry */\n'
        )
        decoy_contract = registry.derive_contract(
            REPO_ROOT, crate_root_override=harmless_decoys
        )
        self.assertFalse(
            decoy_contract["attachment_boundary"][
                "crate_root_constructs_registry_instance"
            ]
        )
        harmless_drift = self.crate_root + b"\n// source identity drift\n"
        with self.assertRaisesRegex(registry.ContractError, "deterministic capture"):
            registry.check(REPO_ROOT, crate_root_override=harmless_drift)

    def test_ioctl_boundary_is_hash_bound_and_remains_negative(self):
        contract = registry.derive_contract(REPO_ROOT)
        boundary = contract["ioctl_boundary"]
        self.assertEqual(sha256(self.ioctl_contract), boundary["contract_sha256"])
        self.assertEqual(len(self.ioctl_contract), boundary["contract_size"])
        decoded = json.loads(self.ioctl_contract.decode("utf-8"))
        decoded["implementation"]["registration_supported"] = True
        mutated = registry.render_contract(decoded)
        with self.assertRaisesRegex(registry.ContractError, "registration support"):
            registry.derive_contract(REPO_ROOT, ioctl_contract_override=mutated)
        decoded = json.loads(self.ioctl_contract.decode("utf-8"))
        decoded["independent_device_registry_test"] = True
        mutated = registry.render_contract(decoded)
        with self.assertRaisesRegex(registry.ContractError, "deterministic capture"):
            registry.check(REPO_ROOT, ioctl_contract_override=mutated)

    def test_contract_cannot_self_attest_credit_runtime_or_adapter_completion(self):
        for path, key, value in (
                (("readiness",), "status", "PASS"),
                (("readiness",), "credit_eligible", True),
                (("evidence_policy",), "credit_eligible", True),
                (("evidence_policy",), "linux_adapter_validated", True),
                (("evidence_policy",), "exact_kbuild_validated", True),
                (("evidence_policy",), "rocky_runtime_validated", True)):
            with self.subTest(path=path, key=key):
                decoded = json.loads(self.contract.decode("utf-8"))
                target = decoded
                for component in path:
                    target = target[component]
                target[key] = value
                with self.assertRaisesRegex(registry.ContractError, "deterministic capture"):
                    registry.check(
                        REPO_ROOT, contract_override=registry.render_contract(decoded))

    def test_exact_fixture_compiles_and_runs_when_rustc_is_available(self):
        configured = os.environ.get("MCKERNEL_RUSTC_1_92")
        rustc = configured or shutil.which("rustc")
        if not rustc:
            self.skipTest("rustc is not available")
        version = subprocess.check_output([rustc, "--version"]).decode("utf-8")
        if configured:
            self.assertIn("rustc 1.92.0", version)
        with tempfile.TemporaryDirectory(prefix="ihk-device-registry-rust-") as temporary:
            library = os.path.join(temporary, "device-registry.rlib")
            tests = os.path.join(temporary, "device-registry-tests")
            subprocess.check_call(
                [rustc, "--edition=2021", "-Dwarnings", "--crate-type", "lib",
                 registry.FIXTURE_PATH, "-o", library], cwd=REPO_ROOT)
            subprocess.check_call(
                [rustc, "--edition=2021", "-Dwarnings", "--test",
                 registry.FIXTURE_PATH, "-o", tests], cwd=REPO_ROOT)
            listed = subprocess.check_output([tests, "--list"], cwd=REPO_ROOT)
            test_lines = [line for line in listed.decode("utf-8").splitlines()
                          if line.endswith(": test")]
            self.assertEqual(29, len(test_lines))
            subprocess.check_call([tests, "--test-threads=1"], cwd=REPO_ROOT)


if __name__ == "__main__":
    unittest.main()
