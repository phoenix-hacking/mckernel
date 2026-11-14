// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
// Private source-only lifetime helpers; neither do_fork nor C selector is replaced.
use core::ffi::c_void;
use core::marker::PhantomData;
use core::mem::{offset_of, size_of, MaybeUninit};
use core::ptr::{addr_of, addr_of_mut, null_mut, NonNull};
use core::sync::atomic::{AtomicI32, AtomicPtr, Ordering};
use crate::abi::{CInt, CULong, CpuSet, Process, ProcessVm, Thread};
use crate::lock_helpers::McsRwlockNodeIrqsave;
use crate::syscall_policy::clone_report_thread_result;
const EINVAL:CInt=22;
const ENOMEM:CInt=12;
const EBUSY:CInt=16;
const CLONE_VM:CInt=0x100;
unsafe extern "C" { fn schedule(); }

// Reuse the exact already prepared TID-before-enqueue helper once. The compositor
// must not also emit this export from the full syscall-policy candidate.
include!("f03_clone_enqueue_reused.rs");
include!("f03_clone_lifetime_abi.rs");

// Same checked pin implementation as bad-ref-correction-1. Only the module-local
// EINVAL path changes when lifted out of the old nested do_fork module.
fn pin_live_counter(counter:&AtomicI32)->Result<(),CInt>{
    let mut old=counter.load(Ordering::SeqCst);
    loop {
        if old<=0{return Err(-EINVAL);}
        if old==i32::MAX{return Err(-75);}
        match counter.compare_exchange_weak(old,old+1,Ordering::SeqCst,Ordering::SeqCst){
            Ok(_)=>return Ok(()),Err(actual)=>old=actual,
        }
    }
}

const ORIGINAL_CHILD:CULong=1;
const CALLER_CPU:CULong=2;
const CHILD_PIN:CULong=4;
const VM_PIN:CULong=8;
const TID_SLOT:CULong=16;
const ORIGINAL_PUBLICATION_UNKNOWN:CULong=32;
const CHILD_RELEASE_STARTED:CULong=64;
const VM_RELEASE_STARTED:CULong=128;

#[repr(C)]
struct UnknownCloneRecord {
    next:*mut UnknownCloneRecord,
    disposition:CInt, // 1 = retained UNKNOWN; never a cleanup authorization.
    reason:CInt,
    obligations:CULong,
    child:*mut Thread,
    process:*mut Process,
    vm:*mut ProcessVm,
    cpu:CInt,
    cpu_reservation_obtained:CInt,
    child_tid:CInt,
    tid_table_created:CInt,
    tid_table:*mut c_void,
    tid_count:CInt,
    child_release_result:CInt,
    vm_release_result:CInt,
}
#[used]
static UNKNOWN_CLONES:AtomicPtr<UnknownCloneRecord>=AtomicPtr::new(null_mut());
unsafe fn retain_record(record:*mut UnknownCloneRecord,reason:CInt){
    // Record allocation is live and uniquely owned before publication. No input
    // child/VM/process pointer is dereferenced while publishing UNKNOWN.
    unsafe{(*record).disposition=1;(*record).reason=reason;}
    let mut head=UNKNOWN_CLONES.load(Ordering::Acquire);
    loop {
        unsafe{(*record).next=head;}
        match UNKNOWN_CLONES.compare_exchange_weak(head,record,Ordering::AcqRel,Ordering::Acquire){
            Ok(_)=>return,Err(actual)=>head=actual,
        }
    }
}

/// Reserve before constructing a child or acquiring any CPU credit.
#[must_use]
pub(crate) struct ReservedQuarantine { record:*mut UnknownCloneRecord }
impl ReservedQuarantine {
    pub(crate) unsafe fn reserve()->Result<Self,CInt>{
        let record=unsafe{crate::mem_helpers::kmalloc(size_of::<UnknownCloneRecord>() as CInt,0)}.cast::<UnknownCloneRecord>();
        if record.is_null(){Err(-ENOMEM)}else{Ok(Self{record})}
    }
}
impl Drop for ReservedQuarantine {
    fn drop(&mut self){if !self.record.is_null(){unsafe{crate::mem_helpers::kfree(self.record.cast());}}}
}

/// Exactly the caller's original CPU disposition, supplied by constructor owner.
/// A numeric CPU ID never supplies a reservation.
pub(crate) enum CpuDisposition { Reserved(CInt), SelectedWithoutReservation(CInt) }

