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
