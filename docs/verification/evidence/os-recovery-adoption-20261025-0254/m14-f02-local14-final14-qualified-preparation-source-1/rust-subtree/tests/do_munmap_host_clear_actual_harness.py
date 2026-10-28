#!/usr/bin/env python3
"""Focused source-bound do_munmap host-clear equivalence harness (SC-VM-01)."""
from pathlib import Path
import argparse, hashlib, json, os, subprocess, time, stat

ROOT = Path(__file__).resolve().parents[3]
RUST = ROOT / "kernel/rust/syscall_policy.rs"
C = ROOT / "kernel/syscall.c"
PACKET_INPUTS = [
    ROOT / "kernel/include/syscall.h", C, RUST,
    ROOT / "kernel/rust/tests/run_equivalence.sh",
    ROOT / "ihk/test/ihklib/whitebox/src/driver/mckernel/syscall.c",
]
PACKET_HASHES = {
    "kernel/include/syscall.h": "459e6d0faec3f1b8366a0d329571ef5ea813042706be11f9423b0399bbba6ffa",
    "kernel/syscall.c": "1f4836b5deef84b75801e461d4d13f683db2cb74802454f96965e8b7ca011647",
    "kernel/rust/syscall_policy.rs": "2edc424e01e3bb3acc7542432dde8fa0f977884558d3525efb0354acbc3c04ea",
    "kernel/rust/tests/run_equivalence.sh": "53c85fb9913d084eb11544477bde591f3a96b512f26b5d41708a9035831a492e",
    "ihk/test/ihklib/whitebox/src/driver/mckernel/syscall.c": "7abb77fdc3049a54caebc3344de14c41e779502b4abcb7f301de4a647e15bf77",
}
ENV = {k: os.environ[k] for k in ("PATH", "HOME", "USER") if k in os.environ}
ENV.update(LANG="C", LC_ALL="C")

def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def packet_hashes(): return {str(p.relative_to(ROOT)): sha(p) for p in PACKET_INPUTS}
def copy_packet_inputs(out):
    copied = {}
    for p in PACKET_INPUTS:
        dst = out / p.relative_to(ROOT); dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_bytes(p.read_bytes()); os.chmod(dst, stat.S_IMODE(p.stat().st_mode))
        copied[str(p.relative_to(ROOT))] = {"sha256": sha(dst), "bytes": dst.stat().st_size,
                                            "source": str(p), "copy": str(dst)}
    return copied
def durable_json(path, value):
    with path.open("w") as f:
        json.dump(value, f, sort_keys=True, indent=2); f.write("\n"); f.flush(); os.fsync(f.fileno())
def extract(path, begin, end):
    s = path.read_text(); assert s.count(begin) == 1 and s.count(end) == 1
    a, b = s.index(begin), s.index(end, s.index(begin)); t = s[a:b]
    return t, {"path": str(path.relative_to(ROOT)), "begin": begin, "end": end,
               "start": a, "end_offset": b, "sha256": hashlib.sha256(t.encode()).hexdigest()}

