"""Configure isolated copies of actual M14 CMake selection statements.

No production project, SDK, Rust compiler, kernel target or native controls are
used. These tests cover option/guard/property composition, not image acceptance.
"""
from pathlib import Path
import os
import re
import shutil
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]
CMAKE_SOURCE = ROOT / "kernel/CMakeLists.txt"
OPTION = "ENABLE_RUST_M14_SYSCALL_ADAPTERS"
BASE_ARCH = {"MCKERNEL_RUST_SYSCALL_POLICY_HELPERS", "MCKERNEL_RUST_X86_CPU_HELPERS"}
EARLY_ARCH = "MCKERNEL_RUST_F06_OBTAIN_CLONE_CPUID"
NEW_ARCH = {
    "MCKERNEL_RUST_F06_NATIVE_SIGNAL_BAD_FRAME",
    "MCKERNEL_RUST_F06_PTRACE_REGSET_LOG",
    "MCKERNEL_RUST_F06_SIGNAL_TRAP_INFO",
}
NEW_GENERIC = "MCKERNEL_RUST_F03_FORWARD_ADAPTERS"
NEW_CFG = {
    "f03_forward_adapters_candidate",
    "f06_signal_ptrace_diagnostics_candidate",
    "f06_signal_trap_info_candidate",
}
NEW_MODULES = {
    "f03_forward_adapters.rs",
    "f03_ptrace_adapters.rs",
    "f03_host_cleanup.rs",
    "f03_credential_refresh.rs",
    "f06_signal_ptrace_diagnostics.rs",
    "f06_signal_trap_info.rs",
}


def commands(source):
    """Read line-started CMake commands, respecting quoted/comment parentheses.

    Only command names and verbatim spans are needed for the few extracted
    statements; this does not interpret CMake expressions or execute source.
    """
    result = []
    offset = 0
    pattern = re.compile(r"^[ \t]*([A-Za-z_][A-Za-z_0-9]*)\s*\(", re.M)
    while match := pattern.search(source, offset):
        cursor = match.end()
        depth, quoted, comment = 1, False, False
        while depth:
            if cursor >= len(source):
                raise ValueError("Unclosed CMake command: " + match.group(1))
            char = source[cursor]
            if comment:
                comment = char != "\n"
            elif char == "\\":
                cursor += 1
            elif char == '"':
                quoted = not quoted
            elif not quoted:
                if char == "#":
                    comment = True
                elif char == "(":
                    depth += 1
                elif char == ")":
                    depth -= 1
            cursor += 1
        result.append((match.group(1).lower(), source[match.start():cursor]))
        offset = cursor
    return result


def one(items, description):
    if len(items) != 1:
        raise ValueError(f"Expected one {description}, found {len(items)}")
    return items[0]


def if_block(parsed, index):
    depth = 0
    for end in range(index, len(parsed)):
        name = parsed[end][0]
        depth += (name == "if") - (name == "endif")
        if depth == 0:
            return "\n".join(text for _, text in parsed[index:end + 1])
    raise ValueError("Unclosed candidate if block")


def selection_statements():
    parsed = commands(CMAKE_SOURCE.read_text())
    option = one([text for name, text in parsed
                  if name == "option" and re.search(r"\(\s*" + OPTION + r"\s", text)],
                 "candidate option")
    guard = one([if_block(parsed, index) for index, (name, text) in enumerate(parsed)
                 if name == "if" and re.search(r"\(\s*" + OPTION + r"\s+AND\b", text)],
                "unsupported-profile guard")
    blocks = [if_block(parsed, index) for index, (name, text) in enumerate(parsed)
              if name == "if" and re.search(r"\(\s*" + OPTION + r"\s*\)", text)]
    if len(blocks) != 2:
        raise ValueError(f"Expected two candidate selection blocks, found {len(blocks)}")
    early = one([text for name, text in parsed
                 if name == "set_property" and '"${MCKERNEL_F06_C_SOURCE}"' in text
                 and re.search(r"\b" + EARLY_ARCH + r"\b", text)],
                "earlier F06 architecture append")
    # Match the actual base setter by its two complete guard names; support the
    # original setter spelling so a regression is demonstrated by behavior.
    base = one([text for name, text in parsed
                if name in ("set_property", "set_source_files_properties")
                and '"${PROJECT_SOURCE_DIR}/arch/${ARCH}/kernel/syscall.c"' in text
                and all(re.search(r"\b" + flag + r"\b", text) for flag in BASE_ARCH)],
               "final SMP-x86 architecture base setter")
    return option, guard, blocks, early, base


