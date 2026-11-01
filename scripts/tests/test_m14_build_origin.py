"""Exercise the actual selected F06 origin producer without a kernel build.

These checks run only the source-metadata generator used by CMake. They do not
compile a kernel, grant native admission, or accept production artifacts.
"""

import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]
PRODUCER = ROOT / "scripts/derive_f06_origin.py"
SOURCE = ROOT / "arch/x86_64/kernel/syscall.c"
DEBUG_HEADER = ROOT / "lib/include/ihk/debug.h"
SOURCE_BINDING = ROOT / "scripts/f06_origin_source_binding.json"


def selected_profile():
    """Follow the production CMake binding instead of choosing a test profile."""
    source = (ROOT / "kernel/CMakeLists.txt").read_text()
    matches = re.findall(
        r'set\(MCKERNEL_F06_ORIGIN_PROFILE\s+"\$\{PROJECT_SOURCE_DIR\}/([^"\n]+)"\)',
        source,
    )
    if len(matches) != 1:
        raise ValueError(f"Expected one literal F06 profile binding, found {len(matches)}")
    return ROOT / matches[0]


class M14BuildOriginTests(unittest.TestCase):
    def run_producer(self, profile, source, output, binding=SOURCE_BINDING):
        command = [sys.executable, "-B", str(PRODUCER), "--profile", str(profile),
                   "--source", str(source), "--output", str(output)]
        if binding is not None:
            command.extend(["--source-binding", str(binding)])
        return subprocess.run(
            command,
            capture_output=True, text=True, timeout=15,
        )

    def assert_rejected(self, result, output, reason=None):
        self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
        if reason is not None:
            self.assertIn(reason, result.stderr)
        self.assertFalse((output / "ORIGIN-BINDING.json").exists(),
                         "Rejected source/profile must not emit a binding receipt")

    def test_selected_profile_generates_current_source_metadata(self):
        profile = selected_profile()
        with tempfile.TemporaryDirectory(prefix="m14-build-origin-") as temporary:
            output = Path(temporary) / "output"
            result = self.run_producer(profile, SOURCE, output)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            receipt = json.loads((output / "ORIGIN-BINDING.json").read_text())
            self.assertEqual(receipt["source_sha256"],
                             hashlib.sha256(SOURCE.read_bytes()).hexdigest())
            self.assertEqual(receipt["profile_sha256"],
                             hashlib.sha256(profile.read_bytes()).hexdigest())
            self.assertEqual(receipt["source_binding_sha256"],
                             hashlib.sha256(SOURCE_BINDING.read_bytes()).hexdigest())
            self.assertEqual(receipt["command"]["argv"][-1], receipt["origin_utf8"])
            self.assertEqual(receipt["origin_bytes_with_nul"],
                             list(receipt["origin_utf8"].encode("ascii") + b"\0"))
            self.assertEqual(receipt["new_C_runtime_objects"], 0)
            self.assertIsNone(receipt["compiled_Rust_metadata_qualification"])
            metadata = (output / "f06_clone_cpuid_metadata.rs").read_text()
            for slot in receipt["clone_cpuid_debug_slots"]:
                self.assertIn(f"= {slot['line_flags']};", metadata)

    def test_current_source_without_binding_still_rejects(self):
        with tempfile.TemporaryDirectory(prefix="m14-build-origin-unbound-") as temporary:
            output = Path(temporary) / "output"
            self.assert_rejected(
                self.run_producer(selected_profile(), SOURCE, output, binding=None), output,
                "exact proposed architecture source bytes required")

    def test_changed_binding_bytes_are_rejected(self):
        with tempfile.TemporaryDirectory(prefix="m14-build-origin-binding-") as temporary:
            root = Path(temporary)
            binding = root / "modified-binding.json"
            binding.write_bytes(SOURCE_BINDING.read_bytes() + b"\n")
            output = root / "output"
            result = self.run_producer(selected_profile(), SOURCE, output, binding=binding)
            self.assert_rejected(result, output)
            self.assertIn("binding", result.stderr.lower())

    def test_changed_profile_bytes_are_rejected(self):
        with tempfile.TemporaryDirectory(prefix="m14-build-origin-profile-") as temporary:
            root = Path(temporary)
            profile = root / "modified-profile.json"
            profile.write_bytes(selected_profile().read_bytes() + b"\n")
            output = root / "output"
            self.assert_rejected(self.run_producer(profile, SOURCE, output), output,
                                 "unqualified SDK profile bytes")

    def test_changed_source_bytes_are_rejected(self):
        with tempfile.TemporaryDirectory(prefix="m14-build-origin-source-") as temporary:
            root = Path(temporary)
            source = root / "arch/x86_64/kernel/syscall.c"
            source.parent.mkdir(parents=True)
            source.write_bytes(SOURCE.read_bytes() + b"\n/* unbound source change */\n")
            output = root / "output"
            self.assert_rejected(self.run_producer(selected_profile(), source, output), output,
                                 "exact proposed architecture source bytes required")

    def test_changed_debug_header_is_rejected(self):
        with tempfile.TemporaryDirectory(prefix="m14-build-origin-header-") as temporary:
            root = Path(temporary)
            source = root / "arch/x86_64/kernel/syscall.c"
            source.parent.mkdir(parents=True)
            source.write_bytes(SOURCE.read_bytes())
            header = root / "lib/include/ihk/debug.h"
            header.parent.mkdir(parents=True)
            header.write_bytes(DEBUG_HEADER.read_bytes() + b"\n/* unbound header change */\n")
            output = root / "output"
            self.assert_rejected(self.run_producer(selected_profile(), source, output), output,
                                 "genuine defining Ddebug header changed")

    def test_clone_body_and_logical_line_checks_remain_independent(self):
        spec = importlib.util.spec_from_file_location("m14_origin_producer", PRODUCER)
        producer = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(producer)
        original = SOURCE.read_text()
        signature = "int obtain_clone_cpuid(cpu_set_t *cpu_set, int use_last) {"
        start = original.index(signature)
        return_position = original.index("return min_cpu;", start)
        changed_body = (original[:return_position] + "return min_cpu + 0;" +
                        original[return_position + len("return min_cpu;"):])
        marker = "#line 884\n" + signature
        self.assertEqual(original.count(marker), 1)
        changed_line = original.replace(marker, "#line 885\n" + signature, 1)
        for text, reason in (
            (changed_body, "qualified full body changed"),
            (changed_line, "genuine retained C descriptor identity changed"),
        ):
            with self.subTest(reason=reason), tempfile.TemporaryDirectory(
                    prefix="m14-build-origin-invariant-") as temporary:
                root = Path(temporary)
                source = root / "arch/x86_64/kernel/syscall.c"
                source.parent.mkdir(parents=True)
                source.write_text(text)
                header = root / "lib/include/ihk/debug.h"
                header.parent.mkdir(parents=True)
                header.write_bytes(DEBUG_HEADER.read_bytes())
                # Test only an invariant rejection. This helper is never used to
                # qualify altered source or bypass the public source-binding gate.
                with self.assertRaisesRegex(ValueError, reason):
                    producer.derive_clone_cpuid(
                        selected_profile(), source, "/src/arch/x86_64/kernel/syscall.c")

    def test_original_source_without_binding_remains_accepted_when_available(self):
        git = shutil.which("git")
        if git is None:
            self.skipTest("Git unavailable for optional original-source fixture")
        revision = "5a5d7e77ab4ada91777f1ee06c5d7fbdb98f5b71:arch/x86_64/kernel/syscall.c"
        # Never fetch history for this optional preservation check.
        env = dict(os.environ, GIT_NO_LAZY_FETCH="1", GIT_TERMINAL_PROMPT="0")
        original = subprocess.run([git, "show", revision], cwd=ROOT, env=env,
                                  capture_output=True, timeout=15)
        if original.returncode:
            self.skipTest("Original source object is not available locally")
        with tempfile.TemporaryDirectory(prefix="m14-build-origin-original-") as temporary:
            root = Path(temporary)
            source = root / "arch/x86_64/kernel/syscall.c"
            source.parent.mkdir(parents=True)
            source.write_bytes(original.stdout)
            header = root / "lib/include/ihk/debug.h"
            header.parent.mkdir(parents=True)
            header.write_bytes(DEBUG_HEADER.read_bytes())
            output = root / "output"
            result = self.run_producer(selected_profile(), source, output, binding=None)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            receipt = json.loads((output / "ORIGIN-BINDING.json").read_text())
            self.assertEqual(receipt["source_sha256"],
                             hashlib.sha256(original.stdout).hexdigest())
            self.assertIsNone(receipt.get("source_binding_sha256"))

    def test_configured_metadata_inputs_trigger_reconfigure(self):
        cmake = os.environ.get("CMAKE") or shutil.which("cmake")
        if cmake is None:
            self.skipTest("CMake unavailable for isolated dependency-property check")
        parser_path = ROOT / "scripts/tests/test_m14_syscall_selection.py"
        spec = importlib.util.spec_from_file_location("m14_cmake_commands", parser_path)
        parser = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(parser)
        parsed = parser.commands((ROOT / "kernel/CMakeLists.txt").read_text())
        bindings = [text for name, text in parsed if name == "set"
                    and re.search(r"\(\s*MCKERNEL_F06_", text)
                    and '"${PROJECT_SOURCE_DIR}/' in text]
        dependencies = [text for name, text in parsed if name == "set_property"
                        and "CMAKE_CONFIGURE_DEPENDS" in text
                        and "MCKERNEL_F06_ORIGIN_PRODUCER" in text]
        self.assertTrue(dependencies, "Expected actual F06 dependency statements")
        fixture = "\n".join([
            "cmake_minimum_required(VERSION 3.16)",
            "project(m14_origin_dependencies LANGUAGES NONE)",
            "set(ARCH x86_64)", *bindings, *dependencies,
            "get_property(inputs DIRECTORY PROPERTY CMAKE_CONFIGURE_DEPENDS)",
            'file(WRITE "${CMAKE_BINARY_DIR}/dependencies.txt" "${inputs}")',
        ])
        with tempfile.TemporaryDirectory(prefix="m14-build-origin-deps-") as temporary:
            root = Path(temporary)
            source, build = root / "source", root / "build"
            source.mkdir()
            (source / "CMakeLists.txt").write_text(fixture)
            result = subprocess.run([cmake, "-S", str(source), "-B", str(build)],
                                    capture_output=True, text=True, timeout=15)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            inputs = set((build / "dependencies.txt").read_text().split(";"))
            expected = {str(source / relative) for relative in (
                "scripts/derive_f06_origin.py", "scripts/f06_origin_command_profile.json",
                "scripts/f06_origin_source_binding.json", "arch/x86_64/kernel/syscall.c",
                "lib/include/ihk/debug.h",
            )}
            self.assertTrue(expected.issubset(inputs),
                            "Missing actual configure dependencies: " + str(expected - inputs))


if __name__ == "__main__":
    unittest.main()
