// HOST-only typed lower PMU/usercopy/table bindings. NO ownership/group/ref,
// mapping/gate/lifetime/waitq/schedule body is implemented or replaced here.
// Common P04 projector appends PRIVATE_TABLE_TAILS inside the named ORIGINAL
// modules and REAL_X86_SOURCE_TAIL inside its x86_perfctr binding module.
// Real ownership source remains compiler-scheduler cbea/23c297 +events15979.
use core::cell::RefCell;
use core::ffi::c_void;
use core::mem::{offset_of,size_of};
use core::sync::atomic::{AtomicI64,Ordering};
use std::collections::VecDeque;
use crate::abi::{CInt,CLong,CULong,SizeT,Thread,X86UserContext};

#[derive(Clone,Copy,Debug,PartialEq,Eq)]
pub enum MapKind { Hardware,Cache,CacheExtra,Raw }
#[derive(Clone,Debug,PartialEq,Eq)]
pub enum PerfEffect {
 MaskCheck{mask:CULong,result:CInt},
 InitRaw{counter:CInt,code:CULong,mode:CInt,result:CInt},
 CounterStart{mask:CULong,result:CInt},
 CounterStop{mask:CULong,flags:CInt,result:CInt},
 CounterRead{counter:CInt,value:CULong},
 ExtraReserved{event:usize,index:CInt,register:u32,config:CULong,result:CInt},
 SetPeriod{event:usize,result:CInt},
 EventUpdate{event:usize,result:CULong},
 HwInitialize{event:usize,result:CInt},
 AtomicRead{address:usize,value:CLong},
 AtomicSet{address:usize,value:CLong},
 Map{kind:MapKind,input:CULong,value:CULong},
 Validate{code:CULong,result:CInt},
 ExtraId{code:CULong,extra:CULong,id:CInt},
 LegacyCounterAllocate{thread:usize,event:usize},
 LegacyExtraSet{event:usize},
 CopyToUser{destination:CULong,bytes:Vec<u8>,result:CLong},
 Mmap{address:CULong,length:SizeT,prot:CInt,flags:CInt,fd:CInt,offset:CLong,result:CLong},
 ContextForward{number:CInt,fd:CULong,result:CLong},
 HookFired,
}
struct Lower {
 trace:Vec<PerfEffect>, facts:Option<(CInt,CULong,CULong)>,
 init:VecDeque<CInt>,start:VecDeque<CInt>,stop:VecDeque<CInt>,read:VecDeque<CULong>,extra:VecDeque<CInt>,
 maps:Vec<(MapKind,CULong,CULong)>,validate:Vec<(CULong,CInt)>,
 extra_descriptors:Vec<(CULong,CULong,CInt,u32,CInt)>,
 user_ranges:Vec<(usize,usize)>,copy_results:VecDeque<CLong>,mmap_results:VecDeque<CLong>,forward:VecDeque<CLong>,
 hook:Option<unsafe fn()>,
}
impl Default for Lower {
 fn default()->Self { Self{trace:Vec::new(),facts:None,init:VecDeque::new(),start:VecDeque::new(),stop:VecDeque::new(),read:VecDeque::new(),extra:VecDeque::new(),maps:Vec::new(),validate:Vec::new(),extra_descriptors:Vec::new(),user_ranges:Vec::new(),copy_results:VecDeque::new(),mmap_results:VecDeque::new(),forward:VecDeque::new(),hook:None} }
}
thread_local!{static LOWER:RefCell<Lower>=RefCell::new(Lower::default());}
fn record(effect:PerfEffect){LOWER.with(|x|x.borrow_mut().trace.push(effect));}
fn setup(){crate::host_effects::assert_effects_unlocked("PMU/usercopy fixture setup");}
fn pmu_context(){
 assert!(crate::host_effects::hash_borrows_held().is_empty(),"PMU under hash borrow");
 let locks=crate::host_effects::held_locks();
 assert!(locks.is_empty()||(locks.len()==1&&locks[0].class==crate::host_effects::LockClass::State),"PMU under P/R or nested S");
}
pub fn perf_trace()->Vec<PerfEffect>{LOWER.with(|x|x.borrow().trace.clone())}
/// Trace only. Never reset live ownership objects, counters or pending scripts.
pub fn reset_perf_trace(){setup();LOWER.with(|x|{let mut x=x.borrow_mut();assert!(x.hook.is_none(),"discarding pending unlocked hook");x.trace.clear();});}
pub fn configure_pmu(counters:CInt,programmable:CULong,fixed:CULong){setup();assert!(counters>0&&counters<=CULong::BITS as CInt);LOWER.with(|x|x.borrow_mut().facts=Some((counters,programmable,fixed)));}
pub fn set_init_results(v:&[CInt]){setup();LOWER.with(|x|x.borrow_mut().init=v.iter().copied().collect());}
pub fn set_start_results(v:&[CInt]){setup();LOWER.with(|x|x.borrow_mut().start=v.iter().copied().collect());}
pub fn set_stop_results(v:&[CInt]){setup();LOWER.with(|x|x.borrow_mut().stop=v.iter().copied().collect());}
pub fn set_read_results(v:&[CULong]){setup();LOWER.with(|x|x.borrow_mut().read=v.iter().copied().collect());}
pub fn set_extra_results(v:&[CInt]){setup();LOWER.with(|x|x.borrow_mut().extra=v.iter().copied().collect());}
pub fn set_map_entries(kind:MapKind,v:&[(CULong,CULong)]){setup();LOWER.with(|x|{let mut x=x.borrow_mut();x.maps.retain(|r|r.0!=kind);x.maps.extend(v.iter().map(|(a,b)|(kind,*a,*b)));});}
pub fn set_validate_entries(v:&[(CULong,CInt)]){setup();LOWER.with(|x|x.borrow_mut().validate=v.to_vec());}
pub fn set_extra_descriptors(v:&[(CULong,CULong,CInt,u32,CInt)]){setup();LOWER.with(|x|x.borrow_mut().extra_descriptors=v.to_vec());}
/// Explicit device input for the common fixture's raw type4/config1/flags2.
/// It says nothing about native PMU support; no success reply script is seeded.
pub fn configure_raw_event_for_fixture(){configure_pmu(4,0x0f,0);set_map_entries(MapKind::Raw,&[(1,1)]);set_validate_entries(&[(1,1)]);set_extra_descriptors(&[(1,0,-1,0,0)]);}
pub fn arm_after_state_unlock(hook:unsafe fn()){setup();LOWER.with(|x|{let mut x=x.borrow_mut();assert!(x.hook.is_none(),"one-shot hook already armed");x.hook=Some(hook);});}
pub fn hook_pending()->bool{LOWER.with(|x|x.borrow().hook.is_some())}
/// ONLY common's wrapper for a registered actual S unlock calls this, AFTER
/// a215 unlock restored IRQ state. Never called from a PMU provider callback.
pub fn after_state_unlock(){
 if !crate::host_effects::held_locks().is_empty()||!crate::host_effects::hash_borrows_held().is_empty()||!crate::host_effects::irq_enabled(){return;}
 let hook=LOWER.with(|x|x.borrow_mut().hook.take());
 if let Some(hook)=hook{record(PerfEffect::HookFired);unsafe{hook()};}
}
pub fn assert_no_legacy_calls(){assert!(!perf_trace().iter().any(|x|matches!(x,PerfEffect::LegacyCounterAllocate{..}|PerfEffect::LegacyExtraSet{..})),"managed fixture used unqualified legacy counter path");}