class M14SignalForwardSelectionTests(unittest.TestCase):
    def test_signal_pair_tracks_c_selection_and_rust_inputs(self):
        option_name = "MCKERNEL_F03_SIGNAL_FORWARD_EXPERIMENTAL"
        parsed = commands(CMAKE_SOURCE.read_text())
        option = one([text for name, text in parsed if name == "option"
                      and re.search(r"\(\s*" + option_name + r"\s", text)],
                     "signal-forward option")
        guard = one([if_block(parsed, index) for index, (name, text) in enumerate(parsed)
                     if name == "if" and re.search(r"\(\s*" + option_name + r"\s+AND\b", text)],
                    "signal-forward supported-profile guard")
        blocks = [if_block(parsed, index) for index, (name, text) in enumerate(parsed)
                  if name == "if" and re.search(r"\(\s*" + option_name + r"\s*\)", text)]
        self.assertEqual(len(blocks), 2)
        cmake = os.environ.get("CMAKE") or shutil.which("cmake")
        self.assertIsNotNone(cmake, "CMake is required")
        fixture = "\n".join([
            "cmake_minimum_required(VERSION 3.16)",
            "project(signal_pair_selection LANGUAGES NONE)", option, guard,
            'set(RUST_KERNEL_CFG BASE_CFG)',
            'set(RUST_KERNEL_SRCS base.rs)',
            'set_property(SOURCE "${CMAKE_CURRENT_SOURCE_DIR}/syscall.c" PROPERTY',
            '    COMPILE_DEFINITIONS MCKERNEL_RUST_SYSCALL_POLICY_HELPERS)',
            *blocks,
            'get_source_file_property(defs "${CMAKE_CURRENT_SOURCE_DIR}/syscall.c" COMPILE_DEFINITIONS)',
            'file(WRITE "${CMAKE_BINARY_DIR}/selection.txt"',
            '    "defs=${defs}\\ncfg=${RUST_KERNEL_CFG}\\nsrcs=${RUST_KERNEL_SRCS}\\n")',
        ])
        for enabled in (False, True):
            with self.subTest(enabled=enabled), tempfile.TemporaryDirectory(prefix="m14-signal-selection-") as temp:
                source, build = Path(temp) / "source", Path(temp) / "build"
                source.mkdir()
                (source / "CMakeLists.txt").write_text(fixture)
                result = subprocess.run([cmake, "-S", str(source), "-B", str(build),
                                         "-DENABLE_RUST_KERNEL=ON", "-DARCH=x86_64",
                                         "-D" + option_name + "=" + ("ON" if enabled else "OFF")],
                                        capture_output=True, text=True, timeout=30)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                observed = dict(line.split("=", 1) for line in
                                (build / "selection.txt").read_text().splitlines())
                self.assertCountEqual(observed["defs"].split(";"),
                                      ["MCKERNEL_RUST_SYSCALL_POLICY_HELPERS"] +
                                      (["MCKERNEL_RUST_F03_SIGNAL_FORWARD"] if enabled else []))
                self.assertEqual(observed["cfg"].split(";"), ["BASE_CFG"] +
                                 (["--cfg", "f03_signal_forward_defined_candidate"] if enabled else []))
                self.assertCountEqual([Path(path).name for path in observed["srcs"].split(";")],
                                      ["base.rs"] +
                                      (["f03_signal_forward_defined_candidate.rs"] if enabled else []))
        for profile in (("OFF", "x86_64"), ("ON", "arm64")):
            with self.subTest(unsupported=profile), tempfile.TemporaryDirectory(prefix="m14-signal-profile-") as temp:
                source, build = Path(temp) / "source", Path(temp) / "build"
                source.mkdir()
                (source / "CMakeLists.txt").write_text(fixture)
                result = subprocess.run([cmake, "-S", str(source), "-B", str(build),
                                         "-DENABLE_RUST_KERNEL=" + profile[0], "-DARCH=" + profile[1],
                                         "-D" + option_name + "=ON"],
                                        capture_output=True, text=True, timeout=30)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("M14 signal forwarding requires", result.stdout + result.stderr)


