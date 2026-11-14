"""Compile extracted production dispatch against a mock, without runtime credit."""

import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import unittest


REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts import ihk_smp_native_lifecycle_check as lifecycle


def extract_function(source: str, name: str) -> str:
    code = lifecycle._mask_rust_comments_and_literals(source)
    matches = list(re.finditer(r"(?m)^\s*(?:pub(?:\(super\))?\s+)?fn " + re.escape(name) + r"\(", code))
    if len(matches) != 1:
        raise AssertionError(f"expected one production {name} function")
    start = matches[0].start()
    opening = code.index("{", matches[0].end())
    depth = 1
    for end in range(opening + 1, len(code)):
        if code[end] == "{":
            depth += 1
        elif code[end] == "}":
            depth -= 1
            if depth == 0:
                return source[start:end + 1].strip()
    raise AssertionError(f"unclosed production {name} function")


def render_fixture(source: str) -> str:
    constants = []
    for name in ("IHK_DEVICE_GET_BUILDID", "IHK_COMPAT_BUILD_ID",
                 "IHK_DEVICE_CREATE_OS", "IHK_DEVICE_DESTROY_OS", "IHK_SMP_CONTROL_DEVICE_MINOR"):
        matches = re.findall(r"(?m)^const " + name + r":[^\n]+;$", source)
        if len(matches) != 1:
            raise AssertionError(f"expected one production {name} constant")
        constants.append(matches[0])
    template = (REPO_ROOT / "scripts/tests/fixtures/ihk_smp_buildid_compile.rs").read_text()
    cpu_source = (REPO_ROOT / "host-kernel/native-rust/smp_cpu.rs").read_text()
    memory_source = (REPO_ROOT / "host-kernel/native-rust/smp_memory.rs").read_text()
    cpu_abi = (REPO_ROOT / "host-kernel/native-rust/abi/x86_64.rs").read_text()
    cpu_constants = []
    for name in ("IHK_DEVICE_RESERVE_CPU", "IHK_DEVICE_RELEASE_CPU",
                 "IHK_DEVICE_GET_NUM_CPUS", "IHK_DEVICE_QUERY_CPU"):
        matches = re.findall(r"(?m)^pub const " + name + r":[^\n]+;$", cpu_abi)
        if len(matches) != 1:
            raise AssertionError(f"expected one canonical CPU ABI constant: {name}")
        cpu_constants.append(matches[0])
    memory_constants = []
    for name in ("IHK_DEVICE_RESERVE_MEM", "IHK_DEVICE_RELEASE_MEM",
                 "IHK_DEVICE_QUERY_MEM", "IHK_DEVICE_RELEASE_MEM_PARTIALLY"):
        matches = re.findall(r"(?m)^pub const " + name + r":[^\n]+;$", cpu_abi)
        if len(matches) != 1:
            raise AssertionError(f"expected one canonical memory ABI constant: {name}")
        memory_constants.append(matches[0])
    replacements = {
        "// PRODUCTION_CPU_ABI_CONSTANTS": "\n".join(cpu_constants),
        "// PRODUCTION_CPU_HANDLES": extract_function(cpu_source, "handles"),
        "// PRODUCTION_MEMORY_ABI_CONSTANTS": "\n".join(memory_constants),
        "// PRODUCTION_MEMORY_HANDLES": extract_function(memory_source, "handles"),
        "// PRODUCTION_BUILDID_CONSTANTS": "\n".join(constants),
        "// PRODUCTION_BUILDID_DISPATCH": extract_function(source, "control_device_ioctl"),
        "// PRODUCTION_DEVICE_REQUEST": extract_function(source, "control_device_request"),
        "// PRODUCTION_NATIVE_IOCTL": extract_function(source, "ioctl"),
        "// PRODUCTION_COMPAT_IOCTL": "#[cfg(CONFIG_COMPAT)]\n" + extract_function(source, "compat_ioctl"),
    }
    for marker, value in replacements.items():
        if template.count(marker) != 1:
            raise AssertionError(f"missing or duplicate fixture marker: {marker}")
        template = template.replace(marker, value)
    return template


class IhkSmpBuildidSourceFixtureTests(unittest.TestCase):
    def test_extracted_production_dispatch_against_mock_usercopy(self) -> None:
        compiler = os.environ.get("RUSTC") or shutil.which("rustc")
        if compiler is None:
            self.skipTest("rustc unavailable for the source-only GET_BUILDID fixture")
        contract = lifecycle._load_json(REPO_ROOT / lifecycle.DEFAULT_CONTRACT)
        source = (REPO_ROOT / contract["production_source"]).read_text()
        lifecycle._validate_rust_source(source, contract)
        with tempfile.TemporaryDirectory(prefix="ihk-buildid-source-fixture-") as temporary:
            directory = Path(temporary)
            fixture = directory / "ihk_smp_buildid_compile.rs"
            fixture.write_text(render_fixture(source))
            (directory / "ihk-compat-build-id.bin").write_bytes(b"fixture-id\0")
            binary = directory / "fixture-tests"
            compile_result = subprocess.run(
                [compiler, "--edition=2021", "--test", "--cfg", "CONFIG_COMPAT", str(fixture), "-o", str(binary)],
                capture_output=True, text=True, check=False,
            )
            self.assertEqual(0, compile_result.returncode, compile_result.stderr)
            result = subprocess.run([str(binary)], capture_output=True, text=True, check=False)
            self.assertEqual(0, result.returncode, result.stdout + result.stderr)
            self.assertIn("8 passed; 0 failed", result.stdout)


if __name__ == "__main__":
    unittest.main()
