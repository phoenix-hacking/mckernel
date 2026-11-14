"""Genuine offline BFD/tool regression using M15_DIAGNOSTIC_PROFILE.

The profile is shared with test_m15_diagnostic_dwarf. Compile actual current Rust
bodies, use actual selected BFD headers/archives, and bypass target main with
nonshipped C observers. No fake library objects/providers, devices or GDB.
"""
from pathlib import Path
import hashlib
import json
import os
import re
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]

ECLAIR_OBSERVER = r'''
/* Nonshipped ordinary BFD/dump consumer; never calls eclair main. */
#include "/usr/include/bfd.h"
#include <stdint.h>
#include <stddef.h>
#include <stdlib.h>
#include <stdio.h>
#include <string.h>
#include <ihk/ihk_host_user.h>
OPTIONS_DECL
extern struct options opt;
extern bfd *symbfd,*dumpbfd;
extern asymbol **symtab;
extern long nsyms;
extern dump_mem_chunks_t *mem_chunks;
extern unsigned long MAP_KERNEL_START;
extern int setup_symbols(char*),setup_dump(char*),read_mem(uintptr_t,void*,size_t);
extern uintptr_t lookup_symbol(char*);
static int make_dump(const char *path) {
    unsigned char first[16],second[8];
    for(unsigned k=0;k<sizeof(first);++k)first[k]=(unsigned char)(0xa0+k);
    for(unsigned k=0;k<sizeof(second);++k)second[k]=(unsigned char)(0xb0+k);
    dump_mem_chunks_t *chunks=calloc(1,sizeof(*chunks)+2*sizeof(chunks->chunks[0]));
    if(!chunks)return 1;
    chunks->nr_chunks=2;chunks->kernel_base=0;chunks->phys_start=0x1000;
    chunks->chunks[0]=(struct dump_mem_chunk){.addr=0x1000,.size=sizeof(first)};
    chunks->chunks[1]=(struct dump_mem_chunk){.addr=0x3000,.size=sizeof(second)};
    bfd *out=bfd_openw(path,"elf64-x86-64");int ok=0;
    if(!out)goto done;
    if(!bfd_set_format(out,bfd_object)||!bfd_set_arch_mach(out,bfd_arch_i386,bfd_mach_x86_64))goto close;
    asection *a=bfd_make_section_anyway_with_flags(out,"physchunks",SEC_HAS_CONTENTS);
    asection *b=bfd_make_section_anyway_with_flags(out,"physmem0",SEC_HAS_CONTENTS);
    asection *c=bfd_make_section_anyway_with_flags(out,"physmem1",SEC_HAS_CONTENTS);
    if(!a||!b||!c)goto close;
    size_t size=sizeof(*chunks)+2*sizeof(chunks->chunks[0]);
    if(!bfd_set_section_size(a,size)||!bfd_set_section_size(b,sizeof(first))||!bfd_set_section_size(c,sizeof(second)))goto close;
    if(!bfd_set_section_contents(out,a,chunks,0,size)||!bfd_set_section_contents(out,b,first,0,sizeof(first))||!bfd_set_section_contents(out,c,second,0,sizeof(second)))goto close;
    ok=1;
close:
    if(!bfd_close(out))ok=0;
done:
    free(chunks);return ok?0:1;
}
int __wrap_main(int argc,char **argv) {
    if(argc!=3)return 2;
    bfd_init();if(make_dump(argv[2]))return 3;
    opt.interactive=0;opt.mcos_fd=-1;opt.dump_path=argv[2];
    if(setup_symbols(argv[1]))return 4;
    uintptr_t actual=lookup_symbol("m15_fixture_global"),expected=(uintptr_t)-1;
    long upper=bfd_get_symtab_upper_bound(symbfd);asymbol **symbols=malloc((size_t)upper);
    if(upper<=0||!symbols)return 5;
    long count=bfd_canonicalize_symtab(symbfd,symbols);
    for(long k=0;k<count;++k)if(!strcmp(bfd_asymbol_name(symbols[k]),"m15_fixture_global"))expected=bfd_asymbol_value(symbols[k]);
    free(symbols);
    fprintf(stderr,"symbol actual=%lu reference=%lu missing=%lu\n",(unsigned long)actual,(unsigned long)expected,(unsigned long)lookup_symbol("m15_missing_symbol"));
    if(expected==(uintptr_t)-1||actual!=expected||lookup_symbol("m15_missing_symbol")!=(uintptr_t)-1)return 6;
    if(setup_dump(argv[2]))return 7;
    MAP_KERNEL_START=0xffffffff81000000UL;
    const uintptr_t base=0xffff800000000000UL;
    unsigned char got[16];memset(got,0,sizeof(got));
    if(read_mem(base+0x1000,got,16))return 8;
    for(unsigned k=0;k<16;++k)if(got[k]!=(unsigned char)(0xa0+k))return 9;
    if(read_mem(base+0x100f,got,1)||got[0]!=0xaf)return 10;
    if(read_mem(base+0x3000,got,8))return 11;
    for(unsigned k=0;k<8;++k)if(got[k]!=(unsigned char)(0xb0+k))return 12;
    if(read_mem(base+0x2000,got,1)!=1||read_mem(0x10,got,1)!=1)return 13;
    free(symtab);symtab=NULL;nsyms=0;int sym_closed=bfd_close(symbfd);symbfd=NULL;
    free(mem_chunks);mem_chunks=NULL;int dump_closed=bfd_close(dumpbfd);dumpbfd=NULL;
    printf("{\"success\":true,\"symbol_address\":%lu,\"reference_address\":%lu,\"chunks\":2,\"whole_chunk_read\":16,\"exact_end_read\":1,\"second_chunk_read\":8,\"unmapped_results\":[1,1],\"sym_close\":%s,\"dump_close\":%s}\n",(unsigned long)actual,(unsigned long)expected,sym_closed?"true":"false",dump_closed?"true":"false");
    return !sym_closed||!dump_closed;
}
'''
MCINSPECT_OBSERVER = r'''
#include "/usr/include/bfd.h"
#include <stdio.h>
#include <stdint.h>
#include <stdlib.h>
#include <string.h>
extern bfd *symbfd;
extern asymbol **symtab;
extern long nsyms;
extern int init_bfd_symbols(char *);
extern uintptr_t lookup_bfd_symbol(char *);
int __wrap_main(int argc,char **argv) {
    if(argc!=2)return 2;
    bfd_init();if(init_bfd_symbols(argv[1]))return 3;
    const char *names[2]={"m15_fixture_global","main"};
    uintptr_t actual[2],expected[2]={(uintptr_t)-1,(uintptr_t)-1};
    for(int j=0;j<2;++j) {
        actual[j]=lookup_bfd_symbol((char *)names[j]);
        for(long k=0;k<nsyms;++k)if(!strcmp(bfd_asymbol_name(symtab[k]),names[j]))expected[j]=bfd_asymbol_value(symtab[k]);
        if(expected[j]==(uintptr_t)-1||actual[j]!=expected[j])return 4;
    }
    if(lookup_bfd_symbol("m15_missing_symbol")!=(uintptr_t)-1)return 5;
    free(symtab);symtab=NULL;nsyms=0;int closed=bfd_close(symbfd);symbfd=NULL;
    printf("{\"success\":true,\"actual\":[%lu,%lu],\"reference\":[%lu,%lu],\"missing_sentinel\":true,\"close\":%s}\n",(unsigned long)actual[0],(unsigned long)actual[1],(unsigned long)expected[0],(unsigned long)expected[1],closed?"true":"false");
    return !closed;
}
'''
FIXTURE = "struct m15_fixture { unsigned char marker; unsigned long word; unsigned short tail; };\nstruct m15_fixture m15_fixture_global={3,123,9};\nint main(void){return m15_fixture_global.marker;}\n".replace("\\n", "\n")


class RealBfdDiagnosticTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        name = os.environ.get("M15_DIAGNOSTIC_PROFILE")
        if not name:
            raise unittest.SkipTest("set M15_DIAGNOSTIC_PROFILE for genuine HOST BFD/libdwarf inputs")
        cls.profile = json.loads(Path(name).read_text())
        p = cls.profile
        cls.base = p["namespace_argv"]
        cls.work = Path(tempfile.mkdtemp(prefix="m15-diagnostic-bfd-", dir=p["work_root"]))
        cls.commands = []
        cls.cc = ["/usr/bin/cc", "-B/usr/lib/x86_64-linux-gnu/", "-isystem", "/usr/include/x86_64-linux-gnu"]
        pins = {"/usr/include/bfd.h":"de900a9fe4ac94543ee1382cebc3063c3d7e20d16bc934fc816133dd55fe2432",
                "/usr/lib64/libbfd.so":"6cfd31804974c248c9512879e7b77a94862f92150c2171d901140464ea936ab3",
                "/usr/lib64/libbfd.a":"2324c3f9557b3387126123659badf4cccdbbd272104aec42a21c709c31bf6d4e",
                "/usr/bin/cc":"2092e32fa9abee9ccbf777a5f893b9cc608582b660c93e742a17c3eb7da109c2"}
        check = "import hashlib,json; pins=" + repr(pins) + "; got={p:hashlib.sha256(open(p,'rb').read()).hexdigest() for p in pins}; assert got==pins,(got,pins); print(json.dumps(got))"
        cls.command("production-pins", ["/usr/bin/python3", "-c", check])
        cls.command("typed-layout", cls.cc + ["-std=gnu11", str(ROOT / "executer/user/cmake/bfd_layout_witness.c"),
                    "/usr/lib64/libbfd.so", "-o", str(cls.work / "typed-layout")])
        cls.command("typed-layout-run", [str(cls.work / "typed-layout")])
        (cls.work / "fixture.c").write_text(FIXTURE)
        cls.command("fixture", cls.cc + ["-g", "-O0", str(cls.work / "fixture.c"), "-o", str(cls.work / "fixture")])
        common = [p["rustc"], "--crate-type", "lib", "--edition=2021", "-C", "panic=abort", "-C", "opt-level=2",
                  "-C", "debuginfo=1", "-C", "force-unwind-tables=no"]
        for tool in ("eclair", "mcinspect"):
            cls.command(tool + "-compile", common + ["--crate-name", tool + "_helpers", "--cfg", tool + "_full_body",
                        "--emit=obj=" + str(cls.work / (tool + ".o")), str(ROOT / ("executer/user/rust/" + tool + "_helpers.rs"))])
        cls.command("arch-compile", common + ["--crate-name", "arch_eclair_x86_64",
                    "--emit=obj=" + str(cls.work / "arch.o"), str(ROOT / "executer/user/rust/arch_eclair_x86_64.rs")])
        declaration = re.search(r"struct options \{.*?\}; /\* struct options \*/",
                                (ROOT / "executer/user/eclair.c").read_text(), re.S).group()
        (cls.work / "eclair-observer.c").write_text(ECLAIR_OBSERVER.replace("OPTIONS_DECL", declaration))
        (cls.work / "mcinspect-observer.c").write_text(MCINSPECT_OBSERVER)
        for tool in ("eclair", "mcinspect"):
            objects = [str(cls.work / (tool + ".o")), p["bfd_accessors"]]
            libraries = []
            if tool == "eclair":
                objects += [str(cls.work / "arch.o")]
            else:
                libraries += [str(Path(p["dwarf_build"]) / "libdwarf.a"), "-lz",
                              "-L" + str(Path(p["elf_prefix"]) / "usr/lib/x86_64-linux-gnu"), "-lelf"]
            cls.command(tool + "-link", cls.cc + ["-Wall", "-Wextra", "-Werror", "-O2",
                        "-I" + str(ROOT / "ihk/linux/include"), str(cls.work / (tool + "-observer.c"))] + objects + libraries +
                        ["/usr/lib64/libbfd.so", "-Wl,--wrap=main", "-Wl,--trace", "-Wl,-Map=" + str(cls.work / (tool + ".map")),
                         "-o", str(cls.work / tool)])
        paths = [ROOT / "executer/user/rust/eclair_helpers.rs", ROOT / "executer/user/rust/mcinspect_helpers.rs",
                 ROOT / "executer/user/rust/arch_eclair_x86_64.rs", ROOT / "executer/user/cmake/bfd_layout_witness.c"]
        (cls.work / "source-identities.json").write_text(json.dumps({"scope":"Genuine ordinary ELF/BFD-written dump HOST consumer; target main bypassed; no device/debugger",
            "source_sha256": {str(path):hashlib.sha256(path.read_bytes()).hexdigest() for path in paths}}, indent=2))
        print("Real BFD diagnostic artifacts:", cls.work)

    @classmethod
    def command(cls, label, args):
        result = subprocess.run(cls.base + args, capture_output=True, timeout=90)
        for channel in ("stdout", "stderr"):
            (cls.work / (label + "." + channel)).write_bytes(getattr(result, channel))
        cls.commands.append({"label":label,"argv":cls.base + args,"returncode":result.returncode,
            "stdout_sha256":hashlib.sha256(result.stdout).hexdigest(),"stderr_sha256":hashlib.sha256(result.stderr).hexdigest()})
        (cls.work / "commands.json").write_text(json.dumps(cls.commands, indent=2))
        if result.returncode:
            raise AssertionError(label + " failed: " + result.stdout.decode(errors="replace")[-3000:] + result.stderr.decode(errors="replace")[-3000:])
        return result

    def test_actual_mcinspect_symbol_addresses(self):
        result = self.command("mcinspect-consumer", [str(self.work / "mcinspect"), str(self.work / "fixture")])
        observed = json.loads(result.stdout)
        self.assertTrue(observed["success"] and observed["missing_sentinel"] and observed["close"])
        self.assertEqual(observed["actual"], observed["reference"])

    def test_actual_eclair_symbols_and_offline_dump_reads(self):
        result = self.command("eclair-consumer", [str(self.work / "eclair"), str(self.work / "fixture"), str(self.work / "ordinary-dump.elf")])
        observed = json.loads(result.stdout.splitlines()[-1])
        self.assertTrue(observed["success"] and observed["sym_close"] and observed["dump_close"])
        self.assertEqual(observed["symbol_address"], observed["reference_address"])
        self.assertEqual([observed["chunks"], observed["whole_chunk_read"], observed["exact_end_read"], observed["second_chunk_read"]], [2,16,1,8])
        self.assertEqual(observed["unmapped_results"], [1,1])


if __name__ == "__main__":
    unittest.main()
