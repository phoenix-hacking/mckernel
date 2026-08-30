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
MCD0_IOCTL_X86_64 = (
    REPO_ROOT / "scripts/native-rust-runtime-mcd0-ioctl-x86_64.S"
)
MCD0_IOCTL_I386 = REPO_ROOT / "scripts/native-rust-runtime-mcd0-ioctl-i386.S"


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

    def test_executed_workflow_provenance_is_exact_and_manifest_bound(self) -> None:
        runtime_evidence._validate_runtime_workflow_provenance_boundary(
            self.workflow
        )
        document = yaml.safe_load(self.workflow)
        steps = document["jobs"]["exact-runtime"]["steps"]
        verify = next(
            step
            for step in steps
            if step.get("name")
            == "Verify immutable build inputs and native module link contracts"
        )
        capture = next(
            step
            for step in steps
            if step.get("name") == "Create a credit-forbidden technical capture"
        )
        expected_env = {
            "CALLER_WORKFLOW_REF": "${{ github.workflow_ref }}",
            "CALLER_WORKFLOW_SHA": "${{ github.workflow_sha }}",
            "DEFINING_WORKFLOW_FILE_PATH": "${{ job.workflow_file_path }}",
            "DEFINING_WORKFLOW_REF": "${{ job.workflow_ref }}",
            "DEFINING_WORKFLOW_REPOSITORY": "${{ job.workflow_repository }}",
            "DEFINING_WORKFLOW_SHA": "${{ job.workflow_sha }}",
        }
        for step in (verify, capture):
            for name, value in expected_env.items():
                self.assertEqual(value, step["env"][name])

        verify_script = verify["run"]
        sequence = (
            '[[ "$CALLER_WORKFLOW_SHA" =~ ^[0-9a-f]{40}$ ]]',
            'test "$GITHUB_SHA" = "$CALLER_WORKFLOW_SHA"',
            'test "$CALLER_WORKFLOW_SHA" = "$DEFINING_WORKFLOW_SHA"',
            'case "$GITHUB_EVENT_NAME" in',
            'test "$EXPECTED_HEAD_SHA" = "$CALLER_WORKFLOW_SHA"',
            'workflow_git fetch --no-tags --depth=1 origin "$GITHUB_REF"',
            'candidate_caller_workflow_blob="$(workflow_git rev-parse --verify',
            'executed_caller_workflow_blob="$(workflow_git rev-parse --verify',
            'candidate_job_workflow_blob="$(workflow_git rev-parse --verify',
            'executed_job_workflow_blob="$(workflow_git rev-parse --verify',
            'test "$candidate_caller_workflow_blob" =',
            'test "$candidate_job_workflow_blob" = "$executed_job_workflow_blob"',
            'executed-caller-workflow.yml',
            'executed-runtime-workflow.yml',
            '/usr/bin/cmp -- "$GITHUB_WORKSPACE/$caller_workflow_path"',
            '/usr/bin/cmp -- "$GITHUB_WORKSPACE/$runtime_workflow_path"',
            'runtime-workflow-provenance.json',
            '"schema": "mckernel-native-rust-runtime-workflow-provenance-v1"',
        )
        positions = [verify_script.index(fragment) for fragment in sequence]
        self.assertEqual(positions, sorted(positions))
        for filename in (
            "executed-caller-workflow.yml",
            "executed-runtime-workflow.yml",
            "runtime-workflow-provenance.json",
        ):
            self.assertGreaterEqual(self.workflow.count(filename), 2)

        required_flags = (
            "--github-event-name",
            "--github-ref",
            "--github-sha",
            "--github-workflow-ref",
            "--github-workflow-sha",
            "--github-workflow-blob-sha1",
            "--job-workflow-ref",
            "--job-workflow-sha",
            "--job-workflow-repository",
            "--job-workflow-file-path",
            "--job-workflow-blob-sha1",
            "--workflow-provenance",
        )
        for flag in required_flags:
            self.assertEqual(2, capture["run"].count(flag), flag)

        mutations = [
            (
                '          test "$GITHUB_SHA" = "$CALLER_WORKFLOW_SHA"\n',
                "",
            ),
            (
                '          test "$CALLER_WORKFLOW_SHA" = "$DEFINING_WORKFLOW_SHA"\n',
                "",
            ),
            (
                '              test "$EXPECTED_HEAD_SHA" = "$CALLER_WORKFLOW_SHA"\n',
                "",
            ),
            (
                '            workflow_git fetch --no-tags --depth=1 origin "$GITHUB_REF"\n',
                '            workflow_git fetch origin "$GITHUB_REF" || true\n',
            ),
            (
                '          test "$candidate_caller_workflow_blob" = \\\n'
                '            "$executed_caller_workflow_blob"\n',
                "",
            ),
            (
                '          test "$candidate_job_workflow_blob" = "$executed_job_workflow_blob"\n',
                "",
            ),
            (
                '          /usr/bin/cmp -- "$GITHUB_WORKSPACE/$runtime_workflow_path" \\\n'
                '            "$RUNTIME_EVIDENCE/executed-runtime-workflow.yml"\n',
                "",
            ),
            (
                '              "schema": "mckernel-native-rust-runtime-workflow-provenance-v1",\n',
                '              "schema": "unreviewed",\n',
            ),
            (
                '          CALLER_WORKFLOW_SHA: ${{ github.workflow_sha }}\n',
                "",
            ),
            (
                '          DEFINING_WORKFLOW_SHA: ${{ job.workflow_sha }}\n',
                "",
            ),
        ]
        for flag in required_flags:
            mutations.append(
                (
                    '            {0} '.format(flag),
                    '            --removed-provenance-field ',
                )
            )
        for old, new in mutations:
            mutation = self.workflow.replace(old, new, 1)
            self.assertNotEqual(self.workflow, mutation)
            with self.subTest(old=old.strip()):
                with self.assertRaises(runtime_evidence.EvidenceError):
                    runtime_evidence._validate_runtime_workflow_provenance_boundary(
                        mutation
                    )

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
            "CONFIG_COMPAT",
            "CONFIG_DEVTMPFS",
            "CONFIG_IA32_EMULATION",
            "CONFIG_MISC_DEVICES",
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
            "scripts/native-rust-runtime-mcd0-ioctl-x86_64.S",
            "scripts/native-rust-runtime-mcd0-ioctl-i386.S",
            "scripts/native-rust-runtime-poweroff.S",
            "chmod 1777 \"$INITRAMFS_ROOT/tmp\"",
            "copy_executable /usr/bin/stat /bin/stat",
            "--32 scripts/native-rust-runtime-mcd0-ioctl-i386.S",
            "-m elf_i386 -nostdlib -static -s -z noexecstack",
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
            'MCD0 NODE status=present dev=$mcd0_dev',
            'MCD0 OPEN_CLOSE mode=sequential count=4 status=ok',
            'MCD0 OPEN_CLOSE mode=overlapping count=8 status=ok',
            'MCD0 IOCTL abi=x86_64 expected_errno=EINVAL status=ok',
            'MCD0 IOCTL abi=i386 expected_errno=EINVAL status=ok',
            'MCD0 NEGATIVE operation=unload-smp-with-open-file status=$mcd0_negative_status',
            'MCD0 CLOSE phase=after-module-owner-negative status=ok',
            'negative_output="$(rmmod ihk 2>&1)"',
            'phase=after-negative references=$references users=$users',
            'rmmod mcctrl || { fail unload-mcctrl; exit 1; }',
            'phase=after-mcctrl-unload references=$references users=$users',
            'rmmod ihk_smp_x86_64 || { fail unload-ihk-smp-x86-64; exit 1; }',
            'MCD0 NODE status=removed',
            'phase=after-smp-unload references=$references users=$users',
            'rmmod ihk || { fail unload-ihk; exit 1; }',
            'emit_state first-cycle-clean',
            'RELOAD cycle=1 phase=begin',
            'RELOAD_LOAD cycle=1 module=ihk status=ok',
            'RELOAD_LOAD cycle=1 module=ihk_smp_x86_64 status=ok',
            'RELOAD_LOAD cycle=1 module=mcctrl status=ok',
            'MCD0 RELOAD cycle=1 dev=$mcd0_reload_dev open_close=1 ioctl_x86_64=EINVAL ioctl_i386=EINVAL status=ok',
            'RELOAD_UNLOAD cycle=1 module=mcctrl status=ok',
            'RELOAD_UNLOAD cycle=1 module=ihk_smp_x86_64 status=ok',
            'RELOAD_UNLOAD cycle=1 module=ihk status=ok',
            'RELOAD cycle=1 status=ok',
            'emit_state final-clean',
        )
        positions = [self.init.index(value) for value in ordered]
        self.assertEqual(sorted(positions), positions)
        self.assertIn('[ "$negative_status" -eq 1 ]', self.init)
        self.assertIn('"Module ihk is in use"', self.init)
        self.assertIn('[ "$mcd0_negative_status" -eq 1 ]', self.init)
        self.assertIn('"Module ihk_smp_x86_64 is in use"', self.init)
        self.assertIn("mount -n -t devtmpfs devtmpfs /dev", self.init)
        self.assertIn("valid_mcd0_dev_identity() {", self.init)
        self.assertIn("mcd0_node_matches_identity() {", self.init)
        self.assertIn("*[!0-9]*) return 1", self.init)
        self.assertEqual(2, self.init.count('valid_mcd0_dev_identity "$mcd0'))
        self.assertEqual(2, self.init.count('mcd0_node_matches_identity "$mcd0'))
        self.assertIn("[ \"$minor\" -le 1048575 ]", self.init)
        self.assertIn("/bin/stat -c '%t:%T' /dev/mcd0", self.init)
        self.assertNotIn("/bin/stat -L", self.init)
        self.assertIn("expected=\"$(printf 'a:%x' \"$minor\")\"", self.init)
        self.assertNotIn("10:[0-9]*)", self.init)
        self.assertIn("for worker in 1 2 3 4 5 6 7 8", self.init)
        self.assertIn("[ ! -e /dev/mcd0 ]", self.init)
        self.assertIn("[ ! -e /sys/class/misc/mcd0 ]", self.init)
        self.assertEqual(5, self.init.count("[ ! -L /dev/mcd0 ]"))
        self.assertEqual(2, self.init.count("[ ! -L /sys/class/misc/mcd0 ]"))
        self.assertEqual(2, self.init.count('"$MCD0_IOCTL_NATIVE"'))
        self.assertEqual(2, self.init.count('"$MCD0_IOCTL_COMPAT"'))
        self.assertIn('[ "$references" = 1 ]', self.init)
        self.assertIn('[ "$references" = 0 ]', self.init)
        self.assertEqual(
            3,
            self.init.count(
                "mcctrl,ihk_smp_x86_64,|ihk_smp_x86_64,mcctrl,) ;;"
            ),
        )
        self.assertIn('[ "$users" = \'ihk_smp_x86_64,\' ]', self.init)
        self.assertNotIn('[ "$users" = ihk_smp_x86_64 ]', self.init)

    @unittest.skipUnless(shutil.which("bash"), "bash required")
    def test_mcd0_device_identity_parser_is_canonical_decimal_only(self) -> None:
        start = self.init.index("valid_mcd0_dev_identity() {")
        end = self.init.index(
            "\n}\n\nmcd0_node_matches_identity()", start
        ) + len("\n}")
        function = self.init[start:end]
        script = function + r'''
for value in 10:0 10:1 10:9 10:10 10:255 10:1048575; do
    valid_mcd0_dev_identity "$value" || exit 81
done
for value in 9:1 11:1 10: 10:00 10:01 10:-1 10:+1 10:1x 10:x1 \
    10:1048576 10:9999999 10:999999999999999999999; do
    if valid_mcd0_dev_identity "$value"; then
        exit 82
    fi
done
'''
        completed = subprocess.run(
            [shutil.which("bash"), "--noprofile", "--norc"],
            input=script,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        self.assertEqual(0, completed.returncode, completed.stderr)

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
        nm_sequence = (
            "expected_nm_nevra=binutils-2.41-63.el10.x86_64",
            'expected_nm_digest_algorithm="$(/usr/bin/rpm -q --qf \'%{FILEDIGESTALGO}\\n\' binutils)"',
            'test "$expected_nm_digest_algorithm" = 8',
            "nm_path=/usr/bin/nm",
            'expected_nm_inventory="$(' ,
            "/usr/bin/rpm -q --qf '[%{FILENAMES}\\t%{FILEDIGESTS}\\n]' binutils",
            'test "${#expected_nm_inventory}" -gt 0',
            'test "${#expected_nm_inventory}" -le 1048576',
            "expected_nm_sha256=",
            "expected_nm_rows=0",
            "while IFS=$'\\t' read -r rpm_filename rpm_digest; do",
            'done <<< "$expected_nm_inventory"',
            'test "$expected_nm_rows" -eq 1',
            "verify_nm_package() {",
            'exec {nm_fd}<"$nm_path"',
            'nm_exec="/proc/self/fd/$nm_fd"',
            'test "$(/usr/bin/sha256sum -- "$nm_exec")" = \\',
            "assert_nm_binding() {",
            '--modinfo-sha256 "$expected_modinfo_sha256"',
            '--nm-fd "$nm_fd"',
            '--nm-sha256 "$expected_nm_sha256"',
            "exec {nm_fd}<&-",
        )
        nm_positions = [capture_script.index(item) for item in nm_sequence]
        self.assertEqual(nm_positions, sorted(nm_positions))
        self.assertEqual(2, capture_script.count('--nm-fd "$nm_fd"'))
        self.assertEqual(
            2,
            capture_script.count(
                '--modinfo-sha256 "$expected_modinfo_sha256"'
            ),
        )
        self.assertEqual(
            2, capture_script.count('--nm-sha256 "$expected_nm_sha256"')
        )
        self.assertGreaterEqual(capture_script.count("assert_nm_binding"), 5)
        self.assertIn("verification=\"$(/usr/bin/rpm -V binutils)\" || return 1", capture_script)
        self.assertIn('test "$nm_path" -ef "$nm_exec"', capture_script)
        self.assertIn('"$expected_nm_sha256  $nm_exec"', capture_script)

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
                "          test ! -L \"$nm_path\"\n",
                "          test -e \"$nm_path\"\n",
            ),
            (
                (
                    '          test "$(/usr/bin/rpm -q --qf \'%{NEVRA}\\n\' binutils)" = \\\n'
                    '            "$expected_nm_nevra"\n'
                ),
                "",
            ),
            (
                '          test "$(/usr/bin/rpm -qf --qf \'%{NAME}\\n\' "$nm_path")" = binutils\n',
                "",
            ),
            (
                '          test "$expected_nm_digest_algorithm" = 8\n',
                '          test -n "$expected_nm_digest_algorithm"\n',
            ),
            (
                "            /usr/bin/rpm -q --qf '[%{FILENAMES}\\t%{FILEDIGESTS}\\n]' binutils\n",
                "            /usr/bin/rpm -ql binutils\n",
            ),
            (
                '          test "${#expected_nm_inventory}" -le 1048576\n',
                "",
            ),
            (
                '          done <<< "$expected_nm_inventory"\n',
                '          done < <(printf \'%s\\n\' "$expected_nm_inventory")\n',
            ),
            (
                '          test "$expected_nm_rows" -eq 1\n',
                '          test "$expected_nm_rows" -ge 1\n',
            ),
            (
                '          [[ "$expected_nm_sha256" =~ ^[0-9a-f]{64}$ ]]\n',
                '          test -n "$expected_nm_sha256"\n',
            ),
            (
                (
                    "          verify_nm_package() {\n"
                    "            local verification\n"
                    '            verification="$(/usr/bin/rpm -V binutils)" || return 1\n'
                    '            test -z "$verification"\n'
                    "          }\n"
                ),
                "",
            ),
            (
                '              test "$nm_path" -ef "$nm_exec" &&\n',
                "",
            ),
            (
                (
                    '              test "$(/usr/bin/sha256sum -- "$nm_exec")" = \\\n'
                    '              "$expected_nm_sha256  $nm_exec" &&\n'
                ),
                "",
            ),
            (
                (
                    '              test "$(/usr/bin/rpm -q --qf \'%{NEVRA}\\n\' binutils)" = \\\n'
                    '              "$expected_nm_nevra" &&\n'
                ),
                "",
            ),
            (
                '              test "$(/usr/bin/rpm -qf --qf \'%{NAME}\\n\' "$nm_path")" = binutils &&\n',
                "",
            ),
            (
                "              verify_nm_package\n",
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
                    '            sha256sum --check --strict SHA256SUMS\n'
                    '          )\n'
                    '          assert_modinfo_binding\n'
                    '          assert_nm_binding\n'
                    '          /usr/bin/env -i LANG=C LC_ALL=C PATH=/usr/bin:/bin '
                    'PYTHONHASHSEED=0 TZ=UTC \\\n'
                    '            /usr/bin/python3 -E -s scripts/native_rust_runtime_evidence.py \\\n'
                    '            --repo "$GITHUB_WORKSPACE" \\\n'
                    '            --modinfo-fd "$modinfo_fd" \\\n'
                    '            --modinfo-sha256 "$expected_modinfo_sha256" \\\n'
                    '            --nm-fd "$nm_fd" \\\n'
                    '            --nm-sha256 "$expected_nm_sha256" \\\n'
                ),
                (
                    '            sha256sum --check --strict SHA256SUMS\n'
                    '          )\n'
                    '          assert_modinfo_binding\n'
                    '          assert_nm_binding\n'
                    '          /usr/bin/env -i LANG=C LC_ALL=C PATH=/usr/bin:/bin '
                    'PYTHONHASHSEED=0 TZ=UTC \\\n'
                    '            /usr/bin/python3 -E -s scripts/native_rust_runtime_evidence.py \\\n'
                    '            --repo "$GITHUB_WORKSPACE" \\\n'
                    '            --modinfo-sha256 "$expected_modinfo_sha256" \\\n'
                    '            --nm-fd "$nm_fd" \\\n'
                    '            --nm-sha256 "$expected_nm_sha256" \\\n'
                ),
            ),
            (
                '            --nm-fd "$nm_fd" \\\n',
                "",
            ),
            (
                '            --modinfo-sha256 "$expected_modinfo_sha256" \\\n',
                "",
            ),
            (
                '            --nm-sha256 "$expected_nm_sha256" \\\n',
                "",
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
                    '          assert_nm_binding\n'
                    '          exec {nm_fd}<&-\n'
                    '          exec {modinfo_fd}<&-\n'
                ),
                (
                    '            --build-evidence-dir "$BUILD_EVIDENCE"\n'
                    '          assert_nm_binding\n'
                    '          exec {nm_fd}<&-\n'
                    '          exec {modinfo_fd}<&-\n'
                ),
            ),
            (
                (
                    '            sha256sum --check --strict SHA256SUMS\n'
                    '          )\n'
                    '          assert_modinfo_binding\n'
                    '          assert_nm_binding\n'
                    '          /usr/bin/env -i LANG=C LC_ALL=C PATH=/usr/bin:/bin '
                ),
                (
                    '            sha256sum --check --strict SHA256SUMS\n'
                    '          )\n'
                    '          exec {modinfo_fd}<&-\n'
                    '          assert_nm_binding\n'
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
                    runtime_evidence._validate_runtime_nm_boundary(mutation)

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
            trusted_modinfo_sha256 = runtime_evidence._sha256_file(target)

            def runtime_modinfo_call(descriptor_number):
                with mock.patch.object(
                    runtime_evidence,
                    "EXPECTED_MODINFO_SHA256",
                    trusted_modinfo_sha256,
                ):
                    return runtime_evidence._run_field(
                        module,
                        "name",
                        descriptor_number,
                        modinfo_sha256=trusted_modinfo_sha256,
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
                    lambda: runtime_modinfo_call(descriptor),
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
                invalid_format_sha256 = runtime_evidence._sha256_file(
                    invalid_format
                )

                def runtime_invalid_format_call():
                    with mock.patch.object(
                        runtime_evidence,
                        "EXPECTED_MODINFO_SHA256",
                        invalid_format_sha256,
                    ):
                        return runtime_evidence._run_field(
                            module,
                            "name",
                            invalid_format_fd,
                            modinfo_sha256=invalid_format_sha256,
                        )

                invalid_calls = (
                    (lambda: ihk_lifecycle._modinfo(module, "name", invalid_format_fd), ihk_lifecycle.ValidationError),
                    (lambda: smp_lifecycle._modinfo(module, "name", invalid_format_fd), smp_lifecycle.ValidationError),
                    (lambda: mcctrl_lifecycle._modinfo(module, "name", invalid_format_fd), mcctrl_lifecycle.ValidationError),
                    (runtime_invalid_format_call, runtime_evidence.EvidenceError),
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

    @unittest.skipUnless(shutil.which("as") and shutil.which("ld"), "binutils required")
    def test_mcd0_ioctl_helpers_are_static_native_and_compat_executables(self) -> None:
        cases = (
            (
                MCD0_IOCTL_X86_64,
                "--64",
                "elf_x86_64",
                "ELF64",
                "Advanced Micro Devices X86-64",
            ),
            (MCD0_IOCTL_I386, "--32", "elf_i386", "ELF32", "Intel 80386"),
        )
        with tempfile.TemporaryDirectory(prefix="native-rust-mcd0-ioctl-") as temporary:
            root = Path(temporary)
            for source, as_mode, ld_mode, elf_class, machine in cases:
                with self.subTest(source=source.name):
                    obj = root / (source.stem + ".o")
                    executable = root / source.stem
                    subprocess.run(
                        ["as", as_mode, str(source), "-o", str(obj)], check=True
                    )
                    subprocess.run(
                        [
                            "ld",
                            "-m",
                            ld_mode,
                            "-nostdlib",
                            "-static",
                            "-s",
                            "-z",
                            "noexecstack",
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
                    self.assertIn("Class:                             " + elf_class, output)
                    self.assertIn("Machine:                           " + machine, output)

                    program = source.read_text(encoding="utf-8")
                    self.assertIn("/dev/mcd0", program)
                    self.assertIn("cmp $-22", program)
                    self.assertIn(".note.GNU-stack", program)

        expected_retained_modes = (
            "chmod 0644 \\\n"
            '            "$RUNTIME_EVIDENCE/'
            'native-rust-runtime-mcd0-ioctl-x86_64" \\\n'
            '            "$RUNTIME_EVIDENCE/'
            'native-rust-runtime-mcd0-ioctl-i386"'
        )
        self.assertIn(expected_retained_modes, self.workflow)


if __name__ == "__main__":
    unittest.main()