/// A unique original child obligation plus newly acquired storage references.
/// Drop retains its exact record. No implicit destructor touches child/VM/CPU/TID.
#[must_use]
pub(crate) struct PreparedSharedChild { record:NonNull<UnknownCloneRecord> }
impl Drop for PreparedSharedChild {
    fn drop(&mut self){unsafe{retain_record(self.record.as_ptr(),-EBUSY);}}
}
impl PreparedSharedChild {
    /// # Safety
    /// Called for the exact successful CLONE_VM clone_thread return, before
    /// graph/runqueue publication. Caller transfers its ORIGINAL child cleanup,
    /// CPU and any existing TID-slot obligations once and stops legacy cleanup.
    /// Current Thread owns a live reference to the same VM. Pool publication,
    /// ptrace and native admission retain their separate provider contracts.
    pub(crate) unsafe fn adopt(
        mut slot:ReservedQuarantine,current:*mut Thread,child:*mut Thread,
        cpu:CpuDisposition,table_created:CInt,
    )->Result<Self,CInt>{
        // adopt ALWAYS transfers the exact input obligations into its reserved
        // record. Any validation failure below returns with that record UNKNOWN;
        // Err never returns a legacy-destruction/reset permission to the caller.
        let (cpu,reserved)=match cpu{CpuDisposition::Reserved(id)=>(id,1),CpuDisposition::SelectedWithoutReservation(id)=>(id,0)};
        let record=slot.record;slot.record=null_mut();
        unsafe{record.write(UnknownCloneRecord{
            next:null_mut(),disposition:0,reason:0,
            obligations:ORIGINAL_CHILD|(if reserved!=0{CALLER_CPU}else{0}),
            child,process:null_mut(),vm:null_mut(),cpu,cpu_reservation_obtained:reserved,
            child_tid:0,tid_table_created:table_created,tid_table:null_mut(),tid_count:0,
            child_release_result:CInt::MIN,vm_release_result:CInt::MIN,
        });}
        if current.is_null()||child.is_null()||cpu<0{
            unsafe{retain_record(record,-EINVAL);}return Err(-EINVAL);
        }
        let process=unsafe{(*child).proc};
        let vm=unsafe{(*child).vm};
        unsafe{(*record).process=process;(*record).vm=vm;}
        if process.is_null()||vm.is_null()||unsafe{(*current).vm!=vm||(*current).proc!=process}{
            unsafe{retain_record(record,-EINVAL);}return Err(-EINVAL);
        }
        let mut node=MaybeUninit::<McsRwlockNodeIrqsave>::uninit();
        unsafe{crate::lock_helpers::__mcs_rwlock_reader_lock(addr_of_mut!((*process).threads_lock).cast(),node.as_mut_ptr());}
        unsafe{
            (*record).child_tid=(*child).tid;
            (*record).tid_table=(*process).tids.cast();
            (*record).tid_count=(*process).nr_tids;
            // Record a TID-slot obligation only when this exact pointer occurs
            // in the actual live table under its owning threads_lock.
            if !(*process).tids.is_null(){
                for index in 0..(*process).nr_tids.max(0) as usize{
                    let entry=(*process).tids.cast::<crate::abi::McexecTid>().add(index);
                    if (*entry).thread==child{(*record).obligations|=TID_SLOT;break;}
                }
            }
            crate::lock_helpers::__mcs_rwlock_reader_unlock(addr_of_mut!((*process).threads_lock).cast(),node.as_mut_ptr());
        }
        // Ownership has now transferred even when either checked pin fails.
        let vm_counter=unsafe{AtomicI32::from_ptr(addr_of_mut!((*vm).refcount.counter))};
        if let Err(error)=pin_live_counter(vm_counter){unsafe{retain_record(record,error);}return Err(error);}
        unsafe{(*record).obligations|=VM_PIN;}
        let child_counter=unsafe{AtomicI32::from_ptr(addr_of_mut!((*child).refcount.counter))};
        if let Err(error)=pin_live_counter(child_counter){unsafe{retain_record(record,error);}return Err(error);}
        unsafe{(*record).obligations|=CHILD_PIN;}
        Ok(Self{record:unsafe{NonNull::new_unchecked(record)}})
    }

