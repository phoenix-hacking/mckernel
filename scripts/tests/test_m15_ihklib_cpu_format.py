"""Exercise the recovered libihk CPU formatter through its actual public APIs.

This builds only the shared Rust parser/formatter module and the two actual C
formatting functions. libc allocation/string calls are real; the Rust loglevel
observation double disables diagnostics. No IHK library producer, SDK, device
or module is used. Set RUSTC to select the qualified user Rust compiler.
"""

from pathlib import Path
import ctypes
import os
import shutil
import subprocess
import tempfile
import unittest


REPO = Path(__file__).resolve().parents[2]
SOURCE = REPO / "ihk/linux/user/rust/whole70/ihklib_cli_parsers_ikc_shared.rs"
C_SOURCE = REPO / "ihk/linux/user/ihklib.c"


HARNESS = r'''
#[path = "__SOURCE__"]
mod actual;

// Observation double: a valid formatter/parser call does not log. Keeping the
// existing module's logger disabled also excludes any /dev/kmsg diagnostic path.
#[no_mangle]
pub static mut loglevel: core::ffi::c_int = 0;

#[repr(C)]
struct CpuReq {
    cpus: *mut core::ffi::c_int,
    num_cpus: core::ffi::c_int,
}

unsafe extern "C" {
    fn free(pointer: *mut core::ffi::c_void);
}

fn format(cpus: &[i32]) -> String {
    let mut owned = cpus.to_vec();
    let mut req = CpuReq {
        cpus: owned.as_mut_ptr(),
        num_cpus: owned.len() as i32,
    };
    unsafe {
        let text = actual::cpu_req2str((&mut req as *mut CpuReq).cast());
        assert!(!text.is_null(), "formatter allocation failed");
        let result = std::ffi::CStr::from_ptr(text).to_str().unwrap().to_owned();
        free(text.cast());
        result
    }
}

fn parse(text: &str) -> Vec<i32> {
    let text = std::ffi::CString::new(text).unwrap();
    unsafe {
        let count = actual::cpu_str2count(text.as_ptr() as *mut _);
        assert!(count >= 0, "formatter emitted invalid CPU syntax: {text:?}");
        let mut values = vec![-1; count as usize];
        let mut req = CpuReq { cpus: values.as_mut_ptr(), num_cpus: 0 };
        assert_eq!(actual::cpu_str2req(
            text.as_ptr() as *mut _, count, (&mut req as *mut CpuReq).cast(),
        ), count);
        assert_eq!(req.num_cpus, count);
        values
    }
}

#[test]
fn zero_before_a_gap_is_retained() {
    assert_eq!(format(&[0, 2]), "0,2");
    assert_eq!(format(&[0, 2, 4]), "0,2,4");
}

#[test]
fn zero_before_a_later_range_is_retained() {
    assert_eq!(format(&[0, 2, 3]), "0,2-3");
}

#[test]
fn zero_in_a_contiguous_range_keeps_existing_compression() {
    assert_eq!(format(&[0, 1, 3]), "0-1,3");
    assert_eq!(format(&[0, 1, 2]), "0-2");
}

#[test]
fn singleton_and_empty_outputs_keep_existing_contract() {
    assert_eq!(format(&[0]), "0");
    assert_eq!(format(&[9]), "9");
    assert_eq!(format(&[]), "");
}

#[test]
fn positive_cpu_sets_keep_existing_formatting() {
    assert_eq!(format(&[2, 4, 5, 7]), "2,4-5,7");
}

#[test]
fn every_small_sorted_cpu_set_round_trips_without_lost_members() {
    // Membership is independent of the formatter's range compression choices.
    // Empty output intentionally has no parser round-trip contract.
    for bits in 1u32..(1 << 8) {
        let cpus: Vec<i32> = (0..8).filter(|cpu| bits & (1 << cpu) != 0).collect();
        let text = format(&cpus);
        assert_eq!(parse(&text), cpus, "lost CPU membership for {bits:#x}: {text}");
    }
}

#[test]
fn long_sparse_set_preserves_zero_across_formatter_growth() {
    let cpus: Vec<i32> = (0..128).step_by(2).collect();
    let expected = cpus.iter().map(i32::to_string).collect::<Vec<_>>().join(",");
    assert!(expected.len() > 64);
    let text = format(&cpus);
    assert_eq!(text, expected);
    assert_eq!(parse(&text), cpus);
}
'''