pub(crate) mod x86_perfctr {
 use super::*;
 // Exact existing x86_perfctr.rs representations; no invented padding/fields.
 #[repr(C,align(8))] pub struct PerfEventAttrOpaque{data:[u8;104]}
 #[repr(C)] pub struct HwPerfEventExtra{pub config:CULong,pub reg:u32,pub idx:CInt}
 #[repr(C)] pub struct McPerfEvent{pub attr:PerfEventAttrOpaque,pub extra_reg:HwPerfEventExtra,pub hw_config:CULong}
 pub unsafe extern "C" fn ihk_mc_perf_get_num_counters()->CInt{LOWER.with(|x|x.borrow().facts.expect("PMU facts unbound").0)}
 pub unsafe extern "C" fn ihk_mc_perf_counter_mask_check(mask:CULong)->CInt{
  let (_,regular,fixed)=LOWER.with(|x|x.borrow().facts.expect("PMU facts unbound"));
  // Same genuine availability predicate, including its any-valid-bit behavior.
  let result=(((mask&regular)|(mask&fixed))!=0) as CInt;
  record(PerfEffect::MaskCheck{mask,result});result
 }
 pub unsafe extern "C" fn ihk_mc_perfctr_init_raw(counter:CInt,code:u32,mode:CInt)->CInt{
  pmu_context();let result=LOWER.with(|x|x.borrow_mut().init.pop_front().expect("init_raw signed reply unbound"));
  record(PerfEffect::InitRaw{counter,code:code as CULong,mode,result});result
 }
 pub unsafe extern "C" fn ihk_mc_perfctr_start(mask:CULong)->CInt{
  pmu_context();let result=LOWER.with(|x|x.borrow_mut().start.pop_front().expect("start signed reply unbound"));record(PerfEffect::CounterStart{mask,result});result
 }
 pub unsafe extern "C" fn ihk_mc_perfctr_stop(mask:CULong,flags:CInt)->CInt{
  pmu_context();let result=LOWER.with(|x|x.borrow_mut().stop.pop_front().expect("stop signed reply unbound"));record(PerfEffect::CounterStop{mask,flags,result});result
 }
 pub unsafe extern "C" fn ihk_mc_perfctr_read(counter:CInt)->CULong{
  pmu_context();let value=LOWER.with(|x|x.borrow_mut().read.pop_front().expect("PMU read reply unbound"));record(PerfEffect::CounterRead{counter,value});value
 }
 pub(crate) unsafe fn managed_set_extra_reserved(event:*mut McPerfEvent,index:CInt)->CInt{
  pmu_context();assert!(!event.is_null());
  let (register,config)=unsafe{((*event).extra_reg.reg,(*event).extra_reg.config)};
  let result=LOWER.with(|x|x.borrow_mut().extra.pop_front().expect("reserved extra programming reply unbound"));
  record(PerfEffect::ExtraReserved{event:event as usize,index,register,config,result});result
 }
 pub unsafe extern "C" fn ihk_mc_perfctr_set_extra(event:*mut McPerfEvent)->CInt{
  record(PerfEffect::LegacyExtraSet{event:event as usize});panic!("unreserved legacy extra-map body outside managed fixture scope")
 }
 pub unsafe extern "C" fn ihk_mc_perfctr_alloc(thread:*mut Thread,event:*mut c_void)->CInt{
  record(PerfEffect::LegacyCounterAllocate{thread:thread as usize,event:event as usize});
  // Common appends the byte-identical ORIGINAL pure selector body, not a mirror.
  unsafe{crate::x86_perfctr::host_actual_legacy_perfctr_alloc(thread,event)}
 }
 pub unsafe extern "C" fn hw_perf_event_init(event:*mut McPerfEvent)->CInt{
  let result=unsafe{crate::x86_perfctr::host_actual_hw_perf_event_init(event)};
  record(PerfEffect::HwInitialize{event:event as usize,result});result
 }
 pub unsafe extern "C" fn ihk_mc_event_set_period(event:*mut McPerfEvent)->CInt{
  pmu_context();let result=unsafe{crate::x86_perfctr::host_actual_ihk_mc_event_set_period(event)};
  record(PerfEffect::SetPeriod{event:event as usize,result});result
 }
 pub unsafe extern "C" fn ihk_mc_event_update(event:*mut McPerfEvent)->CULong{
  pmu_context();let result=unsafe{crate::x86_perfctr::host_actual_ihk_mc_event_update(event)};
  record(PerfEffect::EventUpdate{event:event as usize,result});result
 }
}
pub unsafe extern "C" fn atomic_read(pointer:*mut c_void)->CLong{
 assert!(!pointer.is_null());assert_eq!((pointer as usize)%8,0);
 let value=unsafe{AtomicI64::from_ptr(pointer.cast()).load(Ordering::SeqCst)};
 record(PerfEffect::AtomicRead{address:pointer as usize,value});value
}
pub unsafe extern "C" fn atomic_set(pointer:*mut c_void,value:CLong){
 assert!(!pointer.is_null());assert_eq!((pointer as usize)%8,0);
 unsafe{AtomicI64::from_ptr(pointer.cast()).store(value,Ordering::SeqCst)};
 // ALL genuine stores are retained, INCLUDING constructor initialization.
 record(PerfEffect::AtomicSet{address:pointer as usize,value});
}
pub unsafe extern "C" fn event_update(event:*mut c_void)->CULong{unsafe{crate::x86_perfctr::ihk_mc_event_update(event.cast())}}
pub unsafe extern "C" fn set_period(event:*mut c_void)->CInt{unsafe{crate::x86_perfctr::ihk_mc_event_set_period(event.cast())}}
pub unsafe extern "C" fn init_raw(counter:CInt,code:CULong,mode:CInt)->CInt{unsafe{crate::x86_perfctr::ihk_mc_perfctr_init_raw(counter,code as u32,mode)}}
pub unsafe extern "C" fn start(mask:CULong)->CInt{unsafe{crate::x86_perfctr::ihk_mc_perfctr_start(mask)}}
pub unsafe extern "C" fn stop(mask:CULong,flags:CInt)->CInt{unsafe{crate::x86_perfctr::ihk_mc_perfctr_stop(mask,flags)}}
pub unsafe extern "C" fn extra_set(event:*mut c_void)->CInt{unsafe{crate::x86_perfctr::ihk_mc_perfctr_set_extra(event.cast())}}
fn map(kind:MapKind,input:CULong)->CULong{
 let value=LOWER.with(|x|x.borrow().maps.iter().find(|r|r.0==kind&&r.1==input).map(|r|r.2).expect("PMU mapping input unbound"));record(PerfEffect::Map{kind,input,value});value
}
pub unsafe extern "C" fn hardware_map(input:CULong)->CULong{map(MapKind::Hardware,input)}
pub unsafe extern "C" fn cache_map(input:CULong)->CULong{map(MapKind::Cache,input)}
pub unsafe extern "C" fn cache_extra_map(input:CULong)->CULong{map(MapKind::CacheExtra,input)}
pub unsafe extern "C" fn raw_map(input:CULong)->CULong{map(MapKind::Raw,input)}
pub unsafe extern "C" fn validate(code:CULong)->CInt{
 let result=LOWER.with(|x|x.borrow().validate.iter().find(|r|r.0==code).map(|r|r.1).expect("PMU validation input unbound"));record(PerfEffect::Validate{code,result});result
}
pub unsafe extern "C" fn extra_id(code:CULong,extra:CULong)->CInt{
 let id=LOWER.with(|x|x.borrow().extra_descriptors.iter().find(|r|r.0==code&&r.1==extra).map(|r|r.2).expect("extra descriptor input unbound"));record(PerfEffect::ExtraId{code,extra,id});id
}
pub unsafe extern "C" fn extra_msr(id:CInt)->u32{LOWER.with(|x|x.borrow().extra_descriptors.iter().find(|r|r.2==id).map(|r|r.3).expect("extra MSR id unbound"))}
pub unsafe extern "C" fn extra_index(id:CInt)->CInt{LOWER.with(|x|x.borrow().extra_descriptors.iter().find(|r|r.2==id).map(|r|r.4).expect("extra index id unbound"))}

