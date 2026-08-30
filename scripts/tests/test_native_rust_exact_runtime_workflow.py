#!/usr/bin/env python3

from __future__ import print_function

import contextlib
import io
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import unittest
from unittest import mock

import yaml

from scripts import native_rust_runtime_evidence as runtime_evidence
from scripts import ihk_native_lifecycle_check as ihk_lifecycle
from scripts import ihk_smp_native_lifecycle_check as smp_lifecycle
from scripts import mcctrl_native_lifecycle_check as mcctrl_lifecycle


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
        self.assertEqual(
            2,
            self.init.count(
                "mcctrl,ihk_smp_x86_64,|ihk_smp_x86_64,mcctrl,) ;;"
            ),
        )
        self.assertIn('[ "$users" = \'ihk_smp_x86_64,\' ]', self.init)
        self.assertNotIn('[ "$users" = ihk_smp_x86_64 ]', self.init)

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

    def test_bootstrap_can_replace_coreutils_single_explicitly(self) -> None:
        self.assertIn(
            "dnf -y --allowerasing --setopt=install_weak_deps=False install \\\n"
            "            coreutils\n",
            self.workflow,
        )
        self.assertEqual(1, self.workflow.count("--allowerasing"))
        self.assertIn("! /usr/bin/rpm -q coreutils-single", self.workflow)
        self.assertIn(
            "dnf -y --setopt=install_weak_deps=False install \\\n"
            "            bash binutils cpio findutils gawk git-core gzip kmod \\\n"
            "            qemu-kvm-core python3 sed util-linux which",
            self.workflow,
        )
        bootstrap = self.workflow.index(
            "      - name: Initialize first-failure evidence and exact Rocky tools"
        )
        checkout = self.workflow.index(
            "      - name: Check out the exact candidate without credentials"
        )
        recursive = self.workflow.index("          submodules: recursive")
        self.assertLess(bootstrap, checkout)
        self.assertLess(checkout, recursive)
        self.assertEqual(1, self.workflow[bootstrap:checkout].count("git-core"))
        self.assertEqual(1, self.workflow.count("git-core"))

    def test_packaged_modinfo_symlink_is_descriptor_and_owner_bound(self) -> None:
        runtime_evidence._validate_runtime_modinfo_boundary(self.workflow)
        document = yaml.safe_load(self.workflow)
        step = next(
            step
            for step in document["jobs"]["exact-runtime"]["steps"]
            if step.get("name")
            == "Verify immutable build inputs and native module link contracts"
        )
        script = step["run"]
        sequence = (
            "expected_modinfo_nevra=kmod-31-13.el10.x86_64",
            "expected_modinfo_sha256=7e91f52ed2cd5e2c4f82de4bb07bbaa7179cd5c053b7afcf2fd231056681ed55",
            'modinfo_path="$(command -v modinfo)"',
            "modinfo_target=/usr/bin/kmod",
            'test "$modinfo_path" = /usr/sbin/modinfo',
            "test -L /usr/sbin/modinfo",
            'test "$(/usr/bin/readlink -- /usr/sbin/modinfo)" = ../bin/kmod',
            'exec {modinfo_fd}<"$modinfo_target"',
            'modinfo_exec="/proc/self/fd/$modinfo_fd"',
            "assert_modinfo_binding() {",
            'test "$(/usr/bin/rpm -q --qf \'%{NEVRA}\\n\' kmod)" = \\',
            'test "$(/usr/bin/rpm -qf --qf \'%{NAME}\\n\' "$modinfo_path")" = kmod &&',
            'test "$(/usr/bin/rpm -qf --qf \'%{NAME}\\n\' "$modinfo_target")" = kmod',
            "run_modinfo() (",
            'exec -a modinfo "$modinfo_exec" "$@"',
            'test "$(run_modinfo -F name "$BUILD_EVIDENCE/ihk.ko")" = ihk',
            'test "$(run_modinfo -F name "$BUILD_EVIDENCE/ihk-smp-x86_64.ko")" = ihk_smp_x86_64',
            'test "$(run_modinfo -F name "$BUILD_EVIDENCE/mcctrl.ko")" = mcctrl',
            "scripts/ihk_native_lifecycle_check.py",
            "scripts/ihk_smp_native_lifecycle_check.py",
            "scripts/mcctrl_native_lifecycle_check.py",
            "exec {modinfo_fd}<&-",
        )
        positions = [script.index(fragment) for fragment in sequence]
        self.assertEqual(positions, sorted(positions))
        self.assertNotIn("test ! -L /usr/sbin/modinfo", script)
        self.assertNotRegex(script, r'(?m)^\s*"\$modinfo_path"(?:\s|$)')
        self.assertEqual(3, script.count('--modinfo-fd "$modinfo_fd"'))
        capture_script = next(
            item["run"]
            for item in document["jobs"]["exact-runtime"]["steps"]
            if item.get("name") == "Create a credit-forbidden technical capture"
        )
        self.assertEqual(2, capture_script.count('--modinfo-fd "$modinfo_fd"'))
        self.assertIn("assert_modinfo_binding() {", capture_script)
        self.assertIn('exec {modinfo_fd}<"$modinfo_target"', capture_script)
        self.assertIn("exec {modinfo_fd}<&-", capture_script)

        mutations = (
            (
                "          test -L /usr/sbin/modinfo\n",
                "          test -e /usr/sbin/modinfo\n",
            ),
            (
                '          test "$(/usr/bin/readlink -- /usr/sbin/modinfo)" = ../bin/kmod\n',
                '          test -n "$(/usr/bin/readlink -- /usr/sbin/modinfo)"\n',
            ),
            (
                '              test "$modinfo_path" -ef "$modinfo_exec" &&\n',
                "",
            ),
            (
                '              test "$modinfo_target" -ef "$modinfo_exec" &&\n',
                "",
            ),
            (
                (
                    '              test "$(/usr/bin/sha256sum -- "$modinfo_exec")" = \\\n'
                    '              "$expected_modinfo_sha256  $modinfo_exec" &&\n'
                ),
                "",
            ),
            (
                '              exec -a modinfo "$modinfo_exec" "$@"\n',
                '              "$modinfo_path" "$@"\n',
            ),
            (
                (
                    '              test "$(/usr/bin/rpm -q --qf \'%{NEVRA}\\n\' kmod)" = \\\n'
                    '              "$expected_modinfo_nevra" &&\n'
                ),
                "",
            ),
            (
                '            --modinfo-fd "$modinfo_fd"\n',
                "",
            ),
            (
                '            --modinfo-fd "$modinfo_fd" \\\n',
                "",
            ),
            (
                (
                    '            --repo "$GITHUB_WORKSPACE" \\\n'
                    '            --modinfo-fd "$modinfo_fd" \\\n'
                    '            --check-runtime-evidence \\\n'
                ),
                (
                    '            --repo "$GITHUB_WORKSPACE" \\\n'
                    '            --check-runtime-evidence \\\n'
                ),
            ),
            (
                (
                    '            --output "$RUNTIME_EVIDENCE/capture.json"\n'
                    '          assert_modinfo_binding\n'
                ),
                '            --output "$RUNTIME_EVIDENCE/capture.json"\n',
            ),
            (
                (
                    '          assert_modinfo_binding\n'
                    '          /usr/bin/env -i LANG=C LC_ALL=C PATH=/usr/bin:/bin '
                    'PYTHONHASHSEED=0 TZ=UTC \\\n'
                    '            /usr/bin/python3 -E -s scripts/ihk_native_lifecycle_check.py'
                ),
                (
                    '          exec {modinfo_fd}<&-\n'
                    '          /usr/bin/env -i LANG=C LC_ALL=C PATH=/usr/bin:/bin '
                    'PYTHONHASHSEED=0 TZ=UTC \\\n'
                    '            /usr/bin/python3 -E -s scripts/ihk_native_lifecycle_check.py'
                ),
            ),
            (
                (
                    '            --build-evidence-dir "$BUILD_EVIDENCE"\n'
                    '          assert_modinfo_binding\n'
                    '          exec {modinfo_fd}<&-\n'
                ),
                (
                    '            --build-evidence-dir "$BUILD_EVIDENCE"\n'
                    '          exec {modinfo_fd}<&-\n'
                ),
            ),
            (
                (
                    '            sha256sum --check --strict SHA256SUMS\n'
                    '          )\n'
                    '          assert_modinfo_binding\n'
                    '          /usr/bin/env -i LANG=C LC_ALL=C PATH=/usr/bin:/bin '
                ),
                (
                    '            sha256sum --check --strict SHA256SUMS\n'
                    '          )\n'
                    '          exec {modinfo_fd}<&-\n'
                    '          /usr/bin/env -i LANG=C LC_ALL=C PATH=/usr/bin:/bin '
                ),
            ),
            (
                "          assert_modinfo_binding\n          exec {modinfo_fd}<&-\n",
                "          exec {modinfo_fd}<&-\n",
            ),
        )
        for old, new in mutations:
            mutation = self.workflow.replace(old, new, 1)
            self.assertNotEqual(self.workflow, mutation)
            with self.subTest(new=new.strip()):
                with self.assertRaises(runtime_evidence.EvidenceError):
                    runtime_evidence._validate_runtime_modinfo_boundary(mutation)

    def test_retained_modinfo_descriptor_rejects_namespace_content_and_argv0_attacks(self) -> None:
        shell = r"""
set -euo pipefail
root=$1
attack=$2
modinfo_path="$root/usr/sbin/modinfo"
modinfo_target="$root/usr/bin/kmod"
attacker="$root/usr/bin/attacker"
exec {modinfo_fd}<"$modinfo_target"
modinfo_exec="/proc/self/fd/$modinfo_fd"
expected_sha256="$(/usr/bin/sha256sum -- "$modinfo_exec")"
assert_binding() {
  test -L "$modinfo_path" &&
  test "$(/usr/bin/readlink -- "$modinfo_path")" = ../bin/kmod &&
  test ! -L "$modinfo_target" &&
  test "$modinfo_path" -ef "$modinfo_exec" &&
  test "$modinfo_target" -ef "$modinfo_exec" &&
  test "$(/usr/bin/sha256sum -- "$modinfo_exec")" = "$expected_sha256"
}
run_bound() (
  assert_binding &&
  exec -a modinfo "$modinfo_exec" --noprofile --norc -p -c 'test "$0" = modinfo'
)
assert_binding
run_bound
case "$attack" in
  pre-owner-alias-retarget)
    /usr/bin/ln -sfn ../bin/attacker "$modinfo_path"
    ;;
  post-owner-target-replacement)
    : simulated-owner-lookup-complete
    /usr/bin/mv -- "$attacker" "$modinfo_target"
    ;;
  post-owner-content-replacement)
    : simulated-owner-lookup-complete
    /usr/bin/cp -- /usr/bin/false "$modinfo_target"
    ;;
  *) exit 80 ;;
esac
if assert_binding; then
  exit 81
fi
if test "$attack" != post-owner-content-replacement; then
  (exec -a modinfo "$modinfo_exec" --noprofile --norc -p -c 'test "$0" = modinfo')
  if "$modinfo_path"; then
    exit 82
  fi
fi
exec {modinfo_fd}<&-
"""
        for attack in (
            "pre-owner-alias-retarget",
            "post-owner-target-replacement",
            "post-owner-content-replacement",
        ):
            with self.subTest(attack=attack), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                binary = root / "usr/bin"
                sbin = root / "usr/sbin"
                binary.mkdir(parents=True)
                sbin.mkdir(parents=True)
                shutil.copy2("/usr/bin/bash", binary / "kmod")
                shutil.copy2("/usr/bin/false", binary / "attacker")
                (sbin / "modinfo").symlink_to("../bin/kmod")
                completed = subprocess.run(
                    [
                        "/usr/bin/bash",
                        "--noprofile",
                        "--norc",
                        "-p",
                        "-c",
                        shell,
                        "descriptor-test",
                        str(root),
                        attack,
                    ],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                )
                self.assertEqual(
                    0,
                    completed.returncode,
                    completed.stderr.decode("utf-8", errors="replace"),
                )

    @unittest.skipUnless(shutil.which("cc"), "C compiler required")
    def test_internal_modinfo_calls_use_only_the_inherited_fd_without_path_alias(self) -> None:
        source_text = r'''
#include <stdio.h>
#include <string.h>

int main(int argc, char **argv) {
    if (strcmp(argv[0], "modinfo") != 0) {
        return 91;
    }
    if (argc != 4 || strcmp(argv[1], "-F") != 0) {
        return 92;
    }
    puts("bound-descriptor");
    return 0;
}
'''
        with tempfile.TemporaryDirectory(prefix="native-rust-modinfo-fd-") as directory:
            root = Path(directory)
            source = root / "bound-modinfo.c"
            target = root / "kmod"
            retained = root / "retained-kmod"
            alias = root / "modinfo"
            module = root / "candidate.ko"
            source.write_text(source_text, encoding="utf-8")
            module.write_bytes(b"fixture")
            subprocess.run(
                [shutil.which("cc"), "-O0", "-o", str(target), str(source)],
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            alias.symlink_to(target.name)
            descriptor = os.open(str(target), os.O_RDONLY)
            try:
                executable = "/proc/self/fd/{0}".format(descriptor)
                wrong_argv0 = subprocess.run(
                    ["attacker", "-F", "name", str(module)],
                    executable=executable,
                    pass_fds=(descriptor,),
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                )
                self.assertEqual(91, wrong_argv0.returncode)

                expected_calls = (
                    lambda: ihk_lifecycle._modinfo(module, "name", descriptor),
                    lambda: smp_lifecycle._modinfo(module, "name", descriptor),
                    lambda: mcctrl_lifecycle._modinfo(module, "name", descriptor),
                    lambda: runtime_evidence._run_field(module, "name", descriptor),
                )
                expected_values = (
                    "bound-descriptor",
                    ["bound-descriptor"],
                    "bound-descriptor",
                    ["bound-descriptor"],
                )
                with mock.patch.dict(
                    os.environ,
                    {
                        "LANG": "attacker",
                        "LC_ALL": "attacker",
                        "LD_LIBRARY_PATH": str(root / "attacker-libraries"),
                        "LD_PRELOAD": str(root / "attacker-preload.so"),
                        "PATH": str(root),
                        "TZ": "attacker",
                    },
                    clear=True,
                ):
                    for call, expected in zip(expected_calls, expected_values):
                        self.assertEqual(expected, call())

                alias.unlink()
                alias.symlink_to("attacker")
                target.rename(retained)
                shutil.copy2("/usr/bin/false", target)
                for call, expected in zip(expected_calls, expected_values):
                    self.assertEqual(expected, call())
            finally:
                os.close(descriptor)

            for checker, error in (
                (ihk_lifecycle._modinfo_execution, ihk_lifecycle.ValidationError),
                (smp_lifecycle._modinfo_execution, smp_lifecycle.ValidationError),
                (mcctrl_lifecycle._modinfo_execution, mcctrl_lifecycle.ValidationError),
                (runtime_evidence._modinfo_execution, runtime_evidence.EvidenceError),
            ):
                with self.subTest(checker=checker.__module__, failure="closed"):
                    with self.assertRaises(error):
                        checker(descriptor)

            pipe_read, pipe_write = os.pipe()
            try:
                for checker, error in (
                    (ihk_lifecycle._modinfo_execution, ihk_lifecycle.ValidationError),
                    (smp_lifecycle._modinfo_execution, smp_lifecycle.ValidationError),
                    (mcctrl_lifecycle._modinfo_execution, mcctrl_lifecycle.ValidationError),
                    (runtime_evidence._modinfo_execution, runtime_evidence.EvidenceError),
                ):
                    with self.subTest(checker=checker.__module__, failure="non-regular"):
                        with self.assertRaises(error):
                            checker(pipe_read)
            finally:
                os.close(pipe_read)
                os.close(pipe_write)

            non_executable = root / "non-executable"
            non_executable.write_bytes(b"not executable\n")
            non_executable.chmod(0o644)
            non_executable_fd = os.open(str(non_executable), os.O_RDONLY)
            try:
                for checker, error in (
                    (ihk_lifecycle._modinfo_execution, ihk_lifecycle.ValidationError),
                    (smp_lifecycle._modinfo_execution, smp_lifecycle.ValidationError),
                    (mcctrl_lifecycle._modinfo_execution, mcctrl_lifecycle.ValidationError),
                    (runtime_evidence._modinfo_execution, runtime_evidence.EvidenceError),
                ):
                    with self.subTest(checker=checker.__module__, failure="non-executable"):
                        with self.assertRaises(error):
                            checker(non_executable_fd)
                    with self.subTest(checker=checker.__module__, failure="reserved"):
                        with self.assertRaises(error):
                            checker(2)
                    with self.subTest(checker=checker.__module__, failure="boolean"):
                        with self.assertRaises(error):
                            checker(True)
            finally:
                os.close(non_executable_fd)

            invalid_format = root / "invalid-format"
            invalid_format.write_bytes(b"not an executable format\n")
            invalid_format.chmod(0o755)
            invalid_format_fd = os.open(str(invalid_format), os.O_RDONLY)
            try:
                invalid_calls = (
                    (lambda: ihk_lifecycle._modinfo(module, "name", invalid_format_fd), ihk_lifecycle.ValidationError),
                    (lambda: smp_lifecycle._modinfo(module, "name", invalid_format_fd), smp_lifecycle.ValidationError),
                    (lambda: mcctrl_lifecycle._modinfo(module, "name", invalid_format_fd), mcctrl_lifecycle.ValidationError),
                    (lambda: runtime_evidence._run_field(module, "name", invalid_format_fd), runtime_evidence.EvidenceError),
                )
                for call, error in invalid_calls:
                    with self.subTest(failure="exec-format", error=error.__name__):
                        with self.assertRaises(error):
                            call()
            finally:
                os.close(invalid_format_fd)

    def test_lifecycle_clis_reject_modinfo_fd_without_a_module(self) -> None:
        cases = (
            (ihk_lifecycle, {"module": "ihk"}),
            (smp_lifecycle, {"artifact_validated": False, "module": "ihk_smp_x86_64", "parameters": 0}),
            (mcctrl_lifecycle, {"module": "mcctrl"}),
        )
        for checker, summary in cases:
            stderr = io.StringIO()
            with self.subTest(checker=checker.__name__), mock.patch.object(
                checker, "validate_repository", return_value=summary
            ), contextlib.redirect_stderr(stderr):
                status = checker.main(
                    ["--repo", str(REPO_ROOT), "--modinfo-fd", "3"]
                )
            self.assertEqual(1, status)
            self.assertIn("--modinfo-fd requires --module", stderr.getvalue())

    def test_lifecycle_clis_forward_modinfo_fd_to_artifact_validation(self) -> None:
        module_path = Path("/tmp/native-rust-modinfo-fd-forwarding.ko")
        cases = (
            (ihk_lifecycle, {"module": "ihk", "version": "1", "parameters": 0, "dependencies": 0}),
            (smp_lifecycle, {"artifact_validated": False, "module": "ihk_smp_x86_64", "parameters": 0}),
            (mcctrl_lifecycle, {"artifact_validated": False, "module": "mcctrl", "parameters": 0, "dependencies": 1, "ihk_symbol_import_status": "blocked", "binfmt_status": "blocked"}),
        )
        for checker, summary in cases:
            stdout = io.StringIO()
            with self.subTest(checker=checker.__name__), mock.patch.object(
                checker, "validate_repository", return_value=summary
            ), mock.patch.object(
                checker, "validate_module_artifact"
            ) as validate_artifact, contextlib.redirect_stdout(stdout):
                status = checker.main(
                    [
                        "--repo",
                        str(REPO_ROOT),
                        "--module",
                        str(module_path),
                        "--modinfo-fd",
                        "19",
                    ]
                )
            self.assertEqual(0, status)
            self.assertEqual(19, validate_artifact.call_args.args[-1])

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
