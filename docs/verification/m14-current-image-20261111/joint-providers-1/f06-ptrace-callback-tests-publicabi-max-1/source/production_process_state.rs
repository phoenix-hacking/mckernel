use core::ffi::c_void;
use crate::abi::{CInt,CULong};
const PT_TRACE_SYSCALL: CInt = 0x200;

const PTRACE_RESUME_SIGNAL_SOURCE_SENDSIG: CInt = 1;

const PTRACE_RESUME_SIGNAL_SOURCE_RECVSIG: CInt = 2;

#[no_mangle]
pub unsafe extern "C" fn process_thread_ptrace_saved_context_clear_result(
    thread: *mut c_void,
    saved_valid_offset: CULong,
) -> CInt {
    if thread.is_null() {
        return 0;
    }

    *(thread
        .cast::<u8>()
        .wrapping_add(saved_valid_offset as usize)
        .cast::<CInt>()) = 0;
    1
}

#[no_mangle]
pub unsafe extern "C" fn process_thread_ptrace_trace_syscall_update_result(
    thread: *mut c_void,
    ptrace_offset: CULong,
    trace_syscall: CInt,
) -> CInt {
    if thread.is_null() {
        return 0;
    }

    let ptrace = thread
        .cast::<u8>()
        .wrapping_add(ptrace_offset as usize)
        .cast::<CInt>();
    *ptrace &= !PT_TRACE_SYSCALL;
    if trace_syscall != 0 {
        *ptrace |= PT_TRACE_SYSCALL;
    }
    *ptrace
}

#[no_mangle]
pub unsafe extern "C" fn process_thread_ptrace_pending_signal_take_result(
    thread: *mut c_void,
    sendsig_offset: CULong,
    recvsig_offset: CULong,
    source: CInt,
) -> *mut c_void {
    if thread.is_null() {
        return core::ptr::null_mut();
    }

    let base = thread.cast::<u8>();
    let slot = if source == PTRACE_RESUME_SIGNAL_SOURCE_SENDSIG {
        base.wrapping_add(sendsig_offset as usize)
            .cast::<*mut c_void>()
    } else if source == PTRACE_RESUME_SIGNAL_SOURCE_RECVSIG {
        base.wrapping_add(recvsig_offset as usize)
            .cast::<*mut c_void>()
    } else {
        return core::ptr::null_mut();
    };

    let pending = *slot;
    *slot = core::ptr::null_mut();
    pending
}
// Explicit controlled HOST lookup/unlock effects; never kernel locks or refs.
pub unsafe extern "C" fn find_thread(pid:CInt,tid:CInt)->*mut crate::abi::Thread { crate::host_find(pid,tid) }
pub unsafe extern "C" fn thread_unlock(thread:*mut crate::abi::Thread) { crate::host_thread_unlock(thread) }
