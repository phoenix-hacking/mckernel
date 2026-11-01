"""Real offline DWARF regression; requires an explicit genuine-provider profile.

M15_DIAGNOSTIC_PROFILE names JSON with namespace_argv, work_root, rustc,
dwarf_build, dwarf_source, elf_prefix and bfd_accessors. No synthetic Dwarf or
BFD provider is used. The full current sources are compiled; only main is
redirected to an observer, and thin Rust observer entries expose private queries.
No McKernel device, daemon, debugger or target main is invoked.
"""
from pathlib import Path
import hashlib
import json
import os
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
RUST_SUFFIX = r"""
// NONSHIPPED: expose unchanged private queries to the real-library observer.
#[no_mangle]
pub unsafe extern "C" fn diagnostic_size(dbg:*mut c_void,name:*const u8,out:*mut usize)->c_int {
    let mut arg=DwarfSizeArg{name,sizep:out};
    unsafe {dwarf_walk_tree_internal(dbg,dwarf_size_cb,(&mut arg as *mut DwarfSizeArg).cast())}
}
#[no_mangle]
pub unsafe extern "C" fn diagnostic_offset(dbg:*mut c_void,name:*const u8,field:*const u8,out:*mut usize)->c_int {
    let mut arg=DwarfStructFieldOffsetArg{struct_name:name,field_name:field,offp:out};
    unsafe {dwarf_walk_tree_internal(dbg,dwarf_struct_field_offset_cb,(&mut arg as *mut DwarfStructFieldOffsetArg).cast())}
}
"""
FIXTURE = r"""
struct m15_fixture { unsigned char marker; unsigned long word; unsigned short tail; };
struct m15_fixture m15_fixture_global = {3, 123, 9};
int main(void) { return m15_fixture_global.marker; }
"""
SECOND_CU = r"""
struct m15_other { int tag; unsigned long value; };
struct m15_other m15_other_global = {7, 99};
"""
C_SUFFIX = r"""
int diagnostic_size(Dwarf_Debug dbg, const char *name, size_t *out) {
    struct dwarf_size_arg arg = {.name=(char *)name,.sizep=out};
    return dwarf_walk_tree(dbg,dwarf_size,&arg);
}
int diagnostic_offset(Dwarf_Debug dbg, const char *name, const char *field, size_t *out) {
    struct dwarf_struct_field_offset_arg arg = {
        .struct_name=(char *)name,.field_name=(char *)field,.offp=out};
    return dwarf_walk_tree(dbg,dwarf_struct_field_offset,&arg);
}
int mcinspect_dwarf_init_read_bridge(int fd,Dwarf_Debug *dbg,Dwarf_Error *err) {
    return dwarf_init(fd,DW_DLC_READ,NULL,NULL,dbg,err)==DW_DLV_OK ? 0 : -1;
}
int mcinspect_dwarf_finish_bridge(Dwarf_Debug dbg,Dwarf_Error *err) {
    return dwarf_finish(dbg,err);
}
"""
OBSERVER = r"""
#include <stdio.h>
#include <stddef.h>
#include <fcntl.h>
#include <unistd.h>
#include <libdwarf.h>
struct m15_fixture { unsigned char marker; unsigned long word; unsigned short tail; };
struct m15_other { int tag; unsigned long value; };
extern int mcinspect_dwarf_init_read_bridge(int,Dwarf_Debug*,Dwarf_Error*);
extern int mcinspect_dwarf_finish_bridge(Dwarf_Debug,Dwarf_Error*);
extern int diagnostic_size(Dwarf_Debug,const char*,size_t*);
extern int diagnostic_offset(Dwarf_Debug,const char*,const char*,size_t*);
int __wrap_main(int argc,char **argv) {
    if(argc!=2) return 2;
    int fd=open(argv[1],O_RDONLY); if(fd<0) return 3;
    Dwarf_Debug dbg=NULL; Dwarf_Error err=NULL;
    if(mcinspect_dwarf_init_read_bridge(fd,&dbg,&err)) {close(fd);return 4;}
    int rc[8]; size_t v[8]={0};
    const size_t expected[8]={sizeof(struct m15_fixture),offsetof(struct m15_fixture,word),
        sizeof(struct m15_other),offsetof(struct m15_other,value),
        offsetof(struct m15_fixture,tail),sizeof(struct m15_fixture),0,
        offsetof(struct m15_fixture,word)};
    rc[0]=diagnostic_size(dbg,"m15_fixture",v);
    rc[1]=diagnostic_offset(dbg,"m15_fixture","word",v+1);
    rc[2]=diagnostic_size(dbg,"m15_other",v+2);
    rc[3]=diagnostic_offset(dbg,"m15_other","value",v+3);
    rc[4]=diagnostic_offset(dbg,"m15_fixture","tail",v+4);
    rc[5]=diagnostic_size(dbg,"m15_fixture",v+5);
    rc[6]=diagnostic_size(dbg,"m15_missing_type",v+6);
    rc[7]=diagnostic_offset(dbg,"m15_fixture","word",v+7);
    int finish=mcinspect_dwarf_finish_bridge(dbg,&err),closed=close(fd),failed=0;
    printf("{\"returncodes\":[");
    for(int k=0;k<8;++k) {printf("%s%d",k?",":"",rc[k]);
        if(rc[k]!=(k==6?-1:0)||v[k]!=expected[k]) failed=1;}
    printf("],\"values\":[");
    for(int k=0;k<8;++k) printf("%s%zu",k?",":"",v[k]);
    printf("],\"finish\":%d,\"close\":%d}\n",finish,closed);
    return failed||finish||closed;
}
"""


class RealDwarfDiagnosticTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        profile = os.environ.get("M15_DIAGNOSTIC_PROFILE")
        if not profile:
            raise unittest.SkipTest("set M15_DIAGNOSTIC_PROFILE for genuine HOST BFD/libdwarf inputs")
        cls.profile = json.loads(Path(profile).read_text())
        selected = cls.profile
        cls.base = selected["namespace_argv"]
        cls.work = Path(tempfile.mkdtemp(prefix="m15-diagnostic-dwarf-", dir=selected["work_root"]))
        cls.commands = []
        cls.dwarf_build = Path(selected["dwarf_build"])
        cls.cc = ["/usr/bin/cc", "-B/usr/lib/x86_64-linux-gnu/",
                  "-isystem", "/usr/include/x86_64-linux-gnu"]
        cls.link = [selected["bfd_accessors"], str(cls.dwarf_build / "libdwarf.a"),
                    "-lz", "-L" + str(Path(selected["elf_prefix"]) / "usr/lib/x86_64-linux-gnu"),
                    "-lelf", "/usr/lib64/libbfd.so", "-Wl,--wrap=main"]
        for name, data in [("fixture.c", FIXTURE), ("other.c", SECOND_CU), ("observer.c", OBSERVER)]:
            (cls.work / name).write_text(data)
        cls.command("fixture", cls.cc + ["-gdwarf-4", "-g", "-O0", str(cls.work / "fixture.c"),
                    str(cls.work / "other.c"), "-o", str(cls.work / "fixture")])
        source = (ROOT / "executer/user/rust/mcinspect_helpers.rs").read_bytes()
        (cls.work / "mcinspect-observed.rs").write_bytes(source + RUST_SUFFIX.encode())
        cls.command("rust", [selected["rustc"], "--crate-name", "mcinspect_helpers", "--crate-type", "lib",
                    "--edition=2021", "-C", "panic=abort", "-C", "opt-level=2", "-C", "debuginfo=1",
                    "-C", "force-unwind-tables=no", "--cfg", "mcinspect_full_body",
                    "--emit=obj=" + str(cls.work / "rust.o"), str(cls.work / "mcinspect-observed.rs")])
        shim = cls.work / "include/libdwarf"
        shim.mkdir(parents=True)
        (shim / "libdwarf.h").symlink_to(cls.dwarf_build / "libdwarf.h")
        csource = '#define main retained_mcinspect_main\n#include "' + str(ROOT / "executer/user/mcinspect.c") + '"\n#undef main\n'
        (cls.work / "mcinspect-observed.c").write_text(csource + C_SUFFIX)
        include = ["-I" + str(cls.dwarf_build), "-I" + str(cls.work / "include"),
                   "-I" + str(Path(selected["dwarf_source"]) / "libdwarf")]
        cls.command("retained-c", cls.cc + include + ["-g", "-O2", "-c", str(cls.work / "mcinspect-observed.c"),
                    "-o", str(cls.work / "c.o")])
        for language in ("rust", "c"):
            cls.command(language + "-link", cls.cc + include + [str(cls.work / "observer.c"),
                        str(cls.work / (language + ".o"))] + cls.link + ["-Wl,--trace",
                        "-Wl,-Map=" + str(cls.work / (language + ".map")), "-o", str(cls.work / language)])
        (cls.work / "source-identities.json").write_text(json.dumps({
            "scope": "Genuine DWARF4 offline HOST consumer; no device/debugger/target main execution",
            "sources": {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in (
                ROOT / "executer/user/rust/mcinspect_helpers.rs", ROOT / "executer/user/mcinspect.c")},
            "rust_source_prefix_bytes": len(source),
            "rust_source_prefix_verified": (cls.work / "mcinspect-observed.rs").read_bytes()[:len(source)] == source,
            "private_observer_entries_only": ["diagnostic_size", "diagnostic_offset"],
            "fixture": "Two ordinary compilation units; compiler sizeof/offsetof are the oracle",
        }, indent=2))
        print("Real diagnostic artifacts:", cls.work)

    @classmethod
    def command(cls, label, args):
        result = subprocess.run(cls.base + args, capture_output=True, timeout=90)
        for channel in ("stdout", "stderr"):
            (cls.work / (label + "." + channel)).write_bytes(getattr(result, channel))
        cls.commands.append({"label": label, "argv": cls.base + args, "returncode": result.returncode,
            "stdout_sha256": hashlib.sha256(result.stdout).hexdigest(),
            "stderr_sha256": hashlib.sha256(result.stderr).hexdigest()})
        (cls.work / "commands.json").write_text(json.dumps(cls.commands, indent=2))
        if result.returncode:
            raise AssertionError(label + " failed: " + result.stdout.decode(errors="replace")[-3000:] +
                                 result.stderr.decode(errors="replace")[-3000:])
        return result

    def test_current_rust_restarts_independent_real_dwarf_queries(self):
        result = self.command("rust-consumer", [str(self.work / "rust"), str(self.work / "fixture")])
        observed = json.loads(result.stdout)
        self.assertEqual(observed["returncodes"], [0, 0, 0, 0, 0, 0, -1, 0])
        self.assertEqual(observed["values"], [24, 8, 16, 8, 16, 24, 0, 8])

    def test_retained_c_restarts_independent_real_dwarf_queries(self):
        result = self.command("c-consumer", [str(self.work / "c"), str(self.work / "fixture")])
        observed = json.loads(result.stdout)
        self.assertEqual(observed["returncodes"], [0, 0, 0, 0, 0, 0, -1, 0])
        self.assertEqual(observed["values"], [24, 8, 16, 8, 16, 24, 0, 8])


if __name__ == "__main__":
    unittest.main()