/// Caller owns these actual HOST buffers for the synchronous primitive calls.
pub unsafe fn register_user_memory(pointer:*mut u8,length:usize){setup();assert!(!pointer.is_null());let start=pointer as usize;let end=start.checked_add(length).expect("user buffer extent");LOWER.with(|x|x.borrow_mut().user_ranges.push((start,end)));}
pub fn set_copy_results(values:&[CLong]){setup();LOWER.with(|x|x.borrow_mut().copy_results=values.iter().copied().collect());}
pub fn set_mmap_results(values:&[CLong]){setup();LOWER.with(|x|x.borrow_mut().mmap_results=values.iter().copied().collect());}
pub fn set_context_forward_results(values:&[CLong]){setup();LOWER.with(|x|x.borrow_mut().forward=values.iter().copied().collect());}
fn writable(address:usize,length:usize)->bool{address.checked_add(length).map_or(false,|end|LOWER.with(|x|x.borrow().user_ranges.iter().any(|(a,b)|*a<=address&&end<=*b)))}
pub unsafe extern "C" fn copy_to_user(destination:CULong,source:*const u8,length:SizeT)->CLong{
 crate::host_effects::assert_effects_unlocked("copy_to_user");assert!(length==0||!source.is_null());
 let bytes=if length==0{Vec::new()}else{unsafe{core::slice::from_raw_parts(source,length)}.to_vec()};
 let scripted=LOWER.with(|x|x.borrow_mut().copy_results.pop_front());
 let result=if let Some(error)=scripted.filter(|value|*value!=0){error}else if writable(destination as usize,length){unsafe{core::ptr::copy(source,destination as *mut u8,length)};0}else{-14};
 record(PerfEffect::CopyToUser{destination,bytes,result});result
}
pub unsafe extern "C" fn do_mmap(address:CULong,length:SizeT,prot:CInt,flags:CInt,fd:CInt,offset:CLong,_extra:CInt,_node:*mut c_void)->CLong{
 crate::host_effects::assert_effects_unlocked("do_mmap");let result=LOWER.with(|x|x.borrow_mut().mmap_results.pop_front().expect("mmap reply unbound"));
 if result>=0{assert!(writable(result as usize,length),"positive mmap reply lacks actual writable HOST span");}
 record(PerfEffect::Mmap{address,length,prot,flags,fd,offset,result});result
}
pub unsafe extern "C" fn context_forward(number:CInt,context:*mut c_void)->CLong{
 crate::host_effects::assert_effects_unlocked("context_forward");assert!(!context.is_null());let fd=unsafe{crate::x86_cpu_helpers::ihk_mc_syscall_arg0(context.cast::<X86UserContext>())};
 let result=LOWER.with(|x|x.borrow_mut().forward.pop_front().expect("context forward reply unbound"));record(PerfEffect::ContextForward{number,fd,result});result
}
// Exact C mc_perf_event.h273 layout, union represented by its unsigned-long
// capabilities member. offset_of supplies the genuine40/1024 provider fields.
#[repr(C)]
pub struct PerfMmapPage{pub version:u32,pub compat_version:u32,pub lock:u32,pub index:u32,pub offset:CLong,pub time_enabled:CULong,pub time_running:CULong,pub capabilities:CULong,pub pmc_width:u16,pub time_shift:u16,pub time_mult:u32,pub time_offset:CULong,pub time_zero:CULong,pub size:u32,pub reserved:[u8;118*8+4],pub data_head:CULong,pub data_tail:CULong}
const _:()={assert!(offset_of!(PerfMmapPage,capabilities)==40);assert!(offset_of!(PerfMmapPage,data_head)==1024);assert!(size_of::<PerfMmapPage>()==1040);};

