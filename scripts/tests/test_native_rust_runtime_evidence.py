#!/usr/bin/env python3

from __future__ import print_function

import contextlib
import copy
import hashlib
import io
import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest


REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts import native_rust_runtime_evidence as evidence


KERNEL_RELEASE = "6.12.0-211.44.1.el10_2.x86_64"


def valid_serial() -> str:
    protocol = evidence.PROTOCOL
    records = [
        f"{protocol} BEGIN",
        f"{protocol} KERNEL_RELEASE actual={KERNEL_RELEASE} expected={KERNEL_RELEASE}",
        f"{protocol} STATE_BEGIN label=initial-clean",
        f"{protocol} STATE_END label=initial-clean",
        f"{protocol} LOAD module=ihk status=ok",
        "ihk: lifecycle=load version=1.7.0rc4 abi=1 parameters=0 dependencies=0",
        f"{protocol} LOAD module=ihk_smp_x86_64 status=ok",
        "ihk_smp_x86_64: lifecycle=load parameters=6 dependency=ihk "
        "import_namespace=MCKERNEL_IHK_V1",
        f"{protocol} LOAD module=mcctrl status=ok",
        (
            "mcctrl: lifecycle=load foundation=1 parameters=0 declared_dependencies=1 "
            "ihk_import=source-bound-anchor binfmt=blocked-no-safe-rust-api"
        ),
        f"{protocol} STATE_BEGIN label=all-loaded",
        f"{protocol} MODULE ihk 1 2 mcctrl,ihk_smp_x86_64 Live 0x0",
        f"{protocol} MODULE ihk_smp_x86_64 1 0 - Live 0x0",
        f"{protocol} MODULE mcctrl 1 0 - Live 0x0",
        f"{protocol} STATE_END label=all-loaded",
        f"{protocol} REFCOUNT module=ihk phase=all-loaded references=2 users=mcctrl,ihk_smp_x86_64",
        f"{protocol} NEGATIVE operation=unload-provider-first status=1",
        f"{protocol} NEGATIVE_OUTPUT_BEGIN",
        "rmmod: ERROR: Module ihk is in use by: mcctrl ihk_smp_x86_64",
        f"{protocol} NEGATIVE_OUTPUT_END",
        f"{protocol} REFCOUNT module=ihk phase=after-negative references=2 "
        "users=mcctrl,ihk_smp_x86_64",
        f"{protocol} STATE_BEGIN label=after-negative",
        f"{protocol} MODULE ihk 1 2 mcctrl,ihk_smp_x86_64 Live 0x0",
        f"{protocol} MODULE ihk_smp_x86_64 1 0 - Live 0x0",
        f"{protocol} MODULE mcctrl 1 0 - Live 0x0",
        f"{protocol} STATE_END label=after-negative",
        "mcctrl: lifecycle=unload foundation=1 parameters=0 declared_dependencies=1 "
        "ihk_import=source-bound-anchor binfmt=blocked-no-safe-rust-api",
        f"{protocol} UNLOAD module=mcctrl status=ok",
        f"{protocol} REFCOUNT module=ihk phase=after-mcctrl-unload references=1 "
        "users=ihk_smp_x86_64",
        "ihk_smp_x86_64: lifecycle=unload parameters=6 dependency=ihk "
        "import_namespace=MCKERNEL_IHK_V1",
        f"{protocol} UNLOAD module=ihk_smp_x86_64 status=ok",
        f"{protocol} REFCOUNT module=ihk phase=after-smp-unload references=0 users=-",
        "ihk: lifecycle=unload version=1.7.0rc4 abi=1 parameters=0 dependencies=0",
        f"{protocol} UNLOAD module=ihk status=ok",
        f"{protocol} STATE_BEGIN label=final-clean",
        f"{protocol} STATE_END label=final-clean",
        f"{protocol} DMESG_BEGIN",
        "ihk: lifecycle=load version=1.7.0rc4 abi=1 parameters=0 dependencies=0",
        "ihk_smp_x86_64: lifecycle=load parameters=6 dependency=ihk "
        "import_namespace=MCKERNEL_IHK_V1",
        "mcctrl: lifecycle=load foundation=1 parameters=0 declared_dependencies=1 "
        "ihk_import=source-bound-anchor binfmt=blocked-no-safe-rust-api",
        "mcctrl: lifecycle=unload foundation=1 parameters=0 declared_dependencies=1 "
        "ihk_import=source-bound-anchor binfmt=blocked-no-safe-rust-api",
        "ihk_smp_x86_64: lifecycle=unload parameters=6 dependency=ihk "
        "import_namespace=MCKERNEL_IHK_V1",
        "ihk: lifecycle=unload version=1.7.0rc4 abi=1 parameters=0 dependencies=0",
        f"{protocol} DMESG_END",
        f"{protocol} COMPLETE status=technical-capture-unreviewed credit=forbidden",
    ]
    return "\n".join(records) + "\n"


class NativeRustRuntimeEvidenceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory(prefix="native-rust-runtime-evidence-")
        self.root = Path(self.temporary.name)

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def copy_contract_repository(self) -> Path:
        repo = self.root / "repo"
        contract = json.loads(
            (REPO_ROOT / evidence.DEFAULT_CONTRACT).read_text(encoding="utf-8")
        )
        relative_paths = {evidence.DEFAULT_CONTRACT.as_posix()}
        relative_paths.update(contract["repository_inputs"].values())
        for relative in relative_paths:
            destination = repo / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(REPO_ROOT / relative, destination)
        return repo

    def mutate_text(self, repo: Path, relative: str, old: str, new: str) -> None:
        path = repo / relative
        text = path.read_text(encoding="utf-8")
        self.assertIn(old, text)
        path.write_text(text.replace(old, new, 1), encoding="utf-8")

    def write_serial(self, text: str) -> Path:
        path = self.root / "serial.log"
        path.write_text(text, encoding="utf-8")
        return path

    def test_repository_contract_passes_without_gate_credit(self) -> None:
        summary = evidence.validate_contract(REPO_ROOT)
        self.assertEqual(evidence.CONTRACT_ID, summary["contract_id"])
        self.assertEqual(["IHK-001", "SMP-001", "MCC-001"], summary["gate_ids"])
        self.assertEqual("tcg", summary["runtime"]["qemu_accelerator"])

    def test_cli_does_not_report_pass_or_credit(self) -> None:
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            status = evidence.main(["--repo", str(REPO_ROOT), "--check-contract"])
        self.assertEqual(0, status)
        rendered = output.getvalue()
        self.assertIn("CONTRACT-VERIFIED", rendered)
        self.assertIn("credit=FORBIDDEN", rendered)
        self.assertIn("review=REQUIRED", rendered)
        self.assertNotIn("PASS", rendered)

    def test_credit_mutation_is_rejected(self) -> None:
        repo = self.copy_contract_repository()
        path = repo / evidence.DEFAULT_CONTRACT
        contract = json.loads(path.read_text(encoding="utf-8"))
        contract["gate"]["credit_eligible"] = True
        path.write_text(json.dumps(contract, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        with self.assertRaisesRegex(evidence.EvidenceError, "credit/review boundary"):
            evidence.validate_contract(repo)

    def test_full_module_tree_claim_mutation_is_rejected(self) -> None:
        repo = self.copy_contract_repository()
        path = repo / evidence.DEFAULT_CONTRACT
        contract = json.loads(path.read_text(encoding="utf-8"))
        contract["build_scope"]["builds_full_module_tree"] = True
        path.write_text(json.dumps(contract, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        with self.assertRaisesRegex(evidence.EvidenceError, "exact build scope"):
            evidence.validate_contract(repo)

    def test_rk002_credit_mutation_is_rejected(self) -> None:
        repo = self.copy_contract_repository()
        path = repo / evidence.DEFAULT_CONTRACT
        contract = json.loads(path.read_text(encoding="utf-8"))
        contract["build_scope"]["credit_eligible"] = True
        path.write_text(json.dumps(contract, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        with self.assertRaisesRegex(evidence.EvidenceError, "exact build scope"):
            evidence.validate_contract(repo)

    def test_host_kvm_mutation_is_rejected(self) -> None:
        repo = self.copy_contract_repository()
        workflow = ".github/workflows/native-rust-host-modules-exact-runtime.yml"
        with (repo / workflow).open("a", encoding="utf-8") as stream:
            stream.write("# /dev/kvm\n")
        with self.assertRaisesRegex(evidence.EvidenceError, "forbidden host/credit"):
            evidence.validate_contract(repo)

    def test_workflow_pass_claim_mutation_is_rejected(self) -> None:
        repo = self.copy_contract_repository()
        workflow = ".github/workflows/native-rust-host-modules-exact-runtime.yml"
        with (repo / workflow).open("a", encoding="utf-8") as stream:
            stream.write("# PASS\n")
        with self.assertRaisesRegex(evidence.EvidenceError, "may not claim a gate PASS"):
            evidence.validate_contract(repo)

    def test_missing_openssl_cli_package_is_rejected(self) -> None:
        repo = self.copy_contract_repository()
        workflow = ".github/workflows/native-rust-host-modules-exact-build.yml"
        self.mutate_text(
            repo,
            workflow,
            "openssl openssl-devel patch",
            "openssl-devel patch",
        )
        with self.assertRaisesRegex(evidence.EvidenceError, "OpenSSL CLI closure"):
            evidence.validate_contract(repo)

    def test_openssl_libraries_cannot_substitute_for_the_cli(self) -> None:
        repo = self.copy_contract_repository()
        workflow = ".github/workflows/native-rust-host-modules-exact-build.yml"
        self.mutate_text(
            repo,
            workflow,
            "openssl openssl-devel patch",
            "openssl-libs openssl-devel patch",
        )
        with self.assertRaisesRegex(evidence.EvidenceError, "OpenSSL CLI closure"):
            evidence.validate_contract(repo)

    def test_required_artifact_removal_is_rejected(self) -> None:
        repo = self.copy_contract_repository()
        path = repo / evidence.DEFAULT_CONTRACT
        contract = json.loads(path.read_text(encoding="utf-8"))
        contract["artifact_contract"]["runtime_evidence_files"].remove("serial.log")
        path.write_text(json.dumps(contract, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        with self.assertRaisesRegex(evidence.EvidenceError, "artifact file set differs"):
            evidence.validate_contract(repo)

    def test_load_order_mutation_is_rejected(self) -> None:
        repo = self.copy_contract_repository()
        init = "scripts/native-rust-runtime-init.sh"
        self.mutate_text(
            repo,
            init,
            'insmod "$IHK" || { fail load-ihk; exit 1; }',
            'insmod "$MCCTRL" || { fail load-mcctrl-early; exit 1; }',
        )
        with self.assertRaisesRegex(evidence.EvidenceError, "load/negative/reverse-unload order"):
            evidence.validate_contract(repo)

    def test_complete_serial_protocol_is_accepted(self) -> None:
        result = evidence.validate_serial(self.write_serial(valid_serial()), KERNEL_RELEASE)
        self.assertEqual(2, result["provider_refcount"])
        self.assertEqual(["ihk_smp_x86_64", "mcctrl"], result["provider_users"])
        self.assertEqual(1, result["negative_unload_status"])

    def test_successful_provider_first_unload_is_rejected(self) -> None:
        serial = valid_serial().replace(
            "NEGATIVE operation=unload-provider-first status=1",
            "NEGATIVE operation=unload-provider-first status=0",
            1,
        )
        with self.assertRaisesRegex(evidence.EvidenceError, "negative test did not fail"):
            evidence.validate_serial(self.write_serial(serial), KERNEL_RELEASE)

    def test_wrong_provider_first_unload_diagnostic_is_rejected(self) -> None:
        serial = valid_serial().replace(
            "rmmod: ERROR: Module ihk is in use by: mcctrl ihk_smp_x86_64",
            "rmmod: ERROR: permission denied",
            1,
        )
        with self.assertRaisesRegex(evidence.EvidenceError, "lacks the in-use diagnostic"):
            evidence.validate_serial(self.write_serial(serial), KERNEL_RELEASE)

    def test_wrong_provider_user_set_is_rejected(self) -> None:
        serial = valid_serial().replace(
            "REFCOUNT module=ihk phase=all-loaded references=2 users=mcctrl,ihk_smp_x86_64",
            "REFCOUNT module=ihk phase=all-loaded references=2 users=mcctrl",
            1,
        )
        with self.assertRaisesRegex(evidence.EvidenceError, "provider refcount/users differ"):
            evidence.validate_serial(self.write_serial(serial), KERNEL_RELEASE)

    def test_retained_module_in_final_state_is_rejected(self) -> None:
        serial = valid_serial().replace(
            f"{evidence.PROTOCOL} STATE_END label=final-clean",
            (
                f"{evidence.PROTOCOL} MODULE ihk 1 0 - Live 0x0\n"
                f"{evidence.PROTOCOL} STATE_END label=final-clean"
            ),
            1,
        )
        with self.assertRaisesRegex(evidence.EvidenceError, "retains a native module"):
            evidence.validate_serial(self.write_serial(serial), KERNEL_RELEASE)

    def test_negative_test_module_state_change_is_rejected(self) -> None:
        serial = valid_serial().replace(
            f"{evidence.PROTOCOL} MODULE mcctrl 1 0 - Live 0x0\n",
            "",
            1,
        )
        with self.assertRaisesRegex(evidence.EvidenceError, "loaded module state differs"):
            evidence.validate_serial(self.write_serial(serial), KERNEL_RELEASE)

    def test_lifecycle_diagnostic_mutation_is_rejected(self) -> None:
        serial = valid_serial().replace(
            "ihk: lifecycle=unload version=1.7.0rc4 abi=1 parameters=0 dependencies=0",
            "ihk: lifecycle=unload version=wrong",
        )
        with self.assertRaisesRegex(evidence.EvidenceError, "lifecycle diagnostics"):
            evidence.validate_serial(self.write_serial(serial), KERNEL_RELEASE)

    def test_capture_readiness_cannot_be_mutated(self) -> None:
        unsigned = {
            "schema_version": 1,
            "contract_id": evidence.CONTRACT_ID,
            "contract_sha256": "1" * 64,
            "identity": {},
            "build": {},
            "runtime": {},
            "readiness": {
                "credit_eligible": False,
                "gate_status": "NOT_READY",
                "independent_reviewed": False,
                "status": "CAPTURED_UNREVIEWED",
                "blockers": [
                    "GitHub artifact digest must be retained immutably",
                    "independent evidence review must verify and register this exact capture",
                ],
            },
        }
        capture = copy.deepcopy(unsigned)
        capture["capture_sha256"] = evidence._sha256_bytes(evidence._canonical_bytes(unsigned))
        evidence.validate_capture(capture)
        capture["readiness"]["credit_eligible"] = True
        with self.assertRaisesRegex(evidence.EvidenceError, "bypass independent review"):
            evidence.validate_capture(capture)

    def test_build_manifest_accepts_kbuild_dot_command_records(self) -> None:
        directory = self.root / "build"
        directory.mkdir()
        command = directory / ".ihk.o.cmd"
        command.write_bytes(b"cmd_drivers/misc/mckernel/ihk.o := rustc\n")
        digest = hashlib.sha256(command.read_bytes()).hexdigest()
        (directory / "SHA256SUMS").write_text(
            f"{digest}  .ihk.o.cmd\n", encoding="utf-8"
        )
        self.assertEqual(digest, evidence._parse_sums(directory)[".ihk.o.cmd"])

    def write_build_scope_artifacts(self) -> tuple[Path, dict[str, str]]:
        directory = self.root / "scope"
        directory.mkdir()
        source = self.root / "native-rust-source" / "linux-6.12.0-211.44.1.el10_2"
        output = self.root / "native-rust-build"
        prefix = f"make -C {source} O={output} ARCH=x86_64 LLVM=1"
        values = {
            "build.commands": (
                f"{prefix} rustavailable\n"
                f"{prefix} -j2 bzImage\n"
                f"{prefix} -j2 {' '.join(evidence.BUILD_MODULE_TARGETS)}\n"
            ),
            "build.exit-code": "0\n",
            "build.log": "Rust is available!\n",
            "build-log.exit-code": "0\n",
            "build.phase": "complete\n",
            "built-module-artifacts.txt": (
                "\n".join(sorted(evidence.BUILD_MODULE_TARGETS)) + "\n"
            ),
            "module-targets.txt": "\n".join(evidence.BUILD_MODULE_TARGETS) + "\n",
        }
        records = {}
        for name, value in values.items():
            path = directory / name
            path.write_text(value, encoding="utf-8")
            records[name] = hashlib.sha256(path.read_bytes()).hexdigest()
        return directory, records

    def test_build_scope_artifacts_bind_only_three_native_modules(self) -> None:
        directory, records = self.write_build_scope_artifacts()
        result = evidence._validate_build_scope_artifacts(directory, records)
        self.assertEqual(evidence.BUILD_KERNEL_TARGETS, result["kernel_targets"])
        self.assertEqual(evidence.BUILD_MODULE_TARGETS, result["module_targets"])

    def test_unrelated_module_artifact_is_rejected(self) -> None:
        directory, records = self.write_build_scope_artifacts()
        path = directory / "built-module-artifacts.txt"
        path.write_text(path.read_text(encoding="utf-8") + "drivers/gpu/radeon.ko\n")
        records[path.name] = hashlib.sha256(path.read_bytes()).hexdigest()
        with self.assertRaisesRegex(evidence.EvidenceError, "artifact scope differs"):
            evidence._validate_build_scope_artifacts(directory, records)

    def test_failed_or_incomplete_build_scope_is_rejected(self) -> None:
        directory, records = self.write_build_scope_artifacts()
        exit_code = directory / "build.exit-code"
        exit_code.write_text("2\n", encoding="utf-8")
        records[exit_code.name] = hashlib.sha256(exit_code.read_bytes()).hexdigest()
        with self.assertRaisesRegex(evidence.EvidenceError, "successful exit"):
            evidence._validate_build_scope_artifacts(directory, records)

        exit_code.write_text("0\n", encoding="utf-8")
        records[exit_code.name] = hashlib.sha256(exit_code.read_bytes()).hexdigest()
        phase = directory / "build.phase"
        phase.write_text("bzImage\n", encoding="utf-8")
        records[phase.name] = hashlib.sha256(phase.read_bytes()).hexdigest()
        with self.assertRaisesRegex(evidence.EvidenceError, "complete phase"):
            evidence._validate_build_scope_artifacts(directory, records)

        phase.write_text("complete\n", encoding="utf-8")
        records[phase.name] = hashlib.sha256(phase.read_bytes()).hexdigest()
        tee_status = directory / "build-log.exit-code"
        tee_status.write_text("1\n", encoding="utf-8")
        records[tee_status.name] = hashlib.sha256(tee_status.read_bytes()).hexdigest()
        with self.assertRaisesRegex(evidence.EvidenceError, "log capture"):
            evidence._validate_build_scope_artifacts(directory, records)

    def test_broad_modules_command_artifact_is_rejected(self) -> None:
        directory, records = self.write_build_scope_artifacts()
        commands = directory / "build.commands"
        text = commands.read_text(encoding="utf-8")
        text = text.replace(
            "-j2 " + " ".join(evidence.BUILD_MODULE_TARGETS), "-j2 modules", 1
        )
        commands.write_text(text, encoding="utf-8")
        records[commands.name] = hashlib.sha256(commands.read_bytes()).hexdigest()
        with self.assertRaisesRegex(evidence.EvidenceError, "bounded target scope"):
            evidence._validate_build_scope_artifacts(directory, records)

    def test_module_command_before_kernel_artifact_is_rejected(self) -> None:
        directory, records = self.write_build_scope_artifacts()
        commands = directory / "build.commands"
        lines = commands.read_text(encoding="utf-8").splitlines()
        lines[1], lines[2] = lines[2], lines[1]
        commands.write_text("\n".join(lines) + "\n", encoding="utf-8")
        records[commands.name] = hashlib.sha256(commands.read_bytes()).hexdigest()
        with self.assertRaisesRegex(evidence.EvidenceError, "bounded target scope"):
            evidence._validate_build_scope_artifacts(directory, records)

    def test_resolved_config_missing_unload_support_is_rejected(self) -> None:
        path = self.root / "resolved.config"
        requirements = {
            "enabled": ["CONFIG_MODULES", "CONFIG_MODULE_UNLOAD"],
            "disabled": ["CONFIG_MODULE_SIG_FORCE"],
        }
        path.write_text(
            "CONFIG_MODULES=y\n"
            "# CONFIG_MODULE_UNLOAD is not set\n"
            "# CONFIG_MODULE_SIG_FORCE is not set\n",
            encoding="utf-8",
        )
        with self.assertRaisesRegex(evidence.EvidenceError, "CONFIG_MODULE_UNLOAD"):
            evidence._validate_resolved_config(path, requirements)


if __name__ == "__main__":
    unittest.main()
