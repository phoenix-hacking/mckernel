"""Configure actual M15 user-tool selection without compiling any Rust crate.

Only the user CMake selection section and BFD object's command are configured.
The BFD layout probe is an explicit fixture seam: its pinned production header,
library/compiler checks are neither executed nor relaxed by this test. No
generated objects, linked tools, production BFD ABI or native behavior qualify.
"""
from pathlib import Path
import os
import re
import shlex
import shutil
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]
USER = ROOT / "executer/user"


def selection_source(*, default_tools=False):
    source = (USER / "CMakeLists.txt").read_text()
    start = source.index("option(ENABLE_RUST_USER_TOOLS ")
    end = source.index("set(SCHED_YIELD_SRCS ", start)
    selected = source[start:end]
    # An option moved before its first child use also includes unrelated SDK
    # library declarations. Supply only libmcexec's inert interface below;
    # neither SDK subdirectories nor architecture assembly belong to this test.
    selected = re.sub(r"(?m)^add_subdirectory\(lib\)\s*$", "", selected)
    selected = re.sub(r"(?m)^add_library\(libmcexec STATIC arch/\$\{ARCH\}/archdep\.S\)\s*$", "", selected)
    selected = re.sub(r"(?m)^(?:SET_TARGET_PROPERTIES|set_property)\([^\n]*libmcexec[^\n]*\)\s*$", "", selected)
    if default_tools:
        # Include the newly affected ordinary default targets verbatim. Optional
        # QLMPI/UTI profile sections are neither extracted nor activated.
        sched_start = source.index("set(SCHED_YIELD_SRCS ")
        sched_end = source.index("if (ENABLE_QLMPI)", sched_start)
        ldump_start = source.index("set(LDUMP2MCDUMP_SRCS ")
        ldump_end = source.index("configure_file(vmcore2mckdump.in ", ldump_start)
        mcps_start = source.index("option(MCKERNEL_ALLOW_RUNTIME_SCRIPT_FALLBACK ")
        mcps_end = source.index("# Preserve full install paths;", mcps_start)
        selected += source[sched_start:sched_end] + source[ldump_start:ldump_end] + source[mcps_start:mcps_end]
    return selected


def bfd_command_source():
    source = (USER / "cmake/BfdRustAccessors.cmake").read_text()
    # Keep the actual production custom command and target declarations. The
    # selected-layout qualification before this point belongs to separate real
    # BFD checks; this fixture cannot and does not establish those pins.
    return source[source.index('set(BFD_RUST_OBJ "'):]


def object_prerequisites(recipe):
    return {match.group(1) for match in re.finditer(
        r"(?m)^rust/[^:\n]+\.o: (.+)$", recipe)}


