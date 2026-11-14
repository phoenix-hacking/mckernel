"""Actual C/Rust CLI query functions with observed providers; no device access.

The C shim records prerequisite ordering, allocation ownership, formatting, and
release calls. It is solely an isolated unit observer, never a CLI link provider.
"""
from pathlib import Path
import os
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
USER = ROOT / "ihk/linux/user"


def function(source, marker):
    start = source.index(marker)
    brace = source.index("{", start)
    depth = 1
    end = brace + 1
    while depth:
        depth += (source[end] == "{") - (source[end] == "}")
        end += 1
    return source[start:end]


COMMON = r'''
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdarg.h>
#include <errno.h>
#include <sys/types.h>
struct ihk_cpu_req { int *cpus; int num_cpus; };
struct ihk_mem_req { size_t *sizes; int *numa_ids; int num_chunks; int min_chunk_size; int max_size_ratio_all; int timeout; };
enum { GET_NUM_CPUS=1, QUERY_CPU=2, QUERY_MEM=3, RELEASE_MEM=4, RELEASE_CPU=5 };
int scenario, calls, allocations, live, formats, releases;
int observed_ioctl(int fd, unsigned long request, ...) {
    (void)fd;
    calls++;
    if (request == RELEASE_MEM) { releases++; return 0; }
    if (request == GET_NUM_CPUS) return scenario == 1 ? -1 : 2;
    va_list ap; va_start(ap, request); void *arg=va_arg(ap,void *); va_end(ap);
    if (request == QUERY_MEM && calls == 1) {
        ((struct ihk_mem_req *)arg)->num_chunks=2;
        return scenario == 1 ? -1 : 0;
    }
    if (scenario == 2) return -1;
    return 0;
}
void *observed_calloc(size_t n, size_t size) {
    allocations++;
    if (scenario == 3 && allocations == 2) return NULL;
    /* Never allocate a negative provider count in the pre-fix observer. */
    if (n > 4096 || size > 4096) return NULL;
    void *p=calloc(n,size); if (p) live++; return p;
}
void observed_free(void *p) { if(p) live--; free(p); }
char *observed_format(void) {
    formats++; char *p=malloc(1); if(p) { *p=0; live++; } return p;
}
int cpu_str2count(char *p) { (void)p; return 2; }
int cpu_str2req(char *p,int n,struct ihk_cpu_req *r) { (void)p; r->num_cpus=n; return 0; }
int mem_str2count(char *p) { (void)p; return 2; }
int mem_str2req(char *p,struct ihk_mem_req *r) { (void)p; r->num_chunks=2; return 0; }
char *cpu_req2str(struct ihk_cpu_req *r) { (void)r; return observed_format(); }
char *mem_req2str(struct ihk_mem_req *r) { (void)r; return observed_format(); }
extern int run(int operation, int cpu);
int main(int argc,char **argv) {
    if(argc!=4) return 90;
    scenario=atoi(argv[1]); int result=run(atoi(argv[2]),atoi(argv[3]));
    fprintf(stderr,"OBS %d %d %d %d %d %d\n",result,calls,allocations,formats,releases,live);
    return 0;
}
'''


