import contextlib
import io
import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
from unittest import mock


REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts import mcctrl_native_lifecycle_check as lifecycle


class McctrlNativeLifecycleCheckTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory(prefix="mcctrl-native-lifecycle-")
        self.repo = Path(self.temporary.name) / "repo"
        contract_path = REPO_ROOT / lifecycle.DEFAULT_CONTRACT
        with contract_path.open("r", encoding="utf-8") as stream:
            self.contract = json.load(stream)
        relative_paths = {
            lifecycle.DEFAULT_CONTRACT.as_posix(),
            self.contract["production_source"],
            self.contract["provider_source"],
            self.contract["kconfig"]["path"],
            self.contract["kbuild"]["path"],
            self.contract["stage_manifest"],
            self.contract["reference_inventory"],
            self.contract["selected_kernel"]["source_lock"],
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

    def write_json(self, relative: str, value: object) -> None:
        (self.repo / relative).write_text(
            json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )

    def test_repository_source_contract_passes_without_gate_credit(self) -> None:
        summary = lifecycle.validate_repository(REPO_ROOT)
        self.assertEqual("MCC-001", summary["gate_id"])
        self.assertEqual("mcctrl", summary["module"])
        self.assertEqual(0, summary["parameters"])
        self.assertEqual(1, summary["dependencies"])
        self.assertEqual("source-bound", summary["ihk_symbol_import_status"])
        self.assertEqual("blocked", summary["binfmt_status"])
        self.assertTrue(summary["source_symbol_reference_present"])
        self.assertFalse(summary["artifact_validated"])
        self.assertFalse(summary["built_symbol_reference_validated"])
        self.assertFalse(summary["rocky_build_load_validated"])
        self.assertFalse(summary["runtime_symbol_reference_proven"])
        self.assertFalse(summary["gate_credit_eligible"])

    def test_cli_deliberately_does_not_report_gate_pass(self) -> None:
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            result = lifecycle.main(["--repo", str(REPO_ROOT)])
        self.assertEqual(0, result)
        rendered = output.getvalue()
        self.assertIn("SOURCE-CONTRACT-VERIFIED", rendered)
        self.assertIn("rocky_build_load=NOT_EVALUATED", rendered)
        self.assertIn("runtime_symbol_reference=NOT_PROVEN", rendered)
        self.assertNotIn("PASS", rendered)

    def test_optional_author_metadata_is_rejected(self) -> None:
        self.mutate_text(
            self.contract["production_source"],
            '    name: "mcctrl",\n',
            '    name: "mcctrl",\n    author: "invented",\n',
        )
        with self.assertRaisesRegex(lifecycle.ValidationError, "author is absent"):
            lifecycle.validate_repository(self.repo)

    def test_parameter_surface_drift_is_rejected(self) -> None:
        self.mutate_text(
            self.contract["production_source"],
            "const MCCTRL_PARAMETER_COUNT: usize = 0;",
            "const MCCTRL_PARAMETER_COUNT: usize = 1;",
        )
        with self.assertRaisesRegex(lifecycle.ValidationError, "parameter count"):
            lifecycle.validate_repository(self.repo)

    def test_source_import_status_overclaim_is_rejected(self) -> None:
        self.mutate_text(
            self.contract["production_source"],
            'const MCCTRL_IHK_IMPORT_STATUS: &str = "source-bound-anchor";',
            'const MCCTRL_IHK_IMPORT_STATUS: &str = "runtime-proven";',
        )
        with self.assertRaisesRegex(lifecycle.ValidationError, "source-bound IHK anchor"):
            lifecycle.validate_repository(self.repo)

    def test_hand_authored_depends_metadata_is_rejected(self) -> None:
        source = self.repo / self.contract["production_source"]
        with source.open("a", encoding="utf-8") as stream:
            stream.write('static BAD: &[u8] = b"depends=ihk\\0";\n')
        with self.assertRaisesRegex(lifecycle.ValidationError, "modpost derive"):
            lifecycle.validate_repository(self.repo)

    def test_unreviewed_ffi_import_is_rejected(self) -> None:
        source = self.repo / self.contract["production_source"]
        with source.open("a", encoding="utf-8") as stream:
            stream.write('extern "C" { fn ihk_unreviewed(); }\n')
        with self.assertRaisesRegex(lifecycle.ValidationError, "extern boundary"):
            lifecycle.validate_repository(self.repo)

    def test_provider_symbol_import_drift_is_rejected(self) -> None:
        self.mutate_text(
            self.contract["production_source"],
            '#[link_name = "ihk_provider_lifecycle_v1"]',
            '#[link_name = "wrong_provider_symbol"]',
        )
        with self.assertRaisesRegex(lifecycle.ValidationError, "provider-symbol import"):
            lifecycle.validate_repository(self.repo)

    def test_provider_anchor_reference_is_required(self) -> None:
        self.mutate_text(
            self.contract["production_source"],
            "core::ptr::read_volatile(core::ptr::addr_of!(IHK_PROVIDER_LIFECYCLE_V1))",
            "1_u8",
        )
        with self.assertRaisesRegex(lifecycle.ValidationError, "provider-anchor relocation"):
            lifecycle.validate_repository(self.repo)

    def test_provider_export_namespace_drift_is_rejected(self) -> None:
        self.mutate_text(
            self.contract["provider_source"],
            'namespace: *b"MCKERNEL_IHK_V1\\0"',
            'namespace: *b"UNVERSIONED_____\\0"',
        )
        with self.assertRaisesRegex(lifecycle.ValidationError, "provider anchor"):
            lifecycle.validate_repository(self.repo)

    def test_provider_export_symbol_drift_is_rejected(self) -> None:
        self.mutate_text(
            self.contract["provider_source"],
            '#[export_name = "ihk_provider_lifecycle_v1"]',
            '#[export_name = "wrong_provider_symbol"]',
        )
        with self.assertRaisesRegex(lifecycle.ValidationError, "provider anchor"):
            lifecycle.validate_repository(self.repo)

    def test_missing_namespace_metadata_is_rejected(self) -> None:
        self.mutate_text(
            self.contract["production_source"],
            '*b"import_ns=MCKERNEL_IHK_V1\\0"',
            '*b"import_ns=UNREVIEWED\\0"',
        )
        with self.assertRaisesRegex(lifecycle.ValidationError, "namespace modinfo"):
            lifecycle.validate_repository(self.repo)

    def test_binfmt_registration_claim_is_rejected(self) -> None:
        source = self.repo / self.contract["production_source"]
        with source.open("a", encoding="utf-8") as stream:
            stream.write("fn bad() { register_binfmt(); }\n")
        with self.assertRaisesRegex(lifecycle.ValidationError, "forbidden boundary"):
            lifecycle.validate_repository(self.repo)

    def test_legacy_success_log_claim_is_rejected(self) -> None:
        source = self.repo / self.contract["production_source"]
        with source.open("a", encoding="utf-8") as stream:
            stream.write('// mcctrl: initialized successfully.\n')
        with self.assertRaisesRegex(lifecycle.ValidationError, "falsely emits"):
            lifecycle.validate_repository(self.repo)

    def test_kconfig_provider_dependency_drift_is_rejected(self) -> None:
        self.mutate_text(
            self.contract["kconfig"]["path"],
            "config MCKERNEL_MCCTRL_RUST\n"
            '\ttristate "McKernel control host module (Rust)"\n'
            "\tdepends on MCKERNEL_IHK_RUST",
            "config MCKERNEL_MCCTRL_RUST\n"
            '\ttristate "McKernel control host module (Rust)"\n'
            "\tdepends on MCKERNEL_LEGACY_IHK",
        )
        with self.assertRaisesRegex(lifecycle.ValidationError, "Kconfig dependency"):
            lifecycle.validate_repository(self.repo)

    def test_stage_manifest_namespace_drift_is_rejected(self) -> None:
        path = self.repo / self.contract["stage_manifest"]
        manifest = json.loads(path.read_text(encoding="utf-8"))
        module = next(item for item in manifest["modules"] if item["crate"] == "mcctrl")
        module["required_import_namespaces"] = []
        self.write_json(self.contract["stage_manifest"], manifest)
        with self.assertRaisesRegex(lifecycle.ValidationError, "import namespace"):
            lifecycle.validate_repository(self.repo)

    def test_stage_manifest_source_digest_drift_is_rejected(self) -> None:
        path = self.repo / self.contract["stage_manifest"]
        manifest = json.loads(path.read_text(encoding="utf-8"))
        module = next(item for item in manifest["modules"] if item["crate"] == "mcctrl")
        module["source"]["sha256"] = "0" * 64
        self.write_json(self.contract["stage_manifest"], manifest)
        with self.assertRaisesRegex(lifecycle.ValidationError, "digest is stale"):
            lifecycle.validate_repository(self.repo)

    def test_stage_manifest_provider_digest_drift_is_rejected(self) -> None:
        path = self.repo / self.contract["stage_manifest"]
        manifest = json.loads(path.read_text(encoding="utf-8"))
        module = next(item for item in manifest["modules"] if item["crate"] == "ihk")
        module["source"]["sha256"] = "0" * 64
        self.write_json(self.contract["stage_manifest"], manifest)
        with self.assertRaisesRegex(lifecycle.ValidationError, "provider source digest"):
            lifecycle.validate_repository(self.repo)

    def test_reference_dependency_oracle_drift_is_rejected(self) -> None:
        path = self.repo / self.contract["reference_inventory"]
        inventory = json.loads(path.read_text(encoding="utf-8"))
        inventory["binary_capture"]["modules"]["mcctrl"]["modinfo"]["values"]["depends"] = []
        self.write_json(self.contract["reference_inventory"], inventory)
        with self.assertRaisesRegex(lifecycle.ValidationError, "depends metadata"):
            lifecycle.validate_repository(self.repo)

    def test_reference_parameter_oracle_drift_is_rejected(self) -> None:
        path = self.repo / self.contract["reference_inventory"]
        inventory = json.loads(path.read_text(encoding="utf-8"))
        inventory["source_capture"]["modules"]["mcctrl"]["source_module_parameters"] = [
            {"name": "invented"}
        ]
        self.write_json(self.contract["reference_inventory"], inventory)
        with self.assertRaisesRegex(lifecycle.ValidationError, "parameter surface"):
            lifecycle.validate_repository(self.repo)

    def test_selected_kernel_archive_drift_is_rejected(self) -> None:
        path = self.repo / self.contract["selected_kernel"]["source_lock"]
        source_lock = json.loads(path.read_text(encoding="utf-8"))
        archive = next(
            item
            for item in source_lock["embedded_objects"]
            if item["role"] == "Rocky-derived Linux source archive"
        )
        archive["sha256"] = "0" * 64
        self.write_json(self.contract["selected_kernel"]["source_lock"], source_lock)
        with self.assertRaisesRegex(lifecycle.ValidationError, "reviewed Linux archive"):
            lifecycle.validate_repository(self.repo)

    def test_contract_cannot_claim_gate_credit(self) -> None:
        path = self.repo / lifecycle.DEFAULT_CONTRACT
        contract = json.loads(path.read_text(encoding="utf-8"))
        contract["gate_credit_eligible"] = True
        self.write_json(lifecycle.DEFAULT_CONTRACT.as_posix(), contract)
        with self.assertRaisesRegex(lifecycle.ValidationError, "credit is forbidden"):
            lifecycle.validate_repository(self.repo)

    def test_contract_cannot_claim_built_or_runtime_symbol_proof(self) -> None:
        path = self.repo / lifecycle.DEFAULT_CONTRACT
        original = json.loads(path.read_text(encoding="utf-8"))
        for field in (
            "built_symbol_reference_validated",
            "runtime_symbol_reference_proven",
        ):
            with self.subTest(field=field):
                contract = json.loads(json.dumps(original))
                contract["ihk_dependency"]["native_symbol_import"][field] = True
                self.write_json(lifecycle.DEFAULT_CONTRACT.as_posix(), contract)
                with self.assertRaisesRegex(lifecycle.ValidationError, "overclaims proof"):
                    lifecycle.validate_repository(self.repo)

    def test_built_artifact_requires_exact_modinfo_and_diagnostics(self) -> None:
        module = self.repo / "mcctrl.ko"
        module.write_bytes(
            b"lifecycle=load\0lifecycle=unload\0ihk_import=source-bound-anchor\0"
            b"binfmt=blocked-no-safe-rust-api\0"
        )
        summary = lifecycle.validate_repository(REPO_ROOT)
        values = {
            "author": "",
            "depends": "ihk",
            "description": "",
            "import_ns": "MCKERNEL_IHK_V1",
            "license": "GPL v2",
            "name": "mcctrl",
            "version": "",
            None: "",
        }
        with mock.patch.object(
            lifecycle, "_modinfo", side_effect=lambda _path, field=None: values[field]
        ), mock.patch.object(
            lifecycle,
            "_undefined_symbols",
            return_value={"ihk_provider_lifecycle_v1"},
        ):
            lifecycle.validate_module_artifact(module, summary)
        self.assertTrue(summary["artifact_validated"])
        self.assertTrue(summary["built_symbol_reference_validated"])
        self.assertFalse(summary["rocky_build_load_validated"])
        self.assertFalse(summary["runtime_symbol_reference_proven"])

        values["depends"] = ""
        with mock.patch.object(
            lifecycle, "_modinfo", side_effect=lambda _path, field=None: values[field]
        ), mock.patch.object(
            lifecycle,
            "_undefined_symbols",
            return_value={"ihk_provider_lifecycle_v1"},
        ):
            with self.assertRaisesRegex(lifecycle.ValidationError, "depends differs"):
                lifecycle.validate_module_artifact(module, summary)

    def test_built_artifact_requires_provider_anchor_relocation(self) -> None:
        module = self.repo / "mcctrl.ko"
        module.write_bytes(
            b"lifecycle=load\0lifecycle=unload\0ihk_import=source-bound-anchor\0"
            b"binfmt=blocked-no-safe-rust-api\0"
        )
        summary = lifecycle.validate_repository(REPO_ROOT)
        values = {
            "author": "",
            "depends": "ihk",
            "description": "",
            "import_ns": "MCKERNEL_IHK_V1",
            "license": "GPL v2",
            "name": "mcctrl",
            "version": "",
            None: "",
        }
        with mock.patch.object(
            lifecycle, "_modinfo", side_effect=lambda _path, field=None: values[field]
        ), mock.patch.object(lifecycle, "_undefined_symbols", return_value=set()):
            with self.assertRaisesRegex(lifecycle.ValidationError, "anchor relocation"):
                lifecycle.validate_module_artifact(module, summary)


if __name__ == "__main__":
    unittest.main()
