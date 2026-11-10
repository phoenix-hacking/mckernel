// Functional OS protocol witness only. No IKC, registry, carrier, native call or fake ACK.
#![no_std]
#[path = "/home/holden/mckernel/kernel/rust/abi.rs"]
mod abi;
use abi::{CInt,CULong,SyscallRequest,SyscallResponse,Thread};
use core::mem::size_of;
use core::ptr::{addr_of_mut,copy_nonoverlapping,write};
use core::sync::atomic::{AtomicU64,Ordering};
const EINVAL:CInt=22;
const CLONE_PARENT: CInt = 0x00008000;
const NR_CLONE:u64=56;const MARKER:u64=0x313030434b46434d;

#[no_mangle]
pub extern "C" fn syscall_use_requester_tid_result(
    syscall_nr: CInt,
    arg0: CULong,
    sched_setaffinity_nr: CInt,
) -> CInt {
    (syscall_nr == sched_setaffinity_nr && arg0 == 0) as CInt
}

#[no_mangle]
pub extern "C" fn syscall_target_tid_result(use_requester_tid: CInt, current_tid: CInt) -> CInt {
    if use_requester_tid != 0 {
        current_tid
    } else {
        0
    }
}

#[no_mangle]
pub unsafe extern "C" fn syscall_send_prepare_result(
    request: *mut SyscallRequest,
    response: *mut SyscallResponse,
) -> CInt {
    if request.is_null() || response.is_null() {
        return -EINVAL;
    }

    write(core::ptr::addr_of_mut!((*response).status), 0);
    write(core::ptr::addr_of_mut!((*request).valid), 0);

    0
}

#[no_mangle]
pub unsafe extern "C" fn syscall_request_copy_result(
    dst: *mut SyscallRequest,
    src: *const SyscallRequest,
) -> CInt {
    if dst.is_null() || src.is_null() {
        return -EINVAL;
    }

    // The Linux proxy protocol historically copies this wire object with
    // memcpy.  In particular, a nested request can begin at an address that
    // is not aligned for `SyscallRequest`; keeping the operation byte-typed
    // preserves those semantics without creating an unaligned Rust reference.
    copy_nonoverlapping(
        src.cast::<u8>(),
        dst.cast::<u8>(),
        size_of::<SyscallRequest>(),
    );

    0
}

#[no_mangle]
pub unsafe extern "C" fn syscall_request_publish_result(request: *mut SyscallRequest) -> CInt {
    if request.is_null() {
        return -EINVAL;
    }

    AtomicU64::from_ptr(addr_of_mut!((*request).valid)).store(1, Ordering::Release);
    0
}

#[no_mangle]
pub unsafe extern "C" fn syscall_offload_prepare_result(
    request: *mut SyscallRequest,
    response: *mut SyscallResponse,
    current_tid: CInt,
    syscall_nr: CInt,
    arg0: CULong,
    sched_setaffinity_nr: CInt,
    spinning_status: CULong,
) -> CInt {
    if request.is_null() || response.is_null() {
        return -EINVAL;
    }

    let use_requester_tid =
        syscall_use_requester_tid_result(syscall_nr, arg0, sched_setaffinity_nr);
    let target_tid = syscall_target_tid_result(use_requester_tid, current_tid);

    write(core::ptr::addr_of_mut!((*request).rtid), current_tid);
    write(core::ptr::addr_of_mut!((*request).ttid), target_tid);
    write(
        core::ptr::addr_of_mut!((*response).req_thread_status),
        spinning_status,
    );
    write(
        core::ptr::addr_of_mut!((*response).pde_data),
        core::ptr::null_mut(),
    );

    use_requester_tid
}

#[no_mangle]
pub extern "C" fn clone_host_parent_flags_result(clone_flags: CInt, ppid_parent_pid: CInt) -> CInt {
    if (clone_flags & CLONE_PARENT) != 0 && ppid_parent_pid != 1 {
        clone_flags
    } else {
        0
    }
}

// The actual unchanged reply observer's first condition is copied byte-for-byte
// below. Return 1 exposes its early-return branch; 0 means only that this FIRST
// discriminator matched. No carrier/ACK acceptance or observer body is simulated.
#[no_mangle]
pub unsafe extern "C" fn f03_reply_observer_ignores_wire(
    request:*mut SyscallRequest,response:*mut SyscallResponse,thread:*mut Thread,
)->CInt {
    if request.is_null()||response.is_null()||thread.is_null()||(*request).number!=NR_CLONE||(*request).args[5]!=MARKER{return 1;}
    0
}
const _: unsafe extern "C" fn(*mut SyscallRequest,*const SyscallRequest)->CInt = syscall_request_copy_result;
const _: unsafe extern "C" fn(*mut SyscallRequest,*mut SyscallResponse,CInt,CInt,CULong,CInt,CULong)->CInt = syscall_offload_prepare_result;