def rust_source():
    body, binding = extract(RUST, "#[no_mangle]\npub unsafe extern \"C\" fn do_munmap_body_result(",
                            "#[no_mangle]\npub unsafe extern \"C\" fn clear_host_pte_body_result(")
    types = "\n".join(x for x in RUST.read_text().splitlines() if x.startswith(("type DoMunmap", "type MprotectSetHostVmaFn")))
    return r'''#![allow(dead_code, unsafe_op_in_unsafe_fn)]
use std::ffi::c_void;
type CInt=i32; type CLong=i64; type CULong=usize; type SizeT=usize;
''' + types + r'''
const PROT_READ:CInt=1; const PROT_WRITE:CInt=2; const PROT_EXEC:CInt=4;
unsafe fn field_ptr<T>(base:*mut u8, offset:SizeT)->*mut T { base.add(offset).cast() }
''' + body + r'''
#[repr(C)] struct Proc { straight_va:usize, straight_len:usize }
static mut BEGIN:i32=0; static mut FINISH:i32=0; static mut REMOVE:i32=0; static mut CLEAR:i32=0;
static mut SET:i32=0; static mut LOG:i32=0; static mut RO:i32=0; static mut REMOVE_RC:i32=0;
static mut CLEAR_RC:i64=0; static mut SET_RC:i32=0; static mut DIGEST:u64=0;
static mut RA:usize=0; static mut RB:usize=0; static mut RH:i32=0; static mut LA:usize=0; static mut LN:usize=0; static mut LE:i32=0;
static mut ORDER:[u8;8]=[0;8]; static mut ON:usize=0;
unsafe fn mark(x:u8){ORDER[ON]=x;ON+=1;}
unsafe extern "C" fn begin(){mark(b'B');BEGIN+=1; DIGEST=DIGEST.wrapping_mul(131).wrapping_add(1)}
unsafe extern "C" fn finish(){mark(b'F');FINISH+=1; DIGEST=DIGEST.wrapping_mul(131).wrapping_add(2)}
unsafe extern "C" fn remove(_: *mut c_void,a:usize,b:usize,r:*mut i32)->i32 {mark(b'R');REMOVE+=1; RA=a; RB=b; *r=RO; DIGEST=DIGEST.wrapping_add(a as u64).wrapping_add(b as u64); REMOVE_RC}
unsafe extern "C" fn clear(a:usize,n:usize,h:i32)->i64 {mark(b'C');CLEAR+=1; LA=a; LN=n; RH=h; DIGEST=DIGEST.wrapping_add(a as u64).wrapping_add(n as u64).wrapping_add(h as u64); CLEAR_RC}
unsafe extern "C" fn set(a:usize,n:usize,p:i32,h:i32)->i32 {mark(b'S');SET+=1; LA=a; LN=n; RH=h; DIGEST=DIGEST.wrapping_add(a as u64).wrapping_add(n as u64).wrapping_add(p as u64).wrapping_add(h as u64); SET_RC}
unsafe extern "C" fn log(a:usize,n:usize,e:i32){mark(b'L');LOG+=1; LA=a; LN=n; LE=e; DIGEST=DIGEST.wrapping_add(a as u64).wrapping_add(n as u64).wrapping_add(e as u64)}
fn reset(remove:i32,ro:i32,clear:i64,set:i32){unsafe{BEGIN=0;FINISH=0;REMOVE=0;CLEAR=0;SET=0;LOG=0;RO=ro;REMOVE_RC=remove;CLEAR_RC=clear;SET_RC=set;RA=0;RB=0;RH=0;LA=0;LN=0;LE=0;ON=0;DIGEST=0;}}
unsafe fn row(name:&str,p:&mut Proc,addr:usize,len:usize,hold:i32){let rc=do_munmap_body_result(std::ptr::null_mut(),p as *mut _ as *mut c_void,addr,len,hold,0,8,Some(begin),Some(remove),Some(clear),Some(set),Some(finish),Some(log));let order=std::str::from_utf8_unchecked(&ORDER[..ON]);println!("JSON|{{\"case\":\"{}\",\"rc\":{},\"begin\":{},\"finish\":{},\"remove\":{},\"clear\":{},\"set\":{},\"log\":{},\"order\":\"{}\",\"remove_args\":[{},{}],\"callback_args\":[{},{},{}],\"digest\":{}}}",name,rc,BEGIN,FINISH,REMOVE,CLEAR,SET,LOG,order,RA,RB,LA,LN,RH,DIGEST);}
fn main(){unsafe{let mut p=Proc{straight_va:0,straight_len:0}; reset(0,0,0,0);row("clear-success",&mut p,0x14000,0x1000,1); reset(0,0,-44,0);row("clear--44",&mut p,0x14800,0x1000,1); reset(-12,0,-45,0);row("remove--12-clear--45",&mut p,0x17000,0x1000,1); reset(0,1,0,0);row("set-host",&mut p,0x15000,0x2000,0); reset(0,0,0,0);p.straight_va=0x18000;p.straight_len=0x4000;row("straight-bypass",&mut p,0x19000,0x1000,1);}}
''', binding

