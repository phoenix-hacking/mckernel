"""Actual ihkconfig index conversion before its first command/API dispatch.

The exact main prefix, usage and optional checked conversion are extracted.
An index recording line replaces the following dispatch; genuine HOST libc
atoi/strtol/errno are used. No device or public library provider is called.
"""
from pathlib import Path
import os
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
SOURCE = Path(os.environ.get("M15_IHKCONFIG_SOURCE", ROOT / "ihk/linux/user/rust/ihkconfig.rs"))


class M15IhkconfigDeviceIndexTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        compiler = os.environ.get("RUSTC") or shutil.which("rustc")
        if not compiler:
            raise unittest.SkipTest("Rust compiler required")
        source = SOURCE.read_text()
        usage = source[source.index("unsafe fn usage() {"):source.index("// Exact defined parsing semantics")]
        marker = '#[no_mangle]\npub unsafe extern "C" fn main('
        start = source.index(marker)
        end = source.index('    if is(arg(2), c!("get"))', start)
        prefix = source[start:end].replace('fn main(', 'fn observed_main(', 1)
        helper = ""
        if "unsafe fn device_index(" in source:
            helper = source[source.index("unsafe fn device_index("):start]
        cls.temporary = tempfile.TemporaryDirectory(prefix="m15-cli-index-", dir=os.environ.get("TMPDIR"))
        cls.addClassCleanup(cls.temporary.cleanup)
        work = Path(cls.temporary.name)
        # Both alternatives are required for source qualification. Bind and use
        # their addresses to keep -Dwarnings independent of which source is read.
        harness = r'''
use std::ffi::{c_char,c_int,c_long,c_void,CString};
use std::ptr::null_mut;
macro_rules! c { ($s:literal) => { concat!($s, "\0").as_ptr().cast::<c_char>() }; }
#[no_mangle]pub static mut __argc:c_int=0;
#[no_mangle]pub static mut __argv:*mut *mut c_char=null_mut();
unsafe fn arg(i:usize)->*mut c_char{*__argv.add(i)}
extern "C" {
 static mut stderr:*mut c_void;
 fn fprintf(stream:*mut c_void,fmt:*const c_char,...)->c_int;
 fn printf(fmt:*const c_char,...)->c_int;
 fn strrchr(s:*const c_char,ch:c_int)->*mut c_char;
 fn strtol(s:*const c_char,end:*mut *mut c_char,base:c_int)->c_long;
 fn atoi(s:*const c_char)->c_int;
 fn __errno_location()->*mut c_int;
}
'''
        main = r'''
fn main() {
 let _bindings=(atoi as unsafe extern "C" fn(*const c_char)->c_int,
                strtol as unsafe extern "C" fn(*const c_char,*mut *mut c_char,c_int)->c_long,
                __errno_location as unsafe extern "C" fn()->*mut c_int);
 let args:Vec<CString>=std::env::args().map(|value|CString::new(value).unwrap()).collect();
 let mut pointers:Vec<*mut c_char>=args.iter().map(|value|value.as_ptr().cast_mut()).collect();
 pointers.push(null_mut());
 unsafe {std::process::exit(observed_main(args.len() as c_int,pointers.as_mut_ptr()));}
}
'''
        unit = work / "index.rs"
        unit.write_text(harness + usage + helper + prefix + '    printf(c!("INDEX\\t%d\\n"), index); 0\n}\n' + main)
        cls.binary = work / "index"
        compiled = subprocess.run([compiler, "--edition=2021", "-Dwarnings", str(unit), "-o", str(cls.binary)],
                                  capture_output=True, text=True)
        if compiled.returncode:
            raise AssertionError(compiled.stdout + compiled.stderr)

    def test_valid_device_index_retains_atoi_numeric_grammar(self):
        for text, value in [("0", 0), ("1", 1), ("63", 63), ("2147483647", 2147483647),
                            ("000", 0), (" +7", 7), ("\t0", 0), ("-0", 0)]:
            with self.subTest(text=text):
                result = subprocess.run([str(self.binary), text, "get"], capture_output=True, text=True)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(result.stdout, "INDEX\t%d\n" % value)
                self.assertEqual(result.stderr, "")

    def test_malformed_or_unrepresentable_index_stops_before_dispatch(self):
        # Out-of-c_int-range inputs exercise defined checked-strtol behavior
        # only. Exclude them from the atoi baseline, whose C behavior is undefined.
        invalid = ["", "foo", "0oops", "1.0", "0x0", "2147483648", "4294967296",
                   "18446744073709551616", "-1", "-2147483649", " ", "+", "-", "3 "]
        if os.environ.get("M15_IHKCONFIG_BASELINE_ONLY") == "1":
            self.assertNotIn("unsafe fn device_index(", SOURCE.read_text())
            undefined_atoi = {"2147483648", "4294967296", "18446744073709551616", "-2147483649"}
            invalid = [text for text in invalid if text not in undefined_atoi]
        for text in invalid:
            with self.subTest(text=text):
                result = subprocess.run([str(self.binary), text, "get"], capture_output=True, text=True)
                self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
                self.assertEqual(result.stdout, "", "Invalid selector reached command dispatch")
                self.assertEqual(result.stderr, "Invalid device index: %s\n" % text)


if __name__ == "__main__":
    unittest.main()
