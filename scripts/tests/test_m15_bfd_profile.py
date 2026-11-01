"""Exercise actual BFD configuration guards without selecting a BFD library.

The fixture stops before the exact pinned-file checks. It cannot qualify a
header/library/compiler, generate a production layout, or build any runtime.
"""
from pathlib import Path
import os
import shutil
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]
MODULE = ROOT / "executer/user/cmake/BfdRustAccessors.cmake"


class M15BfdProfileTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cmake = os.environ.get("CMAKE") or shutil.which("cmake")
        if cls.cmake is None:
            raise unittest.SkipTest("CMake unavailable")

    def configure_guard(self, setup):
        source = MODULE.read_text()
        guard = source[:source.index('file(SHA256 "/usr/include/bfd.h"')]
        with tempfile.TemporaryDirectory(prefix="m15-bfd-profile-") as temporary:
            directory = Path(temporary)
            (directory / "CMakeLists.txt").write_text("\n".join([
                "cmake_minimum_required(VERSION 3.16)",
                "project(m15_bfd_profile_fixture NONE)",
                'set(LIBBFD "/usr/lib64/libbfd.so")',
                setup,
                guard,
                'file(WRITE "${CMAKE_BINARY_DIR}/profile-passed" "guard only\\n")',
            ]))
            result = subprocess.run(
                [self.cmake, "-S", str(directory), "-B", str(directory / "build")],
                capture_output=True, text=True, timeout=20)
            return result, (directory / "build/profile-passed").exists()

    def test_debug_bfd_send_is_rejected_in_directory_and_flag_profiles(self):
        profiles = [
            "add_compile_definitions(DEBUG_BFD_SEND)",
            "add_compile_definitions(DEBUG_BFD_SEND=0)",
            'add_compile_definitions("$<$<CONFIG:Debug>:DEBUG_BFD_SEND>")',
            'set(CMAKE_C_FLAGS "-DDEBUG_BFD_SEND=1")',
            'set(CMAKE_C_FLAGS "-D DEBUG_BFD_SEND")',
            'set(CMAKE_BUILD_TYPE Debug)\nset(CMAKE_C_FLAGS_DEBUG "-DDEBUG_BFD_SEND")',
            "add_compile_options(-DDEBUG_BFD_SEND)",
        ]
        for profile in profiles:
            with self.subTest(profile=profile):
                result, passed = self.configure_guard(profile)
                self.assertNotEqual(result.returncode, 0,
                                    "Unsupported BFD macro profile reached qualification")
                self.assertFalse(passed)
                reason = "generator expressions" if "$<" in profile else "DEBUG_BFD_SEND"
                self.assertIn(reason, result.stdout + result.stderr)

    def test_ordinary_and_unrelated_definitions_pass_the_profile_guard(self):
        for setup in ("", "add_compile_definitions(OTHER_DEBUG_BFD_SEND)",
                      "add_compile_definitions(DEBUG_BFD_SEND_SUFFIX)",
                      'set(CMAKE_C_FLAGS "-O2 -DDEBUG_BFD_SEND_SUFFIX=1")'):
            with self.subTest(setup=setup):
                result, passed = self.configure_guard(setup)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                self.assertTrue(passed)

    def test_directory_generator_expressions_are_explicitly_rejected(self):
        for setup in (
                'add_compile_definitions("$<$<COMPILE_LANGUAGE:C>:M15_EXPECT=1>")',
                'add_compile_options("$<$<COMPILE_LANGUAGE:C>:-DM15_EXPECT=1>")',
                'add_compile_definitions("$<$<CONFIG:Release>:M15_EXPECT=1>")'):
            with self.subTest(setup=setup):
                result, passed = self.configure_guard(setup)
                self.assertNotEqual(result.returncode, 0,
                                    "Unsupported directory generator expression reached qualification")
                self.assertFalse(passed)
                self.assertIn("generator expression", (result.stdout + result.stderr).lower())

    def test_multi_configuration_selection_is_explicitly_rejected(self):
        result, passed = self.configure_guard(
            'set(CMAKE_CONFIGURATION_TYPES "Debug;Release")')
        self.assertNotEqual(result.returncode, 0,
                            "One BFD layout cannot qualify arbitrary configuration-specific flags")
        self.assertFalse(passed)
        self.assertIn("multi-configuration", (result.stdout + result.stderr).lower())

    def test_existing_platform_and_library_selector_guards_remain(self):
        for setup in ("set(CMAKE_CROSSCOMPILING TRUE)",
                      'set(LIBBFD "/unqualified/libbfd.so")'):
            with self.subTest(setup=setup):
                result, passed = self.configure_guard(setup)
                self.assertNotEqual(result.returncode, 0)
                self.assertFalse(passed)

    def test_selected_c_compiler_is_a_configure_input(self):
        source = MODULE.read_text()
        start = source.index("set_property(DIRECTORY APPEND PROPERTY CMAKE_CONFIGURE_DEPENDS")
        end = source.index("\n# Do not reuse cached try_run", start)
        with tempfile.TemporaryDirectory(prefix="m15-bfd-inputs-") as temporary:
            directory = Path(temporary)
            (directory / "CMakeLists.txt").write_text("\n".join([
                "cmake_minimum_required(VERSION 3.16)",
                "project(m15_bfd_inputs_fixture NONE)",
                'set(_bfd_witness "/fixture/witness.c")',
                'set(LIBBFD "/fixture/libbfd.so")',
                'set(CMAKE_C_COMPILER "/fixture/selected-cc")',
                source[start:end],
                "get_directory_property(_inputs CMAKE_CONFIGURE_DEPENDS)",
                'file(WRITE "${CMAKE_BINARY_DIR}/inputs" "${_inputs}")',
            ]))
            result = subprocess.run(
                [self.cmake, "-S", str(directory), "-B", str(directory / "build")],
                capture_output=True, text=True, timeout=20)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            inputs = (directory / "build/inputs").read_text().split(";")
            for required in ("/fixture/witness.c", "/usr/include/bfd.h",
                             "/fixture/libbfd.so", "/fixture/selected-cc"):
                self.assertIn(required, inputs)

    def test_actual_probe_preserves_directory_and_configuration_flags(self):
        source = MODULE.read_text()
        guard = source[:source.index('file(SHA256 "/usr/include/bfd.h"')]
        start = source.index("# Do not reuse cached try_run")
        end = source.index("\nfile(MAKE_DIRECTORY", start)
        profiles = (
            ("directory definition", "add_compile_definitions(M15_EXPECT=1)", None),
            ("Release configuration flags",
             'set(CMAKE_BUILD_TYPE Release)\nset(CMAKE_C_FLAGS_RELEASE "-DM15_EXPECT=1")', None),
            ("existing probe configuration restored",
             'set(CMAKE_BUILD_TYPE Release)\nset(CMAKE_C_FLAGS_RELEASE "-DM15_EXPECT=1")\n'
             'set(CMAKE_TRY_COMPILE_CONFIGURATION MinSizeRel)', "MinSizeRel"),
            ("defined empty probe configuration restored",
             'set(CMAKE_BUILD_TYPE Release)\nset(CMAKE_C_FLAGS_RELEASE "-DM15_EXPECT=1")\n'
             'set(CMAKE_TRY_COMPILE_CONFIGURATION "")', ""),
        )
        for name, setup, prior_configuration in profiles:
            with self.subTest(profile=name), tempfile.TemporaryDirectory(
                    prefix="m15-bfd-probe-flags-") as temporary:
                directory = Path(temporary)
                # This compile observer only checks profile propagation; it is
                # not the BFD layout witness and cannot qualify a production ABI.
                (directory / "flag_observer.c").write_text(
                    "#ifndef M15_EXPECT\n"
                    "#error directory or active configuration flag was lost by the probe\n"
                    "#endif\nint main(void) { return 0; }\n")
                if prior_configuration is not None:
                    restored = '\n'.join([
                        'if(NOT DEFINED CMAKE_TRY_COMPILE_CONFIGURATION OR NOT',
                        '   "${CMAKE_TRY_COMPILE_CONFIGURATION}" STREQUAL "' + prior_configuration + '")',
                        '  message(FATAL_ERROR "Prior probe configuration was not restored")',
                        'endif()',
                    ])
                else:
                    restored = '\n'.join([
                        'if(DEFINED CMAKE_TRY_COMPILE_CONFIGURATION)',
                        '  message(FATAL_ERROR "Originally absent probe configuration was not unset")',
                        'endif()',
                    ])
                (directory / "CMakeLists.txt").write_text("\n".join([
                    "cmake_minimum_required(VERSION 3.16)",
                    "project(m15_bfd_probe_flags_fixture C)",
                    'set(LIBBFD "/usr/lib64/libbfd.so")',
                    setup,
                    guard,
                    'set(LIBBFD "")',
                    'set(_bfd_witness "${CMAKE_CURRENT_SOURCE_DIR}/flag_observer.c")',
                    source[start:end],
                    restored,
                ]))
                result = subprocess.run(
                    [self.cmake, "-S", str(directory), "-B", str(directory / "build")],
                    capture_output=True, text=True, timeout=30)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
