// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
#![no_std]
#![allow(dead_code)]
#[path="abi.ACTUAL.rs"] mod abi;
use core::ffi::c_void;
use core::ptr::null_mut;
use abi::{CInt,CULong,Memobj,ProcessVm,VmRange};
#[repr(C)] struct ProcessSyncArgs { memobj:*mut Memobj }
type ProcessNoirqLockFn=unsafe extern "C" fn(CULong);
type ProcessNoirqUnlockFn=unsafe extern "C" fn(CULong);
type ProcessVisitPteRangeFn=unsafe extern "C" fn(*mut c_void,CULong,CULong,CInt,CInt,*mut c_void,*mut c_void)->CInt;
type ProcessSyncRangeLogFn=unsafe extern "C" fn(*mut ProcessVm,*mut VmRange,CULong,CULong,CInt);
extern "C" {
 fn sync_one_page(arg0:*mut c_void,page_table:*mut c_void,ptep:*mut c_void,pgaddr:*mut c_void,pgshift:CInt)->CInt;
 fn process_sync_memory_range_body_result(vm:*mut ProcessVm,range:*mut VmRange,start:CULong,end:CULong,arg:*mut c_void,visit_step_fn:*mut c_void,lock_fn:Option<ProcessNoirqLockFn>,unlock_fn:Option<ProcessNoirqUnlockFn>,visit_fn:Option<ProcessVisitPteRangeFn>,log_fn:Option<ProcessSyncRangeLogFn>)->CInt;
 fn process_free_range_noirq_lock_bridge(lock_addr:CULong);
 fn process_free_range_noirq_unlock_bridge(lock_addr:CULong);
 fn process_visit_pte_range_bridge(page_table:*mut c_void,start:CULong,end:CULong,pgshift:CInt,flags:CInt,visit_fn:*mut c_void,arg:*mut c_void)->CInt;
 fn process_sync_range_log_bridge(vm:*mut ProcessVm,range:*mut VmRange,start:CULong,end:CULong,error:CInt);
}
#[no_mangle]
pub unsafe extern "C" fn sync_process_memory_range(
    vm: *mut ProcessVm,
    range: *mut VmRange,
    start: CULong,
    end: CULong,
) -> CInt {
    let memobj = if range.is_null() {
        null_mut()
    } else {
        (*range).memobj.cast::<Memobj>()
    };
    let mut args = ProcessSyncArgs { memobj };

    process_sync_memory_range_body_result(
        vm,
        range,
        start,
        end,
        (&mut args as *mut ProcessSyncArgs).cast(),
        sync_one_page as *mut c_void,
        Some(process_free_range_noirq_lock_bridge),
        Some(process_free_range_noirq_unlock_bridge),
        Some(process_visit_pte_range_bridge),
        Some(process_sync_range_log_bridge),
    )
}
