// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
// PRIVATE UNWIRED. Real parent-locked snapshot -> real child nodes. No partial
// object injection, synthetic callback carrier or perf-kind inference.
use core::cell::UnsafeCell;
use core::ffi::c_void;
use core::mem::{size_of,ManuallyDrop};
use core::ptr::{addr_of_mut,null_mut,copy_nonoverlapping,write};
use core::sync::atomic::{AtomicI32,Ordering};
use crate::abi::{CInt,CLong,CULong,Mckfd,Process,ProcessVm};
use super::descriptors::{self,Locked,Prepared};
use super::events::DescriptorEvent;
use super::copy_borrows::{PreparedBorrow,CopyPin};
use super::process_targets::{self,OpeningOwner};
const ENOMEM:CInt=12;const EINVAL:CInt=22;
const FILE:&[u8]=concat!(file!(),"\0").as_bytes();

struct VmPin{vm:*mut ProcessVm}
impl VmPin{
    /// The actual parent/current caller owns a positive VM lifetime already.
    /// CAS refuses0/dying/overflow rather than resurrecting under a raw borrow.
    unsafe fn acquire(vm:*mut ProcessVm)->Result<Self,CInt>{
        if vm.is_null(){return Err(-EINVAL);}
        let refs=unsafe{AtomicI32::from_ptr(addr_of_mut!((*vm).refcount.counter))};let mut observed=refs.load(Ordering::SeqCst);
        loop{if observed<=0{return Err(-EINVAL);}let next=observed.checked_add(1).ok_or(-EINVAL)?;
            match refs.compare_exchange_weak(observed,next,Ordering::SeqCst,Ordering::SeqCst){Ok(_)=>return Ok(Self{vm}),Err(actual)=>observed=actual}}
    }
}
impl Drop for VmPin{fn drop(&mut self){
    // Finite snapshot/callback phase only, on the actual parent owner route,
    // BEFORE returning to the Linux-clone caller. Never deferred to idle.
    unsafe{crate::process_helpers::release_process_vm(self.vm);}
}}
struct Row{child:*mut Mckfd,event:Option<DescriptorEvent>,copy:Option<CopyPin>,prepared:Option<PreparedBorrow>}
struct Snapshot{rows:*mut Row,capacity:usize,used:usize,file:*mut i8,free_line:CInt}
impl Snapshot{
    unsafe fn allocate(count:usize,flags:CULong,file:*mut i8,alloc_line:CInt,free_line:CInt)->Result<Self,CInt>{
        let bytes=count.checked_mul(size_of::<Row>()).filter(|n|*n<=CInt::MAX as usize).ok_or(-ENOMEM)?;
        let rows=if bytes==0{null_mut()}else{unsafe{crate::mem_helpers::kmalloc_tracked(bytes as CInt,flags,FILE.as_ptr().cast_mut().cast(),line!() as CInt)}.cast::<Row>()};
        if bytes!=0&&rows.is_null(){return Err(-ENOMEM);}
        let mut snapshot=Self{rows,capacity:count,used:0,file,free_line};
        for i in 0..count{
            unsafe{write(rows.add(i),Row{child:null_mut(),event:None,copy:None,prepared:None});}snapshot.capacity=i+1;
            let child=unsafe{crate::mem_helpers::kmalloc_tracked(size_of::<Mckfd>() as CInt,flags,file,alloc_line)}.cast::<Mckfd>();
            if child.is_null(){return Err(-ENOMEM);}unsafe{(*rows.add(i)).child=child;}
            unsafe{(*rows.add(i)).prepared=Some(PreparedBorrow::allocate(flags)?);}
        }Ok(snapshot)
    }
}
impl Drop for Snapshot{fn drop(&mut self){
    // Source caller dropped P/R first. Real pending-child descriptor edges,
    // opaque copy borrows and unused preparations never destruct under P/R.
    for i in 0..self.capacity{unsafe{
        let row=self.rows.add(i);drop((*row).event.take());drop((*row).copy.take());drop((*row).prepared.take());
        if !(*row).child.is_null(){crate::mem_helpers::kfree_tracked((*row).child.cast(),self.file,self.free_line);}
    }}
    if !self.rows.is_null(){unsafe{crate::mem_helpers::kfree_tracked(self.rows.cast(),FILE.as_ptr().cast_mut().cast(),line!() as CInt)};}
}}
struct P{raw:*mut c_void,flags:CLong}
impl P{unsafe fn take(process:*mut Process)->Self{let raw=unsafe{addr_of_mut!((*process).mckfd_lock)}.cast();let flags=unsafe{super::super::syscall_mckfd_lock_bridge(raw)};Self{raw,flags}}}
impl Drop for P{fn drop(&mut self){unsafe{super::super::syscall_mckfd_unlock_bridge(self.raw,self.flags)};}}