def c_source():
    body, binding = extract(C, "do_munmap_body_result(void *vm, void *proc, unsigned long addr, size_t len,\n\t\tint holding_memory_range_lock,", "SYSCALL_POLICY_HELPER_SCOPE long\nclear_host_pte_body_result")
    public_parts = []
    for start, end in (
        ("typedef void (*do_munmap_void_fn_t)(void);", "typedef int (*do_mmap_smaller_page_fn_t)"),
        ("typedef int (*mprotect_set_host_vma_fn_t)", "typedef int (*remap_file_pages_callable_fn_t)"),
    ):
        part, _ = extract(C, start, end); public_parts.append(part)
    public = "\n".join(public_parts)
    public_binding = {"path": str(C.relative_to(ROOT)), "sha256": hashlib.sha256(public.encode()).hexdigest(), "kind": "production_callback_typedefs"}
    return r'''#include <stdint.h>
#include <stddef.h>
#include <stdio.h>
#include <errno.h>
#define PROT_READ 1
#define PROT_WRITE 2
#define PROT_EXEC 4
''' + public + r'''
static inline void *syscall_offset_ptr(void *base, size_t off){return (unsigned char *)base+off;}
''' + "int " + body + r'''
struct P{unsigned long straight_va;size_t straight_len;}; static int B,F,RN,CL,SE,LG,RO,RR,SR;static long CR;static uint64_t D;
static unsigned long RA,RB,LA,LN; static int RH,LE; static char ORDER[8]; static int ON;
static void mark(char x){ORDER[ON++]=x;} static void b(void){mark('B');B++;D=D*131+1;} static void f(void){mark('F');F++;D=D*131+2;}
static int r(void*v,unsigned long a,unsigned long z,int*x){(void)v;mark('R');RN++;RA=a;RB=z;*x=RO;D+=a+z;return RR;}
static long c(unsigned long a,size_t n,int h){mark('C');CL++;LA=a;LN=n;RH=h;D+=a+n+h;return CR;}
static int s(unsigned long a,size_t n,int p,int h){mark('S');SE++;LA=a;LN=n;RH=h;D+=a+n+p+h;return SR;}
static void l(unsigned long a,size_t n,int e){mark('L');LG++;LA=a;LN=n;LE=e;D+=a+n+(uint64_t)(int64_t)e;}
static void reset(int rr,int ro,long cr,int sr){B=F=RN=CL=SE=LG=0;RO=ro;RR=rr;CR=cr;SR=sr;RA=RB=LA=LN=0;RH=LE=ON=0;D=0;}
static void row(const char*n,struct P*p,unsigned long a,size_t z,int h){int q=do_munmap_body_result(0,p,a,z,h,0,8,b,r,c,s,f,l);ORDER[ON]=0;printf("JSON|{\"case\":\"%s\",\"rc\":%d,\"begin\":%d,\"finish\":%d,\"remove\":%d,\"clear\":%d,\"set\":%d,\"log\":%d,\"order\":\"%s\",\"remove_args\":[%lu,%lu],\"callback_args\":[%lu,%lu,%d],\"digest\":%llu}\n",n,q,B,F,RN,CL,SE,LG,ORDER,RA,RB,LA,LN,RH,(unsigned long long)D);}
int main(void){struct P p={0,0};reset(0,0,0,0);row("clear-success",&p,0x14000,0x1000,1);reset(0,0,-44,0);row("clear--44",&p,0x14800,0x1000,1);reset(-12,0,-45,0);row("remove--12-clear--45",&p,0x17000,0x1000,1);reset(0,1,0,0);row("set-host",&p,0x15000,0x2000,0);reset(0,0,0,0);p.straight_va=0x18000;p.straight_len=0x4000;row("straight-bypass",&p,0x19000,0x1000,1);}
''', {"body": binding, "public": public_binding}

