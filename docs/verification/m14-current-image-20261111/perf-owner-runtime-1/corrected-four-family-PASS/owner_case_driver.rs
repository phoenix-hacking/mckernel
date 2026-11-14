// Four finite actual-source functional families. Controlled lower primitives
// do not implement registry, event, map, pin, gate, group or cleanup semantics.
use crate::abi::*;
use core::ffi::c_void;
use core::mem::{size_of,offset_of,MaybeUninit};
use core::ptr::{addr_of_mut,read_volatile};
use super::super::f03_sync_child_layout_v2::FullMcPerfEvent as Event;
use crate::f03_perf_attr_callbacks::PerfEventAttr;

struct Actor{process:Box<Process>,thread:Box<Thread>,vm:Box<ProcessVm>}
impl Actor{
 unsafe fn new(pid:CInt)->Self{
  // ABI source consists of integer/union integer and raw pointer fields. These
  // controlled actors are newly initialized/quarantined HOST backing only.
  let mut value=Self{process:Box::new(unsafe{MaybeUninit::<Process>::zeroed().assume_init()}),
   thread:Box::new(unsafe{MaybeUninit::<Thread>::zeroed().assume_init()}),
   vm:Box::new(unsafe{MaybeUninit::<ProcessVm>::zeroed().assume_init()})};
  value.process.pid=pid;value.process.refcount.counter=1;value.thread.refcount.counter=1;value.vm.refcount.counter=1;
  value.thread.proc=&mut *value.process;value.thread.vm=&mut *value.vm;value.process.vm=&mut *value.vm;value.vm.proc=(&mut *value.process as *mut Process).cast::<c_void>();
  crate::host_effects::register_p_lock(addr_of_mut!(value.process.mckfd_lock));
  unsafe{crate::host_effects::register_process(pid,&mut *value.process)};
  value
 }
 fn raw(&mut self)->*mut Thread{&mut *self.thread}
 unsafe fn prepare(&mut self){let raw=self.raw();unsafe{super::prepare_thread(raw,2).expect("actual Thread metadata");super::prepare_created_thread(raw,2).expect("actual Process binding")};}
}
unsafe fn configuration(thread:*mut Thread,request:*mut SyscallRequest,attribute:*mut PerfEventAttr)->super::Open{
 let (read,ioctl,mmap,close,fcntl)=super::entry::host_callbacks();
 super::Open{
 request,thread:thread.cast(),proc:unsafe{(*thread).proc.cast()},attr:attribute.cast(),pid:0,group_fd:-1,
 perf_event_open_nr:298,cpu:0,mckfd_size:size_of::<Mckfd>(),mckfd_alloc_flags:2,
 event_pid_offset:offset_of!(Event,pid),event_counter_id_offset:offset_of!(Event,counter_id),
 proc_mckfd_offset:offset_of!(Process,mckfd),mckfd_next_offset:offset_of!(Mckfd,next),mckfd_fd_offset:offset_of!(Mckfd,fd),mckfd_data_offset:offset_of!(Mckfd,data),
 event_group_leader_offset:offset_of!(Event,group_leader),event_sibling_list_offset:offset_of!(Event,sibling_list),
 event_group_entry_offset:offset_of!(Event,group_entry),event_nr_siblings_offset:offset_of!(Event,nr_siblings),event_pmc_status_offset:offset_of!(Event,pmc_status),
 thread_pmc_alloc_map_offset:offset_of!(Thread,pmc_alloc_map),proc_mckfd_lock_offset:offset_of!(Process,mckfd_lock),mckfd_sig_no_offset:offset_of!(Mckfd,padding),
 mckfd_read_cb_offset:offset_of!(Mckfd,read_cb),mckfd_ioctl_cb_offset:offset_of!(Mckfd,ioctl_cb),mckfd_mmap_cb_offset:offset_of!(Mckfd,mmap_cb),
 mckfd_close_cb_offset:offset_of!(Mckfd,close_cb),mckfd_fcntl_cb_offset:offset_of!(Mckfd,fcntl_cb),
 event_alloc_fn:Some(super::super::f03_perf_alloc_entry_v1::f03_perf_event_allocate_v1),
 counter_alloc_fn:Some(super::super::f03_perf_counter_allocate_v1::f03_perf_counter_allocate_v1),
 syscall_fn:Some(super::super::do_syscall),mckfd_alloc_fn:Some(super::super::syscall_alloc_bridge),
 read_fn:Some(read),ioctl_fn:Some(ioctl),mmap_fn:Some(mmap),close_fn:Some(close),fcntl_fn:Some(fcntl),
 lock_fn:Some(super::super::syscall_mckfd_lock_bridge),unlock_fn:Some(super::super::syscall_mckfd_unlock_bridge),
 }
}
unsafe fn attribute()->PerfEventAttr{let mut attr=unsafe{MaybeUninit::<PerfEventAttr>::zeroed().assume_init()};attr.type_=4;attr.size=size_of::<PerfEventAttr>() as u32;attr.config=1;attr.flags=2;attr}
unsafe fn context(args:[CULong;6])->X86UserContext{
 let mut ctx=unsafe{MaybeUninit::<X86UserContext>::zeroed().assume_init()};ctx.is_gpr_valid=1;
 unsafe{crate::x86_cpu_helpers::ihk_mc_syscall_set_arg0(&mut ctx,args[0]);crate::x86_cpu_helpers::ihk_mc_syscall_set_arg1(&mut ctx,args[1]);
 crate::x86_cpu_helpers::ihk_mc_syscall_set_arg2(&mut ctx,args[2]);crate::x86_cpu_helpers::ihk_mc_syscall_set_arg3(&mut ctx,args[3]);
 crate::x86_cpu_helpers::ihk_mc_syscall_set_arg4(&mut ctx,args[4]);crate::x86_cpu_helpers::ihk_mc_syscall_set_arg5(&mut ctx,args[5]);}ctx
}
unsafe fn pin(process:*mut Process,fd:CInt)->super::DescriptorPin{
 let p=unsafe{addr_of_mut!((*process).mckfd_lock)};let f=unsafe{super::super::syscall_mckfd_lock_bridge(p.cast())};
 let mut row=unsafe{(*process).mckfd.cast::<Mckfd>()};while !row.is_null()&&unsafe{(*row).fd!=fd}{row=unsafe{(*row).next};}
 let pin=unsafe{super::descriptors::pin_managed_locked(process,row)};
 unsafe{super::super::syscall_mckfd_unlock_bridge(p.cast(),f)};pin.expect("managed pin acquisition").expect("actual managed kind")
}
// Only scalar/array/nested scalar observation structs are serialized. This
// formatter changes Debug's field labels/type labels into JSON syntax; it
// cannot synthesize a predicate, omit a field or turn a failed assertion true.
fn scalar_observation_json(debug:&str)->String{
 let bytes=debug.as_bytes();let mut at=0;let mut out=String::new();
 while at<bytes.len(){
  let ch=bytes[at];
  if ch.is_ascii_alphabetic()||ch==b'_'{
   let start=at;while at<bytes.len()&&(bytes[at].is_ascii_alphanumeric()||bytes[at]==b'_'){at+=1;}
   let token=&debug[start..at];let mut next=at;while next<bytes.len()&&bytes[next].is_ascii_whitespace(){next+=1;}
   if next<bytes.len()&&bytes[next]==b'{'{at=next;continue;}
   if next<bytes.len()&&bytes[next]==b':'{out.push('"');out.push_str(token);out.push('"');}
   else{assert!(token=="true"||token=="false","non-scalar observation token");out.push_str(token);}
  }else{assert!(ch.is_ascii_whitespace()||ch.is_ascii_digit()||b"{}[],:-".contains(&ch),"non-scalar observation byte");out.push(ch as char);at+=1;}
 }
 out
}
fn emit(name:&str,json:&str){println!("{{\"family\":\"{}\",\"observation\":{}}}",name,json);}