class IhklibCpuFormatTests(unittest.TestCase):
    def test_actual_recovered_parser_and_formatter(self):
        self.assertTrue(SOURCE.is_file(), "restore the exact IHK source first")
        rustc = shutil.which(os.environ.get("RUSTC") or "rustc")
        if not rustc:
            self.skipTest("Rust compiler unavailable; bind RUSTC to the qualified compiler")
        with tempfile.TemporaryDirectory(prefix="m15-ihklib-cpu-format-") as directory:
            directory = Path(directory)
            harness = directory / "cpu_format.rs"
            harness.write_text(HARNESS.replace("__SOURCE__", str(SOURCE)), encoding="utf-8")
            binary = directory / "cpu_format_tests"
            compiled = subprocess.run(
                [rustc, "--edition=2021", "--test", str(harness), "-o", str(binary)],
                capture_output=True, text=True, timeout=60,
            )
            self.assertEqual(compiled.returncode, 0, compiled.stdout + compiled.stderr)
            executed = subprocess.run(
                [str(binary), "--test-threads=1"],
                capture_output=True, text=True, timeout=30,
            )
            self.assertEqual(executed.returncode, 0, executed.stdout + executed.stderr)

    def test_actual_retained_c_formatter(self):
        self.assertTrue(C_SOURCE.is_file(), "restore the exact IHK source first")
        compiler = shutil.which(os.environ.get("CC") or "cc")
        if not compiler:
            self.skipTest("C compiler unavailable; bind CC to a C compiler")
        source = C_SOURCE.read_text(encoding="utf-8")

        def function(signature):
            start = source.index(signature)
            body = source.index("{", start)
            depth = 1
            end = body + 1
            while depth:
                if source[end] == "{":
                    depth += 1
                elif source[end] == "}":
                    depth -= 1
                end += 1
            return source[start:end]

        # These are the actual retained bodies, including their real variadic
        # formatter and realloc path. No IHK headers or device APIs are linked.
        unit = "\n".join([
            "#include <stdio.h>", "#include <stdlib.h>",
            "#include <stdarg.h>", "#include <string.h>",
            function("static int snprintf_realloc("),
            function("static char *cpu_array2str("),
            "char *observe_cpu_format(int n, int *cpus) { return cpu_array2str(n, cpus); }",
        ])
        with tempfile.TemporaryDirectory(prefix="m15-ihklib-cpu-c-format-") as directory:
            directory = Path(directory)
            harness = directory / "cpu_format.c"
            harness.write_text(unit, encoding="utf-8")
            library = directory / "cpu_format.so"
            compiled = subprocess.run(
                [compiler, "-std=c11", "-shared", "-fPIC", str(harness), "-o", str(library)],
                capture_output=True, text=True, timeout=60,
            )
            self.assertEqual(compiled.returncode, 0, compiled.stdout + compiled.stderr)
            actual = ctypes.CDLL(str(library))
            actual.observe_cpu_format.argtypes = [ctypes.c_int, ctypes.POINTER(ctypes.c_int)]
            actual.observe_cpu_format.restype = ctypes.c_void_p
            libc = ctypes.CDLL(None)
            libc.free.argtypes = [ctypes.c_void_p]
            libc.free.restype = None
            cases = [
                ([], ""), ([0], "0"), ([9], "9"),
                ([0, 2], "0,2"), ([0, 2, 4], "0,2,4"),
                ([0, 2, 3], "0,2-3"), ([0, 1, 3], "0-1,3"),
                ([0, 1, 2], "0-2"), ([2, 4, 5, 7], "2,4-5,7"),
                (list(range(0, 128, 2)), ",".join(map(str, range(0, 128, 2)))),
            ]
            for cpus, expected in cases:
                with self.subTest(cpus=cpus):
                    values = (ctypes.c_int * len(cpus))(*cpus)
                    text = actual.observe_cpu_format(len(cpus), values)
                    self.assertTrue(text, "formatter allocation failed")
                    try:
                        self.assertEqual(ctypes.string_at(text).decode("ascii"), expected)
                    finally:
                        libc.free(text)


if __name__ == "__main__":
    unittest.main()
