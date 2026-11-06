"""Actual ihkmond interval parser with genuine libc, ending before daemon().

The producer's usage, checked helper and run prefix are read from current source.
Only the logging failure endpoint and successful pre-daemon observation are
supplied here. No daemon/supervise body, service, device or worker path is built.
RUSTC must name the compiler selected by the admitted HOST profile explicitly.
"""
from pathlib import Path
import os
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "ihk/linux/user/rust/ihkmond.rs"


class IhkmondIntervalTests(unittest.TestCase):
    def compile_prefix(self, work):
        compiler = os.environ.get("RUSTC")
        self.assertTrue(compiler, "RUSTC must select the admitted Rust compiler")
        self.assertTrue(Path(compiler).is_absolute() and Path(compiler).is_file(),
                        "RUSTC must be an existing absolute compiler path")
        actual = SOURCE.read_text()
        start = actual.index("fn usage(")
        stop = actual.index(" let ret=unsafe{daemon(", actual.index("fn run()->i32{"))
        prefix = actual[start:stop]
        # Safety invariant: real option parsing ends before daemonization or
        # supervision; successful parsing reaches only the marker below.
        self.assertNotIn("daemon(", prefix)
        self.assertNotIn("supervise(", prefix)
        source = r'''
use std::ffi::{CStr,CString};
use std::os::raw::{c_char,c_int};
use std::os::unix::ffi::OsStrExt;
use std::sync::Arc;
macro_rules! c {($s:literal)=>{concat!($s,"\0").as_ptr().cast::<c_char>()};}
#[repr(C)]struct GetoptOption{name:*const c_char,has_arg:c_int,flag:*mut c_int,val:c_int}
unsafe extern "C" {
 fn printf(format:*const c_char,...)->c_int;
 fn atoi(value:*const c_char)->c_int;
 fn getopt_long(argc:c_int,argv:*mut *mut c_char,opts:*const c_char,long:*const GetoptOption,index:*mut c_int)->c_int;
 static mut optarg:*mut c_char;
}
/* Error observation only: no kernel logging or other device operation. */
fn fail(code:i32,_:&str)->i32{code}
'''
        source += prefix
        source += '\n println!("STARTUP {} {} {}",facility,kmsg,interval); 73 }\nfn main(){std::process::exit(run());}\n'
        path = work / "prefix.rs"
        path.write_text(source)
        output = work / "prefix"
        command = [compiler, "--edition=2021", "-Dwarnings", "-C", "codegen-units=1",
                   "-C", "linker=" + os.environ.get("CC", "/usr/bin/cc"),
                   str(path), "-o", str(output)]
        result = subprocess.run(command, capture_output=True, text=True, timeout=60)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        return output

    def test_checked_interval_before_daemon(self):
        with tempfile.TemporaryDirectory(prefix="m15-ihkmond-interval-") as directory:
            binary = self.compile_prefix(Path(directory))
            valid = [((), 600), (("-i", "-1"), -1), (("-i", "0"), 0),
                     (("-i", "600"), 600), (("-i", "2147483647"), 2147483647),
                     (("-i", "-2147483648"), -2147483648), (("-i", "-2"), -2),
                     (("-i", "+600"), 600), (("-i", " \t+600"), 600),
                     (("-i", "000600"), 600), (("-i", "-0"), 0)]
            for options, interval in valid:
                with self.subTest(valid=options):
                    result = subprocess.run([str(binary), *options], capture_output=True,
                                            text=True, timeout=5)
                    self.assertEqual(result.returncode, 73, result.stdout + result.stderr)
                    self.assertEqual(result.stdout, "STARTUP 176 1 " + str(interval) + "\n")
                    self.assertEqual(result.stderr, "")

            invalid = ["", "garbage", "+", "-", "600tail", "-1tail", "2147483648",
                       "-2147483649", "4294967295", "9223372036854775808", "-9223372036854775809"]
            for token in invalid:
                with self.subTest(invalid=token):
                    result = subprocess.run([str(binary), "-i", token], capture_output=True,
                                            text=True, timeout=5)
                    self.assertEqual(result.returncode, 255, result.stdout + result.stderr)
                    self.assertEqual(result.stdout, "")
                    self.assertEqual(result.stderr, "")

            for options in (("--help", "-i", "garbage"), ("-i", "+600", "--help")):
                with self.subTest(help_order=options):
                    result = subprocess.run([str(binary), *options], capture_output=True,
                                            text=True, timeout=5)
                    self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                    self.assertIn("[--help|-?]", result.stdout)
                    self.assertNotIn("STARTUP", result.stdout)
                    self.assertEqual(result.stderr, "")


if __name__ == "__main__":
    unittest.main()
