"""Focused executor libdir behavior from actual C/Rust source functions.

Only find_libdir and its pure Rust string dependencies are extracted. Readlink,
pipe, getline, close, and free are explicit observation doubles. No executor
crate, held source, command subprocess, device, or native lifecycle is run.
Fixture linkage demonstrates the selected function ABI only, not production
providers or final executor ownership.
"""
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]


def item(source, signature):
    start = source.index(signature)
    opening = source.index("{", start)
    depth, end = 1, opening + 1
    while depth:
        depth += (source[end] == "{") - (source[end] == "}")
        end += 1
    return source[start:end]


RUST_PREFIX = r'''
#![allow(dead_code)]
use core::ffi::c_void;
const PATH_MAX: usize = 4096;
const EINVAL: i32 = 22;
const ERANGE: i32 = 34;
const ENOENT: i32 = 2;
const ENAMETOOLONG: i32 = 36;
unsafe extern "C" {
 fn __errno_location() -> *mut i32;
 fn mcexec_find_libdir_readlink_bridge(path: *mut u8, size: usize) -> isize;
 fn mcexec_find_libdir_popen_bridge(cmd: *const u8) -> *mut c_void;
 fn mcexec_find_libdir_getline_bridge(line: *mut *mut u8, len: *mut usize, stream: *mut c_void) -> isize;
 fn mcexec_find_libdir_pclose_bridge(stream: *mut c_void);
 fn mcexec_find_libdir_free_bridge(line: *mut u8);
 fn mcexec_find_libdir_readlink_failed_bridge(error: i32);
 fn mcexec_find_libdir_objdump_failed_bridge(error: i32);
 fn mcexec_find_libdir_rpath_not_found_bridge(error: i32);
}
'''

C_PREFIX = r'''
#define _GNU_SOURCE
#include <assert.h>
#include <errno.h>
#include <limits.h>
#include <stddef.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/types.h>
_Static_assert(sizeof(ssize_t)==sizeof(void *), "Rust isize/C ssize_t ABI");
static int scenario, closes, frees, opens, reads;
static const char *line_value;
static char line_storage[8192];
static char command[8192];
static FILE *const observed_stream = (FILE *)&scenario;
static ssize_t observed_readlink(const char *name, char *path, size_t size) {
 assert(strcmp(name,"/proc/self/exe")==0); reads++;
 if (scenario==11) {errno=EACCES; return -1;}
 if (scenario==13) {memset(path,'x',size); return (ssize_t)size;}
 if (scenario==14) {memset(path,'x',size-1); return (ssize_t)size-1;}
 const char *value="/fixture/mcexec";
 memcpy(path,value,strlen(value)); return (ssize_t)strlen(value);
}
static FILE *observed_popen(const char *cmd, const char *mode) {
 assert(strcmp(mode,"r")==0); opens++;
 assert(strlen(cmd)<sizeof(command)); strcpy(command,cmd);
 if (scenario==12) {errno=EMFILE;return NULL;}
 return observed_stream;
}
static ssize_t observed_getline(char **line, size_t *capacity, FILE *stream) {
 assert(stream==observed_stream);
 *line=line_storage; *capacity=sizeof(line_storage);
 if (scenario==0 || scenario==1) return -1; /* EOF preserves errno. */
 if (scenario==2) {errno=EIO;return -1;}
 strcpy(line_storage,line_value); return (ssize_t)strlen(line_storage);
}
static int observed_pclose(FILE *stream) {assert(stream==observed_stream);closes++;return 0;}
static void observed_free(void *line) {if (line) {assert(line==line_storage);frees++;}}
#define readlink observed_readlink
#define popen observed_popen
#define getline observed_getline
#define pclose observed_pclose
#define free observed_free
'''

