// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
// Eligible namespace/prototype/source-width repairs; no do_fork activation.
use core::ffi::c_void;
use core::mem::MaybeUninit;
use core::ptr::addr_of_mut;
use crate::abi::{CInt,CLong,CULong,Process,Thread};
use crate::lock_helpers::McsRwlockNodeIrqsave;
use crate::fork_control_guest::{
    CallerForkOutcome,process_fork_construct_current_v1,
    process_fork_cancel_constructed_current_v1,
    process_fork_owned_caller_runnable_current_v2,
};

/// Copy only the host flag word under the actual parent-edge update lock.
/// # Safety
/// Running caller retains process; all parent-edge replacement takes its
/// update writer, and the current edge retains parent storage while locked.
/// This requires the same graph contract as existing clone-parent publication.
pub(crate) unsafe fn snapshot_host_parent_flags(process:*mut Process,flags:CInt)->Result<CULong,CInt>{
    if process.is_null(){return Err(-22);}
    let mut node=MaybeUninit::<McsRwlockNodeIrqsave>::uninit();
    unsafe{
        let lock=addr_of_mut!((*process).update_lock).cast();
        crate::lock_helpers::__mcs_rwlock_reader_lock(lock,node.as_mut_ptr());
        let parent=(*process).ppid_parent;
        let result=if parent.is_null(){Err(-22)}else{
            let policy:CInt=crate::syscall_policy::clone_host_parent_flags_result(flags,(*parent).pid);
            // Original C passes signed int to unsigned long. First widen int
            // to signed long, then apply that original modulo-2^64 conversion.
            // No narrowing or alternate provider ABI is introduced.
            let signed:CLong=CLong::from(policy);
            Ok(signed as CULong)
        };
        crate::lock_helpers::__mcs_rwlock_reader_unlock(lock,node.as_mut_ptr());
        result
    }
}

// Exact existing real-crate signatures. They typecheck without exposing the
// pub(super) constructed module itself or copying any constructor/host body.
const _:unsafe extern "C" fn(*mut Thread,CULong,CULong,CInt,CInt,*mut *mut c_void)->*mut Thread
    =process_fork_construct_current_v1;
const _:unsafe extern "C" fn(*mut c_void)->CInt
    =process_fork_cancel_constructed_current_v1;
const _:unsafe extern "C" fn(*mut Thread,*mut Thread,CInt,CULong,*mut c_void,CInt,CInt,CULong,*mut CallerForkOutcome)->CInt
    =process_fork_owned_caller_runnable_current_v2;
