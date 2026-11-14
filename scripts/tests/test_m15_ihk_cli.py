"""Focused recovered CLI regressions; no device, SDK link, or native actions.

Formatting uses actual extracted Rust functions with host libc. Build-input
tests use actual recipes and a compiler observation double, never a real tool
link or whole-library producer invocation.
"""
from pathlib import Path
import os
import shutil
import subprocess
import tempfile
import time
import unittest


ROOT = Path(__file__).resolve().parents[2]
USER = ROOT / "ihk/linux/user"


class M15IhkCliTests(unittest.TestCase):
    def test_ihkconfig_cpu_query_preserves_standalone_zero(self):
        rustc = os.environ.get("RUSTC") or shutil.which("rustc")
        if not rustc:
            self.skipTest("Rust compiler required")
        source = (USER / "rust/ihkconfig.rs").read_text()
        functions = source[source.index("unsafe fn append("):source.index("unsafe fn query(fd:")]
        harness = r'''
use std::ffi::{c_char, c_int, c_ulong};
use std::ptr::null_mut;
macro_rules! c { ($s:literal) => { concat!($s, "\0").as_ptr().cast::<c_char>() }; }
struct CpuReq { cpus: *mut c_int, num_cpus: c_int }
struct MemReq { sizes: *mut usize, numa_ids: *mut c_int, num_chunks: c_int }
unsafe extern "C" {
    fn snprintf(dst: *mut c_char, size: usize, fmt: *const c_char, ...) -> c_int;
    fn malloc(size: usize) -> *mut std::ffi::c_void;
    fn realloc(p: *mut std::ffi::c_void, size: usize) -> *mut std::ffi::c_void;
    fn free(p: *mut std::ffi::c_void);
    fn memset(p: *mut std::ffi::c_void, value: c_int, size: usize) -> *mut std::ffi::c_void;
}
'''
        checks = r'''
fn main() { unsafe {
    let cases: &[(&[i32], &str)] = &[
        (&[0, 2], "0,2"), (&[0, 2, 4], "0,2,4"),
        (&[0, 1, 3], "0-1,3"), (&[0], "0"),
        (&[0, 1, 2], "0-2"), (&[], ""),
    ];
    let mem = MemReq { sizes: null_mut(), numa_ids: null_mut(), num_chunks: 0 };
    for (values, expected) in cases {
        let cpu = CpuReq { cpus: values.as_ptr().cast_mut(), num_cpus: values.len() as i32 };
        let result = query_string(&cpu, &mem, true);
        assert!(!result.is_null());
        assert_eq!(std::ffi::CStr::from_ptr(result).to_str().unwrap(), *expected,
                   "CPU query changed membership for {:?}", values);
        free(result.cast());
    }
    println!("6 actual CLI formatting cases passed");
} }
'''
        with tempfile.TemporaryDirectory(prefix="m15-ihk-cli-format-") as directory:
            work = Path(directory)
            (work / "query.rs").write_text(harness + functions + checks)
            subprocess.run([rustc, "--edition=2021", "-Dwarnings", str(work / "query.rs"),
                            "-o", str(work / "query")], check=True, capture_output=True, text=True)
            result = subprocess.run([str(work / "query")], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertEqual(result.stdout, "6 actual CLI formatting cases passed\n")

    def cmake(self):
        cmake = os.environ.get("CMAKE") or shutil.which("cmake")
        if not cmake or not shutil.which("make") or not shutil.which("cc"):
            self.skipTest("CMake, Make, and C compiler required")
        return cmake

    def prepare_cli_fixture(self, work, binding=None):
        source = (USER / "CMakeLists.txt").read_text()
        start = source.index("# Source-only successor:")
        end = source.index("# PRIVATE proposal:", start)
        for name in ("ihkconfig", "ihkosctl"):
            (work / "rust").mkdir(exist_ok=True)
            for suffix in (name + ".rs", "build_" + name + ".py"):
                shutil.copyfile(USER / "rust" / suffix, work / "rust" / suffix)
        headers = work / "linux/include/ihk"
        headers.mkdir(parents=True)
        for header in ("ihklib.h", "ihklib_private.h", "ihk_host_user.h"):
            (headers / header).write_text("/* nonproduction dependency observer */\n")
        compiler = work / "selected-rustc"
        self.write_compiler(compiler, "first")
        selected = str(compiler) if binding is None else binding
        (work / "CMakeLists.txt").write_text("\n".join([
            "cmake_minimum_required(VERSION 3.16)", "project(m15_ihk_cli_fixture C)",
            "set(ARCH x86_64)", "set(ENABLE_RUST_USER_TOOLS ON)",
            'set(RUSTC "/unrelated/compute-rustc")',
            'set(IHK_USER_RUSTC "' + selected + '")',
            'file(WRITE "${PROJECT_BINARY_DIR}/config.h" "#define BUILDID \\\"fixture\\\"\\n")',
            "add_library(ihklib INTERFACE)", source[start:end],
        ]))
        return compiler

    def write_compiler(self, path, marker):
        path.write_text("#!/usr/bin/env python3\nimport pathlib,sys\n"
                        "for arg in sys.argv[1:]:\n"
                        "    if arg.startswith('--emit=obj='):\n"
                        "        pathlib.Path(arg[len('--emit=obj='):]).write_text('" + marker + "')\n")
        path.chmod(0o755)

    def test_cli_objects_rebuild_when_bound_compiler_is_replaced(self):
        cmake = self.cmake()
        with tempfile.TemporaryDirectory(prefix="m15-ihk-cli-inputs-") as directory:
            work = Path(directory)
            compiler = self.prepare_cli_fixture(work)
            build = work / "build"
            configured = subprocess.run([cmake, "-S", str(work), "-B", str(build)],
                                        capture_output=True, text=True)
            self.assertEqual(configured.returncode, 0, configured.stdout + configured.stderr)
            command = [cmake, "--build", str(build), "--target", "ihkconfig_rust_main", "ihkosctl_rust_main"]
            subprocess.run(command, check=True, capture_output=True, text=True)
            objects = [build / "rust" / (name + ".o") for name in ("ihkconfig", "ihkosctl")]
            self.assertEqual([obj.read_text() for obj in objects], ["first", "first"])
            # Make uses whole-second timestamps on some supported hosts.
            time.sleep(1.1)
            self.write_compiler(compiler, "replaced")
            subprocess.run(command, check=True, capture_output=True, text=True)
            self.assertEqual([obj.read_text() for obj in objects], ["replaced", "replaced"],
                             "Replacing the bound compiler reused stale CLI objects")

    def test_cli_compiler_binding_rejects_missing_file_and_directory(self):
        cmake = self.cmake()
        for selection in ("missing", "directory"):
            with self.subTest(selection=selection), tempfile.TemporaryDirectory(
                    prefix="m15-ihk-cli-binding-") as directory:
                work = Path(directory)
                selected = work / selection
                if selection == "directory":
                    selected.mkdir()
                self.prepare_cli_fixture(work, str(selected))
                result = subprocess.run([cmake, "-S", str(work), "-B", str(work / "build")],
                                        capture_output=True, text=True)
                self.assertNotEqual(result.returncode, 0,
                                    "Invalid compiler binding reached generated CLI recipes")
                self.assertIn("IHK_USER_RUSTC", result.stdout + result.stderr)

    def test_whole_library_rule_tracks_selected_compilers(self):
        cmake = self.cmake()
        with tempfile.TemporaryDirectory(prefix="m15-ihk-producer-inputs-") as directory:
            work = Path(directory)
            compiler = self.prepare_cli_fixture(work)
            producer = (USER / "rust/whole70/Whole70ProducerQualified.cmake").read_text()
            (work / "CMakeLists.txt").write_text("\n".join([
                "cmake_minimum_required(VERSION 3.16)", "project(m15_ihk_producer_inputs C)",
                'set(IHK_USER_RUSTC "' + str(compiler) + '")', producer,
            ]))
            result = subprocess.run([cmake, "-S", str(work), "-B", str(work / "build")],
                                    capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            recipe = (work / "build/CMakeFiles/ihklib_whole70_archive.dir/build.make").read_text()
            dependencies = [line.split(": ", 1)[1] for line in recipe.splitlines()
                            if line.startswith("rust/whole70/libihklib_whole70.a: ")]
            self.assertIn(str(compiler), dependencies)
            self.assertIn(str(Path(shutil.which("cc"))), dependencies)


if __name__ == "__main__":
    unittest.main()
