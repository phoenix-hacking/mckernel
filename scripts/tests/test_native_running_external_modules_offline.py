"""Injected process tests only: synthetic ELF files carry no compilation credit."""
import copy
import hashlib
import json
import os
from pathlib import Path
import struct
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from scripts import native_running_external_modules_offline as driver

ROOT = Path(__file__).resolve().parents[2]
PREPARATION = ROOT / "docs/verification/evidence/native-running-external-modules-preparation-20261017-2.json"


def fake_elf(name, release=driver.RELEASE):
    names = b"\0.shstrtab\0.modinfo\0"
    info = ("name=" + name + "\0vermagic=" + release + " SMP mod_unload \0license=GPL\0").encode()
    header = bytearray(64)
    header[:6] = b"\x7fELF\x02\x01"
    struct.pack_into("<HH", header, 16, 1, 62)
    struct.pack_into("<Q", header, 40, 64)
    struct.pack_into("<HHH", header, 58, 64, 3, 1)
    sections = bytes(64)
    sections += struct.pack("<IIQQQQIIQQ", 1, 3, 0, 0, 256, len(names), 0, 0, 1, 0)
    sections += struct.pack("<IIQQQQIIQQ", 11, 1, 0, 0, 256 + len(names), len(info), 0, 0, 1, 0)
    return bytes(header) + sections + names + info