pub const PRIVATE_TABLE_TAILS:&[(&str,&str)]=&[
("f03_perf_counter_control_v1",r###"
#[export_name="f03_perf_event_layout_v1"]
static HOST_CONTROL_LAYOUT:EventLayout={
 use super::f03_sync_child_layout_v2::FullMcPerfEvent as E;
 EventLayout{group_leader:offset_of!(E,group_leader),sibling_list:offset_of!(E,sibling_list),group_entry:offset_of!(E,group_entry),counter_id:offset_of!(E,counter_id),state:offset_of!(E,state),use_invariant_tsc:offset_of!(E,use_invariant_tsc),base_user_tsc:offset_of!(E,base_user_tsc),stopped_user_tsc:offset_of!(E,stopped_user_tsc),user_accum_count:offset_of!(E,user_accum_count),base_system_tsc:offset_of!(E,base_system_tsc),stopped_system_tsc:offset_of!(E,stopped_system_tsc),system_accum_count:offset_of!(E,system_accum_count),count:offset_of!(E,count),attr:offset_of!(E,attr),hw_config:offset_of!(E,hw_config),extra_reg_reg:offset_of!(E,extra_reg)+offset_of!(crate::x86_perfctr::HwPerfEventExtra,reg),kernel_mode:2,user_mode:1,inactive_state:0,active_state:1,pp_count:2,pp_none:0}
};
#[export_name="f03_perf_counter_providers_v1"]
static HOST_CONTROL_PROVIDERS:Providers=Providers{attr_flags:Some(crate::f03_perf_attr_callbacks::f03_perf_counter_attr_flags_v1),extra_set:Some(crate::host_perf_bindings::extra_set),init_raw:Some(crate::host_perf_bindings::init_raw),mask_check:Some(crate::x86_perfctr::ihk_mc_perf_counter_mask_check),set_period:Some(crate::host_perf_bindings::set_period),counter_start:Some(crate::host_perf_bindings::start),counter_stop:Some(crate::host_perf_bindings::stop),event_update:Some(crate::host_perf_bindings::event_update),read_value:Some(super::f03_perf_read_entries_v1::f03_perf_read_value_bridge_v1),atomic_set:Some(crate::host_perf_bindings::atomic_set)};
"###),
("f03_perf_read_entries_v1",r###"
#[export_name="f03_perf_read_layout_v1"]
static HOST_READ_LAYOUT:ReadLayout={
 use super::f03_sync_child_layout_v2::FullMcPerfEvent as E;
 ReadLayout{attr:offset_of!(E,attr),pid:offset_of!(E,pid),use_invariant_tsc:offset_of!(E,use_invariant_tsc),count:offset_of!(E,count),child_count_total:offset_of!(E,child_count_total),base_user_tsc:offset_of!(E,base_user_tsc),stopped_user_tsc:offset_of!(E,stopped_user_tsc),user_accum_count:offset_of!(E,user_accum_count),base_system_tsc:offset_of!(E,base_system_tsc),stopped_system_tsc:offset_of!(E,stopped_system_tsc),system_accum_count:offset_of!(E,system_accum_count),group_leader:offset_of!(E,group_leader),nr_siblings:offset_of!(E,nr_siblings),sibling_list:offset_of!(E,sibling_list),group_entry:offset_of!(E,group_entry),read_format:offset_of!(E,attr)+offset_of!(crate::f03_perf_attr_callbacks::PerfEventAttr,read_format),group_flag:8}
};
#[export_name="f03_perf_read_providers_v1"]
static HOST_READ_PROVIDERS:ReadProviders=ReadProviders{attr_flags:Some(crate::f03_perf_attr_callbacks::f03_perf_read_attr_flags_v1),update:Some(crate::host_perf_bindings::event_update),atomic_read:Some(crate::host_perf_bindings::atomic_read)};
"###),
("f03_perf_descriptor_entries_v1",r###"
#[export_name="f03_perf_descriptor_layout_v1"]
static HOST_DESCRIPTOR_LAYOUT:CloseLayout={
 use super::f03_sync_child_layout_v2::FullMcPerfEvent as E;
 CloseLayout{counter_id:offset_of!(E,counter_id),extra_reg_reg:offset_of!(E,extra_reg)+offset_of!(crate::x86_perfctr::HwPerfEventExtra,reg),extra_reg_idx:offset_of!(E,extra_reg)+offset_of!(crate::x86_perfctr::HwPerfEventExtra,idx),fcntl_nr:72,forward:Some(crate::host_perf_bindings::context_forward)}
};
"###),
("f03_perf_mmap_entry_v1",r###"
#[export_name="f03_perf_mmap_binding_v1"]
static HOST_MMAP_BINDING:MmapBinding=MmapBinding{map_anonymous:0x20,prot_write:2,data_head:core::mem::offset_of!(crate::host_perf_bindings::PerfMmapPage,data_head),capabilities:core::mem::offset_of!(crate::host_perf_bindings::PerfMmapPage,capabilities),cap_user_rdpmc:1u64<<2,do_mmap:Some(crate::host_perf_bindings::do_mmap)};
"###),
("f03_perf_alloc_entry_v1",r###"
#[export_name="f03_perf_allocation_binding_v1"]
static HOST_ALLOCATION_BINDING:PerfAllocationBinding=PerfAllocationBinding{alloc_flags:2,hardware_type:0,cache_type:3,raw_type:4,reference_cycles:9,allocate:Some(super::perf_event_alloc_kmalloc_bridge),release:Some(super::perf_event_alloc_free_bridge),atomic_set:Some(crate::host_perf_bindings::atomic_set),hardware_map:Some(crate::host_perf_bindings::hardware_map),cache_map:Some(crate::host_perf_bindings::cache_map),cache_extra_map:Some(crate::host_perf_bindings::cache_extra_map),raw_map:Some(crate::host_perf_bindings::raw_map),validate:Some(crate::host_perf_bindings::validate),extra_id:Some(crate::host_perf_bindings::extra_id),extra_msr:Some(crate::host_perf_bindings::extra_msr),extra_index:Some(crate::host_perf_bindings::extra_index),initialize:Some(super::perf_event_alloc_hw_init_bridge)};
"###),
];

pub const REAL_X86_SOURCE_TAIL:&str=r###"// Byte-identical existing function bodies; names only isolated for typed tracing.
mod host_genuine_x86_primitives {
use core::{ffi::c_void,ptr::read_volatile};
use crate::abi::{CInt,CULong,Thread};
use super::{McPerfEvent,ihk_mc_perf_get_num_counters};
const EINVAL:CInt=22;
fn counter_bit(counter:CInt)->CULong { 1_u64.wrapping_shl(counter as u32) as CULong }
pub unsafe extern "C" fn host_actual_legacy_perfctr_alloc(thread: *mut Thread, _event: *mut c_void) -> CInt {
    let mut ret = -EINVAL;
    let counters = unsafe { ihk_mc_perf_get_num_counters() };
    let mut i = 0;
    while i < counters {
        if unsafe { read_volatile(&(*thread).pmc_alloc_map) } & counter_bit(i) == 0 {
            ret = i;
            break;
        }
        i += 1;
    }
    ret
}

pub unsafe extern "C" fn host_actual_hw_perf_event_init(_event: *mut McPerfEvent) -> CInt {
    0
}

pub unsafe extern "C" fn host_actual_ihk_mc_event_set_period(_event: *mut McPerfEvent) -> CInt {
    0
}

pub unsafe extern "C" fn host_actual_ihk_mc_event_update(_event: *mut McPerfEvent) -> u64 {
    0
}
}
pub use host_genuine_x86_primitives::*;
"###;

// Frozen source evidence for typed fields/pure bodies; no runtime instruction.
pub const SOURCE_PINS:&[(&str,&str)]=&[
("/home/holden/mckernel-work/m14-blocker-resolution-20261110/perf-owner-changed-tests-p04tests-max-1/first-whole-compile-1/escalation-events-1/source-overlay/kernel/rust/syscall_policy.rs","784822e941d09ede1c51a443e1e93c105ab089dc7cd33de9f16613533044c503"),
("/home/holden/mckernel-work/m14-blocker-resolution-20261110/perf-owner-changed-tests-p04tests-max-1/first-whole-compile-1/escalation-events-1/source-overlay/kernel/rust/f03_perf_owner/hardware.rs","0d7ca949b101b3faa35eb18051bfa6d2e37fd1451db32c65d572c35ca49e4cf3"),
("/home/holden/mckernel-work/m14-blocker-resolution-20261110/perf-owner-changed-tests-p04tests-max-1/first-whole-compile-1/escalation-events-1/source-overlay/kernel/rust/f03_perf_owner/runtime.rs","667d4c3b39734879d6fad59480eb6861d91549fbfc055c01c8b95ff0e7c3bef1"),
("/home/holden/mckernel-work/m14-blocker-resolution-20261110/perf-owner-changed-tests-p04tests-max-1/first-whole-compile-1/escalation-events-1/source-overlay/kernel/rust/x86_perfctr.rs","f4d8351d685d1968b1902ed877ed52fe66b35093f2aed72a63a0c717b33a9379"),
("/home/holden/mckernel/kernel/rust/abi.rs","ff48bc2e7c8fe00abf19572a3fe75661dd464a7a475fec91a0ac7d870f6fdd3e"),
("/home/holden/mckernel/lib/include/mc_perf_event.h","8a9978dcab179a63b3aff3b66641a4814bacaf86cf4631ecdf39e32df45ea5dd"),
("/home/holden/mckernel/lib/include/ihk/perfctr.h","c075498676943becced5b999376d16f60f78e5a9c1d0098b2bf2c484d70eed47"),
("/home/holden/mckernel/lib/include/ihk/mm.h","a1b412608df7512a1b7295c6f19b3ec5a77e6364e8f24b208ab1a29e7556e5b1"),
];