pub(crate) unsafe fn run(){
 crate::host_perf_bindings::configure_raw_event_for_fixture();
 crate::host_effects::register_lock(super::descriptors::host_registry_lock_address(),crate::host_effects::LockClass::Registry);
 assert_eq!(size_of::<SyscallRequest>(),72);assert_eq!(core::mem::align_of::<SyscallRequest>(),8);
 // Remote positive reference controls exercise the complete actual CAS helper
 // and unchanged full F02 release body; no lower lookup mutates a refcount.
 let mut positive=unsafe{Actor::new(1001)};let mut zero=unsafe{Actor::new(1002)};let mut overflow=unsafe{Actor::new(1003)};
 zero.process.refcount.counter=0;overflow.process.refcount.counter=CInt::MAX;
 let mut node=MaybeUninit::<crate::lock_helpers::McsRwlockNodeIrqsave>::uninit();
 crate::host_effects::reset_trace();
 let target=unsafe{super::target_family::exercise_actual_positive_target([1001,1002,1003],
 [&mut *positive.process,&mut *zero.process,&mut *overflow.process],node.as_mut_ptr().cast(),
 crate::host_effects::find_process,crate::host_effects::unlock_process)};
 assert_eq!(target.positive_body_ref,2);assert_eq!(target.positive_result,-4_294_967_301);assert_eq!(target.positive_final_ref,1);
 assert_eq!(target.zero_error,-22);assert_eq!(target.zero_body_calls,0);assert_eq!(target.zero_final_ref,0);
 assert_eq!(target.overflow_error,-22);assert_eq!(target.overflow_body_calls,0);assert_eq!(target.overflow_final_ref,CInt::MAX);
 let tr=crate::host_effects::snapshot();
 let order:Vec<&str>=tr.iter().filter_map(|v|match v{crate::host_effects::Effect::HashFind{..}=>Some("find"),crate::host_effects::Effect::HashUnlock{..}=>Some("unlock"),crate::host_effects::Effect::Marker(s) if s=="target_body"=>Some("body"),crate::host_effects::Effect::Marker(s) if s=="actual_release_process_body"=>Some("release"),_=>None}).collect();
 assert_eq!(order,vec!["find","unlock","body","release","find","unlock","find","unlock"]);
 let mut tool=unsafe{Actor::new(1101)};let mut remote=unsafe{Actor::new(1102)};let mut child=unsafe{Actor::new(1103)};
 unsafe{tool.prepare();remote.prepare();crate::host_effects::set_current(tool.raw());}
 let mut request=unsafe{MaybeUninit::<SyscallRequest>::zeroed().assume_init()};let mut attr=unsafe{attribute()};
 let mut cfg=unsafe{configuration(tool.raw(),&mut request,&mut attr)};cfg.pid=remote.process.pid;
 crate::host_effects::set_host_replies(&[801]);crate::host_effects::set_forward_replies(&[0]);
 assert_eq!(unsafe{super::open_from_body(cfg)},801);unsafe{super::host_register_event_state(&mut *tool.process,801)};
 let storage=unsafe{pin(&mut *tool.process,801)};
 let mut enable=unsafe{context([0,0x2400,0,0,0,0])};let mut close=unsafe{context([801,0,0,0,0,0])};
 let monitor=unsafe{super::monitor_family::exercise_monitor_family(tool.raw(),remote.raw(),child.raw(),storage,&mut enable,&mut close)};
 assert_eq!(monitor,super::monitor_family::EXPECTED_MONITOR_OBSERVATION);
 emit("positive-target-and-monitor",&format!("{{\"target\":{},\"monitor\":{}}}",scalar_observation_json(&format!("{target:?}")),scalar_observation_json(&format!("{monitor:?}"))));

 let mut counter_tool=unsafe{Actor::new(1201)};let mut actor=unsafe{Actor::new(1202)};let mut inherited=unsafe{Actor::new(1203)};
 unsafe{counter_tool.prepare();actor.prepare();crate::host_effects::set_current(counter_tool.raw());}
 let cfg=unsafe{configuration(counter_tool.raw(),&mut request,&mut attr)};
 let counters=unsafe{super::counter_epoch_family::exercise_counter_epoch_family(counter_tool.raw(),actor.raw(),inherited.raw(),cfg)};
 assert_eq!(counters,super::counter_epoch_family::EXPECTED_COUNTER_EPOCH_OBSERVATION);emit("executing-thread-and-captured-epoch",&scalar_observation_json(&format!("{counters:?}")));

 let mut vm_actor=unsafe{Actor::new(1301)};unsafe{vm_actor.prepare();crate::host_effects::set_current(vm_actor.raw());}
 let cfg=unsafe{configuration(vm_actor.raw(),&mut request,&mut attr)};
 let vm=unsafe{super::vm_drain_family::exercise_vm_drain_family(vm_actor.raw(),cfg)};
 assert_eq!(vm,super::vm_drain_family::EXPECTED_VM_DRAIN_OBSERVATION);emit("p-held-vm-drain-and-last-pin",&scalar_observation_json(&format!("{vm:?}")));

 // UNKNOWN lower host-close debt is the last family and remains explicit. No
 // idle retry/false cleanup or native-host-FD acceptance follows this model.
 let mut rollback_actor=unsafe{Actor::new(1401)};unsafe{rollback_actor.prepare();crate::host_effects::set_current(rollback_actor.raw());}
 let cfg=unsafe{configuration(rollback_actor.raw(),&mut request,&mut attr)};
 let rollback=unsafe{super::rollback_family::exercise_rollback_family(rollback_actor.raw(),cfg)};
 assert_eq!(rollback,super::rollback_family::EXPECTED_ROLLBACK_OBSERVATION);emit("allocation-group-hostfd-rollback",&scalar_observation_json(&format!("{rollback:?}")));
 assert!(crate::host_effects::held_locks().is_empty());assert!(crate::host_effects::hash_borrows_held().is_empty());assert!(crate::host_effects::irq_enabled());
 assert_eq!(crate::platform_bindings::SCHEDULE_CALLS.load(core::sync::atomic::Ordering::SeqCst),0);
 // All backing remains quarantined through every observation and genuine hook.
 let _keep=(positive,zero,overflow,tool,remote,child,counter_tool,actor,inherited,vm_actor,rollback_actor,request,attr);
}
