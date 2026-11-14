"""Actual ELF RPATH/RUNPATH discovery through real host libc/objdump/awk.

Only the eligible libdir functions, pure Rust dependencies, and actual C libdir
bridges are extracted. The tiny host executables exercise those functions;
they are not executor builds or production Rust-provider closure evidence.
"""
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

from scripts.tests.test_m15_executor_libdir import ROOT, RUST_PREFIX, item

C_PREFIX = r'''
#define _GNU_SOURCE
#include <errno.h>
#include <limits.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/types.h>
#include <unistd.h>
'''
C_MAIN = r'''
extern ssize_t mcexec_find_libdir_body(char *,size_t);
int main(void) {
 char output[PATH_MAX]="";
 ssize_t result=find_libdir(output,sizeof(output));
 printf("C:%zd:%s\n",result,output);
 output[0]=0;
 result=mcexec_find_libdir_body(output,sizeof(output));
 printf("Rust:%zd:%s\n",result,output);
 return 0;
}
'''


class ExecutorLibdirRealProvidersTests(unittest.TestCase):
    def test_rpath_and_runpath_from_actual_host_elf(self):
        rustc = shutil.which(os.environ.get("RUSTC") or "rustc")
        cc = shutil.which("gcc")
        if not rustc or not cc or not shutil.which("objdump") or not shutil.which("awk"):
            self.skipTest("Rust compiler, GCC, objdump and awk unavailable; bind RUSTC to the qualified compiler")
        rust = (ROOT / "executer/user/rust/mcexec_helpers.rs").read_text()
        c = (ROOT / "executer/user/mcexec.c").read_text()
        constants = "\n".join(line for line in rust.splitlines() if line.startswith((
            "static PROC_SELF_EXE:", "static OBJDUMP_RPATH_PREFIX:", "static OBJDUMP_RPATH_SUFFIX:")))
        signatures = ["unsafe fn cstr_bytes<'a>(", "unsafe fn cstr_len(",
                      "fn byte_at(", "fn contains_byte(", "unsafe fn copy_bytes(",
                      "unsafe fn write_nul(", 'pub unsafe extern "C" fn mcexec_copy_path_result(',
                      'pub unsafe extern "C" fn mcexec_objdump_rpath_cmd_result(',
                      'pub unsafe extern "C" fn mcexec_find_libdir_body(']
        rust_body = "\n".join(("#[no_mangle]\n" if sig.startswith("pub ") else "") + item(rust,sig) for sig in signatures)
        c_body = item(c,"static ssize_t find_libdir(char *libdir, size_t len)\n{") + "\n"
        for signature in [
            "ssize_t mcexec_find_libdir_readlink_bridge(char *path, size_t size)\n{",
            "void *mcexec_find_libdir_popen_bridge(const char *cmd)\n{",
            "ssize_t mcexec_find_libdir_getline_bridge(char **line, size_t *linelen,",
            "void mcexec_find_libdir_pclose_bridge(void *filep)\n{",
            "void mcexec_find_libdir_free_bridge(char *line)\n{",
            "void mcexec_find_libdir_readlink_failed_bridge(int error)\n{",
            "void mcexec_find_libdir_objdump_failed_bridge(int error)\n{",
            "void mcexec_find_libdir_rpath_not_found_bridge(int error)\n{",
        ]:
            c_body += item(c,signature) + "\n"
        with tempfile.TemporaryDirectory(prefix="m15-executor-libdir-real-") as tmp:
            out = Path(tmp)
            (out/"fixture.rs").write_text(RUST_PREFIX + constants + "\n" + rust_body)
            (out/"fixture.c").write_text(C_PREFIX + c_body + C_MAIN)
            command = [rustc,"--edition=2021","--crate-type=staticlib","-C","opt-level=1",str(out/"fixture.rs"),"-o",str(out/"libfixture.a")]
            result = subprocess.run(command,capture_output=True,text=True,timeout=60)
            self.assertEqual(result.returncode,0,result.stdout+result.stderr)
            for tag,dtags in [("RUNPATH","--enable-new-dtags"),("RPATH","--disable-new-dtags")]:
                # Only the literal ELF tag value has whitespace; the executable
                # path uses the unchanged ordinary command-input profile.
                for libdir in ("/fixture/lib", "/fixture/lib dir"):
                    with self.subTest(tag=tag, libdir=libdir):
                        binary = out/(tag.lower() + ("-space" if " " in libdir else ""))
                        command = [cc,"-std=gnu11","-O1","-Wall","-Wextra","-Werror=incompatible-pointer-types",str(out/"fixture.c"),str(out/"libfixture.a"),"-ldl","-lpthread","-lm",f"-Wl,{dtags},-rpath,{libdir}","-o",str(binary)]
                        result = subprocess.run(command,capture_output=True,text=True,timeout=60)
                        self.assertEqual(result.returncode,0,result.stdout+result.stderr)
                        headers = subprocess.run(["objdump","-x",str(binary)],capture_output=True,text=True,timeout=10)
                        self.assertEqual(headers.returncode,0,headers.stderr)
                        self.assertTrue(any(line.split(None,1)==[tag,libdir] for line in headers.stdout.splitlines()),headers.stdout)
                        result = subprocess.run([str(binary)],capture_output=True,text=True,timeout=10)
                        self.assertEqual(result.returncode,0,result.stdout+result.stderr)
                        expected = f"C:{len(libdir)}:{libdir}\nRust:{len(libdir)}:{libdir}\n"
                        self.assertEqual(result.stdout,expected,result.stdout+result.stderr)


if __name__ == "__main__":
    unittest.main()
