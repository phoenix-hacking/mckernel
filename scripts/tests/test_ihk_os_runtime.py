"""Execute the complete native OS adapter with fault-injectable Linux mocks."""

from contextlib import nullcontext
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]


class NativeOsRuntimeTests(unittest.TestCase):
    def test_complete_adapter_ownership_failure_and_race_cases(self):
        rustc = os.environ.get("MCKERNEL_RUSTC_1_92") or os.environ.get("RUSTC") or shutil.which("rustc")
        if not rustc:
            self.skipTest("rustc is unavailable for native OS adapter execution")
        template = (ROOT / "scripts/tests/fixtures/ihk_os_runtime_compile.rs").read_text()
        # Keep private-access tests and corruption injection in the fixture,
        # appended to byte-for-byte production bodies in disposable copies.
        template, runtime_tests = template.split("// RUNTIME_PRIVATE_TESTS\n")
        runtime_tests, registry_fault = runtime_tests.split("// REGISTRY_FIXTURE_FAULT\n")
        modules = []
        for name in ("abi", "application_abi", "service_abi", "device_registry", "os_registry", "ihk_ioctl", "os_service", "os_runtime"):
            relative = {"abi": "abi/x86_64.rs", "application_abi": "abi/application.rs",
                        "service_abi": "abi/os_service.rs"}.get(name, name + ".rs")
            path = ROOT / "host-kernel/native-rust" / relative
            # Match the production crate's data-only ABI-module visibility lint.
            attributes = '#[allow(unreachable_pub)]\n' if name == 'abi' else ''
            modules.append(attributes + '#[path = "' + str(path) + '"]\nmod ' + name + ';')
        provider = (ROOT / "host-kernel/native-rust/ihk_smp_x86_64.rs").read_text()
        registration = provider.split("ihk_os_create_unbooted_v6(", 1)[1].split("Some(ihk_smp_os_ioctl_v2)", 1)[0]
        self.assertEqual("2", registration.splitlines()[-2].strip().rstrip(","))
        start = provider.split('unsafe extern "C" fn ihk_smp_start_boot_v3', 1)[1].split("fn shutdown_v6_post_effect", 1)[0]
        self.assertIn("match smp_cpu::start_os_boot(owner)", start)
        self.assertIn("Ok(()) => 0", start)
        self.assertEqual(1, template.count("// SOURCE_MODULES"))
        retained = os.environ.get("MCKERNEL_OS_RUNTIME_EVIDENCE")
        workspace = (nullcontext(tempfile.mkdtemp(prefix="ihk-os-runtime-", dir=retained))
                     if retained else tempfile.TemporaryDirectory(prefix="ihk-os-runtime-"))
        with workspace as temporary:
            directory = Path(temporary)
            for name in ("abi", "application_abi", "service_abi", "device_registry", "os_registry", "ihk_ioctl", "os_service", "os_runtime"):
                relative = {"abi": "abi/x86_64.rs", "application_abi": "abi/application.rs",
                            "service_abi": "abi/os_service.rs"}.get(name, name + ".rs")
                source = ROOT / "host-kernel/native-rust" / relative
                copy = directory / (name + ".rs")
                supplement = {"os_runtime": runtime_tests, "os_registry": registry_fault}.get(name, "")
                copy.write_text(source.read_text() + ("\n" + supplement if supplement else ""))
                modules = [entry.replace(str(source), str(copy)) for entry in modules]
            fixture = directory / "fixture.rs"
            fixture.write_text(template.replace("// SOURCE_MODULES", "\n".join(modules)))
            binary = directory / "tests"
            environment = dict(os.environ, RUSTC_BOOTSTRAP="1")
            def captured(label, command, **kwargs):
                (directory / (label + ".command.json")).write_text(json.dumps(command) + "\n")
                try:
                    result = subprocess.run(command, capture_output=True, text=True, **kwargs)
                except subprocess.TimeoutExpired as error:
                    (directory / (label + ".stdout")).write_bytes(error.stdout or b"")
                    (directory / (label + ".stderr")).write_bytes(error.stderr or b"")
                    (directory / (label + ".status.json")).write_text(
                        json.dumps({"returncode": None, "timeout_seconds": error.timeout}) + "\n")
                    raise
                (directory / (label + ".stdout")).write_text(result.stdout)
                (directory / (label + ".stderr")).write_text(result.stderr)
                (directory / (label + ".status.json")).write_text(
                    json.dumps({"returncode": result.returncode}) + "\n")
                return result

            result = captured("compile",
                [rustc, "--edition=2021", "--test", "--cfg", "CONFIG_COMPAT", "-Dwarnings", "-Dunreachable-pub",
                 str(fixture), "-o", str(binary)],
                env=environment, timeout=90,
            )
            self.assertEqual(0, result.returncode, result.stdout + result.stderr)
            result = captured("run", [str(binary), "--test-threads=1"], timeout=90)
            self.assertEqual(0, result.returncode, result.stdout + result.stderr)
            self.assertIn("70 passed; 0 failed", result.stdout)
            print(result.stdout, end="")


if __name__ == "__main__":
    unittest.main()