C_BRIDGES_AND_CASES = r'''
#undef readlink
#undef popen
#undef getline
#undef pclose
#undef free
/* These are observation doubles, never production provider substitutions. */
ssize_t mcexec_find_libdir_readlink_bridge(char *path,size_t len) {return observed_readlink("/proc/self/exe",path,len);}
void *mcexec_find_libdir_popen_bridge(const char *cmd) {return observed_popen(cmd,"r");}
ssize_t mcexec_find_libdir_getline_bridge(char **line,size_t *len,void *stream) {return observed_getline(line,len,stream);}
void mcexec_find_libdir_pclose_bridge(void *stream) {(void)observed_pclose(stream);}
void mcexec_find_libdir_free_bridge(char *line) {observed_free(line);}
void mcexec_find_libdir_readlink_failed_bridge(int error) {assert(error==EACCES);}
void mcexec_find_libdir_objdump_failed_bridge(int error) {assert(error==EMFILE);}
void mcexec_find_libdir_rpath_not_found_bridge(int error) {assert(error==ENOENT || error==EIO);}
extern ssize_t mcexec_find_libdir_body(char *,size_t);
static ssize_t (*const implementations[])(char *,size_t)={find_libdir,mcexec_find_libdir_body};
int main(int argc,char **argv) {
 assert(argc==3); scenario=atoi(argv[1]);
 unsigned implementation=(unsigned)atoi(argv[2]);assert(implementation<2);
 {
  closes=frees=opens=reads=0;command[0]=0;
  errno=scenario==1 ? EBUSY : 0;
  char output[64], before[64]; memset(output,0x5a,sizeof output);memcpy(before,output,sizeof output);
  line_value="/opt/lib\n"; size_t capacity=sizeof(output);char *destination=output;
  ssize_t expected=8;
  switch (scenario) {
   case 0: case 1: expected=-ENOENT;break;
   case 2: expected=-EIO;break;
   case 3: break;
   case 4: line_value="/opt/lib";break;
   case 5: capacity=8;expected=-ERANGE;break;
   case 6: capacity=9;break;
   case 7: line_value="relative\n";expected=-EINVAL;break;
   case 8: line_value="\n";expected=-EINVAL;break;
   case 9: destination=NULL;expected=-EINVAL;break;
   case 10: capacity=0;expected=-EINVAL;break;
   case 11: expected=-EACCES;break;
   case 12: expected=-EMFILE;break;
   case 13: break;
   case 14: expected=-ERANGE;break;
   default: abort();
  }
  ssize_t result=implementations[implementation](destination,capacity);
  if (result!=expected) {fprintf(stderr,"case %d %s returned %zd expected %zd\n",scenario,implementation ? "Rust" : "C",result,expected);return 1;}
  if (expected>=0) {
   assert(strcmp(output,"/opt/lib")==0);
   assert(memcmp(output+9,before+9,sizeof(output)-9)==0);
  } else assert(memcmp(output,before,sizeof(output))==0);
  int opened=scenario!=9 && scenario!=10 && scenario!=11 && scenario!=14;
  int got_line=opened && scenario!=12;
  assert(opens==opened); assert(closes==got_line);assert(frees==got_line);
  if (scenario==13) assert(strcmp(command,"objdump -x /proc/self/exe | awk '$1 ~ /^(RPATH|RUNPATH)$/ { sub(/^[[:space:]]*(RPATH|RUNPATH)[[:space:]]+/, \"\"); print }'")==0);
 }
 printf("case %d C/Rust behavior, ABI and cleanup passed\n",scenario);
 return 0;
}
'''


class ExecutorLibdirTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        rustc = shutil.which(os.environ.get("RUSTC") or "rustc")
        cc = shutil.which("gcc")
        if not rustc or not cc:
            raise unittest.SkipTest("Rust compiler and GCC unavailable; bind RUSTC to the qualified compiler")
        cls.temp = tempfile.TemporaryDirectory(prefix="m15-executor-libdir-")
        cls.addClassCleanup(cls.temp.cleanup)
        out = Path(cls.temp.name)
        rust = (ROOT / "executer/user/rust/mcexec_helpers.rs").read_text()
        c = (ROOT / "executer/user/mcexec.c").read_text()
        constants = "\n".join(line for line in rust.splitlines() if line.startswith((
            "static PROC_SELF_EXE:", "static OBJDUMP_RPATH_PREFIX:", "static OBJDUMP_RPATH_SUFFIX:")))
        signatures = ["unsafe fn cstr_bytes<'a>(", "unsafe fn cstr_len(",
                      "fn byte_at(", "fn contains_byte(", "unsafe fn copy_bytes(",
                      "unsafe fn write_nul(", 'pub unsafe extern "C" fn mcexec_copy_path_result(',
                      'pub unsafe extern "C" fn mcexec_objdump_rpath_cmd_result(',
                      'pub unsafe extern "C" fn mcexec_find_libdir_body(']
        body = "\n".join(("#[no_mangle]\n" if sig.startswith("pub ") else "") + item(rust,sig) for sig in signatures)
        (out / "fixture.rs").write_text(RUST_PREFIX + constants + "\n" + body)
        (out / "fixture.c").write_text(C_PREFIX + item(c,"static ssize_t find_libdir(char *libdir, size_t len)\n{") + C_BRIDGES_AND_CASES)
        cls.binary = out / "fixture"
        for command in ([rustc,"--edition=2021","--crate-type=staticlib","-C","opt-level=1",str(out/"fixture.rs"),"-o",str(out/"libfixture.a")],
                        [cc,"-std=gnu11","-O1","-Wall","-Wextra","-Werror=incompatible-pointer-types","-fsanitize=undefined","-fno-sanitize-recover=undefined",str(out/"fixture.c"),str(out/"libfixture.a"),"-ldl","-lpthread","-lm","-o",str(cls.binary)]):
            result = subprocess.run(command,capture_output=True,text=True,timeout=60)
            if result.returncode:
                raise AssertionError(f"{command}\n{result.stdout}{result.stderr}")

    def test_actual_c_and_rust_libdir_result_and_lifetime(self):
        for scenario in range(15):
            for implementation in range(2):
                with self.subTest(scenario=scenario, implementation=("C", "Rust")[implementation]):
                    result = subprocess.run([str(self.binary),str(scenario),str(implementation)],capture_output=True,text=True,timeout=5)
                    self.assertEqual(result.returncode,0,result.stdout+result.stderr)


if __name__ == "__main__":
    unittest.main()