struct Pending{next:*mut Pending,child:*mut Process,opening:ManuallyDrop<OpeningOwner>}
struct PendingRegistry{first:*mut Pending,deferred:*mut Pending}
struct Cell(UnsafeCell<PendingRegistry>);unsafe impl Sync for Cell{}
static PENDING:Cell=Cell(UnsafeCell::new(PendingRegistry{first:null_mut(),deferred:null_mut()}));
unsafe fn pending(_r:&mut Locked)->&mut PendingRegistry{unsafe{&mut *PENDING.0.get()}}

/// Finite parent copy pins ALL actual80B bytes under parent P, retains real
/// managed descriptor ownership under R BEFORE unlock, and runs only the
/// original opaque dup callback on the genuine allocated/published child node.
/// The caller is the actual current parent Thread with live parent VM. Child
/// remains unpublished. Original clone config supplies allocation/free origins.
pub(crate) unsafe fn copy_descriptors(parent:*mut Process,child:*mut Process,vm:*mut ProcessVm,flags:CULong,file:*mut i8,alloc_line:CInt,free_line:CInt)->CInt{
    match unsafe{copy(parent,child,vm,flags,file,alloc_line,free_line)}{Ok(())=>0,Err(error)=>error}
}
unsafe fn copy(parent:*mut Process,child:*mut Process,vm:*mut ProcessVm,flags:CULong,file:*mut i8,alloc_line:CInt,free_line:CInt)->Result<(),CInt>{
    if parent.is_null()||child.is_null()||parent==child{return Err(-EINVAL);}
    let cpu=unsafe{crate::cls::get_this_cpu_local_var()};let current=unsafe{(*cpu).current};
    if current.is_null()||unsafe{(*current).proc!=parent||(*current).vm!=vm}{return Err(-EINVAL);}
    let parent_handle=unsafe{process_targets::ensure(parent,flags)}?;
    let opening=unsafe{parent_handle.into_opening()}?;
    let child_handle=unsafe{process_targets::ensure(child,flags)}?;
    let _vm_pin=unsafe{VmPin::acquire(vm)}?;
    // This finite actual gate spans through successful Linux child creation,
    // preventing a managed parent close between snapshot and host fd-table copy.
    let pending_row=unsafe{crate::mem_helpers::kmalloc_tracked(size_of::<Pending>() as CInt,flags,FILE.as_ptr().cast_mut().cast(),line!() as CInt)}.cast::<Pending>();
    if pending_row.is_null(){return Err(-ENOMEM);}
    struct PendingPrepared{raw:*mut Pending}
    impl Drop for PendingPrepared{fn drop(&mut self){if !self.raw.is_null(){unsafe{crate::mem_helpers::kfree_tracked(self.raw.cast(),FILE.as_ptr().cast_mut().cast(),line!() as CInt)};}}}
    let mut pending_prepared=PendingPrepared{raw:pending_row};
    let mut snapshot=loop{
        let count={let _p=unsafe{P::take(parent)};let mut n=0usize;let mut node=unsafe{(*parent).mckfd.cast::<Mckfd>()};while !node.is_null(){n=n.checked_add(1).ok_or(-ENOMEM)?;node=unsafe{(*node).next};}n};
        let mut snapshot=unsafe{Snapshot::allocate(count,flags,file,alloc_line,free_line)}?;
        let outcome={let _p=unsafe{P::take(parent)};let mut r=unsafe{Locked::take()};
            let mut node=unsafe{(*parent).mckfd.cast::<Mckfd>()};let mut result=Ok(());
            while !node.is_null(){if snapshot.used==snapshot.capacity{result=Err(-ENOMEM);break;}
                let row=unsafe{&mut *snapshot.rows.add(snapshot.used)};
                match unsafe{descriptors::copy_snapshot_locked(parent,node,&mut r)}{
                    Err(error)=>{result=Err(error);break;},Ok(Some(event))=>row.event=Some(event),
                    Ok(None)=>match unsafe{row.prepared.as_mut().unwrap().acquire_locked(parent,node,&mut r)}{Ok(pin)=>row.copy=Some(pin),Err(error)=>{result=Err(error);break;}}
                }
                unsafe{copy_nonoverlapping(node.cast::<u8>(),row.child.cast::<u8>(),size_of::<Mckfd>());}
                snapshot.used+=1;node=unsafe{(*node).next};
            }result
        };
        match outcome{Ok(())=>break snapshot,Err(error) if error == -ENOMEM=>{drop(snapshot);continue;},Err(error)=>return Err(error)}
    };
    for i in 0..snapshot.used{
        let row=unsafe{&mut *snapshot.rows.add(i)};
        let descriptor=row.child;
        if let Some(event)=row.event.take(){
            let mut prepared=unsafe{Prepared::allocate(child,descriptor,event,flags)}?;
            unsafe{prepared.inherited_host_pending((*descriptor).fd)}?;
            let result={let _p=unsafe{P::take(child)};let mut r=unsafe{Locked::take()};unsafe{prepared.publish(None,&mut r,|_|{})}};
            if let Err((error,prepared,member))=result{drop(member);drop(prepared);return Err(error);}
        }else{
            {let _p=unsafe{P::take(child)};unsafe{(*descriptor).next=(*child).mckfd.cast();(*child).mckfd=descriptor.cast();}}
            // Original callback identity and genuine child allocation; no new
            // backend body/type is selected or synthesized. Parent close waits
            // the opaque CopyPin and final parent VM cannot drain under VmPin.
            if !unsafe{(*descriptor).dup_cb}.is_null(){
                let duplicate:unsafe extern "C" fn(*mut c_void,*mut c_void)->CInt=unsafe{core::mem::transmute((*descriptor).dup_cb)};
                let _=unsafe{duplicate(descriptor.cast(),null_mut())};
            }
        }
        // Ownership moved to actual child list/record; cleanup uses original
        // child transaction drain. Snapshot retains only finite parent pins.
        row.child=null_mut();
    }
    drop(snapshot); // copy borrows BEFORE releasing the finite parent VM pin.
    {let mut r=unsafe{Locked::take()};let state=unsafe{pending(&mut r)};let mut old=state.first;
        while !old.is_null(){if unsafe{(*old).child==child}{return Err(-EINVAL);}old=unsafe{(*old).next};}
        unsafe{write(pending_row,Pending{next:state.first,child,opening:ManuallyDrop::new(opening)});}
        state.first=pending_row;
    }
    pending_prepared.raw=null_mut();let _=child_handle;Ok(())
}