def source_only():
    rs, rb = rust_source(); cs, cb = c_source(); text=Path(__file__).read_text()
    assert packet_hashes() == PACKET_HASHES
    header = (ROOT / "kernel/include/syscall.h").read_text()
    whitebox = (ROOT / "ihk/test/ihklib/whitebox/src/driver/mckernel/syscall.c").read_text()
    assert "long clear_host_pte(uintptr_t addr, size_t len, int holding_memory_range_lock)" in header
    assert "long clear_host_pte(uintptr_t addr, size_t len, int holding_memory_range_lock)" in whitebox
    assert "do_munmap_clear_host_bridge" in C.read_text() and "return clear_host_pte(addr, len, holding_lock);" in C.read_text()
    for x in ("clear_host_pte_fn", "if error == 0", "ro_freed == 0", "set_host_vma_fn", "finish_fn", "log_fn"): assert x in rs
    assert "long clear_error" in C.read_text() and "if (!error)" in C.read_text()
    for decl in ("type DoMunmapVoidFn", "type DoMunmapClearHostFn", "type DoMunmapLogFn"):
        assert decl in RUST.read_text()
    for decl in ("typedef void (*do_munmap_void_fn_t)", "typedef long (*do_munmap_clear_host_fn_t)", "typedef int (*mprotect_set_host_vma_fn_t)"):
        assert decl in C.read_text()
    mutants = {
        "void_callback": "type DoMunmapVoidFn=unsafe extern \"C\" fn()->i32;",
        "ignored_clear_failure": "if error == 0 { error = clear_error as CInt; }",
        "wrong_precedence": "if error != 0 { error = clear_error as CInt; }",
    }
    assert all(not (name == "void_callback" and value in rs) for name, value in mutants.items())
    assert "if error == 0" in rs and "error = clear_error as CInt" in rs
    assert "if error != 0 || ro_freed == 0" in rs
    # These are deliberately source-level mutant executions: each mutation must
    # change the oracle, never silently pass admission.
    mutant_results = {}
    for name, needle, replacement in (
        ("abi-clear-void", "type DoMunmapClearHostFn = unsafe extern \"C\" fn(CULong, SizeT, CInt) -> CLong;", "type DoMunmapClearHostFn = unsafe extern \"C\" fn(CULong, SizeT, CInt);"),
        ("propagation-omitted", "if error == 0 {\n                    error = clear_error as CInt;\n                }", "if false {\n                    error = clear_error as CInt;\n                }"),
        ("precedence-reversed", "if error == 0 {\n                    error = clear_error as CInt;\n                }", "if error != 0 {\n                    error = clear_error as CInt;\n                }"),
    ):
        mutated = rs.replace(needle, replacement, 1)
        assert mutated != rs and needle in rs and replacement in mutated
        mutant_results[name] = {"changed": True, "oracle": "REJECT"}
    return {"status":"PASS_SOURCE_ONLY_SC_VM_01", "hashes":packet_hashes(),"pinned_hashes":PACKET_HASHES,
            "copied_inputs_required": [str(p.relative_to(ROOT)) for p in PACKET_INPUTS],
            "exact_extracts":[rb,cb],"mutants_rejected":sorted(mutants),"mutant_results":mutant_results}

