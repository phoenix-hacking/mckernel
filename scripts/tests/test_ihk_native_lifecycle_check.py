import ast
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

from scripts import ihk_native_lifecycle_check as lifecycle


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
        self.assertEqual(3, summary["transitive_module_count"])
        self.assertEqual(5, summary["support_sources"])

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
        with self.assertRaisesRegex(lifecycle.ValidationError, "forbidden boundary"):
            lifecycle.validate_repository(self.repo)

    def test_core_kconfig_module_dependency_is_rejected(self) -> None:
        self.mutate_text(
            self.contract["kconfig"]["path"],
            '\ttristate "McKernel IHK core host module (Rust)"',
            '\ttristate "McKernel IHK core host module (Rust)"\n\tdepends on MCKERNEL_LEGACY_IHK',
        )
        with self.assertRaisesRegex(lifecycle.ValidationError, "module dependencies"):
            lifecycle.validate_repository(self.repo)

    def test_composite_ihk_kbuild_inputs_are_rejected(self) -> None:
        kbuild = self.repo / self.contract["kbuild"]["path"]
        with kbuild.open("a", encoding="utf-8") as stream:
            stream.write("ihk-y := legacy_ihk.o\n")
        with self.assertRaisesRegex(lifecycle.ValidationError, "composite"):
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
        for index in (3, 4):
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
        for index in (3, 4):
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

    def test_ioctl_dispatch_registration_overclaim_is_rejected(self) -> None:
        support = self.contract["support_sources"][2]
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
        with self.assertRaisesRegex(lifecycle.ValidationError, "overclaims device registration"):
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
        module.write_bytes(b"lifecycle=load\0lifecycle=unload\0")
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
        ):
            lifecycle.validate_module_artifact(module, summary)

        values["depends"] = "legacy_ihk"
        with mock.patch.object(
            lifecycle, "_modinfo", side_effect=lambda _path, field=None: values[field]
        ):
            with self.assertRaisesRegex(lifecycle.ValidationError, "depends differs"):
                lifecycle.validate_module_artifact(module, summary)


if __name__ == "__main__":
    unittest.main()
