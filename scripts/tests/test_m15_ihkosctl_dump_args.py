"""Actual ihkosctl dump parser with genuine HOST libc getopt_long.

The dump API is a recording observer: this qualifies argument consumption only,
not dump production, native devices, or the public library implementation.
"""
from pathlib import Path
import os
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
SOURCE = Path(os.environ.get("M15_IHKOSCTL_SOURCE", ROOT / "ihk/linux/user/rust/ihkosctl.rs"))


class M15IhkosctlDumpArgsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        compiler = os.environ.get("RUSTC") or shutil.which("rustc")
        if not compiler:
            raise unittest.SkipTest("Rust compiler required")
        source = SOURCE.read_text()
        start = source.index("#[cfg(ihkosctl_memdump)]unsafe fn dump(")
        end = source.index("#[cfg(not(ihkosctl_memdump))]unsafe fn dump(", start)
        function = source[start:end]
        option = next(line for line in source.splitlines() if line.startswith("#[repr(C)]struct GetoptOption"))
        cls.temporary = tempfile.TemporaryDirectory(prefix="m15-dump-args-", dir=os.environ.get("TMPDIR"))
        cls.addClassCleanup(cls.temporary.cleanup)
        work = Path(cls.temporary.name)
        harness = r'''
use std::ffi::{c_char,c_int,c_long,c_void,CString,CStr};
use std::ptr::{null_mut,null};
macro_rules! c {($s:literal)=>{concat!($s,"\0").as_ptr().cast::<c_char>()};}
#[no_mangle]static mut __argc:c_int=0;
#[no_mangle]static mut __argv:*mut *mut c_char=null_mut();
unsafe fn arg(i:usize)->*mut c_char{*__argv.add(i)}
extern "C" {
 static mut stderr:*mut c_void;
 static mut optarg:*mut c_char;
 static mut optind:c_int;
 fn getopt_long(argc:c_int,argv:*mut *mut c_char,opts:*const c_char,long:*const GetoptOption,index:*mut c_int)->c_int;
 fn atoi(s:*const c_char)->c_int;
 fn fprintf(stream:*mut c_void,fmt:*const c_char,...)->c_int;
 fn perror(label:*const c_char);
 fn time(out:*mut c_long)->c_long;
 fn localtime(value:*const c_long)->*mut c_void;
 fn strftime(out:*mut c_char,size:usize,fmt:*const c_char,tm:*const c_void)->usize;
 fn ihk_os_makedumpfile(index:c_int,path:*mut c_char,level:c_int,interactive:c_int)->c_int;
}
#[export_name="ihk_os_makedumpfile"]
unsafe extern "C" fn record_dump(index:c_int,path:*mut c_char,level:c_int,interactive:c_int)->c_int {
 println!("CALL\t{}\t{}\t{}\t{}",index,level,interactive,CStr::from_ptr(path).to_str().unwrap());
 37
}
'''
        main = r'''
fn main() {
 let args:Vec<CString>=std::env::args().map(|value|CString::new(value).unwrap()).collect();
 let mut pointers:Vec<*mut c_char>=args.iter().map(|value|value.as_ptr().cast_mut()).collect();
 pointers.push(null_mut());
 unsafe {__argc=args.len() as c_int;__argv=pointers.as_mut_ptr();std::process::exit(dump(0));}
}
'''
        unit = work / "dump.rs"
        unit.write_text(harness + option + "\n" + function + main)
        cls.binary = work / "dump"
        compiled = subprocess.run([compiler, "--edition=2021", "--cfg", "ihkosctl_memdump",
                                   "-Dwarnings", str(unit), "-o", str(cls.binary)],
                                  capture_output=True, text=True)
        if compiled.returncode:
            raise AssertionError(compiled.stdout + compiled.stderr)

    def test_dump_consumes_only_its_options_and_filename(self):
        # Every case starts with the actual command's device index and action.
        cases = [
            (["named.dump"], 37, "CALL\t0\t0\t0\tnamed.dump\n"),
            (["-d", "24", "named.dump"], 37, "CALL\t0\t24\t0\tnamed.dump\n"),
            (["-d24", "--interactive", "named.dump"], 37, "CALL\t0\t24\t1\tnamed.dump\n"),
            (["-i", "-d", "0", "--", "-named.dump"], 37, "CALL\t0\t0\t1\t-named.dump\n"),
            (["-Z"], 1, ""),
            (["-d"], 1, ""),
        ]
        for posix in (False, True):
            environment = dict(os.environ)
            environment.pop("POSIXLY_CORRECT", None)
            if posix:
                environment["POSIXLY_CORRECT"] = "1"
            for args, status, output in cases:
                with self.subTest(posix=posix, args=args):
                    result = subprocess.run([str(self.binary), "0", "dump", *args],
                                            env=environment, capture_output=True, text=True)
                    self.assertEqual(result.returncode, status, result.stdout + result.stderr)
                    self.assertEqual(result.stdout, output, result.stderr)


if __name__ == "__main__":
    unittest.main()
