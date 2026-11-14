#![allow(dead_code)]
// Actual production guest/graph/registry and checked Thread/Process bodies.
// EXPLICIT adapters: C constructor, VM release callback, physical mapping and
// host transport. This proves source semantics, NOT Linux/kernel ABI or MM.
mod abi;mod rbtree;mod process_helpers;mod fork_control_registry;mod fork_control_guest;mod x86_cpu_helpers;
mod application_rpc;mod application_syscall;mod sched_helpers;mod syscall_policy;mod lock_helpers;
use std::sync::atomic::{AtomicUsize,AtomicPtr,AtomicU64,Ordering};
use core::ffi::c_void;
fn unexpected_destructor(){panic!("unexpected final parent destructor")}
mod cls{
 use super::*;static CURRENT:AtomicPtr<abi::CpuLocalVar>=AtomicPtr::new(core::ptr::null_mut());
 pub unsafe fn set(p:*mut abi::CpuLocalVar){CURRENT.store(p,Ordering::SeqCst);}
 pub unsafe fn get_this_cpu_local_var()->*mut abi::CpuLocalVar{CURRENT.load(Ordering::SeqCst)}
 use crate::abi::{CInt,CpuLocalVar};use core::sync::atomic::AtomicI32;
 static mut cpu_local_var_initialized:CInt=1;
 unsafe fn this_cpu_local_var()->*mut CpuLocalVar{get_this_cpu_local_var()}
unsafe fn atomic_counter(counter: *mut crate::abi::IhkAtomic) -> &'static AtomicI32 {
    AtomicI32::from_ptr(&raw mut (*counter).counter)
}
pub unsafe extern "C" fn preempt_disable() {
    if cpu_local_var_initialized != 0 {
        let v = this_cpu_local_var();
        atomic_counter(&raw mut (*v).no_preempt).fetch_add(1, Ordering::SeqCst);
    }
}
pub unsafe extern "C" fn preempt_enable() {
    if cpu_local_var_initialized != 0 {
        let v = this_cpu_local_var();
        atomic_counter(&raw mut (*v).no_preempt).fetch_sub(1, Ordering::SeqCst);
    }
}
}
mod x86_memory_helpers;
mod mem_helpers{
 use super::*;use std::sync::Mutex;use std::alloc::{alloc,dealloc,Layout};
 static LIVE:Mutex<Vec<(usize,usize)>>=Mutex::new(Vec::new());
 pub unsafe fn kmalloc(n:i32,_:i32)->*mut c_void{assert!(n>0);let p=alloc(Layout::from_size_align(n as usize,8).unwrap());
  if !p.is_null(){LIVE.lock().unwrap().push((p as usize,n as usize));}p.cast()}
 pub unsafe fn kfree(p:*mut c_void){let mut live=LIVE.lock().unwrap();let i=live.iter().position(|(v,_)|*v==p as usize).expect("exact allocation owner");
  let(_,n)=live.remove(i);dealloc(p.cast(),Layout::from_size_align(n,8).unwrap());}
 pub fn live()->usize{LIVE.lock().unwrap().len()}
}
#[no_mangle]unsafe extern "C" fn do_syscall(r:*mut abi::SyscallRequest,c:i32)->i64{phase5_tests::transport(r,c)}
#[no_mangle]unsafe extern "C" fn clone_thread(p:*mut abi::Thread,_:u64,_:u64,flags:i32)->*mut abi::Thread{phase5_tests::record_constructor_flags(flags);phase5_tests::construct(p)}
#[no_mangle]unsafe extern "C" fn release_cpuid(cpu:i32){assert_eq!(cpu,1);phase5_tests::CPU.fetch_add(1,Ordering::SeqCst);}
extern "C"{fn process_fork_construct_current_v1(p:*mut abi::Thread,pc:u64,sp:u64,f:i32,cpu:i32,out:*mut *mut c_void)->*mut abi::Thread;}
mod phase5_tests {
 use super::*;use abi::*;
 static IRQ_DISABLED:AtomicUsize=AtomicUsize::new(0);
 static TID_BUFFER:AtomicPtr<u8>=AtomicPtr::new(core::ptr::null_mut());
 static TID_FAULTS:AtomicUsize=AtomicUsize::new(0);static TID_VTOPS:AtomicUsize=AtomicUsize::new(0);
 static CONSTRUCTOR_FLAGS:AtomicUsize=AtomicUsize::new(0);
 static MODE:AtomicUsize=AtomicUsize::new(0);static CHILD:AtomicPtr<Thread>=AtomicPtr::new(core::ptr::null_mut());
 static TARGET:AtomicPtr<CpuLocalVar>=AtomicPtr::new(core::ptr::null_mut());
 static PAYLOAD:AtomicUsize=AtomicUsize::new(0);
 static WAIT_EVENTS:std::sync::Mutex<Vec<u32>>=std::sync::Mutex::new(Vec::new());
 static CHILD_LOCK:AtomicUsize=AtomicUsize::new(0);
 static CALLS:AtomicUsize=AtomicUsize::new(0);static QUEUED:AtomicUsize=AtomicUsize::new(0);
 static THREAD:AtomicUsize=AtomicUsize::new(0);static VM:AtomicUsize=AtomicUsize::new(0);
 static PROCESS:AtomicUsize=AtomicUsize::new(0);static PAGES:AtomicUsize=AtomicUsize::new(0);
 pub(super) static CPU:AtomicUsize=AtomicUsize::new(0);
 pub fn mode()->usize{MODE.load(Ordering::SeqCst)}
 pub fn irq_disabled()->i32{IRQ_DISABLED.load(Ordering::SeqCst)as i32}
 pub fn record_constructor_flags(flags:i32){CONSTRUCTOR_FLAGS.store(flags as usize,Ordering::SeqCst);}
 pub unsafe fn tid_fault(vm:*mut c_void,page:*mut c_void,reason:u64)->i32 {
  assert_eq!(vm,(*CHILD.load(Ordering::SeqCst)).vm.cast());
  assert!(matches!(page as usize,0x1000|0x2000));assert_eq!(reason,0x40000006);
  TID_FAULTS.fetch_add(1,Ordering::SeqCst);if mode()==11{-14}else{0}
 }
 pub unsafe fn tid_vtop(pt:*mut c_void,address:*const c_void,physical:*mut u64)->i32 {
  assert_eq!(pt,0x4000usize as *mut c_void);let user=address as usize;assert!((0x1000..0x3000).contains(&user));
  TID_VTOPS.fetch_add(1,Ordering::SeqCst);if mode()==12&&user>=0x2000{return -14;}
  *physical=TID_BUFFER.load(Ordering::SeqCst).add(user-0x1000)as u64;0
 }
 pub fn tid_memory(start:u64,end:u64)->i32 {
  let base=TID_BUFFER.load(Ordering::SeqCst)as u64;assert!(start>=base&&end<=base+8192);1
 }
 pub fn target()->*mut CpuLocalVar{TARGET.load(Ordering::SeqCst)}
 pub fn queued(){
  if (10..=12).contains(&mode()) {assert!(TID_FAULTS.load(Ordering::SeqCst)>0);let bytes=unsafe{std::slice::from_raw_parts(TID_BUFFER.load(Ordering::SeqCst),8192)};
   match mode(){10=>assert_eq!(&bytes[0x800..0x804],&900i32.to_le_bytes()),11=>assert_eq!(&bytes[0x800..0x804],&[0xaa;4]),
    12=>{assert_eq!(&bytes[0xffe..0x1000],&900i32.to_le_bytes()[..2]);assert_eq!(&bytes[0x1000..0x1002],&[0xaa;2]);},_=>unreachable!()}}
  QUEUED.fetch_add(1,Ordering::SeqCst);
 }
 pub fn thread_final(){THREAD.fetch_add(1,Ordering::SeqCst);}
 pub fn process_final(){PROCESS.fetch_add(1,Ordering::SeqCst);}
 pub fn pages_final(){PAGES.fetch_add(1,Ordering::SeqCst);}
 unsafe fn init(p:*mut AbiListHead){(*p).next=p;(*p).prev=p;}
 pub unsafe fn construct(parent:*mut Thread)->*mut Thread {
  let child=Box::into_raw(Box::new(core::mem::zeroed::<Thread>()));
  assert_eq!(process_helpers::process_thread_alloc_init_body_result(child.cast(),core::mem::size_of::<Thread>()as u64,
   core::mem::offset_of!(Thread,refcount)as u64,core::mem::offset_of!(Thread,hash_list)as u64,
   core::mem::offset_of!(Thread,siblings_list)as u64,None),0);
  let proc=Box::into_raw(Box::new(core::mem::zeroed::<Process>()));let vm=Box::into_raw(Box::new(core::mem::zeroed::<ProcessVm>()));
  let layout=std::alloc::Layout::from_size_align(core::mem::size_of::<AddressSpace>()+4,core::mem::align_of::<AddressSpace>()).unwrap();let space=std::alloc::alloc_zeroed(layout).cast::<AddressSpace>();(*space).nslots=1;(*space).page_table=0x4000usize as *mut c_void;
  (*child).uctx=Box::into_raw(Box::new(core::mem::zeroed::<X86UserContext>()));
  (*child).proc=proc;(*child).vm=vm;(*proc).refcount.counter=2;(*proc).parent=(*parent).proc;(*proc).ppid_parent=(*parent).proc;
  (*proc).main_thread=child;(*proc).vm=vm;init(&raw mut (*proc).threads_list);init(&raw mut (*proc).children_list);
  (*vm).refcount.counter=1;(*vm).proc=proc.cast();(*vm).address_space=space;(*vm).region.user_start=0x1000;(*vm).region.user_end=0x3000;
  CHILD.store(child,Ordering::SeqCst);child
 }
 pub unsafe fn release_vm(pointer:*mut c_void)->i32 {
  let vm=pointer.cast::<ProcessVm>();let count=std::sync::atomic::AtomicI32::from_ptr(&raw mut (*vm).refcount.counter);
  if count.fetch_sub(1,Ordering::SeqCst)!=1{return 0;}
  VM.fetch_add(1,Ordering::SeqCst);process_helpers::release_process_checked((*vm).proc.cast());1
 }
 pub unsafe fn transport(request:*mut SyscallRequest,cpu:i32)->i64 {
  let nth=CALLS.fetch_add(1,Ordering::SeqCst)+1;assert_eq!(cpu,0);
  let parent=(*cls::get_this_cpu_local_var()).current;(*request).rtid=(*parent).tid;(*request).ttid=0;(*request).valid=0;
  assert_eq!((*request).args[4]%8,0);PAYLOAD.store((*request).args[4]as usize,Ordering::SeqCst);let frame=&mut*((*request).args[4]as *mut[u8;128]);let mut response:SyscallResponse=core::mem::zeroed();response.stid=321;
  let physical=&mut response as *mut SyscallResponse as u64;
  if nth==1 {
   let nonce=u64::from_le_bytes(frame[24..32].try_into().unwrap());let mut packet=[0u8;128];
   packet[8..12].copy_from_slice(&4i32.to_le_bytes());packet[32..36].copy_from_slice(&1i32.to_le_bytes());
   packet[56..64].copy_from_slice(&1u64.to_le_bytes());packet[48..52].copy_from_slice(&(*request).rtid.to_le_bytes());
   packet[64..72].copy_from_slice(&56u64.to_le_bytes());
   for(i,arg)in(*request).args.iter().enumerate(){packet[72+i*8..80+i*8].copy_from_slice(&arg.to_le_bytes());}
   packet[120..128].copy_from_slice(&physical.to_le_bytes());let q=application_syscall::Request::decode(&packet,1).unwrap();
   *frame=q.first_fork_receipt(&application_syscall::ForkFirstReceipt{slot:3,generation:5,parent:7,worker:11,delivery:13,child:17,
    child_pid:900,child_mm:0x9000,root:0x4000,start:0x1000,length:0x2000,nonce,response:physical}).unwrap();response.ret=900;
  } else if nth==2 {
   assert_eq!((*request).args[0],1);assert_eq!((*request).args[1],900);assert_eq!(frame[..8],*b"MCFKW001");
   if mode()==1{response.ret=-10;}
  } else {
   assert!(matches!(nth,3|4));assert_eq!(CHILD_LOCK.load(Ordering::SeqCst),0);
   if nth==3 {
    assert_eq!((*request).args[0],2);assert_eq!(frame[..8],*b"MCFKW001");
    assert_eq!(THREAD.load(Ordering::SeqCst),0);
    if mode()==28{
     // Simulate actual nested dispatch reaching a wait-completion drain while
     // this real original-parent transport remains active.
     assert_eq!(fork_control_guest::runnable::process_fork_runtime_drain_current_v1(),-16);
     // Serialization is per parent, not a global service-wide barrier.
     let other=Box::into_raw(Box::new(core::mem::zeroed::<Thread>()));
     let independent=fork_control_registry::claim_parent_drain(other as usize).expect("different current-parent key");drop(independent);
    }
    if mode()==22{response.ret=-16;}
    frame[..8].copy_from_slice(b"MCFKR001");
   }else{
    assert_eq!((*request).args[..2],[3,2]);assert_eq!(frame[..8],*b"MCFKD001");
    assert_eq!((THREAD.load(Ordering::SeqCst),VM.load(Ordering::SeqCst),PROCESS.load(Ordering::SeqCst),PAGES.load(Ordering::SeqCst)),(1,1,1,1));
    if mode()==23{response.ret=-5;}
    frame[..8].copy_from_slice(b"MCFKA001");
   }
   for(at,value)in[(8,77u64),(16,55),(24,if nth==3{23}else{24}),(32,physical)]{frame[at..at+8].copy_from_slice(&value.to_le_bytes());}
  }
  AtomicU64::from_ptr(&raw mut response.status).store(1,Ordering::Release);
  if !(nth==2&&mode()==2)&&!(nth==4&&mode()==24){fork_control_guest::observe_fork_control_reply(request,&mut response,cpu,parent);}
  response.ret
 }
 unsafe fn run(mode:usize)->(fork_control_guest::child_credits::CallerForkOutcome,*mut Thread,*mut Thread){run_case(mode,17,0,false)}
 unsafe fn run_case(mode:usize,flags:i32,child_tid:u64,new_caller:bool)->(fork_control_guest::child_credits::CallerForkOutcome,*mut Thread,*mut Thread){
  for a in [&CALLS,&QUEUED,&THREAD,&VM,&PROCESS,&PAGES,&CPU,&CHILD_LOCK]{a.store(0,Ordering::SeqCst);}MODE.store(mode,Ordering::SeqCst);IRQ_DISABLED.store(0,Ordering::SeqCst);WAIT_EVENTS.lock().unwrap().clear();
  TID_FAULTS.store(0,Ordering::SeqCst);TID_VTOPS.store(0,Ordering::SeqCst);TID_BUFFER.store(Box::into_raw(Box::new([0xaau8;8192])).cast(),Ordering::SeqCst);
  let parent=Box::into_raw(Box::new(core::mem::zeroed::<Thread>()));(*parent).refcount.counter=1;(*parent).tid=19;(*parent).tlsblock_base=0x12345678;
  let proc=Box::into_raw(Box::new(core::mem::zeroed::<Process>()));(*parent).proc=proc;(*proc).refcount.counter=2;init(&raw mut (*proc).children_list);
  (*parent).vm=Box::into_raw(Box::new(core::mem::zeroed::<ProcessVm>()));
  let phash=Box::into_raw(Box::new(core::mem::zeroed::<ProcessHash>()));let thash=Box::into_raw(Box::new(core::mem::zeroed::<ThreadHash>()));
  for i in 0..PROCESS_HASH_SIZE{init(&raw mut (*phash).list[i]);init(&raw mut (*thash).list[i]);}
  let resource=Box::into_raw(Box::new(core::mem::zeroed::<ResourceSet>()));(*resource).process_hash=phash;(*resource).thread_hash=thash;
  let local=Box::into_raw(Box::new(core::mem::zeroed::<CpuLocalVar>()));(*local).current=parent;(*local).resource_set=resource;cls::set(local);
  let target=Box::into_raw(Box::new(core::mem::zeroed::<CpuLocalVar>()));init(&raw mut (*target).runq);(*target).runq_reserved=1;TARGET.store(target,Ordering::SeqCst);
  let mut token=core::ptr::null_mut();let child=process_fork_construct_current_v1(parent,0,0,flags,1,&mut token);assert!(!token.is_null());
  let mut outcome=core::mem::zeroed();let result=if new_caller{fork_control_guest::child_credits::process_fork_owned_caller_runnable_current_v2(parent,child,1,0,token,flags,0,child_tid,&mut outcome)}
   else{fork_control_guest::child_credits::process_fork_owned_caller_runnable_current_v1(parent,child,1,0,token,flags,0,&mut outcome)};assert_eq!(result,0);
  (outcome,parent,child)
 }
 #[test]fn phase5_same_response_then_actual_lists_and_runqueue(){unsafe{
  let(out,parent,child)=run(0);assert_eq!((out.disposition,out.error),(3,900));assert_eq!(CALLS.load(Ordering::SeqCst),2);assert_eq!(QUEUED.load(Ordering::SeqCst),1);
  assert_eq!((*child).tid,900);assert_eq!((*(*child).proc).pid,900);assert_eq!((*child).cpu_id,1);assert_eq!((*child).status,1);assert_eq!((*(*child).uctx).gpr.rax,0);
  let mut payload_offset=0;assert_eq!(fork_control_registry::visit(out.handle,|pointer|{payload_offset=PAYLOAD.load(Ordering::SeqCst)-pointer.as_ptr()as usize;0}),0);
  assert_eq!(payload_offset%8,0);println!("{{\"actual_payload_offset\":{},\"alignment_remainder\":0}}",payload_offset);
  assert_eq!(core::ptr::read_volatile(core::ptr::addr_of!((*(*(*child).vm).address_space).nslots).add(1)),900);
  assert_eq!((*child).tlsblock_base,(*parent).tlsblock_base);assert_eq!((*child).refcount.counter,3);assert_eq!((*(*child).vm).refcount.counter,2);
  assert_eq!((*target()).runq_len,1);assert_eq!((*target()).runq_reserved,0);assert_eq!(CPU.load(Ordering::SeqCst),0);
  let mut observation=core::mem::zeroed();assert_eq!(fork_control_guest::process_fork_guest_control_submit_current_v1(out.handle,&mut observation),-16);
  assert_eq!(CALLS.load(Ordering::SeqCst),2);assert_eq!(THREAD.load(Ordering::SeqCst),0);
 }}
 #[test]fn phase5_missing_host_start_retains_original_graph(){unsafe{
  let(out,parent,child)=run(1);assert_eq!(out.disposition,1);assert_eq!(out.error,-10);assert_eq!(QUEUED.load(Ordering::SeqCst),0);
  assert_eq!((*child).refcount.counter,2);assert_eq!((*(*child).vm).refcount.counter,1);assert_eq!((*parent).refcount.counter,2);assert_eq!(CPU.load(Ordering::SeqCst),0);
 }}
 #[test]fn phase5_scalar_ret0_without_actual_hook_never_publishes(){unsafe{
  let(out,_,child)=run(2);assert_eq!(out.disposition,1);assert_eq!(out.error,-5);assert_eq!(QUEUED.load(Ordering::SeqCst),0);assert_eq!((*child).refcount.counter,2);
 }}
 #[test]fn phase5_partial_publish_keeps_runtime_pin_and_original_owners(){unsafe{
  let(out,parent,child)=run(3);assert_eq!(out.disposition,1);assert_eq!(out.error,-22);assert_eq!(QUEUED.load(Ordering::SeqCst),0);
  assert_eq!((*child).refcount.counter,3);assert_eq!((*(*child).vm).refcount.counter,2);assert_eq!((*parent).refcount.counter,2);assert_eq!(CPU.load(Ordering::SeqCst),0);
 }}

 unsafe extern "C" fn wait_lock(_:*mut c_void,_:*mut c_void){WAIT_EVENTS.lock().unwrap().push(1);}
 unsafe extern "C" fn wait_unlock(lock:*mut c_void,_:*mut c_void){let children=lock as usize==CHILD_LOCK.load(Ordering::SeqCst);WAIT_EVENTS.lock().unwrap().push(if children{3}else{2});if children{CHILD_LOCK.store(0,Ordering::SeqCst);}}
 unsafe extern "C" fn wait_detach(entry:*mut c_void){process_helpers::process_list_detach_result(entry.cast());}
 unsafe extern "C" fn wait_release(proc:*mut c_void){WAIT_EVENTS.lock().unwrap().push(4);assert_eq!(process_helpers::release_process_checked(proc.cast()),0);}
 fn wait_offsets()->syscall_policy::WaitZombieOffsets{use core::mem::offset_of;syscall_policy::WaitZombieOffsets{
 thread_ptrace_offset:offset_of!(Thread,ptrace),proc_pid_offset:offset_of!(Process,pid),proc_ppid_parent_offset:offset_of!(Process,ppid_parent),proc_parent_offset:offset_of!(Process,parent),
 proc_status_offset:offset_of!(Process,status),proc_group_exit_status_offset:offset_of!(Process,group_exit_status),proc_nowait_offset:offset_of!(Process,nowait),proc_update_lock_offset:offset_of!(Process,update_lock),
 proc_children_lock_offset:offset_of!(Process,children_lock),proc_threads_lock_offset:offset_of!(Process,threads_lock),proc_siblings_list_offset:offset_of!(Process,siblings_list),proc_children_list_offset:offset_of!(Process,children_list),
 proc_main_thread_offset:offset_of!(Process,main_thread),proc_stime_offset:offset_of!(Process,stime),proc_utime_offset:offset_of!(Process,utime),proc_stime_children_offset:offset_of!(Process,stime_children),
 proc_utime_children_offset:offset_of!(Process,utime_children),proc_maxrss_offset:offset_of!(Process,maxrss),proc_maxrss_children_offset:offset_of!(Process,maxrss_children)}}
 #[test]fn libc_tid_exact_producer_writes_child_vm_before_runqueue(){unsafe{
  let(out,parent,child)=run_case(10,0x01200011,0x1800,true);
  assert_eq!((out.disposition,out.error),(3,900));assert_eq!(CONSTRUCTOR_FLAGS.load(Ordering::SeqCst),0x01200011);
  assert_eq!((*child).clear_child_tid,0x1800usize as *mut i32);assert_eq!(CALLS.load(Ordering::SeqCst),2);
  assert_eq!((TID_FAULTS.load(Ordering::SeqCst),TID_VTOPS.load(Ordering::SeqCst),QUEUED.load(Ordering::SeqCst)),(1,1,1));
  assert_eq!((*child).refcount.counter,3);assert_eq!((*(*child).vm).refcount.counter,2);assert_eq!((*parent).refcount.counter,2);
  assert_eq!(CPU.load(Ordering::SeqCst),0);assert_eq!(THREAD.load(Ordering::SeqCst),0);
 }}
 #[test]fn libc_tid_native_fault_is_best_effort_and_keeps_runtime_owners(){unsafe{
  let(out,parent,child)=run_case(11,0x01200011,0x1800,true);
  assert_eq!((out.disposition,out.error),(3,900));assert_eq!((*child).clear_child_tid,0x1800usize as *mut i32);
  assert_eq!((TID_FAULTS.load(Ordering::SeqCst),TID_VTOPS.load(Ordering::SeqCst),QUEUED.load(Ordering::SeqCst)),(1,0,1));
  assert_eq!((*child).refcount.counter,3);assert_eq!((*(*child).vm).refcount.counter,2);assert_eq!((*parent).refcount.counter,2);
  assert_eq!((THREAD.load(Ordering::SeqCst),VM.load(Ordering::SeqCst),PROCESS.load(Ordering::SeqCst),CPU.load(Ordering::SeqCst)),(0,0,0,0));
 }}
 #[test]fn libc_tid_partial_cross_page_store_does_not_rollback_or_free(){unsafe{
  let(out,_,child)=run_case(12,0x01200011,0x1ffe,true);
  assert_eq!((out.disposition,out.error),(3,900));assert_eq!((*child).clear_child_tid,0x1ffeusize as *mut i32);
  assert_eq!((TID_FAULTS.load(Ordering::SeqCst),TID_VTOPS.load(Ordering::SeqCst),QUEUED.load(Ordering::SeqCst)),(2,2,1));
  assert_eq!((*child).refcount.counter,3);assert_eq!((*(*child).vm).refcount.counter,2);
  assert_eq!(fork_control_registry::visit(out.handle,|_|0),0);
  assert_eq!((THREAD.load(Ordering::SeqCst),VM.load(Ordering::SeqCst),PROCESS.load(Ordering::SeqCst),CPU.load(Ordering::SeqCst)),(0,0,0,0));
 }}
 #[test]fn libc_tid_unsupported_flags_or_pointerless_old_caller_never_offload(){unsafe{
  for (flags,new_caller)in[(0x01300011,true),(0x01200011,false)]{
   let(out,_,child)=run_case(13,flags,0x1800,new_caller);assert_eq!((out.disposition,out.error),(0,-22));
   assert_eq!((CALLS.load(Ordering::SeqCst),TID_FAULTS.load(Ordering::SeqCst),QUEUED.load(Ordering::SeqCst)),(0,0,0));
   assert_eq!((*child).refcount.counter,2);assert_eq!((*(*child).vm).refcount.counter,1);assert!((*child).clear_child_tid.is_null());
   assert_eq!(CPU.load(Ordering::SeqCst),0);
  }
 }}
 #[test]fn phase5_wait_reap_unpublishes_once_and_pin_survives_exit(){unsafe{
  let(out,parent,child)=run(0);let proc=(*child).proc;let vm=(*child).vm;
  assert_eq!(process_helpers::release_thread_checked(child),0);assert_eq!(release_vm(vm.cast()),0);assert_eq!(process_helpers::release_thread_checked(child),0);
  (*child).status=16;(*proc).status=8;assert_eq!((*child).refcount.counter,1);assert_eq!((*vm).refcount.counter,1);
  let f=fork_control_guest::runnable::prepare_wait_reap;
  assert!(matches!(f(parent,(*parent).proc,proc,900,0x01000000,900),fork_control_guest::runnable::WaitReap::Ordinary));
  let parent_proc=(*parent).proc;(*parent_proc).stime_children.tv_sec=1;(*parent_proc).stime_children.tv_nsec=900000000;
  (*parent_proc).utime_children.tv_sec=1;(*proc).stime.tv_sec=2;(*proc).stime.tv_nsec=900000000;
  (*proc).stime_children.tv_sec=3;(*proc).stime_children.tv_nsec=200000000;
  (*proc).utime.tv_sec=4;(*proc).utime.tv_nsec=2500;(*proc).utime_children.tv_sec=1;(*proc).utime_children.tv_nsec=999998000;
  (*proc).maxrss=8192;(*proc).maxrss_children=16384;
  let offsets=wait_offsets();let mut usage:RUsage=core::mem::zeroed();let mut lock_node:u64=0;
  let children_lock=(&raw mut (*parent_proc).children_lock).cast();CHILD_LOCK.store(children_lock as usize,Ordering::SeqCst);
  assert_eq!(syscall_policy::actual_owned_wait_branch(parent.cast(),parent_proc.cast(),proc.cast(),900,0,900,(&mut usage as *mut RUsage).cast(),
   &offsets,children_lock,(&mut lock_node as *mut u64).cast(),(&mut lock_node as *mut u64).cast(),wait_lock,wait_unlock,wait_detach,wait_release),900);
  assert_eq!(((*parent_proc).stime_children.tv_sec,(*parent_proc).stime_children.tv_nsec),(8,0));
  assert_eq!(((*parent_proc).utime_children.tv_sec,(*parent_proc).utime_children.tv_nsec),(7,500));
  assert_eq!((*parent_proc).maxrss_children,16384);assert_eq!((usage.ru_utime.tv_sec,usage.ru_utime.tv_usec),(4,2));
  assert_eq!((usage.ru_stime.tv_sec,usage.ru_stime.tv_usec),(2,900000));assert_eq!(usage.ru_maxrss,8);
  assert_eq!(*WAIT_EVENTS.lock().unwrap(),vec![1,2,3,4]);
  assert!(!matches!(f(parent,(*parent).proc,proc,900,0,900),fork_control_guest::runnable::WaitReap::Prepared(_)));assert_eq!((*proc).refcount.counter,1);
  assert_eq!((*proc).hash_list.next,&mut (*proc).hash_list as *mut _);assert_eq!((*(*parent).proc).children_list.next,&mut (*(*parent).proc).children_list as *mut _);
  assert_eq!((THREAD.load(Ordering::SeqCst),VM.load(Ordering::SeqCst),PROCESS.load(Ordering::SeqCst),PAGES.load(Ordering::SeqCst),CPU.load(Ordering::SeqCst)),(0,0,0,0,0));
  assert_eq!(fork_control_registry::visit(out.handle,|_|0),0); // all uncertain/final owners remain retained
  let(_,parent,child)=run(0);let proc=(*child).proc;(*proc).status=8;
  assert!(matches!(f(parent,(*parent).proc,proc,900,0,-10),fork_control_guest::runnable::WaitReap::Retained(-10)));
  assert!(matches!(f(parent,(*parent).proc,proc,900,0,900),fork_control_guest::runnable::WaitReap::Retained(-10)));
  assert_eq!((*proc).refcount.counter,2);assert_ne!((*(*parent).proc).children_list.next,&mut (*(*parent).proc).children_list as *mut _);
 }}

 pub fn cascade_event(_event:u32){assert_eq!(CHILD_LOCK.load(Ordering::SeqCst),0);}
 pub fn vm_final(){VM.fetch_add(1,Ordering::SeqCst);}
 unsafe fn exit_before_switch(child:*mut Thread){
  let vm=(*child).vm;let proc=(*child).proc;
  // Existing exit consumes one ordinary Thread and its separate VM edge.
  assert_eq!(process_helpers::release_thread_checked(child),0);assert_eq!(release_vm(vm.cast()),0);
  (*child).status=16;(*proc).status=8;
 }
 unsafe fn exit_after_switch(child:*mut Thread){
  // Explicit platform frontier adapter: real schedule removed this exited
  // thread and switched current before the actual cleanup body is invoked.
  process_helpers::process_list_detach_result(&raw mut (*child).sched_list);
  init(&raw mut (*child).sched_list);(*target()).runq_len-=1;
  sched_helpers::sched_schedule_exit_cleanup(target(),child,16,core::ptr::null());
 }
 unsafe fn actual_reap(parent:*mut Thread,child:*mut Thread){
  let proc=(*child).proc;let parent_proc=(*parent).proc;let offsets=wait_offsets();let mut node:u64=0;
  let lock=(&raw mut (*parent_proc).children_lock).cast();CHILD_LOCK.store(lock as usize,Ordering::SeqCst);
  assert_eq!(syscall_policy::actual_owned_wait_branch(parent.cast(),parent_proc.cast(),proc.cast(),900,0,900,core::ptr::null_mut(),
   &offsets,lock,(&mut node as *mut u64).cast(),(&mut node as *mut u64).cast(),wait_lock,wait_unlock,wait_detach,wait_release),900);
 }
 #[test]fn retirement_wait_first_later_actual_switch_then_parent_entry_acks_once(){unsafe{
  let baseline=mem_helpers::live();let(out,parent,child)=run(20);exit_before_switch(child);actual_reap(parent,child);
  assert_eq!(CALLS.load(Ordering::SeqCst),2);assert_eq!((*parent).refcount.counter,2);
  assert_eq!(fork_control_guest::runnable::process_fork_runtime_drain_current_v1(),0);
  exit_after_switch(child);assert_eq!(fork_control_registry::runtime_exit_observed(out.handle,child as usize),Ok(true));
  assert_eq!(fork_control_guest::runnable::process_fork_runtime_drain_current_v1(),1);
  assert_eq!((CALLS.load(Ordering::SeqCst),THREAD.load(Ordering::SeqCst),VM.load(Ordering::SeqCst),PROCESS.load(Ordering::SeqCst),PAGES.load(Ordering::SeqCst),CPU.load(Ordering::SeqCst)),(4,1,1,1,1,0));
  assert_eq!((*parent).refcount.counter,1);assert_eq!(mem_helpers::live(),baseline);
  assert!(fork_control_registry::visit(out.handle,|_|0)<0);
  assert_eq!(fork_control_guest::runnable::process_fork_runtime_drain_current_v1(),0);assert_eq!(CALLS.load(Ordering::SeqCst),4);
 }}
 #[test]fn retirement_switch_first_wait_commit_drains_outside_locks(){unsafe{
  let baseline=mem_helpers::live();let(out,parent,child)=run(21);exit_before_switch(child);exit_after_switch(child);
  assert_eq!(fork_control_guest::runnable::process_fork_runtime_drain_current_v1(),0);assert_eq!(CALLS.load(Ordering::SeqCst),2);
  actual_reap(parent,child);assert_eq!(CALLS.load(Ordering::SeqCst),4);assert_eq!(mem_helpers::live(),baseline);
  assert_eq!((*parent).refcount.counter,1);assert!(fork_control_registry::visit(out.handle,|_|0)<0);assert_eq!(CPU.load(Ordering::SeqCst),0);
 }}
 #[test]fn retirement_revoke_refusal_retains_graph_requests_parent_and_no_ack(){unsafe{
  let baseline=mem_helpers::live();let(out,parent,child)=run(22);exit_before_switch(child);actual_reap(parent,child);exit_after_switch(child);
  assert_eq!(fork_control_guest::runnable::process_fork_runtime_drain_current_v1(),0);
  assert_eq!((CALLS.load(Ordering::SeqCst),THREAD.load(Ordering::SeqCst),VM.load(Ordering::SeqCst),PROCESS.load(Ordering::SeqCst),CPU.load(Ordering::SeqCst)),(3,0,0,0,0));
  assert_eq!((*child).refcount.counter,1);assert_eq!((*parent).refcount.counter,2);assert!(mem_helpers::live()>baseline);assert_eq!(fork_control_registry::visit(out.handle,|_|0),0);
  assert_eq!(fork_control_guest::runnable::process_fork_runtime_drain_current_v1(),0);assert_eq!(CALLS.load(Ordering::SeqCst),3);
 }}
 #[test]fn retirement_ack_refusal_or_scalar_without_actual_hook_never_releases_parent(){unsafe{
  for mode in [23,24]{let baseline=mem_helpers::live();let(out,parent,child)=run(mode);exit_before_switch(child);actual_reap(parent,child);exit_after_switch(child);
   assert_eq!(fork_control_guest::runnable::process_fork_runtime_drain_current_v1(),0);
   assert_eq!((CALLS.load(Ordering::SeqCst),THREAD.load(Ordering::SeqCst),VM.load(Ordering::SeqCst),PROCESS.load(Ordering::SeqCst),PAGES.load(Ordering::SeqCst),CPU.load(Ordering::SeqCst)),(4,1,1,1,1,0));
   // Child storage is dead: only the independent retained parent/slot/requests
   // are observed here. There is no repeated checked release or dead read.
   assert_eq!((*parent).refcount.counter,2);assert!(mem_helpers::live()>baseline);assert_eq!(fork_control_registry::visit(out.handle,|_|0),0);
   assert_eq!(fork_control_guest::runnable::process_fork_runtime_drain_current_v1(),0);assert_eq!(CALLS.load(Ordering::SeqCst),4);
  }
 }}
 #[test]fn retirement_vm_final_without_nested_process_final_forbids_ack(){unsafe{
  let(out,parent,child)=run(25);let proc=(*child).proc;
  // An independent adversarial storage pin, not constructor/release authority.
  core::sync::atomic::AtomicI32::from_ptr(&raw mut (*proc).refcount.counter).fetch_add(1,Ordering::SeqCst);
  exit_before_switch(child);actual_reap(parent,child);exit_after_switch(child);
  assert_eq!(fork_control_guest::runnable::process_fork_runtime_drain_current_v1(),0);
  assert_eq!((CALLS.load(Ordering::SeqCst),THREAD.load(Ordering::SeqCst),VM.load(Ordering::SeqCst),PROCESS.load(Ordering::SeqCst),PAGES.load(Ordering::SeqCst),CPU.load(Ordering::SeqCst)),(3,1,1,0,0,0));
  assert_eq!((*proc).refcount.counter,1);assert_eq!((*parent).refcount.counter,2);assert_eq!(fork_control_registry::visit(out.handle,|_|0),0);
  assert_eq!(fork_control_guest::runnable::process_fork_runtime_drain_current_v1(),0);assert_eq!(CALLS.load(Ordering::SeqCst),3);
 }}
 #[test]fn retirement_wrong_parent_or_unfinished_publication_never_offloads(){unsafe{
  let(out,parent,child)=run(26);exit_before_switch(child);actual_reap(parent,child);exit_after_switch(child);
  let local=cls::get_this_cpu_local_var();let stranger=Box::into_raw(Box::new(core::mem::zeroed::<Thread>()));(*stranger).proc=(*parent).proc;
  (*local).current=stranger;assert_eq!(fork_control_guest::runnable::process_fork_runtime_drain_current_v1(),0);(*local).current=parent;
  // Actual publication may still own a mutable graph. Carrier metadata alone
  // must prevent any graph read, revoke, release or ACK during that scope.
  assert_eq!(fork_control_registry::visit(out.handle,|c|{fork_control_guest::runnable::fixture_publication_pending(c);0}),0);
  assert_eq!(fork_control_guest::runnable::process_fork_runtime_drain_current_v1(),0);assert_eq!(CALLS.load(Ordering::SeqCst),2);assert_eq!((*child).refcount.counter,1);
 }}

 #[test]fn retirement_exited_parent_or_disabled_irq_never_offloads(){unsafe{
  let(out,parent,child)=run(27);exit_before_switch(child);actual_reap(parent,child);exit_after_switch(child);
  let proc=(*parent).proc;
  for (thread_status,process_status,irq)in[(16,0,0),(0,16,0),(8,0,0),(0,8,0),(0,0,1)]{
   (*parent).status=thread_status;(*proc).status=process_status;IRQ_DISABLED.store(irq,Ordering::SeqCst);
   assert_eq!(fork_control_guest::runnable::process_fork_runtime_drain_current_v1(),-13);
   assert_eq!(CALLS.load(Ordering::SeqCst),2);assert_eq!((*child).refcount.counter,1);assert_eq!((*parent).refcount.counter,2);
   assert_eq!(fork_control_registry::visit(out.handle,|_|0),0);
  }
  (*parent).status=0;(*proc).status=0;IRQ_DISABLED.store(0,Ordering::SeqCst);
  assert_eq!(fork_control_guest::runnable::process_fork_runtime_drain_current_v1(),1);assert_eq!(CPU.load(Ordering::SeqCst),0);
 }}
 #[test]fn retirement_nested_same_parent_drain_refuses_but_other_parent_is_independent(){unsafe{
  let baseline=mem_helpers::live();let(_,parent,child)=run(28);exit_before_switch(child);actual_reap(parent,child);exit_after_switch(child);
  assert_eq!(fork_control_guest::runnable::process_fork_runtime_drain_current_v1(),1);
  assert_eq!(CALLS.load(Ordering::SeqCst),4);assert_eq!(mem_helpers::live(),baseline);assert_eq!((*parent).refcount.counter,1);
  // RAII claim was released even though its last Carrier was detached/freed.
  let again=fork_control_registry::claim_parent_drain(parent as usize).unwrap();drop(again);
  assert_eq!(fork_control_guest::runnable::process_fork_runtime_drain_current_v1(),0);
 }}

 include!("panic-free-cases.inc");

}

#[no_mangle]unsafe extern "C" fn arch_flush_icache_all(){}
#[no_mangle]unsafe extern "C" fn release_thread(p:*mut c_void){process_helpers::release_thread(p.cast());}
#[no_mangle]unsafe extern "C" fn rusage_num_threads_dec(){}
#[export_name="kprintf"]extern "C" fn fixture_unexpected_kprintf()->i32{std::process::abort()}
