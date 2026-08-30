#!/usr/bin/env python3

from __future__ import print_function

import contextlib
import copy
import hashlib
import io
import json
import os
from pathlib import Path
import re
import shutil
import shlex
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

import yaml


REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts import native_rust_runtime_evidence as evidence


KERNEL_RELEASE = "6.12.0-211.44.1.el10_2.mckernel1.x86_64"


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
        f"{protocol} MODULE ihk 1 2 mcctrl,ihk_smp_x86_64, Live 0x0",
        f"{protocol} MODULE ihk_smp_x86_64 1 0 - Live 0x0",
        f"{protocol} MODULE mcctrl 1 0 - Live 0x0",
        f"{protocol} STATE_END label=all-loaded",
        f"{protocol} REFCOUNT module=ihk phase=all-loaded references=2 users=mcctrl,ihk_smp_x86_64,",
        f"{protocol} NEGATIVE operation=unload-provider-first status=1",
        f"{protocol} NEGATIVE_OUTPUT_BEGIN",
        "rmmod: ERROR: Module ihk is in use by: mcctrl ihk_smp_x86_64",
        f"{protocol} NEGATIVE_OUTPUT_END",
        f"{protocol} REFCOUNT module=ihk phase=after-negative references=2 "
        "users=mcctrl,ihk_smp_x86_64,",
        f"{protocol} STATE_BEGIN label=after-negative",
        f"{protocol} MODULE ihk 1 2 mcctrl,ihk_smp_x86_64, Live 0x0",
        f"{protocol} MODULE ihk_smp_x86_64 1 0 - Live 0x0",
        f"{protocol} MODULE mcctrl 1 0 - Live 0x0",
        f"{protocol} STATE_END label=after-negative",
        "mcctrl: lifecycle=unload foundation=1 parameters=0 declared_dependencies=1 "
        "ihk_import=source-bound-anchor binfmt=blocked-no-safe-rust-api",
        f"{protocol} UNLOAD module=mcctrl status=ok",
        f"{protocol} REFCOUNT module=ihk phase=after-mcctrl-unload references=1 "
        "users=ihk_smp_x86_64,",
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

    def test_serial_rejects_fatal_diagnostics_across_the_entire_capture(self) -> None:
        signatures = (
            "BUG: kernel NULL pointer dereference",
            "Oops: 0000 [#1] PREEMPT SMP",
            "Kernel panic - not syncing: injected",
            "Call Trace:",
            "general protection fault, probably for non-canonical address",
            "unable to handle kernel NULL pointer dereference at 00000000",
            "KASAN: use-after-free in injected",
            "UBSAN: array-index-out-of-bounds in injected",
            "slab-use-after-free in injected",
            "double free detected in injected",
            "refcount_t: underflow; use-after-free.",
            "watchdog: BUG: soft lockup - CPU#0 stuck for 22s!",
            "NMI watchdog: Watchdog detected hard LOCKUP on cpu 0",
            "INFO: task init:1 blocked for more than 120 seconds.",
            "kmemleak: unreferenced object 0xffff888000000000",
            "unreferenced object 0xffff888000000000 (size 64):",
        )
        valid = valid_serial()
        complete = (
            f"{evidence.PROTOCOL} COMPLETE "
            "status=technical-capture-unreviewed credit=forbidden\n"
        )
        for index, signature in enumerate(signatures):
            for location, mutation in (
                ("before", signature + "\n" + valid),
                ("after", valid + signature + "\n"),
                ("forged-frame", valid.replace(complete, signature + "\n" + complete)),
            ):
                with self.subTest(index=index, location=location):
                    with self.assertRaisesRegex(
                        evidence.EvidenceError, "fatal diagnostic"
                    ):
                        evidence.validate_serial(
                            self.write_serial(mutation), KERNEL_RELEASE
                        )

    def test_serial_crlf_and_panic_command_line_remain_accepted(self) -> None:
        serial = "Kernel command line: console=ttyS0 panic=-1\n" + valid_serial()
        evidence.validate_serial(
            self.write_serial(serial.replace("\n", "\r\n")), KERNEL_RELEASE
        )

    def test_runtime_tool_replay_ignores_hostile_path_and_loader_environment(self) -> None:
        hostile = self.root / "hostile-bin"
        hostile.mkdir()
        for name in ("modinfo", "nm"):
            executable = hostile / name
            executable.write_text(
                "#!/bin/sh\nprintf '%s\\n' "
                + ("'" + KERNEL_RELEASE + "'" if name == "modinfo" else "'ihk_provider_lifecycle_v1'")
                + "\n",
                encoding="ascii",
            )
            executable.chmod(0o755)
        module = self.root / "hostile.ko"
        module.write_bytes(b"not an ELF module\n")
        hostile_environment = {
            "PATH": str(hostile),
            "LD_AUDIT": str(self.root / "attacker-audit.so"),
            "LD_PRELOAD": str(self.root / "attacker-preload.so"),
        }
        with mock.patch.dict(os.environ, hostile_environment, clear=False):
            with self.assertRaises(evidence.EvidenceError):
                evidence._run_field(module, "vermagic")
            with self.assertRaises(evidence.EvidenceError):
                evidence._nm(module, ["-g", "--defined-only"])

    def test_runtime_tool_replay_uses_exact_rocky_argv_and_closed_environment(self) -> None:
        module = self.root / "module.ko"
        module.write_bytes(b"fixture")
        completed = subprocess.CompletedProcess([], 0, stdout="ihk\n", stderr="")
        with mock.patch.object(evidence.subprocess, "run", return_value=completed) as run:
            self.assertEqual(["ihk"], evidence._run_field(module, "depends"))
            arguments = run.call_args.args[0]
            self.assertEqual(evidence.MODINFO_EXECUTABLE, arguments[0])
            self.assertEqual(
                evidence.BOUND_ROCKY_TOOL_ENVIRONMENT,
                run.call_args.kwargs["env"],
            )
        completed = subprocess.CompletedProcess([], 0, stdout="symbol\n", stderr="")
        with mock.patch.object(evidence.subprocess, "run", return_value=completed) as run:
            self.assertEqual("symbol\n", evidence._nm(module, ["-g"]))
            self.assertEqual(evidence.NM_EXECUTABLE, run.call_args.args[0][0])
            self.assertEqual(
                evidence.BOUND_ROCKY_TOOL_ENVIRONMENT,
                run.call_args.kwargs["env"],
            )

    def write_runtime_evidence_artifact(self) -> Path:
        directory = Path(
            tempfile.mkdtemp(prefix="runtime-artifact-", dir=str(self.root))
        )
        contract = json.loads(
            (REPO_ROOT / evidence.DEFAULT_CONTRACT).read_text(encoding="utf-8")
        )
        expected = contract["artifact_contract"]["runtime_evidence_files"]
        for name in expected:
            if name in {"SHA256SUMS", "capture.json"}:
                continue
            (directory / name).write_bytes((name + "\n").encode("ascii"))
        (directory / "serial.log").write_text(valid_serial(), encoding="ascii")
        (directory / "environment.txt").write_text(
            "container_image={0}\n"
            "runner_arch=x86_64\n"
            "os_release_sha256={1}\n"
            "bash-5.2.26-4.el10.x86_64\n"
            "gpg-pubkey-6fedfc85-682ae1a9.(none)\n"
            "qemu-kvm-core-9.1.0-1.el10.x86_64\n".format(
                contract["runtime"]["container_image"],
                evidence.EXPECTED_ROCKY_OS_RELEASE_SHA256,
            ),
            encoding="ascii",
        )
        (directory / "qemu-command.txt").write_text(
            "/usr/libexec/qemu-kvm -machine q35 -accel tcg -cpu max -smp 2 "
            "-m 2048 -kernel /tmp/native-rust-build-evidence/bzImage "
            "-initrd /tmp/native-rust-runtime-evidence/initramfs.cpio.gz "
            "-append console=ttyS0,115200n8\\ rdinit=/init\\ nokaslr\\ panic=-1 "
            "-display none -monitor none "
            "-serial file:/tmp/native-rust-runtime-evidence/serial.log -no-reboot\n",
            encoding="ascii",
        )
        (directory / "qemu-version.txt").write_text(
            "QEMU emulator version 9.1.0\nCopyright QEMU contributors\n",
            encoding="ascii",
        )
        (directory / "qemu.exit-code").write_text("0\n", encoding="ascii")
        (directory / "qemu.log").write_bytes(b"")
        initramfs_digest = hashlib.sha256(
            (directory / "initramfs.cpio.gz").read_bytes()
        ).hexdigest()
        (directory / "initramfs.sha256").write_text(
            initramfs_digest + "  initramfs.cpio.gz\n", encoding="ascii"
        )
        (directory / "workflow-state").write_text(
            "technical-capture-unreviewed\ncredit=forbidden\n", encoding="ascii"
        )
        capture = self.valid_capture_unsigned()
        capture["contract_sha256"] = evidence._sha256_file(
            REPO_ROOT / evidence.DEFAULT_CONTRACT
        )
        runtime_files = {
            "environment_sha256": "environment.txt",
            "initramfs_sha256": "initramfs.cpio.gz",
            "initramfs_sha256_record": "initramfs.sha256",
            "qemu_command_sha256": "qemu-command.txt",
            "qemu_exit_code_sha256": "qemu.exit-code",
            "qemu_log_sha256": "qemu.log",
            "qemu_version_sha256": "qemu-version.txt",
            "serial_sha256": "serial.log",
        }
        for field, name in runtime_files.items():
            capture["runtime"][field] = hashlib.sha256(
                (directory / name).read_bytes()
            ).hexdigest()
        capture["capture_sha256"] = evidence._sha256_bytes(
            evidence._canonical_bytes(capture)
        )
        (directory / "capture.json").write_text(
            evidence._pretty(capture), encoding="utf-8"
        )
        self.rewrite_runtime_manifest(directory)
        return directory

    def reseal_runtime_file(self, directory: Path, name: str, data: bytes) -> None:
        (directory / name).write_bytes(data)
        capture = json.loads((directory / "capture.json").read_text(encoding="utf-8"))
        fields = {
            "environment.txt": "environment_sha256",
            "initramfs.cpio.gz": "initramfs_sha256",
            "initramfs.sha256": "initramfs_sha256_record",
            "qemu-command.txt": "qemu_command_sha256",
            "qemu.exit-code": "qemu_exit_code_sha256",
            "qemu.log": "qemu_log_sha256",
            "qemu-version.txt": "qemu_version_sha256",
            "serial.log": "serial_sha256",
        }
        if name in fields:
            capture["runtime"][fields[name]] = hashlib.sha256(data).hexdigest()
        unsigned = copy.deepcopy(capture)
        unsigned.pop("capture_sha256")
        capture["capture_sha256"] = evidence._sha256_bytes(
            evidence._canonical_bytes(unsigned)
        )
        (directory / "capture.json").write_text(
            evidence._pretty(capture), encoding="utf-8"
        )
        self.rewrite_runtime_manifest(directory)

    def rewrite_runtime_manifest(self, directory: Path) -> None:
        names = sorted(path.name for path in directory.iterdir() if path.name != "SHA256SUMS")
        (directory / "SHA256SUMS").write_text(
            "".join(
                "{}  {}\n".format(
                    hashlib.sha256((directory / name).read_bytes()).hexdigest(), name
                )
                for name in names
            ),
            encoding="ascii",
        )

    def validate_runtime_artifact(self, directory: Path) -> dict:
        capture = json.loads(
            (directory / "capture.json").read_text(encoding="utf-8")
        )
        with mock.patch.object(
            evidence,
            "_validate_build_evidence_directory",
            return_value=(copy.deepcopy(capture["build"]), {}),
        ):
            return evidence.validate_runtime_evidence_directory(
                REPO_ROOT, directory, self.root
            )

    def validate_runtime_files(
        self, directory: Path, expected_build_bzimage=None
    ) -> dict:
        contract = json.loads(
            (REPO_ROOT / evidence.DEFAULT_CONTRACT).read_text(encoding="utf-8")
        )
        return evidence._validate_runtime_files(
            contract,
            directory / "serial.log",
            directory / "qemu.log",
            directory / "qemu-command.txt",
            directory / "qemu-version.txt",
            directory / "qemu.exit-code",
            directory / "environment.txt",
            directory / "initramfs.cpio.gz",
            directory / "initramfs.sha256",
            expected_build_bzimage,
        )

    def valid_capture_unsigned(self) -> dict:
        digest = "1" * 64
        release = KERNEL_RELEASE
        return {
            "schema_version": 1,
            "contract_id": evidence.CONTRACT_ID,
            "contract_sha256": digest,
            "identity": {
                "candidate_sha": "2" * 40,
                "github_repository": "phoenix-hacking/mckernel",
                "github_run_attempt": "1",
                "github_run_id": "1",
            },
            "build": {
                "artifact_manifest_sha256": digest,
                "bzimage_sha256": digest,
                "config_runtime_requirements": copy.deepcopy(
                    evidence.EXPECTED_RUNTIME_REQUIRED_CONFIG
                ),
                "config_sha256": digest,
                "kbuild_link_closure": {
                    "claims": copy.deepcopy(evidence.EXPECTED_LINK_CLAIMS),
                    "module_count": 3,
                    "raw_record_count": len(evidence.EXPECTED_RAW_RECORD_NAMES),
                    "sha256": digest,
                    "stage_lock_sha256": digest,
                },
                "kconfig_solver": {
                    "claims": copy.deepcopy(evidence.SOLVER_EXPECTED_CLAIMS),
                    "counts": copy.deepcopy(evidence.SOLVER_EXPECTED_COUNTS),
                    "limitations": copy.deepcopy(evidence.SOLVER_EXPECTED_LIMITATIONS),
                    "sha256": digest,
                    "status": evidence.SOLVER_CAPTURE_STATUS,
                },
                "kernel_release": release,
                "modules": {
                    "ihk": {
                        "depends": [],
                        "import_namespaces": [],
                        "sha256": digest,
                    },
                    "ihk_smp_x86_64": {
                        "depends": ["ihk"],
                        "import_namespaces": ["MCKERNEL_IHK_V1"],
                        "sha256": digest,
                    },
                    "mcctrl": {
                        "depends": ["ihk"],
                        "import_namespaces": ["MCKERNEL_IHK_V1"],
                        "sha256": digest,
                    },
                },
                "scope": {
                    "build_commands_sha256": digest,
                    "build_environment_sha256": (
                        evidence.EXPECTED_REPRODUCIBLE_BUILD_ENVIRONMENT_SHA256
                    ),
                    "build_log_sha256": digest,
                    "kernel_targets": list(evidence.BUILD_KERNEL_TARGETS),
                    "module_targets": list(evidence.BUILD_MODULE_TARGETS),
                },
            },
            "runtime": {
                "environment_sha256": digest,
                "initramfs_sha256": digest,
                "initramfs_sha256_record": digest,
                "kernel_release": release,
                "negative_unload_status": 1,
                "provider_refcount": 2,
                "provider_users": ["ihk_smp_x86_64", "mcctrl"],
                "qemu_command_sha256": digest,
                "qemu_exit_code_sha256": digest,
                "qemu_log_sha256": digest,
                "qemu_version_sha256": digest,
                "serial_sha256": digest,
            },
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

    def test_repository_contract_passes_without_gate_credit(self) -> None:
        summary = evidence.validate_contract(REPO_ROOT)
        self.assertEqual(evidence.CONTRACT_ID, summary["contract_id"])
        self.assertEqual(["IHK-001", "SMP-001", "MCC-001"], summary["gate_ids"])
        self.assertEqual("tcg", summary["runtime"]["qemu_accelerator"])

    def test_selected_custom_kernel_identity_mutations_fail_closed(self) -> None:
        mutations = (
            ("kernel_release", "6.12.0"),
            ("kernel_release", evidence.EXPECTED_KERNEL_RELEASE + ".unreviewed"),
            ("localversion", "-211.44.1.el10_2.x86_64"),
        )
        for key, value in mutations:
            with self.subTest(key=key, value=value):
                repo = self.copy_contract_repository()
                path = repo / evidence.DEFAULT_CONTRACT
                contract = json.loads(path.read_text(encoding="utf-8"))
                contract["selected_kernel"][key] = value
                path.write_text(json.dumps(contract), encoding="utf-8")
                with self.assertRaisesRegex(
                    evidence.EvidenceError, "selected kernel identity"
                ):
                    evidence.validate_contract(repo)

    def test_reproducible_build_epoch_must_match_the_source_lock(self) -> None:
        repo = self.copy_contract_repository()
        source_lock = repo / "host-kernel/rocky/source-lock.json"
        value = json.loads(source_lock.read_text(encoding="utf-8"))
        value["repository_snapshot"]["primary_metadata"]["timestamp"] += 1
        source_lock.write_text(
            json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        with self.assertRaisesRegex(
            evidence.EvidenceError, "timestamp authority diverges"
        ):
            evidence.validate_contract(repo)

    def test_reproducible_timestamp_format_is_locale_independent(self) -> None:
        with mock.patch("locale.nl_langinfo", return_value="ATTACKER"):
            summary = evidence.validate_contract(REPO_ROOT)
        self.assertEqual(evidence.CONTRACT_ID, summary["contract_id"])

    def test_every_kbuild_invocation_requires_the_exact_localversion(self) -> None:
        relative = ".github/workflows/native-rust-host-modules-exact-build.yml"
        needle = 'LOCALVERSION="$NATIVE_KERNEL_LOCALVERSION"'
        source = (REPO_ROOT / relative).read_text(encoding="utf-8")
        offsets = [match.start() for match in re.finditer(re.escape(needle), source)]
        self.assertEqual(6, len(offsets))
        for index, offset in enumerate(offsets):
            with self.subTest(index=index):
                repo = self.copy_contract_repository()
                path = repo / relative
                text = path.read_text(encoding="utf-8")
                path.write_text(
                    text[:offset] + 'LOCALVERSION="-unreviewed"' + text[offset + len(needle) :],
                    encoding="utf-8",
                )
                with self.assertRaisesRegex(
                    evidence.EvidenceError,
                    "exact build workflow|Kbuild release|kernel-release",
                ):
                    evidence.validate_contract(repo)

    def test_release_environment_and_postbuild_checks_are_immutable(self) -> None:
        relative = ".github/workflows/native-rust-host-modules-exact-build.yml"
        mutations = (
            (
                "EXPECTED_KERNEL_RELEASE: " + evidence.EXPECTED_KERNEL_RELEASE,
                "EXPECTED_KERNEL_RELEASE: 6.12.0",
            ),
            (
                "NATIVE_KERNEL_LOCALVERSION: "
                + evidence.EXPECTED_KERNEL_LOCALVERSION,
                "NATIVE_KERNEL_LOCALVERSION: -unreviewed",
            ),
            (
                'test "${vermagic%% *}" = "$EXPECTED_KERNEL_RELEASE"',
                'test -n "${vermagic%% *}"',
            ),
            (
                'test "$kernel_release" = "$EXPECTED_KERNEL_RELEASE"',
                'test -n "$kernel_release"',
            ),
        )
        for old, new in mutations:
            with self.subTest(new=new):
                repo = self.copy_contract_repository()
                self.mutate_text(repo, relative, old, new)
                with self.assertRaises(evidence.EvidenceError):
                    evidence.validate_contract(repo)

    def test_postcheck_kernel_release_environment_override_is_rejected(self) -> None:
        repo = self.copy_contract_repository()
        relative = ".github/workflows/native-rust-host-modules-exact-build.yml"
        self.mutate_text(
            repo,
            relative,
            "          printf 'NATIVE_BASELINE_CONFIG=%s\\n' \"$baseline\" >> \"$github_env_file\"\n",
            (
                "          printf 'NATIVE_BASELINE_CONFIG=%s\\n' \"$baseline\" >> \"$github_env_file\"\n"
                "          printf 'NATIVE_KERNEL_LOCALVERSION=-attacker\\n' >> \"$github_env_file\"\n"
                "          printf 'EXPECTED_KERNEL_RELEASE=6.12.0-attacker\\n' >> \"$github_env_file\"\n"
            ),
        )
        with self.assertRaisesRegex(evidence.EvidenceError, "prebuild scope differs"):
            evidence.validate_contract(repo)

    def test_crlf_cannot_alias_runtime_or_workflow_byte_identity(self) -> None:
        for relative in (
            "scripts/native-rust-runtime-init.sh",
            ".github/workflows/native-rust-host-modules-exact-build.yml",
        ):
            with self.subTest(relative=relative):
                repo = self.copy_contract_repository()
                path = repo / relative
                raw = path.read_bytes()
                self.assertNotIn(b"\r", raw)
                path.write_bytes(raw.replace(b"\n", b"\r\n"))
                with self.assertRaises(evidence.EvidenceError):
                    evidence.validate_contract(repo)

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

    def test_opaque_initramfs_replay_residual_cannot_be_promoted(self) -> None:
        repo = self.copy_contract_repository()
        path = repo / evidence.DEFAULT_CONTRACT
        contract = json.loads(path.read_text(encoding="utf-8"))
        contract["runtime_verifier_scope"]["initramfs_cpio_replay"] = True
        path.write_text(
            json.dumps(contract, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        with self.assertRaisesRegex(evidence.EvidenceError, "limitation scope"):
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

    def test_runtime_workflow_inserted_serial_rewrite_step_is_rejected(self) -> None:
        repo = self.copy_contract_repository()
        workflow = repo / ".github/workflows/native-rust-host-modules-exact-runtime.yml"
        text = workflow.read_text(encoding="utf-8")
        capture = "      - name: Create a credit-forbidden technical capture\n"
        self.assertEqual(1, text.count(capture))
        injected = (
            "      - name: Rewrite serial evidence after QEMU\n"
            "        if: ${{ always() }}\n"
            "        run: printf fabricated > \"$RUNTIME_EVIDENCE/serial.log\"\n"
        )
        workflow.write_text(text.replace(capture, injected + capture), encoding="utf-8")
        with self.assertRaisesRegex(evidence.EvidenceError, "workflow byte identity"):
            evidence.validate_contract(repo)

    def test_runtime_workflow_identity_contract_cannot_be_refreshed(self) -> None:
        repo = self.copy_contract_repository()
        path = repo / evidence.DEFAULT_CONTRACT
        contract = json.loads(path.read_text(encoding="utf-8"))
        contract["repository_workflow_identities"]["runtime_workflow"]["sha256"] = (
            "0" * 64
        )
        path.write_text(
            json.dumps(contract, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        with self.assertRaisesRegex(evidence.EvidenceError, "workflow identities"):
                evidence.validate_contract(repo)

    def test_runtime_evidence_steps_reject_startup_and_command_channel_mutations(self) -> None:
        workflow = ".github/workflows/native-rust-host-modules-exact-runtime.yml"
        document = yaml.safe_load((REPO_ROOT / workflow).read_text(encoding="utf-8"))
        protected_names = {
            "Verify immutable build inputs and native module link contracts",
            "Assemble a deterministic lifecycle-only initramfs",
            "Boot the exact kernel under QEMU TCG and capture serial diagnostics",
            "Create a credit-forbidden technical capture",
        }
        steps = {
            step["name"]: step
            for step in document["jobs"]["exact-runtime"]["steps"]
            if "run" in step
        }
        loader_keys = {
            "GLIBC_TUNABLES",
            "LD_ASSUME_KERNEL",
            "LD_AUDIT",
            "LD_BIND_NOW",
            "LD_DEBUG",
            "LD_DEBUG_OUTPUT",
            "LD_DYNAMIC_WEAK",
            "LD_HWCAP_MASK",
            "LD_LIBRARY_PATH",
            "LD_ORIGIN_PATH",
            "LD_PREFER_MAP_32BIT_EXEC",
            "LD_PRELOAD",
            "LD_PROFILE",
            "LD_PROFILE_OUTPUT",
        }
        self.assertTrue(protected_names.issubset(steps))
        for name in protected_names:
            environment = steps[name]["env"]
            self.assertEqual(
                {key: "" for key in loader_keys},
                {key: environment[key] for key in loader_keys},
            )
            self.assertNotIn("LD_SHOW_AUXV", environment)
            run_lines = [
                line.strip()
                for line in steps[name]["run"].splitlines()
                if line.strip()
            ]
            self.assertEqual(
                ["set -euo pipefail", "unset LD_SHOW_AUXV"],
                run_lines[:2],
            )
        mutations = (
            (
                "shell: /usr/bin/bash --noprofile --norc -p -e -o pipefail {0}",
                "shell: bash",
            ),
            ('          LD_AUDIT: ""\n', ""),
            (
                '          LD_PROFILE_OUTPUT: ""\n',
                '          LD_PROFILE_OUTPUT: ""\n'
                '          LD_SHOW_AUXV: ""\n',
            ),
            (
                "          PATH=/usr/sbin:/usr/bin:/sbin:/bin\n"
                "          export PATH\n",
                "          export PATH\n",
            ),
            (
                "          set -euo pipefail\n          unset LD_SHOW_AUXV\n",
                "          set -euo pipefail\n",
            ),
            (
                "          set -euo pipefail\n          unset LD_SHOW_AUXV\n",
                "          unset LD_SHOW_AUXV\n          set -euo pipefail\n",
            ),
            (
                "          unset GITHUB_ENV GITHUB_PATH\n",
                "          printf 'LD_AUDIT=/tmp/attacker.so\\n' >> \"$github_env_file\"\n",
            ),
        )
        for old, new in mutations:
            with self.subTest(new=new):
                repo = self.copy_contract_repository()
                self.mutate_text(repo, workflow, old, new)
                with self.assertRaises(evidence.EvidenceError):
                    evidence.validate_contract(repo)

    def test_runtime_checkout_cannot_omit_git(self) -> None:
        repo = self.copy_contract_repository()
        workflow = ".github/workflows/native-rust-host-modules-exact-runtime.yml"
        self.mutate_text(
            repo,
            workflow,
            "gawk git-core gzip kmod",
            "gawk gzip kmod",
        )
        with self.assertRaisesRegex(
            evidence.EvidenceError,
            "runtime workflow coreutils replacement transaction differs",
        ):
            evidence.validate_contract(repo)

    def test_runtime_git_bootstrap_cannot_move_after_checkout(self) -> None:
        repo = self.copy_contract_repository()
        workflow = ".github/workflows/native-rust-host-modules-exact-runtime.yml"
        path = repo / workflow
        text = path.read_text(encoding="utf-8")
        bootstrap_header = (
            "      - name: Initialize first-failure evidence and exact Rocky tools\n"
        )
        checkout_header = (
            "      - name: Check out the exact candidate without credentials\n"
        )
        download_header = (
            "      - name: Download the exact build artifact from this run\n"
        )
        bootstrap_start = text.index(bootstrap_header)
        checkout_start = text.index(checkout_header)
        download_start = text.index(download_header)
        bootstrap = text[bootstrap_start:checkout_start]
        checkout = text[checkout_start:download_start]
        path.write_text(
            text[:bootstrap_start]
            + checkout
            + bootstrap
            + text[download_start:],
            encoding="utf-8",
        )
        with self.assertRaisesRegex(
            evidence.EvidenceError, "Git bootstrap must precede checkout"
        ):
            evidence.validate_contract(repo)

    def test_runtime_workflow_reusable_trigger_mutation_is_rejected(self) -> None:
        repo = self.copy_contract_repository()
        workflow = ".github/workflows/native-rust-host-modules-exact-runtime.yml"
        self.mutate_text(
            repo,
            workflow,
            "  workflow_call:\n"
            "    inputs:\n"
            "      validation_sha:\n"
            "        description: Exact 40-hex candidate commit\n"
            "        required: true\n"
            "        type: string\n",
            "",
        )
        with self.assertRaisesRegex(
            evidence.EvidenceError, "dispatch/reusable trigger boundary"
        ):
            evidence.validate_contract(repo)

    def test_pr_wrapper_mutations_fail_closed(self) -> None:
        wrapper = ".github/workflows/native-rust-host-modules-exact-runtime-pr.yml"
        mutations = (
            (
                "${{ github.event.pull_request.head.repo.full_name == github.repository }}",
                "${{ always() }}",
            ),
            (
                "validation_sha: ${{ github.event.pull_request.head.sha }}",
                "validation_sha: ${{ github.sha }}",
            ),
            ("contents: read", "contents: write"),
            ("  pull_request:\n", "  pull_request_target:\n"),
            ("    with:\n", "    secrets: inherit\n    with:\n"),
            ("      - scripts/**\n", ""),
        )
        for old, new in mutations:
            with self.subTest(new=new):
                repo = self.copy_contract_repository()
                self.mutate_text(repo, wrapper, old, new)
                with self.assertRaisesRegex(
                    evidence.EvidenceError,
                    "runtime PR wrapper trust/exact-head boundary differs",
                ):
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
        with self.assertRaisesRegex(
            evidence.EvidenceError, "bootstrap scope differs|OpenSSL CLI closure"
        ):
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
        with self.assertRaisesRegex(
            evidence.EvidenceError, "bootstrap scope differs|OpenSSL CLI closure"
        ):
            evidence.validate_contract(repo)

    def test_runtime_config_fragment_mutations_fail_closed(self) -> None:
        relative = "host-kernel/rocky/configs/native-rust-evidence.config"
        mutations = (
            ("CONFIG_MODULES=y\n", ""),
            ("CONFIG_MODULES=y", "CONFIG_MODULES=m"),
            ("CONFIG_MODULES=y", "# CONFIG_MODULES=y"),
            ("CONFIG_MCKERNEL_IHK_RUST=m", "CONFIG_MCKERNEL_IHK_RUST=y"),
            (
                "CONFIG_MODULES=y\nCONFIG_MCKERNEL_IHK_RUST=m\n",
                "CONFIG_MCKERNEL_IHK_RUST=m\nCONFIG_MODULES=y\n",
            ),
            (
                "CONFIG_MCKERNEL_MCCTRL_RUST=m\n",
                "CONFIG_MCKERNEL_MCCTRL_RUST=m\nCONFIG_MCKERNEL_EXTRA_RUST=m\n",
            ),
            (
                "CONFIG_MCKERNEL_IHK_RUST=m\n",
                "CONFIG_MCKERNEL_IHK_RUST=m\nCONFIG_MCKERNEL_IHK_RUST=m\n",
            ),
            (
                "CONFIG_MODULES=y\n",
                "CONFIG_MODULES=y\n# CONFIG_MODULES is not set\n",
            ),
        )
        for old, new in mutations:
            with self.subTest(new=new):
                repo = self.copy_contract_repository()
                self.mutate_text(repo, relative, old, new)
                with self.assertRaisesRegex(
                    evidence.EvidenceError, "runtime config fragment policy violation"
                ):
                    evidence.validate_contract(repo)

    def test_runtime_config_comment_substrings_cannot_satisfy_assignments(self) -> None:
        repo = self.copy_contract_repository()
        relative = "host-kernel/rocky/configs/native-rust-evidence.config"
        self.mutate_text(
            repo,
            relative,
            "CONFIG_MODULES=y",
            "# runtime note contains CONFIG_MODULES=y",
        )
        with self.assertRaisesRegex(
            evidence.EvidenceError, "runtime config fragment policy violation"
        ):
            evidence.validate_contract(repo)

    def test_workflow_must_check_resolved_modules_prerequisite(self) -> None:
        repo = self.copy_contract_repository()
        workflow = ".github/workflows/native-rust-host-modules-exact-build.yml"
        self.mutate_text(
            repo,
            workflow,
            '          grep -qx \'CONFIG_MODULES=y\' "$BUILD_DIR/.config"\n',
            "",
        )
        with self.assertRaisesRegex(
            evidence.EvidenceError, "CONFIG_MODULES prerequisite differs"
        ):
            evidence.validate_contract(repo)

    def test_required_artifact_removal_is_rejected(self) -> None:
        repo = self.copy_contract_repository()
        path = repo / evidence.DEFAULT_CONTRACT
        contract = json.loads(path.read_text(encoding="utf-8"))
        contract["artifact_contract"]["runtime_evidence_files"].remove("serial.log")
        path.write_text(json.dumps(contract, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        with self.assertRaisesRegex(evidence.EvidenceError, "artifact file set differs"):
            evidence.validate_contract(repo)

    def test_runtime_artifact_exact_member_set_is_reconciled(self) -> None:
        directory = self.write_runtime_evidence_artifact()
        records = self.validate_runtime_artifact(directory)
        self.assertIn("native-rust-runtime-poweroff.o", records)
        self.assertEqual(12, len(records) + 1)

    def test_runtime_artifact_missing_or_extra_member_is_rejected(self) -> None:
        for mutation in ("missing-poweroff", "extra"):
            with self.subTest(mutation=mutation):
                directory = self.write_runtime_evidence_artifact()
                if mutation == "missing-poweroff":
                    (directory / "native-rust-runtime-poweroff.o").unlink()
                else:
                    (directory / "unexpected.bin").write_bytes(b"unexpected\n")
                self.rewrite_runtime_manifest(directory)
                with self.assertRaisesRegex(
                    evidence.EvidenceError, "artifact file set differs"
                ):
                    self.validate_runtime_artifact(directory)

    def test_runtime_artifact_hostile_self_reseal_cannot_replace_semantics(self) -> None:
        mutations = (
            ("serial.log", b"self-resealed serial\n", "serial"),
            ("qemu.exit-code", b"1\n", "QEMU did not exit"),
            (
                "qemu-command.txt",
                b"/usr/libexec/qemu-kvm -machine q35 -accel kvm\n",
                "QEMU command",
            ),
            (
                "environment.txt",
                b"container_image=attacker\nrunner_arch=x86_64\n",
                "runtime environment",
            ),
            ("qemu-version.txt", b"not qemu\n", "QEMU version"),
        )
        for name, data, diagnostic in mutations:
            with self.subTest(name=name):
                directory = self.write_runtime_evidence_artifact()
                self.reseal_runtime_file(directory, name, data)
                with self.assertRaisesRegex(evidence.EvidenceError, diagnostic):
                    self.validate_runtime_artifact(directory)

    def test_qemu_command_rejects_exact_argv_decoys_and_accelerator_changes(self) -> None:
        mutations = (
            (
                "/usr/libexec/qemu-kvm -machine",
                "/usr/bin/printf /usr/libexec/qemu-kvm -machine",
            ),
            ("-accel tcg", "-accel tcg -accel tcg"),
            ("-accel tcg", "-accel kvm"),
            (
                "-machine q35",
                "-machine q35 -object memory-backend-file,mem-path=/dev/kvm",
            ),
            ("-no-reboot\n", "-no-reboot -nodefaults\n"),
        )
        for old, new in mutations:
            with self.subTest(new=new):
                directory = self.write_runtime_evidence_artifact()
                command = (directory / "qemu-command.txt").read_text(encoding="ascii")
                self.assertIn(old, command)
                self.reseal_runtime_file(
                    directory,
                    "qemu-command.txt",
                    command.replace(old, new, 1).encode("ascii"),
                )
                with self.assertRaisesRegex(evidence.EvidenceError, "QEMU command"):
                    self.validate_runtime_artifact(directory)

    def test_capture_qemu_paths_must_equal_supplied_files(self) -> None:
        source = self.write_runtime_evidence_artifact()
        runtime_dir = self.root / "native-rust-runtime-evidence"
        source.rename(runtime_dir)
        build_dir = self.root / "native-rust-build-evidence"
        build_dir.mkdir()
        bzimage = build_dir / "bzImage"
        bzimage.write_bytes(b"bootable fixture\n")
        command_path = runtime_dir / "qemu-command.txt"
        command = command_path.read_text(encoding="ascii")
        command = command.replace(
            "/tmp/native-rust-build-evidence/bzImage", str(bzimage)
        ).replace(
            "/tmp/native-rust-runtime-evidence/initramfs.cpio.gz",
            str(runtime_dir / "initramfs.cpio.gz"),
        ).replace(
            "/tmp/native-rust-runtime-evidence/serial.log",
            str(runtime_dir / "serial.log"),
        )
        command_path.write_text(command, encoding="ascii")
        self.validate_runtime_files(runtime_dir, bzimage)

        substitutions = (
            (
                str(bzimage),
                str(self.root / "decoy" / "native-rust-build-evidence" / "bzImage"),
            ),
            (
                str(runtime_dir / "initramfs.cpio.gz"),
                str(
                    self.root
                    / "decoy"
                    / "native-rust-runtime-evidence"
                    / "initramfs.cpio.gz"
                ),
            ),
            (
                str(runtime_dir / "serial.log"),
                str(
                    self.root
                    / "decoy"
                    / "native-rust-runtime-evidence"
                    / "serial.log"
                ),
            ),
        )
        for old, new in substitutions:
            with self.subTest(decoy=new):
                command_path.write_text(command.replace(old, new, 1), encoding="ascii")
                with self.assertRaisesRegex(
                    evidence.EvidenceError,
                    "QEMU command (?:paths differ from captured build/runtime inputs|runtime evidence roots diverge)",
                ):
                    self.validate_runtime_files(runtime_dir, bzimage)
        command_path.write_text(command, encoding="ascii")

    def test_check_runtime_evidence_requires_same_run_build_directory(self) -> None:
        stderr = io.StringIO()
        with contextlib.redirect_stderr(stderr):
            status = evidence.main(
                [
                    "--repo",
                    str(REPO_ROOT),
                    "--check-runtime-evidence",
                    "--runtime-evidence-dir",
                    str(self.root),
                ]
            )
        self.assertEqual(1, status)
        self.assertIn("requires --runtime-evidence-dir and --build-evidence-dir", stderr.getvalue())

    def test_runtime_artifact_cannot_self_reseal_build_identity(self) -> None:
        directory = self.write_runtime_evidence_artifact()
        capture = json.loads(
            (directory / "capture.json").read_text(encoding="utf-8")
        )
        replayed_build = copy.deepcopy(capture["build"])
        capture["build"]["artifact_manifest_sha256"] = "f" * 64
        unsigned = copy.deepcopy(capture)
        unsigned.pop("capture_sha256")
        capture["capture_sha256"] = evidence._sha256_bytes(
            evidence._canonical_bytes(unsigned)
        )
        (directory / "capture.json").write_text(
            evidence._pretty(capture), encoding="utf-8"
        )
        self.rewrite_runtime_manifest(directory)
        with mock.patch.object(
            evidence,
            "_validate_build_evidence_directory",
            return_value=(replayed_build, {}),
        ):
            with self.assertRaisesRegex(
                evidence.EvidenceError, "build evidence facts differ"
            ):
                evidence.validate_runtime_evidence_directory(
                    REPO_ROOT, directory, self.root
                )

    def test_runtime_artifact_manifest_must_be_canonical_order(self) -> None:
        directory = self.write_runtime_evidence_artifact()
        manifest = directory / "SHA256SUMS"
        rows = manifest.read_text(encoding="ascii").splitlines(True)
        self.assertGreater(len(rows), 1)
        manifest.write_text("".join(reversed(rows)), encoding="ascii")
        with self.assertRaisesRegex(evidence.EvidenceError, "canonical-order"):
            self.validate_runtime_artifact(directory)

    def test_capture_build_environment_digest_is_canonical(self) -> None:
        value = self.valid_capture_unsigned()
        value["build"]["scope"]["build_environment_sha256"] = "4" * 64
        value["capture_sha256"] = evidence._sha256_bytes(
            evidence._canonical_bytes(value)
        )
        with self.assertRaisesRegex(
            evidence.EvidenceError, "build environment digest differs"
        ):
            evidence.validate_capture(value)

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

    def test_init_provider_user_grammar_mutations_fail_closed(self) -> None:
        relative = "scripts/native-rust-runtime-init.sh"
        mutations = (
            (
                "mcctrl,ihk_smp_x86_64,|ihk_smp_x86_64,mcctrl,) ;;",
                "*,ihk_smp_x86_64,*) ;;",
            ),
            (
                '[ "$users" = \'ihk_smp_x86_64,\' ]',
                '[ "$users" = ihk_smp_x86_64 ]',
            ),
        )
        for old, new in mutations:
            with self.subTest(new=new):
                repo = self.copy_contract_repository()
                self.mutate_text(repo, relative, old, new)
                with self.assertRaisesRegex(
                    evidence.EvidenceError, "provider-user grammar"
                ):
                    evidence.validate_contract(repo)

    def test_commented_provider_user_decoys_fail_closed(self) -> None:
        relative = "scripts/native-rust-runtime-init.sh"
        mutations = (
            (
                "mcctrl,ihk_smp_x86_64,|ihk_smp_x86_64,mcctrl,) ;;",
                "*) ;; # mcctrl,ihk_smp_x86_64,|ihk_smp_x86_64,mcctrl,) ;;",
            ),
            (
                '[ "$users" = \'ihk_smp_x86_64,\' ] || { fail wrong-users-after-mcctrl; exit 1; }',
                'true # [ "$users" = \'ihk_smp_x86_64,\' ] || { fail wrong-users-after-mcctrl; exit 1; }',
            ),
        )
        for old, new in mutations:
            with self.subTest(new=new):
                repo = self.copy_contract_repository()
                self.mutate_text(repo, relative, old, new)
                with self.assertRaisesRegex(
                    evidence.EvidenceError, "provider-user grammar"
                ):
                    evidence.validate_contract(repo)

    def test_unreachable_and_wrong_phase_provider_user_decoys_fail_closed(self) -> None:
        relative = "scripts/native-rust-runtime-init.sh"
        canonical = "mcctrl,ihk_smp_x86_64,|ihk_smp_x86_64,mcctrl,) ;;"
        sole = (
            '[ "$users" = \'ihk_smp_x86_64,\' ] || '
            "{ fail wrong-users-after-mcctrl; exit 1; }"
        )
        mutations = (
            (
                canonical,
                "*) ;;",
                "\nif false; then\ncase x in\n" + canonical + "\nesac\nfi\n",
            ),
            (
                sole,
                "true",
                "\nif false; then\n" + sole + "\nfi\n",
            ),
        )
        for old, new, suffix in mutations:
            with self.subTest(new=new):
                repo = self.copy_contract_repository()
                self.mutate_text(repo, relative, old, new)
                path = repo / relative
                path.write_text(path.read_text(encoding="utf-8") + suffix, encoding="utf-8")
                with self.assertRaisesRegex(
                    evidence.EvidenceError,
                    "provider-user grammar|runtime init identity",
                ):
                    evidence.validate_contract(repo)

        repo = self.copy_contract_repository()
        path = repo / relative
        text = path.read_text(encoding="utf-8")
        all_loaded = canonical + "\n*) fail wrong-provider-users; exit 1 ;;"
        after_negative = canonical + "\n*) fail negative-test-changed-users; exit 1 ;;"
        self.assertIn(all_loaded, text)
        self.assertIn(after_negative, text)
        text = text.replace(all_loaded, canonical + "\n" + all_loaded, 1)
        text = text.replace(
            after_negative,
            "*) ;;\n*) fail negative-test-changed-users; exit 1 ;;",
            1,
        )
        path.write_text(text, encoding="utf-8")
        with self.assertRaisesRegex(evidence.EvidenceError, "runtime init identity"):
            evidence.validate_contract(repo)

    def test_complete_serial_protocol_is_accepted(self) -> None:
        result = evidence.validate_serial(self.write_serial(valid_serial()), KERNEL_RELEASE)
        self.assertEqual(2, result["provider_refcount"])
        self.assertEqual(["ihk_smp_x86_64", "mcctrl"], result["provider_users"])
        self.assertEqual(1, result["negative_unload_status"])

    def test_timestamped_lifecycle_and_module_taint_grammar_is_accepted(self) -> None:
        serial = valid_serial()
        module_rows = (
            "MODULE ihk 1 2 mcctrl,ihk_smp_x86_64, Live 0x0",
            "MODULE ihk_smp_x86_64 1 0 - Live 0x0",
            "MODULE mcctrl 1 0 - Live 0x0",
        )
        for row in module_rows:
            serial = serial.replace(row, row + " (E)")
        for marker in (
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
        ):
            serial = serial.replace(marker, "[    4.110654] " + marker)
        result = evidence.validate_serial(self.write_serial(serial), KERNEL_RELEASE)
        self.assertEqual(1, result["negative_unload_status"])

    def test_prefixed_protocol_and_lifecycle_decoys_are_rejected(self) -> None:
        protocol = evidence.PROTOCOL
        for record in (
            f"{protocol} BEGIN",
            f"{protocol} LOAD module=ihk status=ok",
            f"{protocol} UNLOAD module=mcctrl status=ok",
            f"{protocol} COMPLETE status=technical-capture-unreviewed credit=forbidden",
        ):
            with self.subTest(record=record):
                serial = valid_serial().replace(record, "ATTACKER-DECOY " + record, 1)
                with self.assertRaises(evidence.EvidenceError):
                    evidence.validate_serial(self.write_serial(serial), KERNEL_RELEASE)

        lifecycle = (
            "mcctrl: lifecycle=load foundation=1 parameters=0 declared_dependencies=1 "
            "ihk_import=source-bound-anchor binfmt=blocked-no-safe-rust-api"
        )
        serial = valid_serial()
        first = serial.index(lifecycle)
        second = serial.index(lifecycle, first + len(lifecycle))
        serial = serial[:second] + "ATTACKER-DECOY " + serial[second:]
        with self.assertRaisesRegex(evidence.EvidenceError, "lifecycle diagnostics"):
            evidence.validate_serial(self.write_serial(serial), KERNEL_RELEASE)

    def test_negative_diagnostic_requires_one_exact_bounded_line(self) -> None:
        canonical = "rmmod: ERROR: Module ihk is in use by: mcctrl ihk_smp_x86_64"
        for mutation in (
            "ATTACKER-DECOY " + canonical,
            canonical + " unrelated",
            canonical + "\n" + canonical,
        ):
            with self.subTest(mutation=mutation):
                serial = valid_serial().replace(canonical, mutation, 1)
                with self.assertRaisesRegex(evidence.EvidenceError, "in-use diagnostic"):
                    evidence.validate_serial(self.write_serial(serial), KERNEL_RELEASE)

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
            "REFCOUNT module=ihk phase=all-loaded references=2 users=mcctrl,ihk_smp_x86_64,",
            "REFCOUNT module=ihk phase=all-loaded references=2 users=mcctrl,",
            1,
        )
        with self.assertRaisesRegex(evidence.EvidenceError, "provider refcount/users differ"):
            evidence.validate_serial(self.write_serial(serial), KERNEL_RELEASE)

    def test_noncanonical_provider_user_grammars_are_rejected(self) -> None:
        canonical = (
            "REFCOUNT module=ihk phase=all-loaded references=2 "
            "users=mcctrl,ihk_smp_x86_64,"
        )
        mutations = (
            canonical[:-1],
            canonical + ",",
            canonical.replace(
                "users=mcctrl,ihk_smp_x86_64,",
                "users=mcctrl,mcctrl,ihk_smp_x86_64,",
            ),
            canonical.replace(
                "users=mcctrl,ihk_smp_x86_64,",
                "users=mcctrl,ihk_smp_x86_64,unrelated,",
            ),
        )
        for mutation in mutations:
            with self.subTest(mutation=mutation):
                serial = valid_serial().replace(canonical, mutation, 1)
                with self.assertRaises(evidence.EvidenceError):
                    evidence.validate_serial(self.write_serial(serial), KERNEL_RELEASE)

    def test_noncanonical_proc_modules_users_are_rejected(self) -> None:
        canonical = "MODULE ihk 1 2 mcctrl,ihk_smp_x86_64, Live 0x0"
        serial = valid_serial().replace(canonical, canonical.replace(", Live", " Live"), 1)
        with self.assertRaisesRegex(evidence.EvidenceError, "provider user grammar"):
            evidence.validate_serial(self.write_serial(serial), KERNEL_RELEASE)

    def test_proc_modules_provider_row_mutations_fail_closed(self) -> None:
        canonical = "MODULE ihk 1 2 mcctrl,ihk_smp_x86_64, Live 0x0"
        mutations = (
            "MODULE ihk 1 2 mcctrl,mcctrl,ihk_smp_x86_64, Live 0x0",
            "MODULE ihk 1 2 mcctrl,,ihk_smp_x86_64, Live 0x0",
            "MODULE ihk 1 2 mcctrl,ihk_smp_x86_64,unrelated, Live 0x0",
            "MODULE ihk 1 2 mcctrl,ihk_smp_x86_64, Live",
            "MODULE ihk 1 2 mcctrl,ihk_smp_x86_64, Live 0x0 extra",
            "MODULE ihk 1 2 mcctrl,ihk_smp_x86_64, Loading 0x0",
            "MODULE ihk size 2 mcctrl,ihk_smp_x86_64, Live 0x0",
            "MODULE ihk 1 refs mcctrl,ihk_smp_x86_64, Live 0x0",
            "MODULE ihk 1 2 mcctrl,ihk_smp_x86_64, Live address",
        )
        for mutation in mutations:
            with self.subTest(mutation=mutation):
                serial = valid_serial().replace(canonical, mutation, 1)
                with self.assertRaises(evidence.EvidenceError):
                    evidence.validate_serial(self.write_serial(serial), KERNEL_RELEASE)

    def test_proc_modules_consumer_row_mutations_fail_closed(self) -> None:
        for module in ("ihk_smp_x86_64", "mcctrl"):
            canonical = "MODULE {0} 1 0 - Live 0x0".format(module)
            mutations = (
                "MODULE {0} bogus garbage Loading attacker extra".format(module),
                "MODULE {0} size 0 - Live 0x0".format(module),
                "MODULE {0} 1 refs - Live 0x0".format(module),
                "MODULE {0} 1 1 - Live 0x0".format(module),
                "MODULE {0} 1 0 ihk, Live 0x0".format(module),
                "MODULE {0} 1 0 - Loading 0x0".format(module),
                "MODULE {0} 1 0 - Live address".format(module),
                "MODULE {0} 1 0 - Live 0x0 extra".format(module),
            )
            for mutation in mutations:
                with self.subTest(module=module, mutation=mutation):
                    serial = valid_serial().replace(canonical, mutation, 1)
                    with self.assertRaises(evidence.EvidenceError):
                        evidence.validate_serial(
                            self.write_serial(serial), KERNEL_RELEASE
                        )

    def test_loaded_module_size_must_be_positive_in_both_frames(self) -> None:
        rows = (
            "MODULE ihk 1 2 mcctrl,ihk_smp_x86_64, Live 0x0",
            "MODULE ihk_smp_x86_64 1 0 - Live 0x0",
            "MODULE mcctrl 1 0 - Live 0x0",
        )
        for row in rows:
            with self.subTest(row=row):
                mutation = row.replace(" 1 ", " 0 ", 1)
                serial = valid_serial().replace(row, mutation)
                with self.assertRaises(evidence.EvidenceError):
                    evidence.validate_serial(self.write_serial(serial), KERNEL_RELEASE)

    def test_proc_modules_taint_grammar_and_stability_are_bound(self) -> None:
        canonical = "MODULE mcctrl 1 0 - Live 0x0"
        for suffix in (" (e)", " E", " (E) extra"):
            with self.subTest(suffix=suffix):
                serial = valid_serial().replace(canonical, canonical + suffix, 1)
                with self.assertRaises(evidence.EvidenceError):
                    evidence.validate_serial(self.write_serial(serial), KERNEL_RELEASE)

        serial = valid_serial()
        first = serial.index(canonical)
        second = serial.index(canonical, first + len(canonical))
        serial = serial[:second] + serial[second:].replace(
            canonical, canonical + " (E)", 1
        )
        with self.assertRaisesRegex(
            evidence.EvidenceError, "complete /proc/modules state"
        ):
            evidence.validate_serial(self.write_serial(serial), KERNEL_RELEASE)

    def test_negative_test_must_preserve_complete_module_state(self) -> None:
        mutations = {
            "ihk": "MODULE ihk 2 2 mcctrl,ihk_smp_x86_64, Live 0x0",
            "ihk_smp_x86_64": "MODULE ihk_smp_x86_64 1 0 - Live 0x1",
            "mcctrl": "MODULE mcctrl 2 0 - Live 0x0",
        }
        for module, mutation in mutations.items():
            with self.subTest(module=module):
                canonical = {
                    "ihk": "MODULE ihk 1 2 mcctrl,ihk_smp_x86_64, Live 0x0",
                    "ihk_smp_x86_64": "MODULE ihk_smp_x86_64 1 0 - Live 0x0",
                    "mcctrl": "MODULE mcctrl 1 0 - Live 0x0",
                }[module]
                serial = valid_serial()
                first = serial.index(canonical)
                second = serial.index(canonical, first + len(canonical))
                serial = serial[:second] + serial[second:].replace(
                    canonical, mutation, 1
                )
                with self.assertRaisesRegex(
                    evidence.EvidenceError, "complete /proc/modules state"
                ):
                    evidence.validate_serial(self.write_serial(serial), KERNEL_RELEASE)

    def test_sole_provider_user_requires_canonical_trailing_comma(self) -> None:
        canonical = (
            "REFCOUNT module=ihk phase=after-mcctrl-unload references=1 "
            "users=ihk_smp_x86_64,"
        )
        for users in ("ihk_smp_x86_64", "mcctrl,", "ihk_smp_x86_64,mcctrl,"):
            with self.subTest(users=users):
                serial = valid_serial().replace(
                    canonical,
                    canonical.split("users=", 1)[0] + "users=" + users,
                    1,
                )
                with self.assertRaises(evidence.EvidenceError):
                    evidence.validate_serial(self.write_serial(serial), KERNEL_RELEASE)

    def test_custom_kernel_release_rejects_bare_wrong_arch_and_extra_suffix(self) -> None:
        for release in (
            "6.12.0",
            "6.12.0-211.44.1.el10_2.mckernel1.aarch64",
            KERNEL_RELEASE + ".unreviewed",
        ):
            with self.subTest(release=release):
                unsigned = self.valid_capture_unsigned()
                unsigned["build"]["kernel_release"] = release
                unsigned["runtime"]["kernel_release"] = release
                value = copy.deepcopy(unsigned)
                value["capture_sha256"] = evidence._sha256_bytes(
                    evidence._canonical_bytes(unsigned)
                )
                with self.assertRaisesRegex(evidence.EvidenceError, "kernel release"):
                    evidence.validate_capture(value)

    def test_module_vermagic_release_is_exact_and_unique(self) -> None:
        module = self.root / "ihk.ko"
        for records in (
            [],
            [KERNEL_RELEASE + " SMP", KERNEL_RELEASE + " SMP"],
            ["6.12.0 SMP"],
            [KERNEL_RELEASE + ".unreviewed SMP"],
        ):
            with self.subTest(records=records), mock.patch.object(
                evidence, "_run_field", return_value=records
            ):
                with self.assertRaisesRegex(evidence.EvidenceError, "vermagic"):
                    evidence._module_vermagic_release(module)
        with mock.patch.object(
            evidence, "_run_field", return_value=[KERNEL_RELEASE + " SMP preempt"]
        ):
            self.assertEqual(KERNEL_RELEASE, evidence._module_vermagic_release(module))

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
        unsigned = self.valid_capture_unsigned()
        capture = copy.deepcopy(unsigned)
        capture["capture_sha256"] = evidence._sha256_bytes(evidence._canonical_bytes(unsigned))
        evidence.validate_capture(capture)
        capture["readiness"]["credit_eligible"] = True
        with self.assertRaisesRegex(evidence.EvidenceError, "bypass independent review"):
            evidence.validate_capture(capture)

    def test_capture_rejects_omitted_or_positive_phase2_summaries(self) -> None:
        mutations = []
        omitted = self.valid_capture_unsigned()
        omitted["build"] = {}
        mutations.append(omitted)
        solver = self.valid_capture_unsigned()
        solver["build"]["kconfig_solver"]["claims"]["credit_eligible"] = True
        mutations.append(solver)
        link = self.valid_capture_unsigned()
        link["build"]["kbuild_link_closure"]["claims"]["production_ready"] = True
        mutations.append(link)
        float_count = self.valid_capture_unsigned()
        float_count["build"]["kconfig_solver"]["counts"]["case_count"] = 54.0
        mutations.append(float_count)
        extra = self.valid_capture_unsigned()
        extra["build"]["kconfig_solver"]["extra"] = False
        mutations.append(extra)
        for index, unsigned in enumerate(mutations):
            with self.subTest(index=index):
                value = copy.deepcopy(unsigned)
                value["capture_sha256"] = evidence._sha256_bytes(
                    evidence._canonical_bytes(unsigned)
                )
                with self.assertRaises(evidence.EvidenceError):
                    evidence.validate_capture(value)

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

    def test_build_manifest_rejects_noncanonical_row_order(self) -> None:
        directory = self.root / "build-order"
        directory.mkdir()
        records = []
        for name in ("a", "b"):
            path = directory / name
            path.write_bytes((name + "\n").encode("ascii"))
            records.append((hashlib.sha256(path.read_bytes()).hexdigest(), name))
        (directory / "SHA256SUMS").write_text(
            "".join("{0}  {1}\n".format(*row) for row in reversed(records)),
            encoding="ascii",
        )
        with self.assertRaisesRegex(evidence.EvidenceError, "canonical-order"):
            evidence._parse_sums(directory)

    def test_precheck_manifest_exact_26_member_closure_is_enforced(self) -> None:
        self.assertEqual(26, len(evidence.EXPECTED_PRECHECK_BUILD_MEMBERS))
        self.assertIn(
            "build.environment", evidence.EXPECTED_PRECHECK_BUILD_MEMBERS
        )
        base = self.root / "precheck-base"
        base.mkdir()
        final_records = {}
        for name in evidence.EXPECTED_PRECHECK_BUILD_MEMBERS:
            data = (name + "\n").encode("ascii")
            (base / name).write_bytes(data)
            final_records[name] = hashlib.sha256(data).hexdigest()
        canonical = "".join(
            "{0}  {1}\n".format(final_records[name], name)
            for name in evidence.EXPECTED_PRECHECK_BUILD_MEMBERS
        )
        (base / "PRECHECK_SHA256SUMS").write_text(canonical, encoding="ascii")
        self.assertEqual(
            final_records,
            evidence._parse_precheck_sums(
                base,
                final_records,
                evidence.EXPECTED_PRECHECK_BUILD_MEMBERS,
            ),
        )

        rows = canonical.splitlines(True)
        mutations = {
            "missing": "".join(rows[1:]),
            "extra": canonical + ("0" * 64) + "  unexpected\n",
            "duplicate": canonical + rows[0],
            "reordered": "".join(reversed(rows)),
            "digest": ("0" * 64) + rows[0][64:] + "".join(rows[1:]),
        }
        for label, content in mutations.items():
            with self.subTest(label=label):
                (base / "PRECHECK_SHA256SUMS").write_text(
                    content, encoding="ascii"
                )
                with self.assertRaises(evidence.EvidenceError):
                    evidence._parse_precheck_sums(
                        base,
                        final_records,
                        evidence.EXPECTED_PRECHECK_BUILD_MEMBERS,
                    )
        (base / "PRECHECK_SHA256SUMS").write_text(canonical, encoding="ascii")

    def test_build_artifact_file_set_is_exact_regular_and_mode_bound(self) -> None:
        directory = self.root / "exact-build"
        directory.mkdir()
        payload = directory / "payload"
        payload.write_bytes(b"bounded\n")
        digest = hashlib.sha256(payload.read_bytes()).hexdigest()
        sums = directory / "SHA256SUMS"
        sums.write_text("{0}  payload\n".format(digest), encoding="utf-8")
        expected = ["SHA256SUMS", "payload"]
        evidence._validate_exact_build_artifact_files(
            directory, {"payload": digest}, expected
        )

        extra = directory / "extra"
        extra.write_bytes(b"unlisted\n")
        with self.assertRaisesRegex(evidence.EvidenceError, "file set differs"):
            evidence._validate_exact_build_artifact_files(
                directory, {"payload": digest}, expected
            )
        extra.unlink()

        os.chmod(str(payload), 0o600)
        with self.assertRaisesRegex(evidence.EvidenceError, "non-0644"):
            evidence._validate_exact_build_artifact_files(
                directory, {"payload": digest}, expected
            )

    def test_build_artifact_directory_rejects_symlink_and_dotdot_paths(self) -> None:
        directory = self.root / "real" / "artifact"
        directory.mkdir(parents=True)
        alias = self.root / "alias"
        alias.symlink_to(self.root / "real", target_is_directory=True)
        with self.assertRaisesRegex(evidence.EvidenceError, "real directories"):
            evidence._regular_evidence_directory(
                alias / "artifact", "build evidence directory"
            )
        with self.assertRaisesRegex(evidence.EvidenceError, "unsafe component"):
            evidence._regular_evidence_directory(
                self.root / "real" / ".." / "real" / "artifact",
                "build evidence directory",
            )

    def test_phase2_reports_cross_bind_config_kconfig_and_stage_lock(self) -> None:
        directory = self.root / "phase2"
        directory.mkdir()
        resolved = b"CONFIG_MODULES=y\n"
        matrix_raw = b"{}\n"
        link_raw = b"{}\n"
        stage = {
            "files": [{"path": "Kconfig", "sha256": "2" * 64}],
            "manifest_sha256": "3" * 64,
        }
        values = {
            "resolved.config": resolved,
            "kconfig-solver-matrix.json": matrix_raw,
            "kbuild-link-closure.json": link_raw,
            "stage-lock.json": (
                json.dumps(stage, sort_keys=True, separators=(",", ":")) + "\n"
            ).encode("ascii"),
        }
        records = {}
        for name, value in values.items():
            (directory / name).write_bytes(value)
            records[name] = hashlib.sha256(value).hexdigest()
        matrix = {
            "claims": {"credit_eligible": False},
            "counts": {"case_count": 54},
            "inputs": {
                "seed_config": {
                    "mode": "0644",
                    "path": "seed.config",
                    "sha256": records["resolved.config"],
                    "size": len(resolved),
                },
                "staged_kconfig": {
                    "path": "drivers/misc/mckernel/Kconfig",
                    "sha256": "2" * 64,
                    "size": 1,
                },
            },
            "limitations": {"scope": "unreviewed"},
            "status": "captured-unreviewed",
        }
        link = {
            "claims": {"credit_eligible": False},
            "modules": [{}, {}, {}],
            "raw_record_names": [str(index) for index in range(16)],
            "stage_lock": {
                "manifest_sha256": "3" * 64,
                "sha256": records["stage-lock.json"],
            },
        }
        with mock.patch.object(evidence, "validate_matrix_bytes", return_value=matrix), mock.patch.object(
            evidence, "check_kbuild_link_closure", return_value=link
        ):
            result = evidence._validate_phase2_build_evidence(directory, records)
            self.assertEqual(54, result["kconfig_solver"]["counts"]["case_count"])
            self.assertEqual(16, result["kbuild_link_closure"]["raw_record_count"])

            matrix["inputs"]["seed_config"]["sha256"] = "4" * 64
            with self.assertRaisesRegex(evidence.EvidenceError, "resolved build config"):
                evidence._validate_phase2_build_evidence(directory, records)
            matrix["inputs"]["seed_config"]["sha256"] = records["resolved.config"]

            matrix["inputs"]["staged_kconfig"]["sha256"] = "5" * 64
            with self.assertRaisesRegex(evidence.EvidenceError, "identities diverge"):
                evidence._validate_phase2_build_evidence(directory, records)

    def write_build_scope_artifacts(self) -> tuple[Path, dict[str, str]]:
        directory = Path(tempfile.mkdtemp(prefix="scope-", dir=str(self.root)))
        source = self.root / "native-rust-source" / "linux-6.12.0-211.44.1.el10_2"
        output = self.root / "native-rust-build"
        prefix = " ".join(
            shlex.quote(item)
            for item in (
                evidence.EXPECTED_KBUILD_ENV_COMMAND_PREFIX
                + [
                "/usr/bin/make",
                "-C",
                str(source),
                "O=" + str(output),
                "ARCH=x86_64",
                "LLVM=1",
                "LOCALVERSION=" + evidence.EXPECTED_KERNEL_LOCALVERSION,
                ]
                + evidence.EXPECTED_KBUILD_MAKE_IDENTITY_ARGUMENTS
            )
        )
        values = {
            "build.commands": (
                f"{prefix} rustavailable\n"
                f"{prefix} -j2 bzImage\n"
                f"{prefix} -j2 {' '.join(evidence.BUILD_MODULE_TARGETS)}\n"
            ),
            "build.environment": evidence._reproducible_build_environment_text(),
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
        self.assertEqual(
            records["build.environment"], result["build_environment_sha256"]
        )

    def test_build_scope_rejects_environment_value_order_and_extra_line_mutations(self) -> None:
        canonical = evidence._reproducible_build_environment_text()
        lines = canonical.splitlines(keepends=True)
        mutations = (
            canonical.replace("KBUILD_BUILD_USER=mckernel", "KBUILD_BUILD_USER=root"),
            "".join((lines[1], lines[0]) + tuple(lines[2:])),
            canonical + "KBUILD_BUILD_USER=attacker\n",
        )
        for mutation in mutations:
            with self.subTest(mutation=mutation):
                directory, records = self.write_build_scope_artifacts()
                path = directory / "build.environment"
                path.write_text(mutation, encoding="utf-8")
                records[path.name] = hashlib.sha256(path.read_bytes()).hexdigest()
                with self.assertRaisesRegex(
                    evidence.EvidenceError, "reproducible build environment differs"
                ):
                    evidence._validate_build_scope_artifacts(directory, records)

    def test_build_command_environment_prefix_rejects_shadow_reorder_and_extra_controls(self) -> None:
        mutations = (
            ("/usr/bin/env -i ", "/usr/bin/env "),
            ("BASH_ENV= ENV=", "ENV= BASH_ENV="),
            ("MAKEFLAGS= MAKEOVERRIDES=", "MAKEFLAGS=KBUILD_BUILD_USER=attacker MAKEOVERRIDES="),
            (" /usr/bin/make ", " CC=/tmp/attacker /usr/bin/make "),
            (" /usr/bin/make ", " make "),
            (
                "KBUILD_BUILD_USER=mckernel KBUILD_BUILD_VERSION=1",
                "KBUILD_BUILD_VERSION=1 KBUILD_BUILD_USER=mckernel",
            ),
        )
        for old, new in mutations:
            with self.subTest(new=new):
                directory, records = self.write_build_scope_artifacts()
                path = directory / "build.commands"
                text = path.read_text(encoding="utf-8")
                self.assertIn(old, text)
                path.write_text(text.replace(old, new, 1), encoding="utf-8")
                records[path.name] = hashlib.sha256(path.read_bytes()).hexdigest()
                with self.assertRaisesRegex(
                    evidence.EvidenceError,
                    "environment boundary differs|bounded target scope",
                ):
                    evidence._validate_build_scope_artifacts(directory, records)

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

    def test_build_command_with_wrong_localversion_is_rejected(self) -> None:
        directory, records = self.write_build_scope_artifacts()
        commands = directory / "build.commands"
        text = commands.read_text(encoding="utf-8").replace(
            "LOCALVERSION=" + evidence.EXPECTED_KERNEL_LOCALVERSION,
            "LOCALVERSION=-unreviewed",
            1,
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
            "modules": {
                "CONFIG_MCKERNEL_IHK_RUST": "m",
                "CONFIG_MCKERNEL_IHK_SMP_X86_64_RUST": "m",
                "CONFIG_MCKERNEL_MCCTRL_RUST": "m",
            },
        }
        path.write_text(
            "CONFIG_MODULES=y\n"
            "# CONFIG_MODULE_UNLOAD is not set\n"
            "# CONFIG_MODULE_SIG_FORCE is not set\n",
            encoding="utf-8",
        )
        with self.assertRaisesRegex(evidence.EvidenceError, "CONFIG_MODULE_UNLOAD"):
            evidence._validate_resolved_config(path, requirements)

    def test_resolved_config_requires_exact_three_modular_native_symbols(self) -> None:
        path = self.root / "resolved.config"
        requirements = {
            "enabled": ["CONFIG_MODULES"],
            "disabled": ["CONFIG_MODULE_SIG_FORCE"],
            "modules": {
                "CONFIG_MCKERNEL_IHK_RUST": "m",
                "CONFIG_MCKERNEL_IHK_SMP_X86_64_RUST": "m",
                "CONFIG_MCKERNEL_MCCTRL_RUST": "m",
            },
        }
        canonical = (
            "CONFIG_MODULES=y\n"
            "# CONFIG_MODULE_SIG_FORCE is not set\n"
            "CONFIG_MCKERNEL_IHK_RUST=m\n"
            "CONFIG_MCKERNEL_IHK_SMP_X86_64_RUST=m\n"
            "CONFIG_MCKERNEL_MCCTRL_RUST=m\n"
        )
        path.write_text(canonical, encoding="utf-8")
        observed = evidence._validate_resolved_config(path, requirements)
        self.assertEqual(requirements, observed)

        mutations = (
            canonical.replace("CONFIG_MCKERNEL_IHK_RUST=m\n", ""),
            canonical.replace("CONFIG_MCKERNEL_IHK_RUST=m", "CONFIG_MCKERNEL_IHK_RUST=y"),
            canonical.replace(
                "CONFIG_MCKERNEL_IHK_SMP_X86_64_RUST=m",
                "# CONFIG_MCKERNEL_IHK_SMP_X86_64_RUST is not set",
            ),
            canonical + "CONFIG_MCKERNEL_MCCTRL_RUST=m\n",
        )
        for index, mutation in enumerate(mutations):
            with self.subTest(index=index):
                path.write_text(mutation, encoding="utf-8")
                with self.assertRaisesRegex(
                    evidence.EvidenceError, "required modular setting"
                ):
                    evidence._validate_resolved_config(path, requirements)

    def test_resolved_config_rejects_weakened_native_module_contract(self) -> None:
        path = self.root / "resolved.config"
        path.write_text(
            "CONFIG_MODULES=y\n"
            "# CONFIG_MODULE_SIG_FORCE is not set\n"
            "CONFIG_MCKERNEL_IHK_RUST=m\n"
            "CONFIG_MCKERNEL_IHK_SMP_X86_64_RUST=m\n"
            "CONFIG_MCKERNEL_MCCTRL_RUST=m\n",
            encoding="utf-8",
        )
        base = {
            "enabled": ["CONFIG_MODULES"],
            "disabled": ["CONFIG_MODULE_SIG_FORCE"],
            "modules": {
                "CONFIG_MCKERNEL_IHK_RUST": "m",
                "CONFIG_MCKERNEL_IHK_SMP_X86_64_RUST": "m",
                "CONFIG_MCKERNEL_MCCTRL_RUST": "m",
            },
        }
        for modules in (
            {"CONFIG_MCKERNEL_IHK_RUST": "m"},
            dict(base["modules"], CONFIG_MCKERNEL_MCCTRL_RUST="y"),
            dict(base["modules"], CONFIG_UNKNOWN="m"),
            [],
        ):
            with self.subTest(modules=modules):
                mutation = copy.deepcopy(base)
                mutation["modules"] = modules
                with self.assertRaisesRegex(
                    evidence.EvidenceError, "native module config contract"
                ):
                    evidence._validate_resolved_config(path, mutation)


if __name__ == "__main__":
    unittest.main()
