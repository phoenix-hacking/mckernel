#!/usr/bin/env python3
"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Source materialization only: no compiler, workload, canonical write or admission.
"""
import difflib
import hashlib
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent
ROOT=Path('/home/holden/mckernel')
SCOPE='Functional McKernel OS/apps and Rust/assembly migration only; no security testing.'

def ref(path):
    raw=path.read_bytes()
    return dict(path=str(path),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())

def function(text,marker):
    start=text.index(marker)
    opening=text.index('{',start)
    depth=1
    end=opening+1
    while depth:
        depth+=(text[end]=='{')-(text[end]=='}')
        end+=1
    return start,end,text[start:end]+'\n'

def main():
    cpath=ROOT/'kernel/syscall.c'; rpath=ROOT/'kernel/rust/syscall_policy.rs'
    c=cpath.read_text(); rust=rpath.read_text()
    start,end,original=function(c,'static long\nperf_mmap(')
    assert c.count('static long\nperf_mmap(')==1
    assert 'f03_perf_mmap_v1' not in rust
    # Last unconditional #line before this body is20792 at physical20988.
    # There are no subsequent #line directives until after the callback.
    prefix=c[:start]; last=prefix.rfind('\n#line ')+1
    directive=c[last:c.index('\n',last)]
    logical=int(directive.split()[1])+prefix[last:].count('\n')-1
    assert directive=='#line 20792'
    binding=(HERE/'perf-mmap-binding.C.inc').read_text()
    paired=('#ifdef MCKERNEL_RUST_SYSCALL_POLICY_HELPERS\n'+binding+
            '#else\n#line '+str(logical)+'\n'+original+
            '#endif\n#line '+str(logical+original.count('\n')-1)+'\n')
    post=c[:start]+paired+c[end:]
    fragment=(HERE/'perf-mmap-entry.Rust.inc').read_text()
    postrust=rust+'\n'+fragment
    (HERE/'perf-mmap-original.C.inc').write_text(original)
    (HERE/'perf-mmap-paired.C.inc').write_text(paired)
    for name,before,after in [('kernel/syscall.c',c,post),('kernel/rust/syscall_policy.rs',rust,postrust)]:
        (HERE/(Path(name).name+'.patch')).write_text(''.join(difflib.unified_diff(before.splitlines(True),after.splitlines(True),fromfile='a/'+name,tofile='b/'+name)))
    (HERE/'abi.current.rs').write_bytes((ROOT/'kernel/rust/abi.rs').read_bytes())
    cpu=(ROOT/'kernel/rust/x86_cpu_helpers.rs').read_text()
    _,_,reader=function(cpu,'#[inline(always)]\nunsafe fn x86_syscall_read(')
    getters='\n'.join(function(cpu,'#[no_mangle]\npub unsafe extern "C" fn ihk_mc_syscall_arg'+str(i)+'(')[2] for i in range(6))
    (HERE/'syscall-getters.current.Rust.inc').write_text(reader+'\n'+getters)
    _,_,body=function(rust,'#[no_mangle]\npub unsafe extern "C" fn perf_mmap_body_result(')
    (HERE/'perf-mmap-body.current.Rust.inc').write_text(body)
    fixture='''#![no_std]
// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
#[path="abi.current.rs"] mod abi;
mod x86_cpu_helpers {
    use crate::abi::{CInt,CULong,X86UserContext};
    use core::ptr::read_volatile;
    include!("syscall-getters.current.Rust.inc");
}
mod policy {
    use crate::abi::{CInt,CLong,CULong,SizeT};
    use core::ffi::c_void;
    use core::ptr::{read_volatile,write_volatile};
    const EINVAL:CInt=22;
    type PerfDoMmapFn=unsafe extern "C" fn(CULong,SizeT,CInt,CInt,CInt,CLong,CInt,*mut c_void)->CLong;
    unsafe fn field_ptr<T>(base:*mut u8,offset:SizeT)->*mut T { unsafe { base.add(offset).cast() } }
    include!("perf-mmap-body.current.Rust.inc");
    include!("perf-mmap-entry.Rust.inc");
}
'''
    # Same-module access is required to witness the actual private binding type.
    witness='''
    #[no_mangle]
    pub static F03_PERF_MMAP_ABI:[CULong;18]=[
        core::mem::size_of::<X86UserContext>() as _,core::mem::align_of::<X86UserContext>() as _,
        core::mem::offset_of!(X86UserContext,gpr.rdi) as _,core::mem::offset_of!(X86UserContext,gpr.rsi) as _,
        core::mem::offset_of!(X86UserContext,gpr.rdx) as _,core::mem::offset_of!(X86UserContext,gpr.r10) as _,
        core::mem::offset_of!(X86UserContext,gpr.r8) as _,core::mem::offset_of!(X86UserContext,gpr.r9) as _,
        core::mem::size_of::<MmapBinding>() as _,core::mem::align_of::<MmapBinding>() as _,
        core::mem::offset_of!(MmapBinding,map_anonymous) as _,core::mem::offset_of!(MmapBinding,prot_write) as _,
        core::mem::offset_of!(MmapBinding,data_head) as _,core::mem::offset_of!(MmapBinding,capabilities) as _,
        core::mem::offset_of!(MmapBinding,cap_user_rdpmc) as _,core::mem::offset_of!(MmapBinding,do_mmap) as _,
        core::mem::size_of::<PerfDoMmapFn>() as _,
        core::mem::size_of::<unsafe extern "C" fn(*mut Mckfd,*mut X86UserContext)->CLong>() as _,
    ];
'''
    (HERE/'perf-mmap-entry.fixture.Rust.inc').write_text(fragment.rstrip()[:-1]+witness+'}\n')
    fixture=fixture.replace('include!("perf-mmap-entry.Rust.inc")','include!("perf-mmap-entry.fixture.Rust.inc")')
    (HERE/'lib.fixture.rs').write_text(fixture)
    old=json.loads((HERE.parent/'m14-f03-selected-residual-implementation-20261026-1/next-perf-attribute-callbacks-1/SOURCE-HANDOFF.NOT-GRANTED.json').read_text())
    commands=old['commands']
    commands[0]['label']='00-current-body-and-new-entry-Rust-object'
    commands[0]['argv']=[x.replace('f03_perf_attr_callbacks','f03_perf_mmap_entry').replace(str(Path(commands[0]['argv'][-1]).parent),str(HERE)) for x in commands[0]['argv']]
    commands[0]['argv'][1:1]=['--cfg','enable_perf']
    oldbase=str(HERE.parent/'m14-f03-selected-residual-implementation-20261026-1/next-perf-attribute-callbacks-1')
    for i in [1,2]:commands[i]['argv']=[x.replace(oldbase,str(HERE)) for x in commands[i]['argv']]
    commands[1]['label']='01-genuine-header-C-reference-link';commands[2]['label']='02-perf-mmap-parity'
    for row in commands:row['purpose']=SCOPE+' HOST ordinary mocked mapping only; no actual mapping, PMU, syscall, Docker, root, or guest operation.'
    plan=dict(scope=SCOPE,status='SOURCE_ONLY_NOT_GRANTED',commands=commands,requires='Root fresh ordinary grant and owned disjoint output directory; inherited historical argv is a source recipe only',expected_stdout='PASS perf-mmap actual-context ABI18; 160 C/Rust pairs; 320 exact-call/context/full-page/canary oracles',limits=dict(jobs=1,CPU=6,AS_bytes=2<<30,CPU_seconds=60,wall_seconds=90),executed=False)
    (HERE/'FUTURE-HOST-COMMAND-PLAN.NOT-GRANTED.json').write_text(json.dumps(plan,indent=2)+'\n')
    inputs=[cpath,rpath,ROOT/'kernel/rust/abi.rs',ROOT/'kernel/rust/x86_cpu_helpers.rs',ROOT/'lib/include/mc_perf_event.h']
    report=dict(scope=SCOPE,status='PRIVATE_SOURCE_READY_NOT_COMPILED',preimages=[ref(p) for p in inputs],target='perf_mmap',selected_current115_C_bytes=196,prior_body_reused='perf_mmap_body_result exact current Rust',logical_fallback_start=logical,predicted_removed_C_functions=1,actual_new_builds=0,actual_native_runs=0,whole_file_retirement=False,canonical_writes=0,deadline='2026-10-29T06:00:00Z',credit_run='7f4af94a83b14cc08f97401f5891d965',ceiling=57774.852125)
    report['files']=[ref(p) for p in sorted(HERE.iterdir()) if p.is_file() and p.name!='SOURCE-READY.json']
    (HERE/'SOURCE-READY.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(dict(status=report['status'],source_ready=ref(HERE/'SOURCE-READY.json'))))

if __name__=='__main__':main()