/// Positive ACTUAL Linux clone result only, before child Thread publication.
/// Activate exact child routes while the parent's table gate still excludes
/// managed close/open, THEN release that same finite guard on the parent route.
pub(crate) unsafe fn finish_child_host_route(child:*mut Process,success:bool){
    let row={let mut r=unsafe{Locked::take()};let state=unsafe{pending(&mut r)};let mut link=&mut state.first as *mut *mut Pending;
        while !unsafe{*link}.is_null()&&unsafe{(**link).child!=child}{link=unsafe{&mut (**link).next};}
        let row=unsafe{*link};if !row.is_null(){unsafe{*link=(*row).next;}}row};
    if success{unsafe{descriptors::activate_child_routes(child);}}
    if !row.is_null(){unsafe{ManuallyDrop::drop(&mut (*row).opening);crate::mem_helpers::kfree_tracked(row.cast(),FILE.as_ptr().cast_mut().cast(),line!() as CInt)};}
}
/// Constructor abort may be reached while another source exclusion is held.
/// Queue only the metadata/gate owner; idle safe point releases it with NO host
/// operation. PendingChildRoute never turns into a parent's numeric close.
pub(crate) unsafe fn abort_pending(child:*mut Process){
    let mut r=unsafe{Locked::take()};let state=unsafe{pending(&mut r)};let mut link=&mut state.first as *mut *mut Pending;
    while !unsafe{*link}.is_null()&&unsafe{(**link).child!=child}{link=unsafe{&mut (**link).next};}
    let row=unsafe{*link};if !row.is_null(){unsafe{*link=(*row).next;(*row).next=state.deferred;}state.deferred=row;}
}
pub(super) unsafe fn drain_deferred(){
    let mut row={let mut r=unsafe{Locked::take()};let state=unsafe{pending(&mut r)};let first=state.deferred;state.deferred=null_mut();first};
    while !row.is_null(){let next=unsafe{(*row).next};unsafe{ManuallyDrop::drop(&mut (*row).opening);crate::mem_helpers::kfree_tracked(row.cast(),FILE.as_ptr().cast_mut().cast(),line!() as CInt)};row=next;}
}
