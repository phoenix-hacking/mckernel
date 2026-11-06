"""Current environment callers retain borrowed inputs and release owned output.

Production parse_env/owner/first/config/kargs blocks are extracted on each run.
Only synchronous observation adapters are supplied for the private operation,
configuration setter and kargs call; these are not actual IHK providers. Genuine
libc handles parsing, allocations, frees and callback string copies. The seven
vectors exclude devices/backends/native behavior and the distinct create-OS parser.
"""
from pathlib import Path
import os
import subprocess
import tempfile
import unittest


ROOT = Path(os.environ.get("M15_REPO", Path(__file__).resolve().parents[2]))
SOURCE = ROOT / "ihk/linux/user/rust/whole70/ihklib_environment.rs"
FIXTURES = Path(__file__).resolve().parent / "fixtures/m15-environment-ownership"

CALLBACK_GLUE = r'''
use core::ffi::{c_char,c_int,c_long,c_void};
use core::ptr::null_mut;
unsafe extern "C" {
 fn calloc(count:usize,size:usize)->*mut c_void;
 fn strndup(text:*const c_char,length:usize)->*mut c_char;
 fn strdup(text:*const c_char)->*mut c_char;
 fn strsep(cursor:*mut *mut c_char,delimiters:*const c_char)->*mut c_char;
 fn strcmp(first:*const c_char,second:*const c_char)->c_int;
 fn strtol(text:*const c_char,end:*mut *mut c_char,base:c_int)->c_long;
 fn free(pointer:*mut c_void);
 fn __errno_location()->*mut c_int;
 fn run_callback_consumer()->c_int;
}
mod runtime_state {
 use core::ffi::{c_int,c_void};
 unsafe extern "C" { fn observe_conf(index:c_int,key:c_int,value:*mut c_void)->c_int; }
 pub unsafe extern "C" fn ihk_reserve_mem_conf(index:c_int,key:c_int,value:*mut c_void)->c_int {
  unsafe {observe_conf(index,key,value)}
 }
}
mod os_kargs {
 use core::ffi::{c_int,c_char};
 unsafe extern "C" { fn observe_kargs(index:c_int,value:*mut c_char)->c_int; }
 pub unsafe extern "C" fn ihk_os_kargs(index:c_int,value:*mut c_char)->c_int {
  unsafe {observe_kargs(index,value)}
 }
}
'''


class IhklibEnvironmentOwnershipTests(unittest.TestCase):
    def compile_current_callers(self, work):
        rustc = os.environ.get("RUSTC")
        self.assertTrue(rustc, "RUSTC must explicitly select the admitted compiler")
        self.assertTrue(Path(rustc).is_absolute() and Path(rustc).is_file())
        cc = os.environ.get("CC", "/usr/bin/cc")
        self.assertTrue(Path(cc).is_absolute() and Path(cc).is_file())
        actual = SOURCE.read_text()

        # The selected functions use top-level closing braces. These exact source
        # boundaries select existing bodies; this fixture has no parser algorithm.
        def function(signature):
            start = actual.index(signature)
            return actual[start:actual.index("\n}\n", start) + 3]

        parse_start = actual.index('#[no_mangle]\npub unsafe extern "C" fn parse_env(')
        operation_start = actual.index("type StringOperation =")
        parse_and_owner = actual[parse_start:operation_start]
        operation_alias = actual[operation_start:actual.index("\n", operation_start) + 1]
        first = function("unsafe fn first(")
        conf = function('#[no_mangle]\npub unsafe extern "C" fn ihk_reserve_mem_conf_str(')
        config_start = actual.index("const CONFIG_KEYS:")
        config_keys = actual[config_start:actual.index("\n];", config_start) + 3] + "\n"
        kargs = function('#[no_mangle]\npub unsafe extern "C" fn ihk_os_kargs_str(')
        blocks = parse_and_owner + operation_alias + first + config_keys + conf + kargs
        # Safety invariant: only these caller bodies and libc-only parser enter
        # the unit. No actual raw operation, ioctl or device provider is linked.
        self.assertNotIn("create_os_environment", blocks)
        self.assertNotIn("ioctl(", blocks)
        unit = CALLBACK_GLUE + "\nmod environment {\nuse super::*;\n" + blocks + r'''
#[no_mangle]
pub unsafe extern "C" fn fixture_first(index:c_int,envp:*const c_char,count:c_int,
 operation:unsafe extern "C" fn(c_int,*mut c_char,*mut c_char)->c_int)->c_int {
 unsafe {first(index,envp,count,b"IHK_CPUS\0",operation)}
}
}
fn main(){std::process::exit(unsafe{run_callback_consumer()});}
'''
        source = work / "current_callers.rs"
        source.write_text(unit)
        observer = work / "callback_consumer.o"
        binary = work / "callback-consumer"
        commands = [
            [cc, "-std=gnu11", "-Wall", "-Wextra", "-Werror",
             "-I" + str(ROOT / "ihk/linux/include"), "-I" + str(FIXTURES),
             "-c", str(FIXTURES / "callback_consumers.c"), "-o", str(observer)],
            [rustc, "--edition=2021", "-Dwarnings", "-C", "codegen-units=1",
             "-C", "linker=" + cc, str(source), "-C", "link-arg=" + str(observer),
             "-C", "link-arg=-Wl,--wrap=calloc,--wrap=strndup,--wrap=strdup,--wrap=free",
             "-o", str(binary)],
        ]
        for command in commands:
            result = subprocess.run(command, capture_output=True, text=True, timeout=60)
            self.assertEqual(result.returncode, 0, repr(command) + "\n" + result.stdout + result.stderr)
        return binary

    def test_synchronous_callers_release_owned_output_and_preserve_errno(self):
        with tempfile.TemporaryDirectory(prefix="m15-environment-ownership-") as directory:
            binary = self.compile_current_callers(Path(directory))
            result = subprocess.run([str(binary)], capture_output=True, text=True, timeout=10)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertEqual(result.stderr, "")
            lines = result.stdout.splitlines()
            self.assertEqual(len(lines), 8, result.stdout)
            self.assertEqual(lines[-1], "callback candidate checks=7 failures=0")
            self.assertEqual(tuple(line.split(" ", 1)[0] for line in lines[:-1]), (
                "first-success", "first-error", "config-setter-success", "config-setter-error",
                "kargs-selected-success", "kargs-selected-error", "kargs-default-success"))
            for line in lines[:-1]:
                self.assertTrue(line.endswith(" callback-calls=1 borrow-ok=1 live=0 reclaimed=0 errno=34 ok=1"), line)


if __name__ == "__main__":
    unittest.main()