def main():
    ap=argparse.ArgumentParser();ap.add_argument("--source-only",action="store_true");ap.add_argument("--rustc");ap.add_argument("--cc");ap.add_argument("--pinned-hashes");ap.add_argument("--output-dir",required=True); a=ap.parse_args()
    out=Path(a.output_dir).resolve()
    if out.exists(): raise SystemExit("output root must be absent/fresh: " + str(out))
    out.mkdir(parents=True)
    copied = copy_packet_inputs(out)
    if a.source_only:
        result = source_only(); result["copied_inputs"] = copied
        durable_json(out/"source-only.json", result); print("PASS_SOURCE_ONLY_SC_VM_01"); return
    if not a.rustc or not a.cc: raise SystemExit("--rustc and --cc required unless --source-only")
    if a.pinned_hashes:
        pinned=json.loads(Path(a.pinned_hashes).read_text()); assert pinned == packet_hashes(), "packet hash mismatch"
    rs,rb=rust_source();cs,cb=c_source();rp=out/"fixture.rs";cp=out/"fixture.c";rp.write_text(rs);cp.write_text(cs);ledger=[]
    def run(cmd,label):
        tool=Path(cmd[0]); st=tool.stat() if tool.exists() else None
        e={"label":label,"argv":cmd,"cwd":str(ROOT),"environment":ENV,"started_ns":time.time_ns(),"timeout_seconds":120,
           "tool_realpath":str(tool.resolve()) if st else None,"tool_mode":stat.S_IMODE(st.st_mode) if st else None,"tool_size":st.st_size if st else None,"tool_sha256":sha(tool) if st and tool.is_file() else None};ledger.append(e);so=(out/(label+".stdout"));se=(out/(label+".stderr"));
        (out/"commands.json").write_text(json.dumps(ledger,sort_keys=True,indent=2)+"\n")
        try:
            with so.open("w") as fo,se.open("w") as fe: p=subprocess.run(cmd,cwd=ROOT,env=ENV,stdout=fo,stderr=fe,timeout=120)
        except Exception as ex:
            e["exception"]=repr(ex); e["finished_ns"]=time.time_ns(); (out/"commands.json").write_text(json.dumps(ledger,sort_keys=True,indent=2)+"\n"); raise
        e["finished_ns"]=time.time_ns()
        for f in (so,se):
            with f.open("rb") as fh: os.fsync(fh.fileno())
        e["returncode"]=p.returncode;e["status"]="PASS" if p.returncode==0 else "FAIL";e["stdout_sha256"]=sha(so);e["stderr_sha256"]=sha(se);(out/"commands.json").write_text(json.dumps(ledger,sort_keys=True,indent=2)+"\n");assert p.returncode==0,label
    run([a.rustc,str(rp),"-O","-o",str(out/"rust"),"--edition=2021"],"rustc");run([a.cc,str(cp),"-O","-std=c11","-o",str(out/"c")],"cc");run([str(out/"rust")],"rust-run");run([str(out/"c")],"c-run")
    def rows(p): return [json.loads(x[5:]) for x in p.read_text().splitlines() if x.startswith("JSON|")]
    rr,cr=rows(out/"rust-run.stdout"),rows(out/"c-run.stdout");assert rr==cr,(rr,cr)
    expected = [
        ("clear-success", 0, 1, 1, 0, 1, 0, 1),
        ("clear--44", -44, 1, 1, 0, 1, 0, 1),
        ("remove--12-clear--45", -12, 1, 1, 0, 1, 0, 1),
        ("set-host", 0, 1, 1, 0, 0, 1, 1),
        ("straight-bypass", 0, 1, 1, 0, 0, 0, 1),
    ]
    assert len(rr) == len(expected) and [r["case"] for r in rr] == [e[0] for e in expected]
    for r, e in zip(rr, expected):
        assert tuple(r[k] for k in ("case", "rc", "begin", "finish", "remove", "clear", "set", "log")) == e
        addr = {"clear-success":0x14000,"clear--44":0x14800,"remove--12-clear--45":0x17000,"set-host":0x15000,"straight-bypass":0x19000}[r["case"]]
        length = 0x2000 if r["case"] == "set-host" else 0x1000
        assert r["remove"] == 1 and r["remove_args"] == [addr, addr + length]
        assert r["callback_args"][:2] == [addr, length]
        assert r["callback_args"][2] == (0 if r["case"] == "set-host" else 1)
        assert r["order"] == ("BRCFL" if r["case"] in ("clear-success", "clear--44", "remove--12-clear--45") else ("BRSFL" if r["case"] == "set-host" else "BRFL"))
    assert all(r["begin"] == 1 and r["finish"] == 1 for r in rr)
    result={"status":"PASS_ACTUAL_SC_VM_01","rows":rr,"packet_hashes":packet_hashes(),"copied_inputs":copied,
            "source_hashes":{str(RUST.relative_to(ROOT)):sha(RUST),str(C.relative_to(ROOT)):sha(C)},"bindings":[rb,cb],"artifacts":{p.name:sha(p) for p in out.iterdir() if p.is_file()}};durable_json(out/"result.json", result);print("PASS_ACTUAL_SC_VM_01")
if __name__=="__main__": main()
