#![no_std]
#[path = "/home/holden/mckernel/kernel/rust/abi.rs"]
mod abi;
mod spinlock_helpers;
mod lock_helpers;
mod process_helpers;
mod syscall_policy;

// Type guards only; no runtime fixture or extra exported/data owner.
const _: unsafe extern "C" fn(abi::CInt, *mut core::ffi::c_void) -> *mut core::ffi::c_void = syscall_policy::syscall_find_process_bridge;
const _: unsafe extern "C" fn(*mut core::ffi::c_void, *mut core::ffi::c_void) = syscall_policy::syscall_process_unlock_bridge;
const _: unsafe extern "C" fn(abi::CInt, *mut lock_helpers::McsRwlockNodeIrqsave) -> *mut abi::Process = process_helpers::find_process;
const _: unsafe extern "C" fn(*mut abi::Process, *mut lock_helpers::McsRwlockNodeIrqsave) = process_helpers::process_unlock;
const _: () = {
    use core::mem::{size_of,align_of,offset_of};
    assert!(size_of::<abi::CInt>() == 4);
    assert!(size_of::<abi::CULong>() == 8);
    assert!(size_of::<*mut core::ffi::c_void>() == 8);
    assert!(size_of::<process_helpers::ProcessFindProcessOffsets>() == 16);
    assert!(align_of::<process_helpers::ProcessFindProcessOffsets>() == 8);
    assert!(offset_of!(abi::Process,hash_list) == 0);
    assert!(offset_of!(abi::Process,pid) == 456);
};
