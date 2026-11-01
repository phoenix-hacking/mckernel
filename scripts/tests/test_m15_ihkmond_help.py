"""Actual daemon CLI prefixes with a marker in place of daemon startup.

Uses real libc getopt/printf, but excludes daemon(), devices, udev, and threads.
The marker is an isolated observation endpoint, never a production provider.
"""
from pathlib import Path
import os
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
USER = ROOT / "ihk/linux/user"


class IhkmondHelpTests(unittest.TestCase):
    def compile_prefix(self, work, language):
        output = work / "prefix"
        if language == "c":
            compiler = shutil.which(os.environ.get("CC") or "cc")
            self.assertIsNotNone(compiler, "C compiler required")
            actual = (USER / "ihkmond.c").read_text()
            definitions = actual[actual.index("struct facility_list {"):actual.index("static ssize_t reap_event(")]
            usage = actual[actual.index("static void show_usage("):actual.index("int main(")]
            main = actual[actual.index("\tint facility = LOG_LOCAL6;", actual.index("int main(")):actual.index('\n\tdprintf("enable_kmsg=', actual.index("int main("))]
            source = r'''
#include <getopt.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <syslog.h>
/* Only CLI failure observation: no printk or daemon runtime enters this unit. */
#define CHKANDJUMP(cond,err,...) do { if(cond) return err; } while(0)
'''
            source += definitions + usage + "\nint main(int argc,char **argv) { int opt,i;\n" + main
            source += '\n printf("STARTUP %d %d %d\\n",facility,enable_kmsg,mon_interval); return 73; }\n'
            path = work / "prefix.c"
            command = [compiler, "-std=c11", "-Wall", "-Wextra", "-Werror", str(path), "-o", str(output)]
        else:
            compiler = shutil.which(os.environ.get("RUSTC") or "rustc")
            self.assertIsNotNone(compiler, "Rust compiler required")
            actual = (USER / "rust/ihkmond.rs").read_text()
            prefix = actual[actual.index("fn usage("):actual.index(" let ret=unsafe{daemon(", actual.index("fn run()->i32{"))]
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
/* Only CLI failure observation: no kernel logging or daemon runtime. */
fn fail(code:i32,_:&str)->i32{code}
'''
            source += prefix + '\n println!("STARTUP {} {} {}",facility,kmsg,interval); 73 }\nfn main(){std::process::exit(run());}\n'
            path = work / "prefix.rs"
            command = [compiler, "--edition=2021", "-Dwarnings", str(path), "-o", str(output)]
        path.write_text(source)
        result = subprocess.run(command, capture_output=True, text=True, timeout=60)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        return output

    def test_help_exits_before_startup(self):
        for language in ("c", "rust"):
            with self.subTest(language=language), tempfile.TemporaryDirectory(prefix="m15-ihkmond-help-") as directory:
                executable = self.compile_prefix(Path(directory), language)
                for argv0 in ("ihkmond", "/fixture/bin/ihkmond"):
                    for options in (("--help",), ("-?",), ("-k", "0", "--help"), ("--help", "-f", "INVALID")):
                        with self.subTest(argv0=argv0, options=options):
                            result = subprocess.run([argv0, *options], executable=str(executable), capture_output=True, text=True, timeout=10)
                            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                            self.assertTrue(result.stdout.startswith("ihkmond [--help|-?]"), result.stdout)
                            self.assertNotIn("STARTUP", result.stdout)
                            self.assertEqual(result.stderr, "")
                for options, expected in (((), "STARTUP 176 1 600\n"), (("-f", "LOG_LOCAL0", "-k", "0", "-i", "-1"), "STARTUP 128 0 -1\n")):
                    with self.subTest(options=options):
                        result = subprocess.run(["ihkmond", *options], executable=str(executable), capture_output=True, text=True, timeout=10)
                        self.assertEqual(result.returncode, 73, result.stdout + result.stderr)
                        self.assertEqual(result.stdout, expected)
                        self.assertEqual(result.stderr, "")


if __name__ == "__main__":
    unittest.main()