class M15UserToolSelectionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cmake = os.environ.get("CMAKE") or shutil.which("cmake")
        if cls.cmake is None:
            raise unittest.SkipTest("CMake unavailable")
        if shutil.which("make") is None or shutil.which("cc") is None:
            raise unittest.SkipTest("Make/C compiler unavailable for configure fixture")

    def configure(self, *, compute="unrelated", user="valid", enabled=True, default_tools=False):
        with tempfile.TemporaryDirectory(prefix="m15-user-selection-") as temporary:
            directory = Path(temporary)
            source, build = directory / "source", directory / "build"
            (source / "cmake").mkdir(parents=True)
            (source / "rust").mkdir()
            (source / "arch/x86_64").mkdir(parents=True)
            for path in ("mcexec.c", "mcinspect.c", "eclair.c", "arch/x86_64/arch-eclair.c",
                         "libsched_yield.c", "ldump2mcdump.c"):
                (source / path).write_text("/* Configure-only fixture; never compiled. */\n")
            qualified = directory / "qualified-user-rustc"
            unrelated = directory / "unrelated-compute-rustc"
            for compiler in (qualified, unrelated):
                compiler.write_text("#!/bin/sh\nexit 91\n")
                compiler.chmod(0o755)
            user_path = {"valid": str(qualified), "relative": "relative-rustc",
                         "absent": str(directory / "absent-rustc"), "empty": ""}[user]
            compute_path = str(unrelated) if compute == "unrelated" else "RUSTC-NOTFOUND"
            # No build is invoked. Register the actual accessor command behind
            # an explicit nonproduction layout seam, so command dependencies
            # remain those of the real module rather than a handwritten double.
            (source / "cmake/BfdRustAccessors.cmake").write_text(
                "# TEST ONLY: production layout/pin checks intentionally not invoked.\n"
                'file(MAKE_DIRECTORY "${CMAKE_CURRENT_BINARY_DIR}/rust")\n'
                'set(_bfd_layout_rs "${CMAKE_CURRENT_BINARY_DIR}/rust/fixture-layout.rs")\n'
                'file(WRITE "${_bfd_layout_rs}" "// Not a qualified BFD layout.\\n")\n'
                + bfd_command_source())
            (source / "rust/mcexec_buildid.rs.in").write_text("// configure-only\n")
            observations = []
            targets = ("mcexec", "mcinspect", "eclair")
            if default_tools:
                targets += ("sched_yield", "ldump2mcdump", "mcps")
            for target in targets:
                observations.extend([
                    f"get_target_property(_sources {target} SOURCES)",
                    f"get_target_property(_deps {target} MANUALLY_ADDED_DEPENDENCIES)",
                    f"get_target_property(_link_inputs {target} LINK_DEPENDS)",
                    f'file(APPEND "${{CMAKE_BINARY_DIR}}/selection.txt" "{target}.sources=${{_sources}}\\n{target}.deps=${{_deps}}\\n")',
                    f'file(APPEND "${{CMAKE_BINARY_DIR}}/selection.txt" "{target}.link_inputs=${{_link_inputs}}\\n")',
                ])
            fixture = "\n".join([
                "cmake_minimum_required(VERSION 3.16)",
                "project(m15_user_selection_fixture LANGUAGES C)",
                "set(ARCH x86_64)",
                "set(CMAKE_FIND_USE_SYSTEM_ENVIRONMENT_PATH FALSE)",
                "set(CMAKE_FIND_USE_CMAKE_SYSTEM_PATH FALSE)",
                f'set(RUSTC "{compute_path}" CACHE FILEPATH "Compute compiler")',
                f'set(MCEXEC_USER_RUSTC "{qualified}" CACHE FILEPATH "Executor compiler")',
                f'set(MCKERNEL_RUNTIME_TOOL_RUSTC "{user_path}" CACHE FILEPATH "User tool compiler")',
                f'set(ENABLE_RUST_USER_TOOLS {"ON" if enabled else "OFF"} CACHE BOOL "")',
                f'set(MCEXEC_ALLOW_C_REFERENCE {"OFF" if enabled else "ON"} CACHE BOOL "")',
                'set(KERNEL_DIR "${CMAKE_CURRENT_SOURCE_DIR}")',
                'set(prefix "/fixture/install")',
                'set(MCKERNELDIR "/fixture/install/kernel")',
                "set(LIBDWARF fixture_dwarf)",
                "set(LIBBFD fixture_bfd)",
                "add_library(libmcexec INTERFACE)",
                selection_source(default_tools=default_tools),
                'file(WRITE "${CMAKE_BINARY_DIR}/selection.txt" "compute=${RUSTC}\\n")',
                *observations,
            ])
            (source / "CMakeLists.txt").write_text(fixture)
            result = subprocess.run(
                [self.cmake, "-G", "Unix Makefiles", "-S", str(source), "-B", str(build)],
                capture_output=True, text=True, timeout=30)
            output = build / "selection.txt"
            observed = dict(line.split("=", 1) for line in output.read_text().splitlines()) \
                if output.exists() else {}
            recipes = {}
            custom_targets = ("mcinspect_rust_helpers", "eclair_rust_helpers", "eclair_arch_rust", "bfd_rust_accessors")
            if default_tools:
                custom_targets += ("sched_yield_rust_main", "ldump2mcdump_rust_helpers", "mcps_rust_main")
            for target in custom_targets:
                path = build / f"CMakeFiles/{target}.dir/build.make"
                recipes[target] = path.read_text() if path.exists() else ""
            for target in ("mcinspect", "eclair"):
                path = build / f"CMakeFiles/{target}.dir/build.make"
                if path.exists():
                    observed[f"{target}.link_prerequisites"] = ";".join(re.findall(
                        rf"(?m)^{target}: (.+)$", path.read_text()))
            return result, observed, recipes, str(qualified), compute_path, str(build)

    def assert_rust_selection(self, observed, recipes, qualified, compute_path):
        self.assertEqual(observed["compute"], compute_path, "User selection must preserve compute compiler")
        for tool, objects, dependencies in (
            ("mcinspect", {"mcinspect_helpers.o", "bfd_accessors.o"},
             {"mcinspect_rust_helpers", "bfd_rust_accessors"}),
            ("eclair", {"eclair_helpers.o", "arch_eclair_x86_64.o", "bfd_accessors.o"},
             {"eclair_rust_helpers", "eclair_arch_rust", "bfd_rust_accessors"}),
        ):
            selected = {Path(value).name for value in observed[f"{tool}.sources"].split(";")}
            self.assertEqual(selected, objects)
            self.assertFalse(any(value.endswith(".c") for value in selected),
                             "Selected Rust tool must not retain C bodies/shims")
            self.assertEqual(set(observed[f"{tool}.deps"].split(";")), dependencies)
        for target, recipe in recipes.items():
            self.assertTrue(recipe, f"Missing actual custom-command recipe for {target}")
            command = next((line for line in recipe.splitlines() if "--crate-name " in line), "")
            self.assertIn(qualified, command, f"{target} must use the independent user compiler")
            self.assertNotIn(compute_path, command)
            self.assertIn(qualified, object_prerequisites(recipe),
                          f"{target} must rebuild after compiler-file replacement")

    def test_qualified_compiler_selects_rust_without_consuming_compute_binding(self):
        for compute in ("unrelated", "missing"):
            with self.subTest(compute=compute):
                result, observed, recipes, qualified, compute_path, _ = self.configure(compute=compute)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                self.assert_rust_selection(observed, recipes, qualified, compute_path)

    def test_rust_tools_reject_unbound_relative_and_nonexistent_user_compilers(self):
        for user in ("empty", "relative", "absent"):
            with self.subTest(user=user):
                result, observed, _, _, _, _ = self.configure(user=user)
                self.assertNotEqual(result.returncode, 0,
                                    "Rust tools must reject an unqualified user compiler at configure time")
                self.assertEqual(observed, {})
                self.assertIn("compiler", (result.stdout + result.stderr).lower())

    def test_actual_invoked_compilers_are_object_file_prerequisites(self):
        result, _, recipes, _, _, _ = self.configure()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        for target, recipe in recipes.items():
            with self.subTest(target=target):
                command = next(line for line in recipe.splitlines() if "--crate-name " in line)
                arguments = shlex.split(command)
                invoked = arguments[arguments.index("--crate-name") - 1]
                self.assertIn(invoked, object_prerequisites(recipe),
                              "Compiler-file replacement must invalidate its object")

    def test_bfd_consumers_track_the_linker_scripts_absolute_archives(self):
        result, observed, _, _, _, _ = self.configure()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        for target in ("mcinspect", "eclair"):
            with self.subTest(target=target):
                inputs = observed[f"{target}.link_inputs"].split(";")
                self.assertIn("/usr/lib64/libbfd.a", inputs)
                self.assertIn("/usr/lib64/libsframe.a", inputs)
                prerequisites = observed[f"{target}.link_prerequisites"].split(";")
                self.assertIn("/usr/lib64/libbfd.a", prerequisites)
                self.assertIn("/usr/lib64/libsframe.a", prerequisites)

    def test_other_default_tools_use_same_user_compiler_and_file_dependencies(self):
        for compute in ("unrelated", "missing"):
            with self.subTest(compute=compute):
                result, observed, recipes, qualified, compute_path, _ = self.configure(
                    compute=compute, default_tools=True)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                self.assert_rust_selection(observed, recipes, qualified, compute_path)
                for target, object_name, dependencies in (
                    ("sched_yield", "libsched_yield.o", {"sched_yield_rust_main"}),
                    ("ldump2mcdump", "ldump2mcdump_helpers.o", {"ldump2mcdump_rust_helpers"}),
                    ("mcps", "mcps.o", {"mcps_rust_main", "mcinspect"}),
                ):
                    self.assertEqual({Path(value).name for value in observed[f"{target}.sources"].split(";")},
                                     {object_name})
                    self.assertEqual(set(observed[f"{target}.deps"].split(";")), dependencies)
                self.assertIn("MCPS_PREFIX=/fixture/install", recipes["mcps_rust_main"])
                self.assertIn("MCPS_MCKERNELDIR=/fixture/install/kernel", recipes["mcps_rust_main"])

    def test_explicit_c_comparison_does_not_require_user_compiler(self):
        result, observed, recipes, _, compute_path, _ = self.configure(enabled=False, user="empty")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(observed["compute"], compute_path)
        self.assertEqual(observed["mcexec.sources"], "mcexec.c")
        self.assertEqual(observed["mcinspect.sources"], "mcinspect.c")
        self.assertEqual(set(observed["eclair.sources"].split(";")),
                         {"eclair.c", "arch/x86_64/arch-eclair.c"})
        self.assertTrue(all(not recipe for recipe in recipes.values()))


if __name__ == "__main__":
    unittest.main()
