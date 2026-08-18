#!/usr/bin/env python3

from pathlib import Path
import os
import shlex
import subprocess
import tempfile
import unittest


REPO_ROOT = Path(__file__).resolve().parents[2]
RUNNER = REPO_ROOT / "scripts/qemu-mckernel-guest.sh"
ROCKY_WRAPPER = REPO_ROOT / "scripts/qemu-rocky-rust-validation.sh"
WORKFLOW = REPO_ROOT / ".github/workflows/rust-x86_64-validation.yml"


class QemuMcKernelGuestCpuPolicyTests(unittest.TestCase):
    def _write_executable(self, path, contents):
        path.write_text(contents, encoding="utf-8")
        path.chmod(0o755)

    def _dry_run_args(self, accel):
        with tempfile.TemporaryDirectory(prefix="qemu-cpu-policy-") as temporary:
            root = Path(temporary)
            fake_bin = root / "bin"
            fake_bin.mkdir()
            image = root / "rocky.qcow2"
            image.write_bytes(b"test image\n")
            ssh_key = root / "id_test"
            ssh_key.write_text("test private key\n", encoding="utf-8")
            ssh_key.with_suffix(".pub").write_text(
                "ssh-ed25519 test qemu-cpu-policy\n", encoding="utf-8"
            )

            self._write_executable(
                fake_bin / "qemu-img",
                """#!/usr/bin/env bash
set -eu
case "$1" in
    info)
        printf 'file format: qcow2\\n'
        ;;
    create)
        for argument in "$@"; do
            output="$argument"
        done
        : >"$output"
        ;;
    *)
        exit 64
        ;;
esac
""",
            )
            self._write_executable(
                fake_bin / "cloud-localds",
                """#!/usr/bin/env bash
set -eu
: >"$1"
""",
            )
            self._write_executable(
                fake_bin / "qemu-system-x86_64",
                """#!/usr/bin/env bash
exit 99
""",
            )

            environment = os.environ.copy()
            environment["PATH"] = f"{fake_bin}{os.pathsep}{environment['PATH']}"
            log_dir = root / "logs"
            # The runner correctly refuses a real KVM launch without /dev/kvm.
            # Override only those two file tests so --dry-run can exercise the
            # production command builder on deterministic test hosts.
            shell = r"""
function [ {
    case "$*" in
        '-r /dev/kvm ]'|'-w /dev/kvm ]') return 0 ;;
        '! -r /dev/kvm ]'|'! -w /dev/kvm ]') return 1 ;;
    esac
    builtin [ "$@"
}
source "$1" \
    --image "$2" \
    --ssh-key "$3" \
    --accel "$4" \
    --log-dir "$5" \
    --dry-run
"""
            result = subprocess.run(
                [
                    "bash",
                    "-c",
                    shell,
                    "qemu-cpu-policy-test",
                    str(RUNNER),
                    str(image),
                    str(ssh_key),
                    accel,
                    str(log_dir),
                ],
                check=True,
                env=environment,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True,
            )
            model_file = (log_dir / "qemu-cpu-model.txt").read_text(
                encoding="utf-8"
            )

        prefix = "QEMU command: "
        command_line = next(
            line[len(prefix) :]
            for line in result.stdout.splitlines()
            if line.startswith(prefix)
        )
        return shlex.split(command_line), result.stdout, model_file

    def test_kvm_command_masks_la57_and_rejects_raw_host(self):
        arguments, stdout, model_file = self._dry_run_args("kvm")
        self.assertEqual(1, arguments.count("-cpu"))
        cpu_index = arguments.index("-cpu")
        self.assertEqual("host,la57=off", arguments[cpu_index + 1])
        self.assertNotEqual("host", arguments[cpu_index + 1])
        self.assertEqual(
            1, stdout.splitlines().count("QEMU cpu model: host,la57=off")
        )
        self.assertEqual("host,la57=off\n", model_file)

    def test_tcg_command_masks_la57_on_max_cpu_model(self):
        arguments, stdout, model_file = self._dry_run_args("tcg")
        self.assertEqual(1, arguments.count("-cpu"))
        cpu_index = arguments.index("-cpu")
        self.assertEqual("max,la57=off", arguments[cpu_index + 1])
        self.assertNotEqual("max", arguments[cpu_index + 1])
        self.assertEqual(
            1, stdout.splitlines().count("QEMU cpu model: max,la57=off")
        )
        self.assertEqual("max,la57=off\n", model_file)

    def test_rocky_workflow_checks_the_pinned_cpu_policy(self):
        wrapper = ROCKY_WRAPPER.read_text(encoding="utf-8")
        workflow = WORKFLOW.read_text(encoding="utf-8")
        self.assertIn("grep -qw la57 /proc/cpuinfo", wrapper)
        self.assertIn('echo "QEMU guest LA57: absent"', wrapper)
        self.assertIn("scripts/qemu-mckernel-guest.sh", workflow)
        self.assertIn(
            "scripts.tests.test_qemu_mckernel_guest_cpu_policy", workflow
        )
        self.assertIn('qemu/qemu-cpu-model.txt"', workflow)
        self.assertIn("test \"$(wc -l < \"$qemu_cpu_model_file\")\" -ne 1", workflow)
        self.assertIn(
            "test \"$(cat \"$qemu_cpu_model_file\")\" != 'host,la57=off'",
            workflow,
        )
        self.assertIn("'QEMU guest LA57: absent'", workflow)


if __name__ == "__main__":
    unittest.main()
