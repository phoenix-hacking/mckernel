// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
// Private UNWIRED weak Process identities; no Event/descriptor owns a persistent
// Process reference. Real final/constructor-abort hooks retire BEFORE memory free.
use core::cell::UnsafeCell;
use core::mem::size_of;
use core::ptr::{null_mut,write};
use crate::abi::{CInt,CULong,Process};
use super::descriptors::Locked;
use super::events::EventPin;
use super::monitors::{Target,MonitorSlot,MonitorRead,ProcessKey,InstallMode,Installed};
use super::thread_counters::EventKey;
use super::forward_gate::{ForwardGate,ForwardGuard};
use core::mem::MaybeUninit;
const EINVAL:CInt=22;const ENOMEM:CInt=12;
const FILE:&[u8]=concat!(file!(),"\0").as_bytes();
struct Record{next:*mut Record,next_free:*mut Record,raw:*mut Process,key:ProcessKey,
    references:usize,target:Target,inherited:MonitorSlot,closing:bool,transaction:MaybeUninit<ForwardGate>}
struct Registry{first:*mut Record,deferred:*mut Record,generation:u64}
struct Cell(UnsafeCell<Registry>);unsafe impl Sync for Cell{}
static REGISTRY:Cell=Cell(UnsafeCell::new(Registry{first:null_mut(),deferred:null_mut(),generation:1}));
unsafe fn state(_r:&mut Locked)->&mut Registry{unsafe{&mut *REGISTRY.0.get()}}
unsafe fn find(raw:*mut Process,r:&mut Locked)->*mut Record{let mut row=unsafe{state(r).first};while !row.is_null(){if unsafe{(*row).raw==raw}{return row;}row=unsafe{(*row).next};}null_mut()}
unsafe fn retain(row:*mut Record)->Result<(),CInt>{let n=unsafe{(*row).references}.checked_add(1).ok_or(-EINVAL)?;if unsafe{(*row).references}==0{return Err(-EINVAL);}unsafe{(*row).references=n;}Ok(())}
unsafe fn release(row:*mut Record,r:&mut Locked){let n=unsafe{(*row).references}.checked_sub(1).expect("perf Process metadata released twice");unsafe{(*row).references=n;}
    if n==0{assert!(unsafe{(*row).raw.is_null()});let reg=unsafe{state(r)};unsafe{(*row).next_free=reg.deferred;reg.deferred=row;}}}
pub(super) struct ProcessHandle{record:*mut Record}
impl ProcessHandle{
    pub(super) fn key(&self)->ProcessKey{unsafe{(*self.record).key}}
    pub(super) unsafe fn opening(&self)->Result<ForwardGuard<'_>,CInt>{unsafe{(*self.record).transaction.assume_init_ref().forward()}}
    pub(super) unsafe fn terminal(&self)->Result<ForwardGuard<'_>,CInt>{
        {let _r=unsafe{Locked::take()};unsafe{(*self.record).closing=true;(*self.record).transaction.assume_init_ref().mark_closing();}}
        // Actual current Process/Thread route is still owned by caller. No
        // allocator/hash/P/R/S/runqueue/IRQ exclusion may span this real wait.
        unsafe{(*self.record).transaction.assume_init_ref().close()}
    }
    pub(super) unsafe fn live_for_open_locked(&self,_r:&mut Locked)->bool{unsafe{!(*self.record).raw.is_null()&&!(*self.record).closing}}

    pub(super) unsafe fn target_locked<'a>(&'a self,_r:&mut Locked)->Result<&'a mut Target,CInt>{
        if unsafe{(*self.record).raw.is_null()}{Err(-EINVAL)}else{Ok(unsafe{&mut (*self.record).target})}
    }
    pub(super) unsafe fn pin_locked(&self,r:&mut Locked)->Result<MonitorRead,CInt>{unsafe{self.target_locked(r)?.pin_locked(r)}}
    pub(super) unsafe fn inherited_slot_locked<'a>(&'a self,_r:&mut Locked)->Result<&'a mut MonitorSlot,CInt>{
        if unsafe{(*self.record).raw.is_null()}{Err(-EINVAL)}else{Ok(unsafe{&mut (*self.record).inherited})}
    }
    pub(super) unsafe fn release_locked(self,r:&mut Locked){let this=core::mem::ManuallyDrop::new(self);unsafe{release(this.record,r);}}
}
impl Drop for ProcessHandle{fn drop(&mut self){let mut r=unsafe{Locked::take()};unsafe{release(self.record,&mut r);}}}