class ExternalModulesDriverTests(unittest.TestCase):
    def setUp(self):
        parent = os.environ.get("MCKERNEL_EXTERNAL_DRIVER_EVIDENCE")
        self.root = Path(tempfile.mkdtemp(prefix="driver-case-", dir=parent))
        self.baseline, self.candidate, self.inputs = [self.root / x for x in ("out", "candidate", "inputs")]
        for path in [self.baseline, self.inputs, self.candidate / "modules", self.candidate / "home", self.candidate / "tmp"]:
            path.mkdir(parents=True, exist_ok=True)
        # Authentication is mocked explicitly; all path/hash/output logic is real.
        # Synthetic input bytes are never passed to a compiler.
        self.manifest = json.loads(PREPARATION.read_text())
        self.manifest["references"] = {}
        self.manifest["rust_support_exact_cmd_deps"] = []
        self.manifest["build_support_stat_only"] = []
        for row in self.manifest["closure"]:
            data = ("synthetic fixture input " + row["path"] + "\n").encode()
            target = self.candidate / "modules" / row["path"]
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
            row["bytes"], row["sha256"] = len(data), hashlib.sha256(data).hexdigest()
        for crate in driver.MODULES:
            prefix = "/out/" + driver.KERNEL + "/drivers/misc/mckernel/"
            content = "deps_original := \\\n  " + prefix + crate + ".rs \\\n"
            name = "baseline-" + crate + ".o.cmd"
            (self.inputs / name).write_text(content)
            self.manifest["references"]["compiler_" + crate] = {
                "path": "/reference/" + name, "retained_copy": "/retained/" + name,
                "sha256": hashlib.sha256(content.encode()).hexdigest()}
        (self.baseline / "build").mkdir()
        tool = self.baseline / "build/fixture-tool"
        tool.write_bytes(b"synthetic tool input, never executed")
        self.basis = {"fixture-tool": hashlib.sha256(tool.read_bytes()).hexdigest()}

    def run_driver(self, executor=None, execute=True):
        with patch.object(driver, "load_preparation", return_value=copy.deepcopy(self.manifest)), \
             patch.object(driver, "BASIS_DIGESTS", self.basis), \
             patch.object(driver.subprocess, "run", side_effect=executor) as process:
            receipt = driver.execute(PREPARATION, self.baseline, self.candidate, self.inputs, run=execute)
        (self.root / "test-receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
        return receipt, process

    def synthetic_process(self, argv, **kwargs):
        self.assertEqual(argv, self.manifest["proposed_external_command"])
        self.assertEqual(kwargs["cwd"], self.baseline / "build")
        self.assertEqual(kwargs["env"], self.manifest["environment"])
        self.assertEqual(kwargs["timeout"], 1800)
        kwargs["stdout"].write(b"synthetic injected executor; no compiler ran\n")
        directory = self.candidate / "modules"
        for crate, module in driver.MODULES.items():
            (directory / (module + ".ko")).write_bytes(fake_elf(crate))
            for suffix in (".o", ".mod.c", ".mod.o"):
                (directory / (module + suffix)).write_bytes(b"synthetic generated fixture\n")
            text = "savedcmd_/candidate/modules/" + crate + ".o := rustc --crate-name " + crate
            text += " --emit=obj=/candidate/modules/" + crate + ".o /candidate/modules/" + crate + ".rs\n"
            text += "source_/candidate/modules/" + crate + ".o := /candidate/modules/" + crate + ".rs\n"
            text += "deps_/candidate/modules/" + crate + ".o := \\\n  /candidate/modules/" + crate + ".rs \\\n"
            (directory / ("." + crate + ".o.cmd")).write_text(text)
        (directory / "modules.order").write_text("".join("/candidate/modules/" + name + ".ko\n" for name in driver.MODULES.values()))
        (directory / "Module.symvers").write_text("0x00000000\tihk_os_create_unbooted_v6\t/candidate/modules/ihk\tEXPORT_SYMBOL_GPL\tMCKERNEL_IHK_V1\n")
        return subprocess.CompletedProcess(argv, 0)

    def test_frozen_preparation_and_exact_all_three_plan(self):
        manifest = driver.load_preparation(PREPARATION)
        plan = driver.plan(manifest)
        self.assertEqual(plan["argv"][-2:], ["-j2", "modules"])
        self.assertEqual(plan["read_only_mounts"], ["/out", "/inputs"])
        self.assertEqual(plan["writable_mounts"], ["/candidate"])
        self.assertEqual(set(plan["all_three_modules_required"]), {"ihk", "ihk-smp-x86_64", "mcctrl"})
        self.assertNotIn("bzImage", plan["argv"])
        provenance = plan["source_provenance"]
        self.assertEqual(provenance["baseline_source_sha"], "942c927b1ec93cc31284ff498455909d9bb2d0fc")
        self.assertEqual(provenance["source_candidate_sha"], "1769263c751befa9983d19705833d3d5ac6a1ace")
        self.assertEqual({row["path"] for row in provenance["reviewed_deltas"]}, set(driver.REPLACEMENTS))
        closure = {row["path"]: row["sha256"] for row in manifest["closure"]}
        encoded = json.dumps(closure, sort_keys=True, separators=(",", ":")).encode()
        self.assertEqual(provenance["closure_sha256"], hashlib.sha256(encoded).hexdigest())
        self.assertIn("not proof of unchanged compiled source", provenance["compatibility_build_id"]["meaning"])
        changed = self.root / "changed-preparation.json"
        changed.write_bytes(PREPARATION.read_bytes() + b" ")
        with self.assertRaisesRegex(ValueError, "frozen preparation digest"):
            driver.load_preparation(changed)

    def test_plan_never_launches_a_process(self):
        receipt, process = self.run_driver(execute=False)
        self.assertEqual(receipt["status"], "PLAN_VALIDATED_NO_BUILD")
        process.assert_not_called()

    def test_injected_process_checks_arguments_environment_and_all_outputs(self):
        receipt, process = self.run_driver(self.synthetic_process)
        self.assertEqual(receipt["status"], "BUILD_ARTIFACT_CHECKS_PASS", receipt)
        self.assertFalse(receipt["application_acceptance"])
        self.assertEqual(len(receipt["artifacts"]), 3)
        self.assertEqual(receipt["make_returncode"], 0)
        self.assertEqual(receipt["source_candidate_sha"], driver.SOURCE_CANDIDATE_SHA)
        self.assertEqual(receipt["baseline_source_sha"], driver.BASELINE_SOURCE_SHA)
        self.assertEqual(receipt["source_provenance"], driver.source_provenance(self.manifest))
        process.assert_called_once()

    def test_old_or_changed_source_never_invokes_make(self):
        (self.candidate / "modules/os_runtime.rs").write_text("old Ready publication")
        receipt, process = self.run_driver(self.synthetic_process)
        self.assertEqual(receipt["status"], "FAIL")
        self.assertIn("source changed: os_runtime.rs", receipt["error"])
        process.assert_not_called()

    def test_missing_module_fails_after_one_process_and_preserves_generated_files(self):
        def missing(argv, **kwargs):
            result = self.synthetic_process(argv, **kwargs)
            (self.candidate / "modules/mcctrl.ko").unlink()
            return result
        receipt, process = self.run_driver(missing)
        self.assertIn("missing or unexpected native module", receipt["error"])
        self.assertEqual(receipt["make_returncode"], 0)
        self.assertIn("ihk.ko", receipt["retained_files"])
        process.assert_called_once()

    def test_nonzero_status_streams_and_partial_output_survive_without_retry(self):
        def failure(argv, **kwargs):
            kwargs["stdout"].write(b"partial stdout\n")
            kwargs["stderr"].write(b"original compiler failure\n")
            (self.candidate / "modules/partial.o").write_bytes(b"partial")
            return subprocess.CompletedProcess(argv, 23)
        receipt, process = self.run_driver(failure)
        self.assertEqual(receipt["status"], "FAIL")
        self.assertEqual(receipt["make_returncode"], 23)
        evidence = self.candidate / "evidence"
        original = (evidence / "receipt.json").read_bytes()
        self.assertEqual((evidence / "make.stderr").read_bytes(), b"original compiler failure\n")
        self.assertIn("partial.o", receipt["retained_files"])
        with self.assertRaises(FileExistsError):
            self.run_driver(failure)
        self.assertEqual((evidence / "receipt.json").read_bytes(), original)
        process.assert_called_once()

    def test_timeout_has_distinct_receipt_and_retains_streams(self):
        def timeout(argv, **kwargs):
            kwargs["stderr"].write(b"partial timeout log")
            raise subprocess.TimeoutExpired(argv, 1800)
        receipt, process = self.run_driver(timeout)
        self.assertEqual(receipt["error"], "external make timeout")
        self.assertIsNone(receipt["make_returncode"])
        self.assertEqual(receipt["timeout_seconds"], 1800)
        process.assert_called_once()

    def test_old_dependency_source_path_is_rejected(self):
        def old(argv, **kwargs):
            result = self.synthetic_process(argv, **kwargs)
            path = self.candidate / "modules/.ihk.o.cmd"
            path.write_text(path.read_text().replace("source_/candidate/modules/ihk.o := /candidate/modules/ihk.rs",
                                                    "source_/candidate/modules/ihk.o := /out/old/ihk.rs"))
            return result
        receipt, process = self.run_driver(old)
        self.assertIn("wrong compiler source", receipt["error"])
        self.assertEqual(receipt["status"], "FAIL")
        process.assert_called_once()

    def test_changed_reference_rejected_before_process(self):
        (self.inputs / "baseline-ihk.o.cmd").write_text("unbound reference")
        receipt, process = self.run_driver(self.synthetic_process)
        self.assertIn("reference changed", receipt["error"])
        process.assert_not_called()

    def test_changed_basis_tool_rejected_before_process(self):
        (self.baseline / "build/fixture-tool").write_bytes(b"changed tool")
        receipt, process = self.run_driver(self.synthetic_process)
        self.assertIn("basis tool/header changed", receipt["error"])
        process.assert_not_called()

    def test_zero_exit_with_wrong_vermagic_is_rejected(self):
        def bad(argv, **kwargs):
            result = self.synthetic_process(argv, **kwargs)
            (self.candidate / "modules/ihk.ko").write_bytes(fake_elf("ihk", "old-kernel"))
            return result
        receipt, process = self.run_driver(bad)
        self.assertIn("wrong vermagic", receipt["error"])
        self.assertEqual(receipt["status"], "FAIL")
        process.assert_called_once()

    def test_make_mutating_source_cannot_pass_output_checks(self):
        def bad(argv, **kwargs):
            result = self.synthetic_process(argv, **kwargs)
            (self.candidate / "modules/sysfs_remote.rs").write_bytes(b"unreviewed replacement")
            return result
        receipt, process = self.run_driver(bad)
        self.assertIn("source changed: sysfs_remote.rs", receipt["error"])
        self.assertEqual(receipt["status"], "FAIL")
        process.assert_called_once()

    def test_symlink_source_and_overlapping_roots_are_rejected(self):
        path = self.candidate / "modules/os_runtime.rs"
        path.unlink()
        path.symlink_to(self.inputs / "baseline-ihk.o.cmd")
        receipt, process = self.run_driver(self.synthetic_process)
        self.assertIn("symlink", receipt["error"])
        process.assert_not_called()
        with self.assertRaisesRegex(ValueError, "overlap"):
            driver.execute(PREPARATION, self.baseline, self.baseline, self.inputs)
        self.assertFalse((self.baseline / "evidence").exists())


if __name__ == "__main__":
    unittest.main()
