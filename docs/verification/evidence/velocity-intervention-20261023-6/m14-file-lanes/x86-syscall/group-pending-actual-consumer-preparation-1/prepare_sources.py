"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Private source derivation only. Never compiles or executes fixture.
"""
from pathlib import Path
import re,json,hashlib
D=Path(__file__).resolve().parent; B=D.parent; K=Path('/home/holden/mckernel'); S=D/'source';S.mkdir(mode=0o700)
def write(n,s):
 p=S/n
 with p.open('x') as f:f.write(s)
def pin(p):
 p=Path(p);b=p.read_bytes();return dict(path=str(p),sha256=hashlib.sha256(b).hexdigest(),bytes=len(b))
def items(s):
 out={}
 for m in re.finditer(r'(?m)^(?:pub(?:\([^\n]+\))? )?(?:unsafe )?(?:extern "C" )?fn (\w+)\s*\(',s):
  start=m.start();before=s[:start]
  while before.endswith(']\n'):
   k=before.rfind('\n',0,len(before)-1)+1
   if not before[k:].startswith('#['):break
   start=k;before=s[:k]
  a=s.index('{',m.end());depth=1;i=a+1
  while depth:
   if s[i]=='{':depth+=1
   elif s[i]=='}':depth-=1
   i+=1
  out[m.group(1)]=(start,i,s[start:i]+'\n')
 return out
def closure(path,roots,prelude):
 s=path.read_text();allf=items(s);selected=set(roots)
 while True:
  reached=set(re.findall(r'\b\w+\b','\n'.join(allf[n][2] for n in selected)))&set(allf)
  nxt=selected|reached
  if nxt==selected:break
  selected=nxt
 chunks=[allf[n] for n in selected];chunks.sort()
 body='\n'.join(t[2] for t in chunks)
 constants={m.group(1):m.group(0) for m in re.finditer(r'(?m)^const (\w+):[^;]+;',s)}
 needed=set(re.findall(r'\b\w+\b',body))&set(constants)
 while True:
  nxt=needed|(set(re.findall(r'\b\w+\b','\n'.join(constants[n] for n in needed)))&set(constants))
  if nxt==needed:break
  needed=nxt
 text=prelude+'\n'+'\n'.join(constants[n] for n in constants if n in needed)+'\n'+body
 return text,[dict(function=n,sha256=hashlib.sha256(allf[n][2].encode()).hexdigest(),bytes=len(allf[n][2].encode())) for n in sorted(selected)]
for name in ['abi','lock_helpers','spinlock_helpers','list_helpers']:
 write(name+'.rs',(K/'kernel/rust'/f'{name}.rs').read_text())
string,sp=closure(K/'kernel/rust/string.rs',['__inline_memset','memset','memcpy','__inline_memcpy','strcmp','strcpy','strlen'],'''use core::ffi::c_void;
use core::ptr::{null_mut,read_volatile,write_volatile};
use crate::abi::{CInt,CLong,CULong,SizeT};''')
write('string.rs',string)
m=(K/'kernel/rust/mem_helpers.rs').read_text()
types='\n'.join(re.findall(r'(?m)^type MemKmalloc(?:IrqSave|IrqRestore|AllocPages|GetCpuLocalVar|SpinLock|SpinUnlock|Corruption|BaseAlloc|BaseFree|SpinInit|TrackLog|InvalidFree)Fn =[^;]+;',m))
a=m.index('#[repr(C)]\npub struct KmallocTrackAddrEntry');z=m.index('#[repr(C)]\npub struct PageallocTrackAddrEntry',a)
extern='''unsafe extern "C" {
fn ihk_mc_get_processor_id()->CInt;
fn get_this_cpu_local_var()->*mut CpuLocalVar;
fn kprintf(format:*const i8,...)->CInt;
fn mem_kmalloc_track_base_alloc_bridge(size:CInt,flag:CULong)->*mut c_void;
fn mem_kmalloc_track_base_free_bridge(ptr:*mut c_void);
fn mem_kmalloc_track_lock_bridge(lock:CULong)->CULong;
fn mem_kmalloc_track_unlock_bridge(lock:CULong,flags:CULong);
fn mem_kmalloc_track_spin_init_bridge(lock:CULong);
fn mem_kmalloc_track_log_bridge(event:CInt,ptr:*mut c_void,file:*mut i8,line:CInt,size:CInt);
fn mem_kmalloc_invalid_free_bridge(ptr:*mut c_void,file:*mut i8,line:CInt);
#[link_name="memdebug"] static mut MEMDEBUG:*mut i8;
#[link_name="kmalloc_track_hash"] static mut KMALLOC_TRACK_HASH:[AbiListHead;256];
#[link_name="kmalloc_track_hash_locks"] static mut KMALLOC_TRACK_HASH_LOCKS:[IhkSpinlock;256];
#[link_name="kmalloc_addr_hash"] static mut KMALLOC_ADDR_HASH:[AbiListHead;256];
#[link_name="kmalloc_addr_hash_locks"] static mut KMALLOC_ADDR_HASH_LOCKS:[IhkSpinlock;256];
#[link_name="kmalloc_runcount"] static mut KMALLOC_RUNCOUNT:CInt;
}'''
mem,mp=closure(K/'kernel/rust/mem_helpers.rs',['kmalloc_tracked','kfree_tracked','___kmalloc_body_result','___kfree_body_result','___kmalloc_init_chunk_result','___kmalloc_insert_chunk_result'],'''use core::ffi::c_void;
use core::mem::{size_of,offset_of};
use core::ptr::null_mut;
use core::sync::atomic::{AtomicI32,Ordering};
use crate::abi::{AbiListHead,CInt,CULong,CpuLocalVar,IhkAtomic,IhkSpinlock,KmallocHeader,SizeT};
use crate::string::{strcmp,strcpy,strlen};
'''+types+'\n'+m[a:z]+extern)
write('mem_helpers.rs',mem)
g=B/'next-do-kill-process-group-source-1';e=B/'next-do-kill-pending-enqueue-source-1'
write('group.FRAGMENT.rs',(g/'candidate/syscall_policy.do_kill_process_group.ABI-CAST.FRAGMENT.rs').read_text())
write('pending.FRAGMENT.rs',(e/'candidate/syscall_policy.do_kill_pending_enqueue.FRAGMENT.rs').read_text())
write('original-group.ACTUAL.inc',(g/'fixture-fragments/original-process-group-branch.ACTUAL.inc').read_text())
write('original-pending.ACTUAL.inc',(e/'fixture-fragments/original-pending-enqueue.ACTUAL.inc').read_text())
write('group_pending_actual.rs','''// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
#![allow(dead_code,unused_imports)]
mod abi; mod lock_helpers; mod spinlock_helpers; mod list_helpers; mod string; mod mem_helpers;
use core::mem::{size_of,align_of,offset_of,MaybeUninit};
use core::ptr::null_mut;
use abi::{Thread,Process,SigInfo,AbiListHead,CInt,CULong,SizeT};
use lock_helpers::McsRwlockNodeIrqsave;
const ESRCH:CInt=3; const ENOMEM:CInt=12;
const SIGKILL:CInt=9; const SIGSTOP:CInt=19; const IHK_MC_AP_NOWAIT:CULong=2;
include!("group.FRAGMENT.rs"); include!("pending.FRAGMENT.rs");
include!("arena_bindings.rs");
#[no_mangle] pub extern "C" fn fixture_group_pending_actual_Rust_ABI(i:usize)->usize {
 let v=[size_of::<Thread>(),align_of::<Thread>(),size_of::<Process>(),align_of::<Process>(),size_of::<abi::ProcessHash>(),offset_of!(abi::ProcessHash,list),offset_of!(abi::ProcessHash,lock),abi::PROCESS_HASH_SIZE,size_of::<abi::SigPending>(),offset_of!(abi::SigPending,info),offset_of!(abi::SigPending,ptracecont),offset_of!(abi::SigPending,interrupted),size_of::<SigInfo>(),size_of::<abi::KmallocHeader>(),offset_of!(abi::CpuLocalVar,free_list),offset_of!(Thread,sigevent),offset_of!(Process,hash_list),size_of::<abi::McsRwlockLock>()];v[i]
}
''')
write('arena_bindings.rs','''// Fixture binding to genuine Rust allocator bodies. No alternative allocator.
// Single-CPU, MEMDEBUG=NULL valid arena only. Physical page growth and remote
// frees HOLD; alloc_pages endpoint is a controlled exhausted-page result.
use core::ffi::c_void;
unsafe extern "C" {
 fn fixture_cpu()->*mut abi::CpuLocalVar;
 fn fixture_arena()->*mut c_void;
 fn fixture_fail_alloc()->CInt;
 fn cpu_disable_interrupt_save()->CULong;
 fn cpu_restore_interrupt(flags:CULong);
 fn fixture_provider_error();
}
#[no_mangle] static mut memdebug:*mut i8=core::ptr::null_mut();
#[no_mangle] static mut kmalloc_track_hash:[AbiListHead;256]=unsafe{core::mem::zeroed()};
#[no_mangle] static mut kmalloc_addr_hash:[AbiListHead;256]=unsafe{core::mem::zeroed()};
#[no_mangle] static mut kmalloc_track_hash_locks:[abi::IhkSpinlock;256]=unsafe{core::mem::zeroed()};
#[no_mangle] static mut kmalloc_addr_hash_locks:[abi::IhkSpinlock;256]=unsafe{core::mem::zeroed()};
#[no_mangle] static mut kmalloc_runcount:CInt=0;
unsafe extern "C" fn pages_exhausted(_:CInt,_:CULong,_:CInt)->*mut c_void {null_mut()}
unsafe extern "C" fn remote_cpu(_:CInt)->*mut c_void {fixture_provider_error();null_mut()}
unsafe extern "C" fn corrupt(_: *mut c_void){fixture_provider_error();}
#[no_mangle] pub unsafe extern "C" fn get_this_cpu_local_var()->*mut abi::CpuLocalVar{fixture_cpu()}
#[no_mangle] pub unsafe extern "C" fn mem_kmalloc_track_base_alloc_bridge(n:CInt,f:CULong)->*mut c_void{
 if fixture_fail_alloc()!=0 {return null_mut();}
 mem_helpers::___kmalloc_body_result(n,f,&raw mut (*fixture_cpu()).free_list,Some(cpu_disable_interrupt_save),Some(cpu_restore_interrupt),Some(pages_exhausted))
}
#[no_mangle] pub unsafe extern "C" fn mem_kmalloc_track_base_free_bridge(p:*mut c_void){
 let rc=mem_helpers::___kfree_body_result(p,&raw mut (*fixture_cpu()).free_list,offset_of!(abi::CpuLocalVar,remote_free_list_lock) as CULong,offset_of!(abi::CpuLocalVar,remote_free_list) as CULong,Some(cpu_disable_interrupt_save),Some(cpu_restore_interrupt),Some(remote_cpu),Some(mem_kmalloc_track_lock_bridge),Some(mem_kmalloc_track_unlock_bridge),Some(corrupt));if rc!=0{fixture_provider_error();}
}
#[no_mangle] pub unsafe extern "C" fn mem_kmalloc_track_lock_bridge(l:CULong)->CULong{spinlock_helpers::__ihk_mc_spinlock_lock(l as *mut spinlock_helpers::IhkSpinlock)}
#[no_mangle] pub unsafe extern "C" fn mem_kmalloc_track_unlock_bridge(l:CULong,f:CULong){spinlock_helpers::__ihk_mc_spinlock_unlock(l as *mut spinlock_helpers::IhkSpinlock,f)}
#[no_mangle] pub unsafe extern "C" fn mem_kmalloc_track_spin_init_bridge(l:CULong){spinlock_helpers::ihk_mc_spinlock_init(l as *mut spinlock_helpers::IhkSpinlock)}
#[no_mangle] pub unsafe extern "C" fn mem_kmalloc_track_log_bridge(_:CInt,_:*mut c_void,_:*mut i8,_:CInt,_:CInt){fixture_provider_error();}
#[no_mangle] pub unsafe extern "C" fn mem_kmalloc_invalid_free_bridge(_:*mut c_void,_:*mut i8,_:CInt){fixture_provider_error();}
#[no_mangle] pub unsafe extern "C" fn fixture_reset_genuine_arena(){
 let h=&raw mut (*fixture_cpu()).free_list;(*h).next=h;(*h).prev=h;
 let c=fixture_arena().cast::<abi::KmallocHeader>();mem_helpers::___kmalloc_init_chunk_result(c,(65536-size_of::<abi::KmallocHeader>()) as CInt);mem_helpers::___kmalloc_insert_chunk_result(h,c);
}
''')
report=dict(scope=__doc__,status='SOURCE_ONLY_NOT_COMPILED',actual_sources=[pin(K/'kernel/rust'/n) for n in ['abi.rs','lock_helpers.rs','spinlock_helpers.rs','list_helpers.rs','string.rs','mem_helpers.rs']],exact_mem_function_extractions=mp,exact_string_function_extractions=sp,real_allocator='kmalloc_tracked/_kmalloc/track_alloc_result -> actual ___kmalloc_body_result with real chunk split/free/consolidation; MEMDEBUG=NULL',controlled='CPU/preempt/IRQ callbacks, bounded HOST backing arena, page exhaustion injection and public recursive signal-delivery effects',holds=['enabled memdebug','remote CPU free','physical page allocation','actual native IRQ/preempt/signal delivery','multicore scheduling'],outputs=[pin(p) for p in sorted(S.iterdir())])
with (D/'SOURCE-EXTRACTION.json').open('x') as f:json.dump(report,f,sort_keys=True,indent=2);f.write('\n')
print('source extraction',len(mp),'actual mem functions',len(sp),'string functions')
