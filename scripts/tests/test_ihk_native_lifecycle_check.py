import ast
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest import mock


REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts import ihk_native_lifecycle_check as lifecycle


def reviewed_artifact_symbols(provider_symbols):
    symbols = set(provider_symbols)
    for provider_symbol in provider_symbols:
        symbols.update(
            {
                f"__ksymtab_{provider_symbol}",
                f"__kstrtab_{provider_symbol}",
                f"__kstrtabns_{provider_symbol}",
            }
        )
    symbols.update({"__ksymtab_gpl", "__ksymtab_strings"})
    return symbols


class IhkNativeLifecycleCheckTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory(prefix="ihk-native-lifecycle-")
        self.repo = Path(self.temporary.name) / "repo"
        contract_path = REPO_ROOT / lifecycle.DEFAULT_CONTRACT
        with contract_path.open("r", encoding="utf-8") as stream:
            self.contract = json.load(stream)
        relative_paths = {
            lifecycle.DEFAULT_CONTRACT.as_posix(),
            self.contract["production_source"],
            self.contract["kconfig"]["path"],
            self.contract["kbuild"]["path"],
            self.contract["stage_manifest"],
            self.contract["reference_inventory"],
        }
        relative_paths.update(item["path"] for item in self.contract["crate_modules"])
        for item in self.contract["support_sources"]:
            relative_paths.add(item["path"])
            relative_paths.add(item["contract_path"])
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

    def test_repository_contract_passes(self) -> None:
        summary = lifecycle.validate_repository(REPO_ROOT)
        self.assertEqual("IHK-001", summary["gate_id"])
        self.assertEqual("ihk", summary["module"])
        self.assertEqual("1.7.0rc4", summary["version"])
        self.assertEqual(0, summary["parameters"])
        self.assertEqual(0, summary["dependencies"])
        self.assertEqual(4, summary["transitive_module_count"])
        self.assertEqual(6, summary["support_sources"])
        self.assertTrue(summary["provider_lease_validated"])
        self.assertEqual(
            [
                "ihk_provider_lifecycle_v1",
                "ihk_smp_provider_attach_v1",
                "ihk_smp_provider_detach_v1",
                "ihk_smp_provider_attach_v2",
                "ihk_smp_provider_detach_v2",
                "ihk_smp_provider_open_v1",
                "ihk_smp_provider_close_v1",
            ],
            summary["provider_symbols"],
        )

    def test_ihk_queue_module_edge_is_required(self) -> None:
        self.mutate_text(
            self.contract["production_source"],
            "mod ikc_queue;",
            "mod missing_queue;",
        )
        with self.assertRaisesRegex(lifecycle.ValidationError, "module edge"):
            lifecycle.validate_repository(self.repo)

    def test_ihk_master_module_edge_is_required(self) -> None:
        self.mutate_text(
            self.contract["production_source"],
            "mod ikc_master;",
            "mod missing_master;",
        )
        with self.assertRaisesRegex(lifecycle.ValidationError, "module edge"):
            lifecycle.validate_repository(self.repo)

    def test_device_registry_module_edge_is_required(self) -> None:
        self.mutate_text(
            self.contract["production_source"],
            "mod device_registry;",
            "mod missing_device_registry;",
        )
        with self.assertRaisesRegex(lifecycle.ValidationError, "module edge"):
            lifecycle.validate_repository(self.repo)

    def test_ihk_ioctl_module_edge_is_required(self) -> None:
        self.mutate_text(
            self.contract["production_source"],
            "mod ihk_ioctl;",
            "mod missing_ioctl;",
        )
        with self.assertRaisesRegex(lifecycle.ValidationError, "module edge"):
            lifecycle.validate_repository(self.repo)

    def test_page_support_module_edges_are_required(self) -> None:
        for present, missing in (
            ("mod page_allocator;", "mod missing_page_allocator;"),
            ("mod page_owner_registry;", "mod missing_page_owner_registry;"),
        ):
            with self.subTest(edge=present):
                source = self.repo / self.contract["production_source"]
                original = source.read_text(encoding="utf-8")
                self.assertIn(present, original)
                source.write_text(original.replace(present, missing, 1), encoding="utf-8")
                with self.assertRaisesRegex(lifecycle.ValidationError, "module edge"):
                    lifecycle.validate_repository(self.repo)
                source.write_text(original, encoding="utf-8")

    def test_lifecycle_crate_root_digest_drift_is_rejected(self) -> None:
        source = self.repo / self.contract["production_source"]
        with source.open("a", encoding="utf-8") as stream:
            stream.write("// unbound lifecycle drift\n")
        with self.assertRaisesRegex(lifecycle.ValidationError, "crate-root digest"):
            lifecycle.validate_repository(self.repo)

    def test_queue_module_digest_drift_is_rejected(self) -> None:
        queue = self.repo / "host-kernel/native-rust/ikc_queue.rs"
        with queue.open("a", encoding="utf-8") as stream:
            stream.write("// unbound queue drift\n")
        with self.assertRaisesRegex(lifecycle.ValidationError, "module digest"):
            lifecycle.validate_repository(self.repo)

    def test_master_module_digest_drift_is_rejected(self) -> None:
        master = self.repo / "host-kernel/native-rust/ikc_master.rs"
        with master.open("a", encoding="utf-8") as stream:
            stream.write("// unbound master drift\n")
        with self.assertRaisesRegex(lifecycle.ValidationError, "module digest"):
            lifecycle.validate_repository(self.repo)

    def test_device_registry_module_digest_drift_is_rejected(self) -> None:
        registry = self.repo / "host-kernel/native-rust/device_registry.rs"
        with registry.open("a", encoding="utf-8") as stream:
            stream.write("// unbound device-registry drift\n")
        with self.assertRaisesRegex(lifecycle.ValidationError, "module digest"):
            lifecycle.validate_repository(self.repo)

    def test_stage_manifest_cannot_omit_queue_module(self) -> None:
        manifest_path = self.repo / self.contract["stage_manifest"]
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest["inputs"] = [
            item
            for item in manifest["inputs"]
            if item.get("destination") != "ikc_queue.rs"
        ]
        manifest_path.write_text(
            json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        with self.assertRaisesRegex(lifecycle.ValidationError, "omits IHK module"):
            lifecycle.validate_repository(self.repo)

    def test_lifecycle_checker_and_tests_parse_as_python_3_6(self) -> None:
        for path in (Path(lifecycle.__file__), Path(__file__)):
            source = path.read_text(encoding="utf-8")
            try:
                ast.parse(source, filename=str(path), feature_version=(3, 6))
            except TypeError:
                ast.parse(source, filename=str(path), feature_version=6)

    def test_stage_manifest_cannot_omit_master_module(self) -> None:
        manifest_path = self.repo / self.contract["stage_manifest"]
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest["inputs"] = [
            item
            for item in manifest["inputs"]
            if item.get("destination") != "ikc_master.rs"
        ]
        manifest_path.write_text(
            json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        with self.assertRaisesRegex(lifecycle.ValidationError, "omits IHK module"):
            lifecycle.validate_repository(self.repo)

    def test_stage_manifest_cannot_omit_device_registry(self) -> None:
        manifest_path = self.repo / self.contract["stage_manifest"]
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest["inputs"] = [
            item
            for item in manifest["inputs"]
            if item.get("destination") != "device_registry.rs"
        ]
        manifest_path.write_text(
            json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        with self.assertRaisesRegex(lifecycle.ValidationError, "omits IHK module"):
            lifecycle.validate_repository(self.repo)

    def test_parameter_surface_drift_is_rejected(self) -> None:
        self.mutate_text(
            self.contract["production_source"],
            "const IHK_PARAMETER_COUNT: usize = 0;",
            "const IHK_PARAMETER_COUNT: usize = 1;",
        )
        with self.assertRaisesRegex(lifecycle.ValidationError, "parameter count"):
            lifecycle.validate_repository(self.repo)

    def test_missing_loadable_version_modinfo_is_rejected(self) -> None:
        self.mutate_text(
            self.contract["production_source"],
            '*b"version=1.7.0rc4\\0"',
            '*b"release=1.7.0rc4\\0"',
        )
        with self.assertRaisesRegex(lifecycle.ValidationError, "version modinfo"):
            lifecycle.validate_repository(self.repo)

    def test_unreviewed_ffi_escape_hatch_is_rejected(self) -> None:
        source = self.repo / self.contract["production_source"]
        with source.open("a", encoding="utf-8") as stream:
            stream.write('extern "C" { fn legacy_ihk_init(); }\n')
        with self.assertRaisesRegex(
            lifecycle.ValidationError,
            "unreviewed C ABI boundary|forbidden boundary",
        ):
            lifecycle.validate_repository(self.repo)

    def test_core_kconfig_module_dependency_is_rejected(self) -> None:
        self.mutate_text(
            self.contract["kconfig"]["path"],
            '\ttristate "McKernel IHK core host module (Rust)"',
            '\ttristate "McKernel IHK core host module (Rust)"\n\tdepends on MCKERNEL_LEGACY_IHK',
        )
        with self.assertRaisesRegex(lifecycle.ValidationError, "shared native Rust Kconfig policy"):
            lifecycle.validate_repository(self.repo)

    def test_shared_kconfig_menu_modules_dependency_is_required(self) -> None:
        self.mutate_text(
            self.contract["kconfig"]["path"],
            "\tdepends on MODULES && m\n",
            "",
        )
        with self.assertRaisesRegex(lifecycle.ValidationError, "shared native Rust Kconfig policy"):
            lifecycle.validate_repository(self.repo)

    def test_shared_kconfig_hidden_edge_is_rejected(self) -> None:
        self.mutate_text(
            self.contract["kconfig"]["path"],
            "\nconfig MCKERNEL_IHK_RUST\n",
            "\nif UNREVIEWED\n\nconfig MCKERNEL_IHK_RUST\n",
        )
        with self.assertRaisesRegex(lifecycle.ValidationError, "shared native Rust Kconfig policy"):
            lifecycle.validate_repository(self.repo)

    def test_composite_ihk_kbuild_inputs_are_rejected(self) -> None:
        kbuild = self.repo / self.contract["kbuild"]["path"]
        with kbuild.open("a", encoding="utf-8") as stream:
            stream.write("ihk-y := legacy_ihk.o\n")
        with self.assertRaisesRegex(lifecycle.ValidationError, "shared native Rust Kbuild policy"):
            lifecycle.validate_repository(self.repo)

    def test_shared_kbuild_continued_comment_is_rejected(self) -> None:
        self.mutate_text(
            self.contract["kbuild"]["path"],
            "obj-$(CONFIG_MCKERNEL_IHK_RUST) += ihk.o\n",
            "# suppress provider mapping \\\n"
            "obj-$(CONFIG_MCKERNEL_IHK_RUST) += ihk.o\n",
        )
        with self.assertRaisesRegex(lifecycle.ValidationError, "shared native Rust Kbuild policy"):
            lifecycle.validate_repository(self.repo)

    def test_stage_manifest_dependency_drift_is_rejected(self) -> None:
        manifest_path = self.repo / self.contract["stage_manifest"]
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        ihk = next(item for item in manifest["modules"] if item["crate"] == "ihk")
        ihk["dependencies"] = ["legacy_ihk"]
        manifest_path.write_text(
            json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        with self.assertRaisesRegex(lifecycle.ValidationError, "dependency set"):
            lifecycle.validate_repository(self.repo)

    def test_support_source_drift_is_rejected(self) -> None:
        support = self.contract["support_sources"][1]
        self.mutate_text(
            support["path"],
            "pub(crate) const OS_CAPACITY: usize = 64;",
            "pub(crate) const OS_CAPACITY: usize = 63;",
        )
        with self.assertRaisesRegex(lifecycle.ValidationError, r"support_sources\[1\] digest"):
            lifecycle.validate_repository(self.repo)

    def test_page_support_source_drift_is_rejected(self) -> None:
        for index in (4, 5):
            with self.subTest(index=index):
                support = self.contract["support_sources"][index]
                source = self.repo / support["path"]
                original = source.read_text(encoding="utf-8")
                source.write_text(original + "// unbound page support drift\n", encoding="utf-8")
                with self.assertRaisesRegex(
                    lifecycle.ValidationError,
                    r"support_sources\[{0}\] digest".format(index),
                ):
                    lifecycle.validate_repository(self.repo)
                source.write_text(original, encoding="utf-8")

    def test_page_support_contract_cannot_claim_credit(self) -> None:
        for index in (4, 5):
            with self.subTest(index=index):
                support = self.contract["support_sources"][index]
                contract_path = self.repo / support["contract_path"]
                original = contract_path.read_text(encoding="utf-8")
                value = json.loads(original)
                value["evidence_policy"]["gate_credit_eligible"] = True
                contract_path.write_text(
                    json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8"
                )
                support["contract_sha256"] = lifecycle._sha256(contract_path)
                lifecycle_contract = self.repo / lifecycle.DEFAULT_CONTRACT
                lifecycle_contract.write_text(
                    json.dumps(self.contract, indent=2, sort_keys=True) + "\n",
                    encoding="utf-8",
                )
                with self.assertRaisesRegex(lifecycle.ValidationError, "claims evidence"):
                    lifecycle.validate_repository(self.repo)
                contract_path.write_text(original, encoding="utf-8")
                self.contract = json.loads(
                    (REPO_ROOT / lifecycle.DEFAULT_CONTRACT).read_text(encoding="utf-8")
                )
                lifecycle_contract.write_text(
                    json.dumps(self.contract, indent=2, sort_keys=True) + "\n",
                    encoding="utf-8",
                )

    def test_support_contract_cannot_claim_credit(self) -> None:
        support = self.contract["support_sources"][1]
        contract_path = self.repo / support["contract_path"]
        value = json.loads(contract_path.read_text(encoding="utf-8"))
        value["readiness"] = {"blockers": [], "credit_eligible": True, "status": "PASS"}
        contract_path.write_text(
            json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        support["contract_sha256"] = lifecycle._sha256(contract_path)
        lifecycle_contract = self.repo / lifecycle.DEFAULT_CONTRACT
        lifecycle_contract.write_text(
            json.dumps(self.contract, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        with self.assertRaisesRegex(lifecycle.ValidationError, "TODO and credit-ineligible"):
            lifecycle.validate_repository(self.repo)

    def test_device_registry_support_contract_binds_source_and_no_credit(self) -> None:
        support = self.contract["support_sources"][2]
        contract_path = self.repo / support["contract_path"]
        original = contract_path.read_text(encoding="utf-8")
        for mutation, error in (
            (("production_source", "sha256", "0" * 64), "does not bind the staged source"),
            (("evidence_policy", "linux_adapter_validated", True), "claims evidence or credit"),
            (("readiness", "status", "PASS"), "must remain TODO and blocked"),
        ):
            with self.subTest(field=mutation[1]):
                value = json.loads(original)
                value[mutation[0]][mutation[1]] = mutation[2]
                contract_path.write_text(
                    json.dumps(value, indent=2, sort_keys=True) + "\n",
                    encoding="utf-8",
                )
                support["contract_sha256"] = lifecycle._sha256(contract_path)
                lifecycle_contract = self.repo / lifecycle.DEFAULT_CONTRACT
                lifecycle_contract.write_text(
                    json.dumps(self.contract, indent=2, sort_keys=True) + "\n",
                    encoding="utf-8",
                )
                with self.assertRaisesRegex(lifecycle.ValidationError, error):
                    lifecycle.validate_repository(self.repo)
                contract_path.write_text(original, encoding="utf-8")

    def test_device_registry_support_contract_cannot_hide_production_instance(self) -> None:
        support = self.contract["support_sources"][2]
        contract_path = self.repo / support["contract_path"]
        value = json.loads(contract_path.read_text(encoding="utf-8"))
        value["attachment_boundary"]["crate_root_constructs_registry_instance"] = False
        contract_path.write_text(
            json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        support["contract_sha256"] = lifecycle._sha256(contract_path)
        lifecycle_contract = self.repo / lifecycle.DEFAULT_CONTRACT
        lifecycle_contract.write_text(
            json.dumps(self.contract, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        with self.assertRaisesRegex(lifecycle.ValidationError, "crate-root attachment"):
            lifecycle.validate_repository(self.repo)

    def test_device_registry_support_contract_cannot_weaken_open_receipts(self) -> None:
        support = self.contract["support_sources"][2]
        contract_path = self.repo / support["contract_path"]
        lifecycle_contract = self.repo / lifecycle.DEFAULT_CONTRACT
        original_device = contract_path.read_text(encoding="utf-8")
        mutations = (
            ("close_symbol", "ihk_smp_provider_detach_v1"),
            ("concurrent_shared_receipts", False),
            ("raw_pointer", True),
            ("source_validated", False),
        )
        for field, replacement in mutations:
            with self.subTest(field=field):
                value = json.loads(original_device)
                value["provider_lease_boundary"]["open_close"][field] = replacement
                contract_path.write_text(
                    json.dumps(value, indent=2, sort_keys=True) + "\n",
                    encoding="utf-8",
                )
                self.contract["support_sources"][2]["contract_sha256"] = (
                    lifecycle._sha256(contract_path)
                )
                lifecycle_contract.write_text(
                    json.dumps(self.contract, indent=2, sort_keys=True) + "\n",
                    encoding="utf-8",
                )
                with self.assertRaisesRegex(
                    lifecycle.ValidationError,
                    "provider-lease boundary differs or overclaims readiness",
                ):
                    lifecycle.validate_repository(self.repo)
                contract_path.write_text(original_device, encoding="utf-8")

    def test_device_registry_attachment_cannot_omit_open_exports(self) -> None:
        support = self.contract["support_sources"][2]
        contract_path = self.repo / support["contract_path"]
        value = json.loads(contract_path.read_text(encoding="utf-8"))
        value["attachment_boundary"]["provider_lease_exports"].remove(
            "ihk_smp_provider_close_v1"
        )
        contract_path.write_text(
            json.dumps(value, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        self.contract["support_sources"][2]["contract_sha256"] = lifecycle._sha256(
            contract_path
        )
        lifecycle_contract = self.repo / lifecycle.DEFAULT_CONTRACT
        lifecycle_contract.write_text(
            json.dumps(self.contract, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        with self.assertRaisesRegex(lifecycle.ValidationError, "crate-root attachment"):
            lifecycle.validate_repository(self.repo)

    def test_provider_lease_contract_cannot_claim_runtime_or_credit(self) -> None:
        contract_path = self.repo / lifecycle.DEFAULT_CONTRACT
        for field in ("rocky_runtime_validated", "credit_eligible"):
            with self.subTest(field=field):
                value = json.loads(contract_path.read_text(encoding="utf-8"))
                value["provider_lease"][field] = True
                contract_path.write_text(
                    json.dumps(value, indent=2, sort_keys=True) + "\n",
                    encoding="utf-8",
                )
                with self.assertRaisesRegex(
                    lifecycle.ValidationError,
                    "provider-lease contract differs or overclaims readiness",
                ):
                    lifecycle.validate_repository(self.repo)
                shutil.copyfile(REPO_ROOT / lifecycle.DEFAULT_CONTRACT, contract_path)

    def test_provider_open_contract_remains_scalar_and_noncrediting(self) -> None:
        contract_path = self.repo / lifecycle.DEFAULT_CONTRACT
        mutations = (
            ("rocky_runtime_validated", True),
            ("credit_eligible", True),
            ("device_node_reachable", True),
            ("duplicate_close_detectable_while_other_references_exist", True),
            ("file_operations_reachable", True),
            ("raw_pointer", True),
            ("rust_layout", True),
            ("multiple_shared_opens", False),
            ("trusted_noncopy_owner_balance_required", False),
            ("exactly_once_close_owner", "untracked-scalar-copy"),
        )
        original = contract_path.read_text(encoding="utf-8")
        for field, replacement in mutations:
            with self.subTest(field=field):
                value = json.loads(original)
                value["provider_lease"]["open_lease"][field] = replacement
                contract_path.write_text(
                    json.dumps(value, indent=2, sort_keys=True) + "\n",
                    encoding="utf-8",
                )
                with self.assertRaisesRegex(
                    lifecycle.ValidationError,
                    "provider-lease contract differs or overclaims readiness",
                ):
                    lifecycle.validate_repository(self.repo)
                contract_path.write_text(original, encoding="utf-8")

    def test_provider_lease_symbols_and_signatures_are_exact(self) -> None:
        mutations = (
            (
                '#[export_name = "ihk_smp_provider_attach_v1"]',
                '#[export_name = "ihk_smp_provider_attach_v2"]',
            ),
            (
                'pub extern "C" fn ihk_smp_provider_attach_v1() -> i64 {',
                'pub extern "C" fn ihk_smp_provider_attach_v1(minor: u32) -> i64 {',
            ),
            (
                'pub extern "C" fn ihk_smp_provider_detach_v1(token: i64) {',
                'pub extern "C" fn ihk_smp_provider_detach_v1(token: u64) {',
            ),
            (
                'pub extern "C" fn ihk_smp_provider_open_v1(minor: u32) -> i64 {',
                'pub extern "C" fn ihk_smp_provider_open_v1(minor: *const u32) -> i64 {',
            ),
            (
                'pub extern "C" fn ihk_smp_provider_close_v1(receipt: i64) {',
                'pub extern "C" fn ihk_smp_provider_close_v1(receipt: u64) {',
            ),
        )
        source = self.repo / self.contract["production_source"]
        original = source.read_text(encoding="utf-8")
        for old, new in mutations:
            with self.subTest(old=old):
                self.assertIn(old, original)
                source.write_text(original.replace(old, new, 1), encoding="utf-8")
                with self.assertRaisesRegex(
                    lifecycle.ValidationError,
                    "exact reviewed boundary",
                ):
                    lifecycle.validate_repository(self.repo)
                source.write_text(original, encoding="utf-8")

    def test_provider_lease_export_namespace_and_pointer_are_exact(self) -> None:
        source = self.repo / self.contract["production_source"]
        original = source.read_text(encoding="utf-8")
        for old, new, error in (
            (
                'namespace: *b"MCKERNEL_IHK_V1\\0",',
                'namespace: *b"MCKERNEL_BAD_V1\\0",',
                "import namespace",
            ),
            (
                "symbol: ihk_smp_provider_attach_v1 as *const () as *const u8,",
                "symbol: core::ptr::null(),",
                "exact reviewed boundary",
            ),
            (
                "symbol: ihk_smp_provider_open_v1 as *const () as *const u8,",
                "symbol: ihk_smp_provider_close_v1 as *const () as *const u8,",
                "exact reviewed boundary",
            ),
        ):
            with self.subTest(old=old):
                self.assertIn(old, original)
                source.write_text(original.replace(old, new, 1), encoding="utf-8")
                with self.assertRaisesRegex(lifecycle.ValidationError, error):
                    lifecycle.validate_repository(self.repo)
                source.write_text(original, encoding="utf-8")

    def test_provider_open_acquire_and_fail_stop_close_are_exact(self) -> None:
        source = self.repo / self.contract["production_source"]
        original = source.read_text(encoding="utf-8")
        mutations = (
            (
                "IHK_DEVICE_REGISTRY.acquire_open_token(minor as usize)",
                "IHK_DEVICE_REGISTRY.encode_provider_token(handle)",
                "exact reviewed boundary",
            ),
            (
                '''    let receipt = match IHK_DEVICE_REGISTRY.acquire_open_token(minor as usize) {
        Ok(receipt) => receipt,
        Err(error) => {
            return error.errno() as i64;
        }
    };''',
                '''    let receipt = match IHK_DEVICE_REGISTRY.acquire_open_token(minor as usize) {
        Ok(receipt) => receipt,
        Err(_error) => {
            return 1;
        }
    };''',
                "acquire-or-negative-errno ordering",
            ),
            (
                "let _ = IHK_DEVICE_REGISTRY.release_owned_open_token(receipt);",
                "let _ = IHK_DEVICE_REGISTRY.decode_provider_token(receipt);",
                "exact reviewed boundary",
            ),
            (
                '''    let _ = IHK_DEVICE_REGISTRY.release_owned_open_token(receipt);
    pr_info!("provider_open=release status=complete minor=0\\n");''',
                '''    pr_info!("provider_open=release status=complete minor=0\\n");
    let _ = IHK_DEVICE_REGISTRY.release_owned_open_token(receipt);''',
                "close-before-success ordering",
            ),
        )
        for old, new, error in mutations:
            with self.subTest(old=old):
                self.assertIn(old, original)
                mutated = original.replace(old, new, 1)
                with self.assertRaisesRegex(lifecycle.ValidationError, error):
                    lifecycle._validate_rust_source(mutated, self.contract)

    def test_provider_open_sites_require_distinct_immediate_safety_annotations(self) -> None:
        source = (self.repo / self.contract["production_source"]).read_text(
            encoding="utf-8"
        )
        mutations = (
            (
                lifecycle.EXPECTED_PROVIDER_OPEN_FFI_SITE,
                '#[export_name = "ihk_smp_provider_open_v1"]\n'
                'pub extern "C" fn ihk_smp_provider_open_v1(minor: u32) -> i64 {',
            ),
            (
                lifecycle.EXPECTED_PROVIDER_CLOSE_FFI_SITE,
                '#[export_name = "ihk_smp_provider_close_v1"]\n'
                'pub extern "C" fn ihk_smp_provider_close_v1(receipt: i64) {',
            ),
            (
                lifecycle.EXPECTED_PROVIDER_CLOSE_FFI_SITE,
                '#[export_name = "ihk_smp_provider_close_v1"]\n'
                "// SAFETY: This exported C ABI carries only a u32 argument and i64 result;\n"
                "// every expected failure becomes a negative errno and no unwind may cross it.\n"
                'pub extern "C" fn ihk_smp_provider_close_v1(receipt: i64) {',
            ),
            (
                lifecycle.EXPECTED_PROVIDER_OPEN_FFI_SITE,
                "// SAFETY: This exported C ABI carries only a u32 argument and i64 result;\n"
                "// every expected failure becomes a negative errno and no unwind may cross it.\n"
                '#[export_name = "ihk_smp_provider_open_v1"]\n'
                'pub extern "C" fn ihk_smp_provider_open_v1(minor: u32) -> i64 {',
            ),
        )
        for old, new in mutations:
            with self.subTest(replacement=new):
                self.assertIn(old, source)
                with self.assertRaisesRegex(
                    lifecycle.ValidationError,
                    "exact reviewed boundary",
                ):
                    lifecycle._validate_rust_source(
                        source.replace(old, new, 1), self.contract
                    )

    def test_provider_open_boundary_rejects_local_unsafe_receipt_storage(self) -> None:
        source = (self.repo / self.contract["production_source"]).read_text(
            encoding="utf-8"
        )
        injected = source.replace(
            "use core::sync::atomic::{AtomicPtr, Ordering};",
            "use core::cell::UnsafeCell;\n"
            "use core::mem::MaybeUninit;\n"
            "use core::sync::atomic::{AtomicPtr, Ordering};",
            1,
        )
        with self.assertRaisesRegex(
            lifecycle.ValidationError,
            "stateless scalar adapter",
        ):
            lifecycle._validate_rust_source(injected, self.contract)

    def test_provider_open_receipt_cannot_be_logged(self) -> None:
        source = (self.repo / self.contract["production_source"]).read_text(
            encoding="utf-8"
        )
        needle = 'pr_info!("provider_open=acquire status=live minor=0\\n");'
        replacement = 'pr_info!("provider_open=acquire receipt={}\\n", receipt);'
        self.assertIn(needle, source)
        with self.assertRaisesRegex(
            lifecycle.ValidationError,
            "exact reviewed boundary|must not disclose opaque",
        ):
            lifecycle._validate_rust_source(
                source.replace(needle, replacement, 1), self.contract
            )

    def test_provider_registry_singleton_and_unload_check_are_exact(self) -> None:
        source = self.repo / self.contract["production_source"]
        original = source.read_text(encoding="utf-8")
        for old, new in (
            (
                "use self::device_registry::{IHK_DEVICE_REGISTRY, SharePolicy};",
                "use self::device_registry::MISSING_DEVICE_REGISTRY;",
            ),
            (
                "match IHK_DEVICE_REGISTRY.active_count() {",
                "match Ok(0) {",
            ),
        ):
            with self.subTest(old=old):
                source.write_text(original.replace(old, new, 1), encoding="utf-8")
                with self.assertRaisesRegex(
                    lifecycle.ValidationError,
                    "exact reviewed boundary",
                ):
                    lifecycle.validate_repository(self.repo)
                source.write_text(original, encoding="utf-8")

    def test_provider_lease_token_cannot_be_logged(self) -> None:
        source = self.repo / self.contract["production_source"]
        original = source.read_text(encoding="utf-8")
        needle = 'pr_info!("provider_lease=attach status=live minor=0\\n");'
        replacement = 'pr_info!("provider_lease=attach token={}\\n", token);'
        self.assertIn(needle, original)
        source.write_text(original.replace(needle, replacement, 1), encoding="utf-8")
        with self.assertRaisesRegex(
            lifecycle.ValidationError,
            "exact reviewed boundary|must not disclose opaque tokens",
        ):
            lifecycle.validate_repository(self.repo)

    def test_commented_detach_body_cannot_authorize_a_noop_export(self) -> None:
        source = (self.repo / self.contract["production_source"]).read_text(
            encoding="utf-8"
        )
        old = '''    let handle = IHK_DEVICE_REGISTRY.retire_owned_provider_token(token);\n    pr_info!(\n        "provider_lease=detach status=vacant minor={} generation={}\\n",\n        handle.minor(),\n        handle.generation(),\n    );'''
        new = '''    /*\n+    let handle = IHK_DEVICE_REGISTRY.retire_owned_provider_token(token);\n+    pr_info!(\n+        "provider_lease=detach status=vacant minor={} generation={}\\n",\n+        handle.minor(),\n+        handle.generation(),\n+    );\n+    */'''
        self.assertIn(old, source)
        with self.assertRaisesRegex(
            lifecycle.ValidationError, "exact reviewed boundary"
        ):
            lifecycle._validate_rust_source(
                source.replace(old, new, 1), self.contract
            )

    def test_ioctl_dispatch_registration_overclaim_is_rejected(self) -> None:
        support = self.contract["support_sources"][3]
        contract_path = self.repo / support["contract_path"]
        value = json.loads(contract_path.read_text(encoding="utf-8"))
        value["implementation"]["registration_supported"] = True
        contract_path.write_text(
            json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        support["contract_sha256"] = lifecycle._sha256(contract_path)
        lifecycle_contract = self.repo / lifecycle.DEFAULT_CONTRACT
        lifecycle_contract.write_text(
            json.dumps(self.contract, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        with self.assertRaisesRegex(
                lifecycle.ValidationError,
                "different negative ioctl boundary|overclaims device registration"):
            lifecycle.validate_repository(self.repo)

    def test_reference_parameter_oracle_drift_is_rejected(self) -> None:
        inventory_path = self.repo / self.contract["reference_inventory"]
        inventory = json.loads(inventory_path.read_text(encoding="utf-8"))
        inventory["source_capture"]["modules"]["ihk"]["source_module_parameters"] = [
            {"name": "unexpected"}
        ]
        inventory_path.write_text(
            json.dumps(inventory, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        with self.assertRaisesRegex(lifecycle.ValidationError, "reference inventory parameter"):
            lifecycle.validate_repository(self.repo)

    def test_built_artifact_contract_checks_modinfo_and_logs(self) -> None:
        module = self.repo / "ihk.ko"
        module.write_bytes(
            b"lifecycle=load\0provider_lease=attach\0provider_lease=detach\0"
            b"provider_open=acquire\0provider_open=release\0"
            b"provider_registry=empty\0lifecycle=unload\0MCKERNEL_IHK_V1\0"
        )
        summary = lifecycle.validate_repository(REPO_ROOT)
        artifact_symbols = reviewed_artifact_symbols(summary["provider_symbols"])
        values = {
            "name": "ihk",
            "version": "1.7.0rc4",
            "license": "GPL v2",
            "depends": "",
            None: "",
        }
        with mock.patch.object(
            lifecycle, "_modinfo", side_effect=lambda _path, field=None: values[field]
        ), mock.patch.object(
            lifecycle, "_defined_symbols", return_value=artifact_symbols
        ):
            lifecycle.validate_module_artifact(module, summary)

        values["depends"] = "legacy_ihk"
        with mock.patch.object(
            lifecycle, "_modinfo", side_effect=lambda _path, field=None: values[field]
        ), mock.patch.object(
            lifecycle, "_defined_symbols", return_value=artifact_symbols
        ):
            with self.assertRaisesRegex(lifecycle.ValidationError, "depends differs"):
                lifecycle.validate_module_artifact(module, summary)

    def test_built_artifact_requires_all_provider_definitions(self) -> None:
        module = self.repo / "ihk.ko"
        module.write_bytes(
            b"lifecycle=load\0provider_lease=attach\0provider_lease=detach\0"
            b"provider_open=acquire\0provider_open=release\0"
            b"provider_registry=empty\0lifecycle=unload\0MCKERNEL_IHK_V1\0"
        )
        summary = lifecycle.validate_repository(REPO_ROOT)
        values = {
            "name": "ihk",
            "version": "1.7.0rc4",
            "license": "GPL v2",
            "depends": "",
            None: "",
        }
        with mock.patch.object(
            lifecycle, "_modinfo", side_effect=lambda _path, field=None: values[field]
        ), mock.patch.object(
            lifecycle,
            "_defined_symbols",
            return_value={"ihk_provider_lifecycle_v1"},
        ):
            with self.assertRaisesRegex(
                lifecycle.ValidationError,
                "lacks provider definitions",
            ):
                lifecycle.validate_module_artifact(module, summary)

    def test_built_artifact_rejects_defined_but_unexported_providers(self) -> None:
        summary = lifecycle.validate_repository(REPO_ROOT)
        with self.assertRaisesRegex(
            lifecycle.ValidationError, "lacks provider GPL export metadata"
        ):
            lifecycle._validate_provider_export_symbols(
                set(summary["provider_symbols"]), set(summary["provider_symbols"])
            )

    def test_built_artifact_rejects_non_gpl_export_section(self) -> None:
        summary = lifecycle.validate_repository(REPO_ROOT)
        symbols = reviewed_artifact_symbols(summary["provider_symbols"])
        symbols.remove("__ksymtab_gpl")
        symbols.add("__ksymtab")
        with self.assertRaisesRegex(lifecycle.ValidationError, "non-GPL __ksymtab"):
            lifecycle._validate_provider_export_symbols(
                symbols, set(summary["provider_symbols"])
            )

    def test_built_artifact_requires_every_namespace_record(self) -> None:
        summary = lifecycle.validate_repository(REPO_ROOT)
        symbols = reviewed_artifact_symbols(summary["provider_symbols"])
        symbols.remove(f'__kstrtabns_{summary["provider_symbols"][1]}')
        with self.assertRaisesRegex(
            lifecycle.ValidationError, "lacks provider GPL export metadata"
        ):
            lifecycle._validate_provider_export_symbols(
                symbols, set(summary["provider_symbols"])
            )

    def test_built_artifact_rejects_unreviewed_provider_export(self) -> None:
        summary = lifecycle.validate_repository(REPO_ROOT)
        symbols = reviewed_artifact_symbols(summary["provider_symbols"])
        symbols.update(
            {
                "ihk_smp_provider_attach_v3",
                "__ksymtab_ihk_smp_provider_attach_v3",
                "__kstrtab_ihk_smp_provider_attach_v3",
                "__kstrtabns_ihk_smp_provider_attach_v3",
            }
        )
        with self.assertRaisesRegex(lifecycle.ValidationError, "unreviewed export metadata"):
            lifecycle._validate_provider_export_symbols(
                symbols, set(summary["provider_symbols"])
            )

    def test_built_artifact_requires_namespace_bytes(self) -> None:
        module = self.repo / "ihk.ko"
        module.write_bytes(
            b"lifecycle=load\0provider_lease=attach\0provider_lease=detach\0"
            b"provider_open=acquire\0provider_open=release\0"
            b"provider_registry=empty\0lifecycle=unload\0"
        )
        summary = lifecycle.validate_repository(REPO_ROOT)
        values = {
            "name": "ihk",
            "version": "1.7.0rc4",
            "license": "GPL v2",
            "depends": "",
            None: "",
        }
        with mock.patch.object(
            lifecycle, "_modinfo", side_effect=lambda _path, field=None: values[field]
        ), mock.patch.object(
            lifecycle,
            "_defined_symbols",
            return_value=reviewed_artifact_symbols(summary["provider_symbols"]),
        ):
            with self.assertRaisesRegex(lifecycle.ValidationError, "namespace bytes"):
                lifecycle.validate_module_artifact(module, summary)

    def test_defined_symbol_scan_includes_local_export_records(self) -> None:
        completed = subprocess.CompletedProcess(
            args=[], returncode=0, stdout="00000000 r __ksymtab_gpl\n", stderr=""
        )
        with mock.patch.object(lifecycle.shutil, "which", return_value="/usr/bin/nm"), \
                mock.patch.object(lifecycle.subprocess, "run", return_value=completed) as run:
            self.assertEqual({"__ksymtab_gpl"}, lifecycle._defined_symbols(Path("ihk.ko")))
        self.assertEqual(
            ["/usr/bin/nm", "-a", "--defined-only", "ihk.ko"],
            run.call_args.args[0],
        )


if __name__ == "__main__":
    unittest.main()