class M14SyscallSelectionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cmake = os.environ.get("CMAKE") or shutil.which("cmake")
        if cls.cmake is None:
            raise unittest.SkipTest("CMake unavailable")
        cls.statements = selection_statements()

    def configure(self, *, enabled=None, profile=None, historical_setter=False):
        option, guard, blocks, early, base = self.statements
        if historical_setter:
            # Restore only the former replacing setter in the temporary fixture.
            # This control must lose the early/new F06 flags on the real CMake
            # property model; the repository itself is never modified.
            base, count = re.subn(r"set_property\(\s*SOURCE\s+",
                                 "set_source_files_properties(\n", base, count=1)
            self.assertEqual(count, 1, "Control requires the repaired append setter")
            base, count = re.subn(r"APPEND\s+PROPERTY\s+COMPILE_DEFINITIONS",
                                 "PROPERTIES COMPILE_DEFINITIONS", base, count=1)
            self.assertEqual(count, 1)
        fixture = "\n".join([
            "cmake_minimum_required(VERSION 3.16)",
            "project(m14_selection_fixture LANGUAGES NONE)",
            option, guard,
            'set(MCKERNEL_F06_C_SOURCE "${PROJECT_SOURCE_DIR}/arch/${ARCH}/kernel/syscall.c")',
            'set(RUST_KERNEL_CFG BASE_RUST_CFG)',
            'set(RUST_KERNEL_SRCS "${CMAKE_CURRENT_SOURCE_DIR}/base.rs")',
            'set_property(SOURCE "${CMAKE_CURRENT_SOURCE_DIR}/syscall.c" PROPERTY',
            '    COMPILE_DEFINITIONS UNRELATED_GENERIC_DEFINITION)',
            early,
            blocks[0], blocks[1], base,
            'get_source_file_property(arch_defs "${MCKERNEL_F06_C_SOURCE}" COMPILE_DEFINITIONS)',
            'get_source_file_property(generic_defs "${CMAKE_CURRENT_SOURCE_DIR}/syscall.c" COMPILE_DEFINITIONS)',
            'file(WRITE "${CMAKE_BINARY_DIR}/selection.txt"',
            f'    "option=${{{OPTION}}}\narch=${{arch_defs}}\ngeneric=${{generic_defs}}\n"',
            '    "cfg=${RUST_KERNEL_CFG}\nsrcs=${RUST_KERNEL_SRCS}\n")',
        ])
        definitions = {
            "ENABLE_RUST_KERNEL": "ON", "ARCH": "x86_64",
            "MCKERNEL_HOST_IRQ_ABI": "linux-6.12", "ENABLE_UBSAN": "OFF",
        }
        definitions.update(profile or {})
        if enabled is not None:
            definitions[OPTION] = "ON" if enabled else "OFF"
        with tempfile.TemporaryDirectory(prefix="m14-selection-") as directory:
            source = Path(directory) / "source"
            build = Path(directory) / "build"
            source.mkdir()
            (source / "CMakeLists.txt").write_text(fixture)
            result = subprocess.run(
                [self.cmake, "-S", str(source), "-B", str(build),
                 *[f"-D{name}={value}" for name, value in definitions.items()]],
                capture_output=True, text=True, timeout=30)
            output = build / "selection.txt"
            observed = dict(line.split("=", 1) for line in output.read_text().splitlines()) \
                if output.exists() else {}
            return result, observed

    def assert_preserved(self, result, observed, *, candidate):
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        arch = observed["arch"].split(";")
        expected_arch = BASE_ARCH | {EARLY_ARCH} | (NEW_ARCH if candidate else set())
        self.assertCountEqual(arch, expected_arch)
        generic = ["UNRELATED_GENERIC_DEFINITION"] + ([NEW_GENERIC] if candidate else [])
        self.assertCountEqual(observed["generic"].split(";"), generic)
        cfg = observed["cfg"].split(";")
        self.assertEqual(cfg[0], "BASE_RUST_CFG")
        self.assertCountEqual(cfg[1:], ["--cfg"] * 3 + list(NEW_CFG) if candidate else [])
        # Every Rust cfg is paired with the immediately preceding --cfg switch.
        for index in range(1, len(cfg), 2):
            self.assertEqual(cfg[index], "--cfg")
        modules = [Path(value).name for value in observed["srcs"].split(";")]
        self.assertCountEqual(modules, {"base.rs"} | (NEW_MODULES if candidate else set()))

    def test_default_off_preserves_earlier_arch_and_unrelated_generic_flags(self):
        result, observed = self.configure()
        self.assert_preserved(result, observed, candidate=False)
        self.assertEqual(observed["option"], "OFF")

    def test_enabled_pairs_c_guards_rust_cfg_and_source_dependencies(self):
        result, observed = self.configure(enabled=True)
        self.assert_preserved(result, observed, candidate=True)
        self.assertEqual(observed["option"], "ON")

    def test_unsupported_profiles_are_rejected_by_actual_guard(self):
        for profile in ({"ENABLE_RUST_KERNEL": "OFF"}, {"ARCH": "arm64"},
                        {"MCKERNEL_HOST_IRQ_ABI": "legacy"}, {"ENABLE_UBSAN": "ON"}):
            with self.subTest(profile=profile):
                result, observed = self.configure(enabled=True, profile=profile)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("M14 syscall adapter candidate requires", result.stdout + result.stderr)
                self.assertEqual(observed, {})

    def test_former_replacing_setter_reproduces_lost_early_flags(self):
        result, observed = self.configure(enabled=True, historical_setter=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertCountEqual(observed["arch"].split(";"), BASE_ARCH)
        self.assertNotIn(EARLY_ARCH, observed["arch"].split(";"))
        self.assertTrue(NEW_ARCH.isdisjoint(observed["arch"].split(";")))
        self.assertIn(NEW_GENERIC, observed["generic"].split(";"))
        self.assertTrue(NEW_CFG.issubset(observed["cfg"].split(";")))


if __name__ == "__main__":
    unittest.main()
