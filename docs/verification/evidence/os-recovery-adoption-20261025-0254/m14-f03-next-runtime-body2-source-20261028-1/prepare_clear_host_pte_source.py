#!/usr/bin/env python3
"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Source preparation only; the held credential draft is never consumed.
"""
import difflib,hashlib,json
from pathlib import Path
HERE=Path(__file__).resolve().parent
ROOT=Path('/home/holden/mckernel')
SCOPE='Functional McKernel OS/apps and Rust/assembly migration only; no security testing.'
def ref(p):
 b=p.read_bytes();return dict(path=str(p),bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
def function(s,marker):
 a=s.index(marker);b=s.index('{',a);depth=1;e=b+1
 while depth:
  depth+=(s[e]=='{')-(s[e]=='}');e+=1
 return a,e,s[a:e]+'\n'
def main():
 cpath=ROOT/'kernel/syscall.c';rpath=ROOT/'kernel/rust/syscall_policy.rs'
 c=cpath.read_text();rust=rpath.read_text()
 a,e,original=function(c,'long clear_host_pte(uintptr_t addr, size_t len, int holding_memory_range_lock)')
 assert c.count('long clear_host_pte(uintptr_t addr, size_t len, int holding_memory_range_lock)')==1
 assert 'mod f03_clear_host_pte_entry_v1' not in rust
 startline=c[:a].count('\n')+1;closeline=c[:e].count('\n')+1
 # Exact existing conditional logical-line anchors; no intervening #line occurs.
 prefix=c[:a];anchor=prefix.rfind('#if defined(MCKERNEL_RUST_SYSCALL_OFFLOAD) && defined(MCKERNEL_RUST_SYSCALL_POLICY_HELPERS) && defined(MCKERNEL_RUST_F03_DISPATCH_CONTEXT)\n#line 4490\n#else\n#line 4499\n#endif')
 assert anchor>=0 and '#line' not in prefix[prefix.index('#endif',anchor)+6:]
 anchor_selected_line=c[:c.index('#line 4490',anchor)].count('\n')+1
 anchor_fallback_line=c[:c.index('#line 4499',anchor)].count('\n')+1
 selected_offset=4490-anchor_selected_line-1
 fallback_offset=4499-anchor_fallback_line-1
 selected_close=closeline+selected_offset;fallback_close=closeline+fallback_offset
 binding=(HERE/'clear-host-pte-binding.C.inc').read_text()
 paired=('#ifdef MCKERNEL_RUST_SYSCALL_POLICY_HELPERS\n'+binding+
  '#else\n#line '+str(startline+fallback_offset)+'\n'+original+'#endif\n'+
  '#if defined(MCKERNEL_RUST_SYSCALL_OFFLOAD) && defined(MCKERNEL_RUST_SYSCALL_POLICY_HELPERS) && defined(MCKERNEL_RUST_F03_DISPATCH_CONTEXT)\n'+
  '#line '+str(selected_close-3)+'\n#else\n#line '+str(fallback_close-1)+'\n#endif\n')
 postc=c[:a]+paired+c[e:]
 fragment=(HERE/'clear-host-pte-entry.Rust.inc').read_text()
 postrust=rust+'\n'+fragment
 (HERE/'clear-host-pte-original.C.inc').write_text(original)
 (HERE/'clear-host-pte-paired.C.inc').write_text(paired)
 for path,before,after in [('kernel/syscall.c',c,postc),('kernel/rust/syscall_policy.rs',rust,postrust)]:
  (HERE/(Path(path).name+'.patch')).write_text(''.join(difflib.unified_diff(before.splitlines(True),after.splitlines(True),fromfile='a/'+path,tofile='b/'+path)))
 _,_,body=function(rust,'#[no_mangle]\npub unsafe extern "C" fn clear_host_pte_body_result(')
 (HERE/'clear-host-pte-body.current.Rust.inc').write_text(body)
 (HERE/'abi.current.rs').write_bytes((ROOT/'kernel/rust/abi.rs').read_bytes())
 witness='''
    #[no_mangle]
    pub static F03_CLEAR_HOST_PTE_ABI:[CULong;18]=[
        core::mem::size_of::<crate::abi::Thread>() as _,core::mem::align_of::<crate::abi::Thread>() as _,
        core::mem::size_of::<ProcessVm>() as _,core::mem::align_of::<ProcessVm>() as _,
        core::mem::size_of::<crate::abi::CpuLocalVar>() as _,core::mem::align_of::<crate::abi::CpuLocalVar>() as _,
        core::mem::offset_of!(crate::abi::CpuLocalVar,current) as _,
        core::mem::offset_of!(crate::abi::Thread,vm) as _,core::mem::offset_of!(ProcessVm,is_memory_range_lock_taken) as _,
        core::mem::size_of::<ClearHostBinding>() as _,core::mem::align_of::<ClearHostBinding>() as _,
        core::mem::offset_of!(ClearHostBinding,munmap_nr) as _,core::mem::offset_of!(ClearHostBinding,forward) as _,
        core::mem::offset_of!(ClearHostBinding,log) as _,core::mem::size_of::<CInt>() as _,
        core::mem::size_of::<SyscallDoSyscall3Fn>() as _,core::mem::size_of::<ClearHostPteLogFn>() as _,
        core::mem::size_of::<CULong>() as _,
    ];
'''
 (HERE/'clear-host-pte-entry.fixture.Rust.inc').write_text(fragment.rstrip()[:-1]+witness+'}\n')
 (HERE/'lib.fixture.rs').write_text('''#![no_std]
// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
#[path="abi.current.rs"] mod abi;
mod cls {
    unsafe extern "C" { pub fn get_this_cpu_local_var()->*mut crate::abi::CpuLocalVar; }
}
mod policy {
    use crate::abi::{CInt,CLong,CULong,SizeT};
    use core::ffi::c_void;
    const EINVAL:CInt=22;
    type SyscallDoSyscall3Fn=unsafe extern "C" fn(CInt,CULong,CULong,CULong)->CLong;
    type ClearHostPteLogFn=unsafe extern "C" fn(CLong);
    unsafe fn field_ptr<T>(base:*mut u8,offset:SizeT)->*mut T { unsafe { base.add(offset).cast() } }
    // Preserve the genuine canonical foreign declaration alongside the new export.
    unsafe extern "C" {
        fn clear_host_pte(addr:CULong,len:SizeT,holding_lock:CInt)->CLong;
        fn syscall_get_processor_id_bridge()->CInt;
    }
    include!("clear-host-pte-body.current.Rust.inc");
    include!("clear-host-pte-entry.fixture.Rust.inc");
}
''')
 oldbase=HERE.parent/'m14-f03-next-runtime-body-source-20261028-1'
 old=json.loads((oldbase/'FUTURE-HOST-COMMAND-PLAN.NOT-GRANTED.json').read_text())
 commands=old['commands']
 for row in commands:
  row['argv']=[x.replace(str(oldbase),str(HERE)) for x in row['argv']]
  row['purpose']=SCOPE+' HOST mocked forwarding/log only; no actual MM, syscall, Docker, root, guest, hardware or controller action.'
 commands[0]['label']='00-existing-body-new-clear-host-entry-Rust-object'
 commands[0]['argv'][commands[0]['argv'].index('f03_perf_mmap_entry')]='f03_clear_host_pte_entry'
 del commands[0]['argv'][1:3] # Existing unrelated perf cfg is unnecessary.
 commands[1]['label']='01-actual-header-original-C-link'
 commands[1]['argv']=[x.replace(str(HERE/'driver.c'),str(HERE/'clear-host-pte-driver.c')) for x in commands[1]['argv']]
 commands[2]['label']='02-clear-host-pte-equivalence'
 plan=dict(scope=SCOPE,status='SOURCE_ONLY_NOT_GRANTED',commands=commands,expected_stdout='PASS clear-host-pte actual-header ABI18; 2304 C/Rust pairs; 4608 exact-forward/publication/restoration/log/full-state oracles',requires='Fresh exact Root ordinary grant; source/header/tool binding; disjoint output directory; existing HOST profile only',limits=dict(jobs=1,CPU=6,AS_bytes=2<<30,CPU_seconds=60,wall_seconds=90),executed=False)
 (HERE/'FUTURE-HOST-COMMAND-PLAN.NOT-GRANTED.json').write_text(json.dumps(plan,indent=2)+'\n')
 paths=[cpath,rpath,ROOT/'kernel/rust/abi.rs',ROOT/'kernel/include/process.h',ROOT/'kernel/include/cls.h',ROOT/'kernel/include/syscall.h']
 selected=[p for p in sorted(HERE.iterdir()) if p.is_file() and p.name not in ('SOURCE-READY.json','setresuid-entry.Rust.inc','driver.c')]
 report=dict(scope=SCOPE,status='PRIVATE_CLEAR_HOST_PTE_SOURCE_READY_NOT_COMPILED',target='clear_host_pte',preimages=[ref(p) for p in paths],files=[ref(p) for p in selected],excluded_held_files=['setresuid-entry.Rust.inc','driver.c'],selected_current115_C_function_bytes=129,existing_Rust_body_reused='clear_host_pte_body_result',line_state=dict(start_physical=startline,close_physical=closeline,selected_offset=selected_offset,fallback_offset=fallback_offset),predicted_C_function_removal=1,actual_builds=0,actual_native=0,canonical_writes=0,whole_file_retirement=False,retained_C_debt=['clear_host_pte_log_bridge','syscall_do_syscall3_bridge','existing forwarding endpoint/request holds'],deadline='2026-10-29T06:00:00Z',credit_run='7f4af94a83b14cc08f97401f5891d965',ceiling=57774.852125)
 (HERE/'SOURCE-READY.json').write_text(json.dumps(report,indent=2)+'\n')
 print(json.dumps(dict(status=report['status'],source_ready=ref(HERE/'SOURCE-READY.json'))))
if __name__=='__main__':main()
