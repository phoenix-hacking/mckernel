#!/usr/bin/env python3

from __future__ import print_function

from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import unittest


REPO_ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = REPO_ROOT / ".github/workflows/native-rust-host-modules-exact-runtime.yml"
PR_WORKFLOW = (
    REPO_ROOT / ".github/workflows/native-rust-host-modules-exact-runtime-pr.yml"
)
INIT = REPO_ROOT / "scripts/native-rust-runtime-init.sh"
POWEROFF = REPO_ROOT / "scripts/native-rust-runtime-poweroff.S"


class NativeRustExactRuntimeWorkflowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.workflow = WORKFLOW.read_text(encoding="utf-8")
        cls.pr_workflow = PR_WORKFLOW.read_text(encoding="utf-8")
        cls.init = INIT.read_text(encoding="utf-8")

    def test_workflow_is_dispatchable_reusable_and_reuses_the_exact_build(self) -> None:
        trigger = self.workflow[: self.workflow.index("permissions:")]
        self.assertIn("workflow_dispatch:", trigger)
        self.assertIn("workflow_call:", trigger)
        self.assertNotIn("pull_request:", trigger)
        self.assertNotIn("push:", trigger)
        self.assertIn(
            "uses: ./.github/workflows/native-rust-host-modules-exact-build.yml",
            self.workflow,
        )
        self.assertIn("validation_sha: ${{ inputs.validation_sha }}", self.workflow)
        self.assertIn("needs: exact-build", self.workflow)

    def test_pr_wrapper_rejects_forks_and_passes_the_exact_head(self) -> None:
        trigger = self.pr_workflow[: self.pr_workflow.index("permissions:")]
        self.assertIn("pull_request:", trigger)
        self.assertIn("branches: [development]", trigger)
        self.assertNotIn("pull_request_target:", self.pr_workflow)
        self.assertNotIn("workflow_dispatch:", self.pr_workflow)
        self.assertNotIn("push:", self.pr_workflow)
        for path in (
            ".github/workflows/native-rust-host-modules-exact-*.yml",
            "host-kernel/native-rust/**",
            "host-kernel/rocky/**",
            "ihk",
            "scripts/**",
        ):
            self.assertIn("      - " + path, trigger)
        self.assertIn("permissions:\n  contents: read", self.pr_workflow)
        self.assertIn(
            "${{ github.event.pull_request.head.repo.full_name == github.repository }}",
            self.pr_workflow,
        )
        self.assertIn(
            "uses: ./.github/workflows/native-rust-host-modules-exact-runtime.yml",
            self.pr_workflow,
        )
        self.assertIn(
            "validation_sha: ${{ github.event.pull_request.head.sha }}",
            self.pr_workflow,
        )
        self.assertNotIn("secrets:", self.pr_workflow)
        self.assertNotIn("contents: write", self.pr_workflow)

    def test_external_actions_and_rocky_runtime_are_immutable(self) -> None:
        image = (
            "rockylinux/rockylinux:10.2@sha256:"
            "e372170ca8630f0f03e9b70fdd0bf4a3ce3426b0de7cdba615f06337389de176"
        )
        self.assertGreaterEqual(self.workflow.count(image), 2)
        uses = re.findall(r"^\s*uses:\s*(\S+)", self.workflow, re.MULTILINE)
        external = [value for value in uses if not value.startswith("./")]
        self.assertGreaterEqual(len(external), 3)
        for value in external:
            self.assertRegex(value, r"^[^@]+@[0-9a-f]{40}$")

    def test_build_artifact_is_hash_checked_before_use(self) -> None:
        download = self.workflow.index("actions/download-artifact@")
        verify = self.workflow.index("sha256sum --check --strict SHA256SUMS", download)
        boot = self.workflow.index("Boot the exact kernel", verify)
        self.assertLess(download, verify)
        self.assertLess(verify, boot)
        self.assertIn(
            "native-rust-exact-build-${{ github.run_id }}-${{ github.run_attempt }}",
            self.workflow,
        )
        for module in ("ihk.ko", "ihk-smp-x86_64.ko", "mcctrl.ko"):
            self.assertIn(module, self.workflow)
        for symbol in (
            "CONFIG_BINFMT_ELF",
            "CONFIG_BLK_DEV_INITRD",
            "CONFIG_MODULES",
            "CONFIG_MODULE_UNLOAD",
            "CONFIG_PRINTK",
            "CONFIG_PROC_FS",
            "CONFIG_RD_GZIP",
            "CONFIG_SERIAL_8250_CONSOLE",
            "CONFIG_SYSFS",
        ):
            self.assertIn(symbol, self.workflow)
        self.assertIn("# CONFIG_MODULE_SIG_FORCE is not set", self.workflow)

    def test_initramfs_is_local_minimal_and_deterministic(self) -> None:
        for fragment in (
            "scripts/native-rust-runtime-init.sh",
            "scripts/native-rust-runtime-poweroff.S",
            "touch -h -d '@0'",
            "LC_ALL=C sort -z",
            "cpio --null --create --format=newc --owner=0:0 --reproducible",
            "gzip -n",
            "initramfs.sha256",
        ):
            self.assertIn(fragment, self.workflow)
        self.assertNotIn("qcow", self.workflow.lower())
        self.assertNotIn("cloud image", self.workflow.lower())
        self.assertNotIn('rm -rf -- "$INITRAMFS_ROOT"', self.workflow)

    def test_qemu_boots_exact_output_under_tcg_without_host_acceleration(self) -> None:
        for fragment in (
            '-accel tcg',
            '-kernel "$BUILD_EVIDENCE/bzImage"',
            '-initrd "$RUNTIME_EVIDENCE/initramfs.cpio.gz"',
            'rdinit=/init',
            '-serial "file:$RUNTIME_EVIDENCE/serial.log"',
            'qemu-command.txt',
            'qemu-version.txt',
            'qemu.exit-code',
            '--qemu-command',
            '--qemu-version',
            '--qemu-exit-code',
        ):
            self.assertIn(fragment, self.workflow)
        self.assertNotIn("/dev/kvm", self.workflow)
        self.assertNotIn("--privileged", self.workflow)

    def test_guest_protocol_exercises_dependency_refcounts_and_reverse_unload(self) -> None:
        ordered = (
            'emit_state initial-clean',
            'insmod "$IHK" || { fail load-ihk; exit 1; }',
            'insmod "$SMP" || { fail load-ihk-smp-x86-64; exit 1; }',
            'insmod "$MCCTRL" || { fail load-mcctrl; exit 1; }',
            'phase=all-loaded references=$references users=$users',
            'negative_output="$(rmmod ihk 2>&1)"',
            'phase=after-negative references=$references users=$users',
            'rmmod mcctrl || { fail unload-mcctrl; exit 1; }',
            'phase=after-mcctrl-unload references=$references users=$users',
            'rmmod ihk_smp_x86_64 || { fail unload-ihk-smp-x86-64; exit 1; }',
            'phase=after-smp-unload references=$references users=$users',
            'rmmod ihk || { fail unload-ihk; exit 1; }',
            'emit_state final-clean',
        )
        positions = [self.init.index(value) for value in ordered]
        self.assertEqual(sorted(positions), positions)
        self.assertIn('[ "$negative_status" -eq 1 ]', self.init)
        self.assertIn('"Module ihk is in use"', self.init)
        self.assertIn('[ "$references" = 1 ]', self.init)
        self.assertIn('[ "$references" = 0 ]', self.init)

    def test_capture_is_unreviewed_and_cannot_claim_credit(self) -> None:
        self.assertIn("technical-capture-unreviewed", self.workflow)
        self.assertIn("credit=forbidden", self.workflow)
        self.assertNotRegex(self.workflow, r"\bPASS\b")
        self.assertNotIn("credit=eligible", self.workflow)
        self.assertIn("if: ${{ always() }}", self.workflow)
        self.assertIn("compression-level: 0", self.workflow)
        self.assertIn("credit forbidden", self.pr_workflow)
        self.assertNotRegex(self.pr_workflow, r"\bPASS\b")
        self.assertNotIn("credit=eligible", self.pr_workflow)

    @unittest.skipUnless(shutil.which("as") and shutil.which("ld"), "binutils required")
    def test_poweroff_helper_is_a_static_x86_64_executable(self) -> None:
        with tempfile.TemporaryDirectory(prefix="native-rust-poweroff-") as temporary:
            obj = Path(temporary) / "poweroff.o"
            executable = Path(temporary) / "poweroff"
            subprocess.run(["as", "--64", str(POWEROFF), "-o", str(obj)], check=True)
            subprocess.run(
                [
                    "ld",
                    "-m",
                    "elf_x86_64",
                    "-nostdlib",
                    "-static",
                    "-s",
                    "-o",
                    str(executable),
                    str(obj),
                ],
                check=True,
            )
            output = subprocess.run(
                ["readelf", "-h", str(executable)],
                check=True,
                stdout=subprocess.PIPE,
                text=True,
            ).stdout
            self.assertIn("Class:                             ELF64", output)
            self.assertIn(
                "Machine:                           Advanced Micro Devices X86-64", output
            )


if __name__ == "__main__":
    unittest.main()