/// Nonallocating actual-identity lookup for terminal/scheduler preparation.
/// Caller owns the genuine current/positive Process lifetime across this call.
pub(super) unsafe fn existing(raw:*mut Process)->Result<Option<ProcessHandle>,CInt>{
    if raw.is_null(){return Err(-EINVAL);}
    let mut r=unsafe{Locked::take()};let row=unsafe{find(raw,&mut r)};
    if row.is_null(){return Ok(None);}
    unsafe{retain(row)?;}Ok(Some(ProcessHandle{record:row}))
}

/// Caller already owns a genuine positive Process lifetime (current Thread,
/// exclusive constructor, or checked with_remote_target), never a hash borrow
/// alone. Allocation is outside hash/P/R/IRQ; the identity generation is real.
pub(super) unsafe fn ensure(raw:*mut Process,flags:CULong)->Result<ProcessHandle,CInt>{
    if raw.is_null(){return Err(-EINVAL);}
    {let mut r=unsafe{Locked::take()};let existing=unsafe{find(raw,&mut r)};if !existing.is_null(){unsafe{retain(existing)?;}return Ok(ProcessHandle{record:existing});}}
    let row=unsafe{crate::mem_helpers::kmalloc_tracked(size_of::<Record>() as CInt,flags,FILE.as_ptr().cast_mut().cast(),line!() as CInt)}.cast::<Record>();
    if row.is_null(){return Err(-ENOMEM);}
    let result={let mut r=unsafe{Locked::take()};let existing=unsafe{find(raw,&mut r)};
        if !existing.is_null(){unsafe{retain(existing)}.map(|_|ProcessHandle{record:existing})}else{
            let reg=unsafe{state(&mut r)};match reg.generation.checked_add(1){None=>Err(-EINVAL),Some(next)=>{
                let generation=reg.generation;
                let target=unsafe{Target::new(raw,generation)}.expect("checked actual Process identity");
                let key=target.key();
                unsafe{write(row,Record{next:reg.first,next_free:null_mut(),raw,key,references:2,target,inherited:MonitorSlot::new(),closing:false,transaction:MaybeUninit::uninit()});
                    ForwardGate::initialize_at((*row).transaction.as_mut_ptr());}
                // A real Process owns this slot, independent of any inherited fd.
                unsafe{(*row).inherited.bind_inherited_locked(key,&mut r)}.expect("new Process monitor slot");
                let reg=unsafe{state(&mut r)};reg.generation=next;reg.first=row;Ok(ProcessHandle{record:row})
            }}
        }
    };
    if result.as_ref().map_or(true,|handle|handle.record!=row){unsafe{crate::mem_helpers::kfree_tracked(row.cast(),FILE.as_ptr().cast_mut().cast(),line!() as CInt)};}
    result
}
/// Read only under the existing caller's real Process lifetime. No lazy allocate
/// in scheduler/exit; construction/enable prebound this record before visibility.
pub(super) unsafe fn pin_under_lock(raw:*mut Process,r:&mut Locked)->Result<MonitorRead,CInt>{
    if raw.is_null(){return Err(-EINVAL);}let row=unsafe{find(raw,r)};
    if row.is_null(){return if unsafe{(*raw).monitoring_event.is_null()}{Ok(MonitorRead::None)}else{Ok(MonitorRead::Unmanaged(unsafe{(*raw).monitoring_event}))};}
    unsafe{(*row).target.pin_locked(r)}
}
pub(super) unsafe fn pin(raw:*mut Process)->Result<MonitorRead,CInt>{
    if raw.is_null(){return Err(-EINVAL);}
    let mut r=unsafe{Locked::take()};let row=unsafe{find(raw,&mut r)};
    if row.is_null(){return if unsafe{(*raw).monitoring_event.is_null()}{Ok(MonitorRead::None)}else{Ok(MonitorRead::Unmanaged(unsafe{(*raw).monitoring_event}))};}
    unsafe{(*row).target.pin_locked(&mut r)}
}
pub(super) unsafe fn current_group_locked(key:ProcessKey,group:EventKey,r:&mut Locked)->bool{
    let row=unsafe{find(key.address as *mut Process,r)};
    if row.is_null() || unsafe{(*row).key!=key}{return false;}
    // Explicit release under R; letting an EventPin's Drop recursively take R
    // here would violate the shared metadata lock contract.
    match unsafe{(*row).target.pin_locked(r)}{
        Ok(MonitorRead::Managed(pin))=>{let matches=pin.selected_group().key()==group;unsafe{pin.release_locked(r);}matches},
        _=>false,
    }
}
/// Genuine last-positive-reference terminal point, BEFORE hash detach/free; also
/// used on a registered unpublished constructor abort. Never resurrects a Process.
pub(crate) unsafe fn retire_before_free(raw:*mut Process){
    if raw.is_null(){return;}
    let mut r=unsafe{Locked::take()};let row=unsafe{find(raw,&mut r)};if row.is_null(){return;}
    unsafe{(*row).target.retire_locked(&mut r);(*row).inherited.retire_locked(&mut r);(*row).raw=null_mut();}
    let reg=unsafe{state(&mut r)};let mut link=&mut reg.first as *mut *mut Record;
    while unsafe{*link}!=row{assert!(!unsafe{*link}.is_null());link=unsafe{&mut (**link).next};}
    unsafe{*link=(*row).next;release(row,&mut r);}
    unsafe{super::maps::reconcile_monitors_locked(|key,group,r|current_group_locked(key,group,r),&mut r);}
}
pub(super) unsafe fn drain_deferred(){
    let mut row={let mut r=unsafe{Locked::take()};let reg=unsafe{state(&mut r)};let first=reg.deferred;reg.deferred=null_mut();first};
    while !row.is_null(){let next=unsafe{(*row).next_free};unsafe{crate::mem_helpers::kfree_tracked(row.cast(),FILE.as_ptr().cast_mut().cast(),line!() as CInt)};row=next;}
}

/// Finite real fork transaction ownership across the existing constructor ->
/// Linux clone call boundary. Stable heap gate is retained by its actual
/// ProcessHandle, so moving this small owner does not move the borrowed Waitq.
/// No actual Process/Thread strong edge is stored; this is NOT a native lease.
pub(super) struct OpeningOwner{guard:core::mem::ManuallyDrop<ForwardGuard<'static>>,handle:core::mem::ManuallyDrop<ProcessHandle>}
impl ProcessHandle{
    pub(super) unsafe fn into_opening(self)->Result<OpeningOwner,CInt>{
        let pointer=unsafe{(*self.record).transaction.as_ptr()};
        let gate: &'static ForwardGate=unsafe{&*pointer};
        let guard=unsafe{gate.forward()}?;
        Ok(OpeningOwner{guard:core::mem::ManuallyDrop::new(guard),handle:core::mem::ManuallyDrop::new(self)})
    }
}
impl Drop for OpeningOwner{fn drop(&mut self){unsafe{
    core::mem::ManuallyDrop::drop(&mut self.guard);
    core::mem::ManuallyDrop::drop(&mut self.handle);
}}}
