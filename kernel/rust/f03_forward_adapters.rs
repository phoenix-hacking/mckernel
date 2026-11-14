// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
// Candidate source only: default selection and final ABI/link/native proof remain open.
use core::mem::MaybeUninit;

use crate::abi::{CInt, CLong, CULong, SyscallRequest};

const SYS_WAIT4: CInt = 61; // Supported x86_64 __NR_wait4.

unsafe extern "C" {
    fn do_syscall(request: *mut SyscallRequest, cpu: CInt) -> CLong;
}

/// Construct a private, completely initialized request and retain it for the
/// complete synchronous transaction. Supported x86 IHK_DMA_ALIGN is empty;
/// SyscallRequest keeps the existing repr(C) natural alignment.
///
/// The old C adapters left the unused arguments unspecified. Zero defines those
/// bytes; parity is with the actual supported consumers, which ignore them, not
/// with unspecified stack contents. This is no waiver of any other partial-
/// request caller's hold. No Rust reference is held across the offload.
///
/// # Safety
/// The current CPU/thread and offload channel satisfy do_syscall's original
/// contract. This adapter is only for consumers that use at most args0..2;
/// callers of the two-argument entry additionally ignore args2.
unsafe fn forward_request(number: CInt, arg0: CULong, arg1: CULong, arg2: CULong) -> CLong {
    let mut request = MaybeUninit::<SyscallRequest>::zeroed();
    let cpu = unsafe { crate::x86_local::ihk_mc_get_processor_id() };
    // Reuse the real six-argument builder and the real do_syscall provider.
    // The local request remains live until the blocking call has returned.
    unsafe {
        crate::syscall_policy::syscall_generic_forwarding_body_result(
            request.as_mut_ptr(), number, arg0, arg1, arg2, 0, 0, 0, cpu,
            Some(do_syscall),
        )
    }
}

/// # Safety
/// Original current-thread/offload and two-argument consumer contracts apply.
#[no_mangle]
pub unsafe extern "C" fn syscall_do_syscall2_bridge(
    syscall_nr: CInt, arg0: CULong, arg1: CULong,
) -> CLong {
    unsafe { forward_request(syscall_nr, arg0, arg1, 0) }
}

/// # Safety
/// Original current-thread/offload and three-argument consumer contracts apply.
#[no_mangle]
pub unsafe extern "C" fn syscall_do_syscall3_bridge(
    syscall_nr: CInt, arg0: CULong, arg1: CULong, arg2: CULong,
) -> CLong {
    unsafe { forward_request(syscall_nr, arg0, arg1, arg2) }
}

/// # Safety
/// Same contract as syscall_do_syscall2_bridge; there is one transaction.
#[no_mangle]
pub unsafe extern "C" fn syscall_policy_do_syscall2_bridge(
    syscall_nr: CInt, arg0: CULong, arg1: CULong,
) -> CLong {
    unsafe { syscall_do_syscall2_bridge(syscall_nr, arg0, arg1) }
}

/// # Safety
/// Same contract as syscall_do_syscall3_bridge; there is one transaction.
#[no_mangle]
pub unsafe extern "C" fn syscall_policy_do_syscall3_bridge(
    syscall_nr: CInt, arg0: CULong, arg1: CULong, arg2: CULong,
) -> CLong {
    unsafe { syscall_do_syscall3_bridge(syscall_nr, arg0, arg1, arg2) }
}

/// # Safety
/// Original host-wait and current-thread/offload contracts apply. Both actual
/// mcexec wait4 consumers read args0/2 and ignore the other arguments. Direct
/// CInt -> CULong casts preserve C's signed extension, including negative pids.
#[no_mangle]
pub unsafe extern "C" fn wait_host_wait4_bridge(pid: CInt, options: CInt) -> CInt {
    // The C return converts do_syscall's long result to int before its caller
    // observes it; preserve that supported x86_64 truncation here.
    unsafe { forward_request(SYS_WAIT4, pid as CULong, 0, options as CULong) as CInt }
}