    /// Actual VM storage reference pins VM independently of the prepared child.
    /// The borrow prevents moving/releasing this owner while its writer lives.
    /// This uses the same range writer as flush/free teardown, and never calls
    /// XPMEM or faults recursively while holding it.
    pub(crate) unsafe fn range_writer(&self)->Result<VmRangeWriter<'_>,CInt>{
        let vm=unsafe{self.record.as_ref().vm};
        unsafe{crate::lock_helpers::ihk_rwspinlock_write_lock_noirq(addr_of_mut!((*vm).memory_range_lock).cast());}
        let writer=VmRangeWriter{vm:unsafe{NonNull::new_unchecked(vm)},owner:PhantomData};
        if unsafe{(*vm).exiting!=0}{drop(writer);return Err(-EBUSY);}
        Ok(writer)
    }

    /// Retain every original and added obligation on a pre-enqueue failure.
    /// Consumes self; Drop publishes one immutable UNKNOWN record exactly once.
    pub(crate) fn quarantine(self,error:CInt){
        let record=self.record;core::mem::forget(self);
        unsafe{retain_record(record.as_ptr(),error);}
    }

    /// Reuse the exact enqueue helper after caller's existing graph/ptrace work.
    ///
    /// # Safety
    /// Caller has satisfied that helper's preparation/report/runqueue contract.
    /// All graph publication must be complete; this function grants no host or
    /// native admission. It consumes only our two NEW references. Original
    /// constructor/CPU/TID disposition is UNKNOWN because the legacy enqueuer
    /// discards its checked result, so its exact record remains retained.
    pub(crate) unsafe fn finish_existing_enqueue(
        self,oldproc:*mut Process,flags:CInt,termsig:CInt,ptrace_event:CInt,
    )->CInt{
        let record=self.record;core::mem::forget(self);
        let r=unsafe{&mut*record.as_ptr()};
        if oldproc!=r.process||flags&CLONE_VM==0{
            unsafe{retain_record(record.as_ptr(),-EINVAL);}return -EINVAL;
        }
        // The existing runq provider decrements a reservation. A helper's
        // selected current CPU supplies none; retain rather than underflow it.
        if r.cpu_reservation_obtained!=1{
            unsafe{retain_record(record.as_ptr(),-EBUSY);}return -EBUSY;
        }
        r.obligations|=ORIGINAL_PUBLICATION_UNKNOWN;
        let tid=unsafe{f03_clone_finish_report_enqueue_v1(r.child,oldproc,flags,termsig,r.cpu,ptrace_event)};
        // Mark before any consuming callback. It may destroy child; do not read
        // child afterwards, and never retry a negative/partial release result.
        r.obligations=(r.obligations&!CHILD_PIN)|CHILD_RELEASE_STARTED;
        let child=r.child;
        r.child_release_result=unsafe{crate::process_helpers::release_thread_checked(child)};
        if !matches!(r.child_release_result,0|1){
            // 2 reports VM destruction, inconsistent with our separate VM pin.
            // Negative/other outcomes may also be partial; never touch VM again.
            unsafe{retain_record(record.as_ptr(),r.child_release_result);}return tid;
        }
        // VM's independent added ref keeps storage live through child teardown.
        r.obligations=(r.obligations&!VM_PIN)|VM_RELEASE_STARTED;
        let vm=r.vm;
        r.vm_release_result=unsafe{crate::process_helpers::release_process_vm_checked(vm)};
        unsafe{retain_record(record.as_ptr(),if r.vm_release_result<0{r.vm_release_result}else{-EBUSY});}
        tid
    }
}

pub(crate) struct VmRangeWriter<'a> { vm:NonNull<ProcessVm>,owner:PhantomData<&'a PreparedSharedChild> }
impl VmRangeWriter<'_>{
    /// Copy range scalars while protected; no range pointer escapes the writer.
    pub(crate) unsafe fn lookup_bounds(&self,address:CULong)->Option<(CULong,CULong)>{
        let range=unsafe{crate::process_helpers::lookup_process_memory_range(self.vm.as_ptr(),address,address.checked_add(1)?)};
        if range.is_null(){None}else{Some(unsafe{((*range).start,(*range).end)})}
    }
}
impl Drop for VmRangeWriter<'_>{
    fn drop(&mut self){unsafe{crate::lock_helpers::ihk_rwspinlock_write_unlock_noirq(addr_of_mut!((*self.vm.as_ptr()).memory_range_lock).cast());}}
}

// Real existing provider signatures, checked by the affected Rust frontend.
const _:unsafe extern "C" fn(*mut Thread)->CInt=crate::process_helpers::release_thread_checked;
const _:unsafe extern "C" fn(*mut ProcessVm)->CInt=crate::process_helpers::release_process_vm_checked;
const _:unsafe extern "C" fn(*mut crate::lock_helpers::IhkRwSpinlock)=crate::lock_helpers::ihk_rwspinlock_write_lock_noirq;
