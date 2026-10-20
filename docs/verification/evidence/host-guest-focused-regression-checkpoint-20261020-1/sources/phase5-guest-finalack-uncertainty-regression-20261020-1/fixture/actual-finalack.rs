#![allow(dead_code)]
// Actual production guest/graph/registry and checked Thread/Process bodies.
// EXPLICIT adapters: C constructor, VM release callback, physical mapping and
// host transport. This proves source semantics, NOT Linux/kernel ABI or MM.
mod abi;mod process_helpers;mod fork_control_registry;mod fork_control_guest;mod x86_cpu_helpers;
mod application_rpc;mod application_syscall;mod sched_helpers;mod syscall_policy;mod lock_helpers;
use std::sync::atomic::{AtomicUsize,AtomicPtr,AtomicU64,Ordering};
use core::ffi::c_void;
fn unexpected_destructor(){panic!("unexpected final parent destructor")}
mod cls{
 use super::*;static CURRENT:AtomicPtr<abi::CpuLocalVar>=AtomicPtr::new(core::ptr::null_mut());
 pub unsafe fn preempt_disable(){} pub unsafe fn preempt_enable(){}
 pub unsafe fn set(p:*mut abi::CpuLocalVar){CURRENT.store(p,Ordering::SeqCst);}
 pub unsafe fn get_this_cpu_local_var()->*mut abi::CpuLocalVar{CURRENT.load(Ordering::SeqCst)}
}
mod x86_memory_helpers{pub unsafe fn write_process_vm(_: *mut crate::abi::ProcessVm,_:*mut core::ffi::c_void,_:*const core::ffi::c_void,_:usize)->i32{panic!("runtime VM write outside normal-fork test scope")}pub unsafe fn virt_to_phys(p:*mut core::ffi::c_void)->u64{p as u64}}
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
#[no_mangle]unsafe extern "C" fn clone_thread(p:*mut abi::Thread,_:u64,_:u64,_:i32)->*mut abi::Thread{phase5_tests::construct(p)}
#[no_mangle]unsafe extern "C" fn release_cpuid(cpu:i32){assert_eq!(cpu,1);phase5_tests::CPU.fetch_add(1,Ordering::SeqCst);}
extern "C"{fn process_fork_construct_current_v1(p:*mut abi::Thread,pc:u64,sp:u64,f:i32,cpu:i32,out:*mut *mut c_void)->*mut abi::Thread;}
mod phase5_tests{
 pub fn mode()->usize{panic!("runtime scheduler outside normal-fork test scope")}pub fn target()->*mut crate::abi::CpuLocalVar{panic!("runtime scheduler outside normal-fork test scope")}pub fn queued(){panic!("runtime scheduler outside normal-fork test scope")}
 use super::*;use abi::{Thread,Process,ProcessVm,AddressSpace,CpuLocalVar,SyscallRequest,SyscallResponse};
 static MODE:AtomicUsize=AtomicUsize::new(0);static CHILD:AtomicPtr<Thread>=AtomicPtr::new(core::ptr::null_mut());
 static CALLS:AtomicUsize=AtomicUsize::new(0);static THREAD:AtomicUsize=AtomicUsize::new(0);
 static VM:AtomicUsize=AtomicUsize::new(0);static PROCESS:AtomicUsize=AtomicUsize::new(0);static PAGES:AtomicUsize=AtomicUsize::new(0);
 pub(super) static CPU:AtomicUsize=AtomicUsize::new(0);
 pub unsafe fn construct(parent:*mut Thread)->*mut Thread{
  let child=Box::into_raw(Box::new(core::mem::zeroed::<Thread>()));
  assert_eq!(process_helpers::process_thread_alloc_init_body_result(child.cast(),core::mem::size_of::<Thread>() as u64,
   core::mem::offset_of!(Thread,refcount)as u64,core::mem::offset_of!(Thread,hash_list)as u64,
   core::mem::offset_of!(Thread,siblings_list)as u64,None),0);
  let proc=Box::into_raw(Box::new(core::mem::zeroed::<Process>()));let vm=Box::into_raw(Box::new(core::mem::zeroed::<ProcessVm>()));
  let asp=Box::into_raw(Box::new(core::mem::zeroed::<AddressSpace>()));(*asp).page_table=0x4000usize as *mut c_void;
  (*child).proc=proc;(*child).vm=vm;(*proc).refcount.counter=2;(*proc).parent=(*parent).proc;
  (*proc).main_thread=child;(*proc).vm=vm;(*vm).refcount.counter=1;(*vm).proc=proc.cast();(*vm).address_space=asp;
  (*vm).region.user_start=0x1000;(*vm).region.user_end=0x3000;CHILD.store(child,Ordering::SeqCst);child
 }
 pub fn thread_final(){THREAD.fetch_add(1,Ordering::SeqCst);}
 pub fn process_final(){PROCESS.fetch_add(1,Ordering::SeqCst);}
 pub fn pages_final(){PAGES.fetch_add(1,Ordering::SeqCst);}
 pub unsafe fn release_vm(p:*mut c_void)->i32{
  let vm=p.cast::<ProcessVm>();let old=AtomicU64::new(0);drop(old);
  let count=std::sync::atomic::AtomicI32::from_ptr(&raw mut (*vm).refcount.counter);
  if count.fetch_sub(1,Ordering::SeqCst)!=1{return 0;}
  VM.fetch_add(1,Ordering::SeqCst);
  let proc=(*vm).proc.cast::<Process>();assert_eq!(process_helpers::release_process_checked(proc),0);
  1
 }
 unsafe fn response(r:*mut SyscallRequest,cpu:i32,ret:i64){
  let parent=(*cls::get_this_cpu_local_var()).current;(*r).rtid=(*parent).tid;(*r).ttid=0;(*r).valid=0;
  let mut response:SyscallResponse=core::mem::zeroed();response.ret=ret;response.stid=321;
  AtomicU64::from_ptr(&raw mut response.status).store(1,Ordering::Release);
  fork_control_guest::observe_fork_control_reply(r,&mut response,cpu,parent);
 }
 pub unsafe fn transport(r:*mut SyscallRequest,cpu:i32)->i64{
  let nth=CALLS.fetch_add(1,Ordering::SeqCst)+1;assert_eq!(cpu,0);
  let frame=&mut*((*r).args[4]as *mut[u8;128]);
  let parent=(*cls::get_this_cpu_local_var()).current;(*r).rtid=(*parent).tid;(*r).ttid=0;(*r).valid=0;
  let mut response:SyscallResponse=core::mem::zeroed();response.stid=321;
  let physical=&mut response as *mut SyscallResponse as u64;
  if nth==1 {
   assert_eq!(frame[..8],*b"MCFKQ001");let nonce=u64::from_le_bytes(frame[24..32].try_into().unwrap());
   let mut packet=[0;128];packet[8..12].copy_from_slice(&4i32.to_le_bytes());packet[32..36].copy_from_slice(&1i32.to_le_bytes());
   packet[56..64].copy_from_slice(&1u64.to_le_bytes());packet[48..52].copy_from_slice(&(*r).rtid.to_le_bytes());packet[64..72].copy_from_slice(&56u64.to_le_bytes());
   for(i,arg)in(*r).args.iter().enumerate(){packet[72+i*8..80+i*8].copy_from_slice(&arg.to_le_bytes());}
   packet[120..128].copy_from_slice(&physical.to_le_bytes());
   let q=application_syscall::Request::decode(&packet,1).unwrap();
   let key=application_syscall::ForkFirstReceipt{slot:3,generation:5,parent:7,worker:11,delivery:13,child:17,
    child_pid:900,child_mm:0x9000,root:0x4000,start:0x1000,length:0x2000,nonce,response:physical};
   *frame=q.first_fork_receipt(&key).unwrap();response.ret=900;
  }else if nth==2 {
   assert_eq!((*r).args[0],2);
   if MODE.load(Ordering::SeqCst)==4{response.ret=-95;}else{
    frame[..8].copy_from_slice(b"MCFKR001");for(at,v)in[(8,19u64),(16,11),(24,23),(32,physical)]{frame[at..at+8].copy_from_slice(&v.to_le_bytes());}
    if MODE.load(Ordering::SeqCst)==1{(*(*CHILD.load(Ordering::SeqCst)).vm).refcount.counter+=1;}
    if MODE.load(Ordering::SeqCst)==2{(*(*CHILD.load(Ordering::SeqCst)).proc).refcount.counter+=1;}
   }
  }else{
   assert_eq!(nth,3);assert_eq!((*r).args[0],3);assert_eq!((*r).args[1],2);
   assert_eq!(frame[..8],*b"MCFKD001");assert_eq!(THREAD.load(Ordering::SeqCst),1);
   assert_eq!(VM.load(Ordering::SeqCst),1);assert_eq!(PROCESS.load(Ordering::SeqCst),1);assert_eq!(PAGES.load(Ordering::SeqCst),1);
   assert_eq!(CPU.load(Ordering::SeqCst),0);
   frame[..8].copy_from_slice(b"MCFKA001");for(at,v)in[(8,19u64),(16,11),(24,29),(32,physical)]{frame[at..at+8].copy_from_slice(&v.to_le_bytes());}
   if MODE.load(Ordering::SeqCst)==3{frame[120]^=1;}
   if MODE.load(Ordering::SeqCst)==5{return -5;}
   if MODE.load(Ordering::SeqCst)==6{return 0;}
  }
  AtomicU64::from_ptr(&raw mut response.status).store(1,Ordering::Release);
  fork_control_guest::observe_fork_control_reply(r,&mut response,cpu,parent);response.ret
 }
 unsafe fn run(mode:usize)->(fork_control_guest::child_credits::CallerForkOutcome,*mut Thread,usize){
  for a in [&CALLS,&THREAD,&VM,&PROCESS,&PAGES,&CPU]{a.store(0,Ordering::SeqCst);}MODE.store(mode,Ordering::SeqCst);
  let parent=Box::into_raw(Box::new(core::mem::zeroed::<Thread>()));(*parent).refcount.counter=1;(*parent).tid=19;
  (*parent).proc=Box::into_raw(Box::new(core::mem::zeroed::<Process>()));(*parent).vm=Box::into_raw(Box::new(core::mem::zeroed::<ProcessVm>()));
  let local=Box::into_raw(Box::new(core::mem::zeroed::<CpuLocalVar>()));(*local).current=parent;cls::set(local);
  let before=mem_helpers::live();let mut token=core::ptr::null_mut();let child=process_fork_construct_current_v1(parent,0,0,0,1,&mut token);
  assert!(!child.is_null());assert!(!token.is_null());
  let mut out=core::mem::zeroed();assert_eq!(fork_control_guest::child_credits::process_fork_owned_caller_current_v2(parent,child,1,0,token,&mut out),0);
  (out,parent,before)
 }
 #[test]fn phase4_real_guest_graph_ack_detaches_then_releases_cpu(){unsafe{
  let(out,p,before)=run(0);assert_eq!(out.disposition,2);assert_eq!(out.error,-11);assert_eq!(CALLS.load(Ordering::SeqCst),3);
  assert_eq!(CPU.load(Ordering::SeqCst),1);assert_eq!((*p).refcount.counter,1);assert_eq!(mem_helpers::live(),before);
  assert_eq!(fork_control_registry::visit(out.handle,|_|panic!("terminal allocation discoverable")),-2);
 }}
 #[test]fn phase4_vm_other_owner_retains_graph_cpu_and_parent(){unsafe{
  let(out,p,_)=run(1);assert_eq!(out.disposition,1);assert_eq!(out.error,-16);assert_eq!(CALLS.load(Ordering::SeqCst),2);
  assert_eq!(THREAD.load(Ordering::SeqCst),1);assert_eq!(VM.load(Ordering::SeqCst),0);assert_eq!(PROCESS.load(Ordering::SeqCst),0);
  assert_eq!(CPU.load(Ordering::SeqCst),0);assert_eq!((*p).refcount.counter,2);
 }}
 #[test]fn phase4_process_other_owner_forbids_final_ack_and_cpu_release(){unsafe{
  let(out,p,_)=run(2);assert_eq!(out.disposition,1);assert_eq!(CALLS.load(Ordering::SeqCst),2);
  assert_eq!(VM.load(Ordering::SeqCst),1);assert_eq!(PROCESS.load(Ordering::SeqCst),0);assert_eq!(PAGES.load(Ordering::SeqCst),0);
  assert_eq!(CPU.load(Ordering::SeqCst),0);assert_eq!((*p).refcount.counter,2);
 }}
 #[test]fn phase4_wrong_final_nonce_keeps_destroyed_graph_and_cpu(){unsafe{
  let(out,p,_)=run(3);assert_eq!(out.disposition,1);assert_eq!(CALLS.load(Ordering::SeqCst),3);
  assert_eq!(PROCESS.load(Ordering::SeqCst),1);assert_eq!(CPU.load(Ordering::SeqCst),0);assert_eq!((*p).refcount.counter,2);
 }}
 #[test]fn phase4_revoke_error_never_enters_guest_destructors(){unsafe{
  let(out,p,_)=run(4);assert_eq!(out.disposition,1);assert_eq!(out.error,-95);assert_eq!(CALLS.load(Ordering::SeqCst),2);
  assert_eq!(THREAD.load(Ordering::SeqCst),0);assert_eq!(VM.load(Ordering::SeqCst),0);assert_eq!(CPU.load(Ordering::SeqCst),0);assert_eq!((*p).refcount.counter,2);
 }}

 #[test]fn finalack_uncertainty_transport_error_retains_exact_owners(){unsafe{uncertain(5,-5)}}
 #[test]fn finalack_uncertainty_missing_publication_retains_exact_owners(){unsafe{uncertain(6,-13)}}
 unsafe fn uncertain(mode:usize,error:i32){
  let(out,parent,before)=run(mode);assert_eq!((out.disposition,out.error),(1,error));
  assert_eq!((THREAD.load(Ordering::SeqCst),VM.load(Ordering::SeqCst),PROCESS.load(Ordering::SeqCst),PAGES.load(Ordering::SeqCst)),(1,1,1,1));
  assert_eq!(CALLS.load(Ordering::SeqCst),3);assert_eq!(CPU.load(Ordering::SeqCst),0);assert_eq!((*parent).refcount.counter,2);
  assert_eq!(mem_helpers::live(),before+5);
  let owners=fork_control_guest::uncertainty_owners(out.handle).expect("retained allocation remains discoverable");
  assert!(owners.iter().all(|p|*p!=0));
  let mut unique=owners.to_vec();unique.sort();unique.dedup();assert_eq!(unique.len(),4);
  // A repeated actual production terminal call cannot reacquire the graph
  // permit, repeat destructive callbacks or manufacture successful retirement.
  assert_eq!(fork_control_guest::retry_final_ack(out.handle),-13);
  assert_eq!(fork_control_guest::uncertainty_owners(out.handle),Some(owners));
  assert_eq!(mem_helpers::live(),before+5);assert_eq!((*parent).refcount.counter,2);
  assert_eq!(CALLS.load(Ordering::SeqCst),3);assert_eq!(CPU.load(Ordering::SeqCst),0);
  assert_eq!((THREAD.load(Ordering::SeqCst),VM.load(Ordering::SeqCst),PROCESS.load(Ordering::SeqCst),PAGES.load(Ordering::SeqCst)),(1,1,1,1));
 }
 #[test]fn finalack_uncertainty_success_retires_once_and_retry_cannot_free(){unsafe{
  let(out,parent,before)=run(0);assert_eq!((out.disposition,out.error),(2,-11));
  assert_eq!(mem_helpers::live(),before);assert_eq!((*parent).refcount.counter,1);assert_eq!(CPU.load(Ordering::SeqCst),1);
  assert_eq!(fork_control_guest::retry_final_ack(out.handle),-2);
  assert_eq!(mem_helpers::live(),before);assert_eq!((*parent).refcount.counter,1);assert_eq!(CPU.load(Ordering::SeqCst),1);
  assert_eq!(CALLS.load(Ordering::SeqCst),3);
  assert_eq!((THREAD.load(Ordering::SeqCst),VM.load(Ordering::SeqCst),PROCESS.load(Ordering::SeqCst),PAGES.load(Ordering::SeqCst)),(1,1,1,1));
 }}
}
