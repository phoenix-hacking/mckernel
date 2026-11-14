// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
// PRIVATE UNWIRED. Actual per-executing-Thread hardware/accounting working state.
// The existing genuine helpers still operate on the real event, under S. A
// window installs this Thread's preallocated state/physical index, saves actual
// helper results, and restores the immutable creation/global storage view.
use core::ffi::c_void;
use core::ptr::{addr_of,addr_of_mut};
use core::sync::atomic::{AtomicI64,Ordering};
use crate::abi::{CInt,CLong,CULong};
use super::super::f03_sync_child_layout_v2::FullMcPerfEvent as Event;

#[derive(Clone,Copy)]
struct Snapshot{
    state:CInt,cpu:CInt,counter:CInt,
    base_user:CLong,stopped_user:CLong,user_accum:CLong,
    base_system:CLong,stopped_system:CLong,system_accum:CLong,
    previous:CLong,sample:u64,last:u64,left:CLong,
    extra_index:CInt,extra_reg:u32,hardware:CULong,
}
impl Snapshot{
    const EMPTY:Self=Self{state:0,cpu:0,counter:0,base_user:0,stopped_user:0,user_accum:0,
        base_system:0,stopped_system:0,system_accum:0,previous:0,sample:0,last:0,left:0,
        extra_index:0,extra_reg:0,hardware:0};
    unsafe fn read(event:*mut Event)->Self{unsafe{
        Self{state:addr_of!((*event).state).read(),cpu:addr_of!((*event).cpu_id).read(),counter:addr_of!((*event).counter_id).read(),
            base_user:addr_of!((*event).base_user_tsc).read(),stopped_user:addr_of!((*event).stopped_user_tsc).read(),user_accum:addr_of!((*event).user_accum_count).read(),
            base_system:addr_of!((*event).base_system_tsc).read(),stopped_system:addr_of!((*event).stopped_system_tsc).read(),system_accum:addr_of!((*event).system_accum_count).read(),
            previous:AtomicI64::from_ptr(addr_of_mut!((*event).hw.prev_count.counter64)).load(Ordering::SeqCst),
            sample:addr_of!((*event).hw.sample_period).read(),last:addr_of!((*event).hw.last_period).read(),
            left:AtomicI64::from_ptr(addr_of_mut!((*event).hw.period_left.counter64)).load(Ordering::SeqCst),
            extra_index:addr_of!((*event).extra_reg.idx).read(),extra_reg:addr_of!((*event).extra_reg.reg).read(),hardware:addr_of!((*event).hw_config).read()}
    }}
    unsafe fn write(self,event:*mut Event){unsafe{
        addr_of_mut!((*event).state).write(self.state);addr_of_mut!((*event).cpu_id).write(self.cpu);addr_of_mut!((*event).counter_id).write(self.counter);
        addr_of_mut!((*event).base_user_tsc).write(self.base_user);addr_of_mut!((*event).stopped_user_tsc).write(self.stopped_user);addr_of_mut!((*event).user_accum_count).write(self.user_accum);
        addr_of_mut!((*event).base_system_tsc).write(self.base_system);addr_of_mut!((*event).stopped_system_tsc).write(self.stopped_system);addr_of_mut!((*event).system_accum_count).write(self.system_accum);
        AtomicI64::from_ptr(addr_of_mut!((*event).hw.prev_count.counter64)).store(self.previous,Ordering::SeqCst);
        addr_of_mut!((*event).hw.sample_period).write(self.sample);addr_of_mut!((*event).hw.last_period).write(self.last);
        AtomicI64::from_ptr(addr_of_mut!((*event).hw.period_left.counter64)).store(self.left,Ordering::SeqCst);
        addr_of_mut!((*event).extra_reg.idx).write(self.extra_index);addr_of_mut!((*event).extra_reg.reg).write(self.extra_reg);addr_of_mut!((*event).hw_config).write(self.hardware);
    }}
}
// Stored inline in each actual CounterSlot row before Thread visibility. It is
// touched only under the matching Event S while a real Operation lease owns row.
pub(super) struct LocalRuntime{initialized:bool,state:Snapshot}
impl LocalRuntime{pub(super) const fn new()->Self{Self{initialized:false,state:Snapshot::EMPTY}}}

pub(super) struct RuntimeWindow{event:*mut Event,runtime:*mut LocalRuntime,original:Snapshot}
impl RuntimeWindow{
    /// Actual Event S is held, matching local runtime belongs to a captured
    /// HardwareLeases operation, and neither P nor R is held. No allocator/copy
    /// to user/offload/log provider may be called until this window and S drop.
    pub(super) unsafe fn enter(raw:*mut c_void,runtime:*mut LocalRuntime,physical:CInt,extra:Option<CInt>)->Self{
        assert!(!raw.is_null()&&!runtime.is_null());let event=raw.cast::<Event>();
        let original=unsafe{Snapshot::read(event)};
        if !unsafe{(*runtime).initialized}{unsafe{(*runtime).state=original;(*runtime).initialized=true;}}
        let mut local=unsafe{(*runtime).state};local.counter=physical;
        if let Some(index)=extra{local.extra_index=index;}
        unsafe{local.write(event);}
        Self{event,runtime,original}
    }
}
impl Drop for RuntimeWindow{fn drop(&mut self){unsafe{
    (*self.runtime).state=Snapshot::read(self.event);
    // count/child_count_total remain genuine shared measurement/accounting
    // fields; they are never lifetime references or blindly restored snapshots.
    self.original.write(self.event);
}}}