class M15IhkCliQueryErrors(unittest.TestCase):
    def compile_observer(self, work, name, language):
        cc = shutil.which("cc")
        if not cc:
            self.skipTest("C compiler required")
        (work / "observer.c").write_text(COMMON)
        source = (USER / ("rust/" + name + ".rs" if language == "rust" else name + ".c")).read_text()
        if language == "c":
            selected = function(source, "static int do_release(") + "\n" + function(source, "static int do_query(")
            prefix = "IHK_DEVICE_" if name == "ihkconfig" else "IHK_OS_"
            for request in ("GET_NUM_CPUS", "QUERY_CPU", "QUERY_MEM", "RELEASE_CPU", "RELEASE_MEM"):
                selected = selected.replace(prefix + request, request)
            macro = "IHKCONFIG" if name == "ihkconfig" else "IHKOSCTL"
            harness = r'''
int __argc=5; char *__argv[6];
static void usage(char **argv) { (void)argv; }
#define dprintf(...) ((void)0)
#define CHK(condition,message,error) do { if(condition) {ret=error;goto fn_fail;} } while(0)
#define ioctl observed_ioctl
#define calloc observed_calloc
#define free observed_free
'''.replace("#define CHK", "#define " + macro + "_CHKANDJUMP")
            harness += selected + r'''
int run(int operation,int cpu) {
    __argv[3]=cpu?"cpu":"mem"; __argv[4]="all";
    return operation?do_release(17):do_query(17);
}
'''
            (work / "unit.c").write_text(COMMON + harness)
            command = [cc, "-std=c11", "-Wall", "-Wextra", "-Werror", str(work / "unit.c"), "-o", str(work / "unit")]
        else:
            rustc = os.environ.get("RUSTC") or shutil.which("rustc")
            if not rustc:
                self.skipTest("Rust compiler required")
            release = "unsafe fn release(" if name == "ihkconfig" else "unsafe fn change_resources("
            selected = function(source, release) + "\n" + function(source, "unsafe fn query(")
            selected = selected.replace("ioctl(", "observed_ioctl(").replace("calloc(", "observed_calloc(").replace("free(", "observed_free(")
            harness = r'''
#![allow(dead_code)]
use std::ffi::{c_char,c_int,c_ulong,c_void};
use std::ptr::null_mut;
macro_rules! c {($s:literal)=>{concat!($s,"\0").as_ptr().cast::<c_char>()};}
#[repr(C)]struct CpuReq{cpus:*mut c_int,num_cpus:c_int}
#[repr(C)]struct MemReq{sizes:*mut usize,numa_ids:*mut c_int,num_chunks:c_int,min_chunk_size:c_int,max_size_ratio_all:c_int,timeout:c_int}
const GET_NUM_CPUS:c_ulong=1; const NUM_CPUS:c_ulong=1; const QUERY_CPU:c_ulong=2; const QUERY_MEM:c_ulong=3;
const RELEASE_MEM:c_ulong=4; const RELEASE_CPU:c_ulong=5; const ASSIGN_MEM:c_ulong=6; const ASSIGN_CPU:c_ulong=7; const EINVAL:c_int=22;
static mut __argc:c_int=5; static mut __argv:[*mut c_char;6]=[null_mut();6];
unsafe fn arg(i:usize)->*mut c_char{__argv[i]}
unsafe fn is(a:*const c_char,b:*const c_char)->bool{strcmp(a,b)==0}
unsafe fn usage(){}
unsafe fn checked_fail(_: *const c_char,_: *const c_char)->c_int{-1}
unsafe fn failed(_: *const c_char,_: *const c_char)->c_int{-1}
unsafe fn zero_mem()->MemReq{MemReq{sizes:null_mut(),numa_ids:null_mut(),num_chunks:0,min_chunk_size:0,max_size_ratio_all:0,timeout:0}}
unsafe fn cpu_array(_: *mut c_char,n:c_int,_: *mut c_int)->c_int{n}
unsafe fn mem_array(_: *mut c_char,_: *mut usize,_: *mut c_int)->c_int{2}
unsafe fn query_string(_: &CpuReq,_: &MemReq,_:bool)->*mut c_char{observed_format()}
unsafe extern "C" {
 static mut stderr:*mut c_void;
 fn printf(fmt:*const c_char,...)->c_int; fn fprintf(stream:*mut c_void,fmt:*const c_char,...)->c_int;
 fn strcmp(a:*const c_char,b:*const c_char)->c_int;
 fn observed_ioctl(fd:c_int,req:c_ulong,...)->c_int;
 fn observed_calloc(n:usize,size:usize)->*mut c_void; fn observed_free(p:*mut c_void);
 fn observed_format()->*mut c_char;
 fn cpu_str2count(p:*mut c_char)->c_int; fn cpu_str2req(p:*mut c_char,n:c_int,r:*mut CpuReq)->c_int;
 fn mem_str2count(p:*mut c_char)->c_int; fn mem_str2req(p:*mut c_char,r:*mut MemReq)->c_int;
 fn cpu_req2str(r:*mut CpuReq)->*mut c_char; fn mem_req2str(r:*mut MemReq)->*mut c_char;
}
'''
            # The raw Python string above retains Rust's one-character C NUL escape.
            harness = harness.replace('"\\0"', '"\0"')
            call = "release(17)" if name == "ihkconfig" else "change_resources(17,false)"
            harness += selected + '\n#[no_mangle]pub unsafe extern "C" fn run(operation:c_int,cpu:c_int)->c_int{__argv[3]=if cpu!=0{c!("cpu")}else{c!("mem")}.cast_mut();__argv[4]=c!("all").cast_mut();if operation!=0{' + call + '}else{query(17)}}\n'
            (work / "unit.rs").write_text(harness)
            result = subprocess.run([rustc, "--edition=2021", "--crate-type=staticlib", "-C", "panic=abort", str(work / "unit.rs"), "-o", str(work / "unit.a")], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            command = [cc, "-std=c11", "-Wall", "-Wextra", "-Werror", str(work / "observer.c"), str(work / "unit.a"), "-ldl", "-lpthread", "-lm", "-o", str(work / "unit")]
        result = subprocess.run(command, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        return work / "unit"

    def test_query_and_release_prerequisites(self):
        for name in ("ihkconfig", "ihkosctl"):
            for language in ("c", "rust"):
                with self.subTest(cli=name, language=language), tempfile.TemporaryDirectory(prefix="m15-cli-query-") as directory:
                    unit = self.compile_observer(Path(directory), name, language)
                    cases = [
                        # scenario, release, cpu, (ret,calls,allocations,formats,releases,live)
                        (1,0,1,(-1,1,0,0,0,0)), (2,0,1,(-1,2,1,0,0,0)),
                        (1,0,0,(-1,1,0,0,0,0)), (2,0,0,(-1,2,2,0,0,0)),
                        (1,1,0,(-1,1,0,0,0,0)), (2,1,0,(-1,2,2,0,0,0)),
                        (3,0,0,(-1,1,2,0,0,0)), (3,1,0,(-1,1,2,0,0,0)),
                        (0,0,1,(0,2,1,1,0,0)), (0,0,0,(0,2,2,1,0,0)),
                        (0,1,0,(0,3,2,0,1,0)),
                    ]
                    for scenario, release, cpu, expected in cases:
                        with self.subTest(scenario=scenario, release=release, cpu=cpu):
                            result = subprocess.run([str(unit), str(scenario), str(release), str(cpu)], capture_output=True, text=True)
                            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                            observation = next(line for line in result.stderr.splitlines() if line.startswith("OBS "))
                            self.assertEqual(tuple(map(int, observation.split()[1:])), expected, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
