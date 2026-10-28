#[cfg(f03_sync_child_event_candidate)]
mod f03_sync_child_layout_v2 {
 use crate::abi::{CInt,CLong,CULong,IhkAtomic64,AbiListHead};
 use crate::f03_perf_attr_callbacks::PerfEventAttr;
 use crate::x86_perfctr::HwPerfEventExtra;
 use core::mem::{size_of,align_of,offset_of};
 #[repr(C)]
 pub struct HwPerfEvent {
  pub prev_count:IhkAtomic64,pub sample_period:u64,pub last_period:u64,pub period_left:IhkAtomic64,
 }
 // Complete genuine runtime mc_perf_event, distinct from x86_perfctr's128B prefix.
 // Used only for constants/layout witnesses; never constructs a borrowed whole C event.
 #[repr(C)]
 pub struct FullMcPerfEvent {
  pub attr:PerfEventAttr,pub extra_reg:HwPerfEventExtra,pub hw_config:CULong,pub hw_config_ext:CULong,
  pub state:CInt,pub cpu_id:CInt,pub counter_id:CInt,pub count:IhkAtomic64,
  pub child_count_total:CULong,pub pmc_status:CULong,pub sample_freq:CULong,
  pub parent:*mut FullMcPerfEvent,pub group_leader:*mut FullMcPerfEvent,
  pub sibling_list:AbiListHead,pub nr_siblings:CInt,pub pid:CInt,pub group_entry:AbiListHead,
  pub use_invariant_tsc:CInt,pub base_user_tsc:CLong,pub stopped_user_tsc:CLong,pub user_accum_count:CLong,
  pub base_system_tsc:CLong,pub stopped_system_tsc:CLong,pub system_accum_count:CLong,pub hw:HwPerfEvent,
 }
 // Rust-owned runtime offset array: no replacement C data object is introduced.
 #[no_mangle]
 pub static f03_sync_child_offsets_v1:[CULong;8]=[
  (offset_of!(FullMcPerfEvent,attr)+offset_of!(PerfEventAttr,flags)) as CULong,
  offset_of!(FullMcPerfEvent,pid) as CULong,
  offset_of!(FullMcPerfEvent,group_leader) as CULong,
  offset_of!(FullMcPerfEvent,counter_id) as CULong,
  offset_of!(FullMcPerfEvent,count) as CULong,
  offset_of!(FullMcPerfEvent,child_count_total) as CULong,
  offset_of!(FullMcPerfEvent,sibling_list) as CULong,
  offset_of!(FullMcPerfEvent,group_entry) as CULong,
 ];
 #[cfg(f03_sync_child_fixture)]
 #[no_mangle]
 pub static F03_SYNC_CHILD_LAYOUT_ABI:[CULong;49]=[
  (size_of::<FullMcPerfEvent>()) as CULong,
  (align_of::<FullMcPerfEvent>()) as CULong,
  (offset_of!(FullMcPerfEvent,attr)) as CULong,
  (offset_of!(FullMcPerfEvent,extra_reg)) as CULong,
  (offset_of!(FullMcPerfEvent,hw_config)) as CULong,
  (offset_of!(FullMcPerfEvent,hw_config_ext)) as CULong,
  (offset_of!(FullMcPerfEvent,state)) as CULong,
  (offset_of!(FullMcPerfEvent,cpu_id)) as CULong,
  (offset_of!(FullMcPerfEvent,counter_id)) as CULong,
  (offset_of!(FullMcPerfEvent,count)) as CULong,
  (offset_of!(FullMcPerfEvent,child_count_total)) as CULong,
  (offset_of!(FullMcPerfEvent,pmc_status)) as CULong,
  (offset_of!(FullMcPerfEvent,sample_freq)) as CULong,
  (offset_of!(FullMcPerfEvent,parent)) as CULong,
  (offset_of!(FullMcPerfEvent,group_leader)) as CULong,
  (offset_of!(FullMcPerfEvent,sibling_list)) as CULong,
  (offset_of!(FullMcPerfEvent,nr_siblings)) as CULong,
  (offset_of!(FullMcPerfEvent,pid)) as CULong,
  (offset_of!(FullMcPerfEvent,group_entry)) as CULong,
  (offset_of!(FullMcPerfEvent,use_invariant_tsc)) as CULong,
  (offset_of!(FullMcPerfEvent,base_user_tsc)) as CULong,
  (offset_of!(FullMcPerfEvent,stopped_user_tsc)) as CULong,
  (offset_of!(FullMcPerfEvent,user_accum_count)) as CULong,
  (offset_of!(FullMcPerfEvent,base_system_tsc)) as CULong,
  (offset_of!(FullMcPerfEvent,stopped_system_tsc)) as CULong,
  (offset_of!(FullMcPerfEvent,system_accum_count)) as CULong,
  (offset_of!(FullMcPerfEvent,hw)) as CULong,
  (size_of::<HwPerfEvent>()) as CULong,
  (align_of::<HwPerfEvent>()) as CULong,
  (offset_of!(HwPerfEvent,prev_count)) as CULong,
  (offset_of!(HwPerfEvent,sample_period)) as CULong,
  (offset_of!(HwPerfEvent,last_period)) as CULong,
  (offset_of!(HwPerfEvent,period_left)) as CULong,
  (size_of::<HwPerfEventExtra>()) as CULong,
  (align_of::<HwPerfEventExtra>()) as CULong,
  (offset_of!(HwPerfEventExtra,config)) as CULong,
  (offset_of!(HwPerfEventExtra,reg)) as CULong,
  (offset_of!(HwPerfEventExtra,idx)) as CULong,
  (size_of::<PerfEventAttr>()) as CULong,
  (align_of::<PerfEventAttr>()) as CULong,
  (offset_of!(PerfEventAttr,flags)) as CULong,
  (offset_of!(PerfEventAttr,sample_type)) as CULong,
  (offset_of!(PerfEventAttr,read_format)) as CULong,
  (size_of::<IhkAtomic64>()) as CULong,
  (align_of::<IhkAtomic64>()) as CULong,
  (size_of::<AbiListHead>()) as CULong,
  (align_of::<AbiListHead>()) as CULong,
  (offset_of!(AbiListHead,next)) as CULong,
  (offset_of!(AbiListHead,prev)) as CULong,
 ];

}
