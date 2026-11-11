//! Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
//! Narrow two-argument offload entry for the qualified ordinary x86_64 profile.
use core::mem::{align_of, offset_of, size_of, MaybeUninit};

use crate::abi::{CInt, CLong, CULong, SyscallRequest};

#[cfg(any(
    not(target_arch = "x86_64"),
    not(native_linux_irq_work_v6_12),
    not(enable_profile),
    not(enable_perf),
    not(enable_rusage),
    enable_tofu,
    enable_fugaku_hacks,
    f03_forward_adapters_candidate,
))]
compile_error!("two-argument offload bridge requires the qualified ordinary profile without broad adapters");

unsafe extern "C" {
    fn do_syscall(request: *mut SyscallRequest, cpu: CInt) -> CLong;
}

/// Preserve the real two-argument offload transaction and signed long result.
///
/// Unused request fields are defined as zero before the unchanged six-argument
/// builder writes number/args and calls the genuine synchronous do_syscall.
/// That provider still owns requester/target TID, publication, accounting,
/// monitor, preemption, nested work and reply handling. No response is supplied
/// here, and no Rust reference spans the transaction or a context switch.
///
/// # Safety
/// The original current Thread/Process and CPU's live offload channel must
/// remain valid through do_syscall. Its Linux/custom consumer uses at most
/// args0/1. The private stack request stays live until the call returns; this
/// entry neither retains a request pointer nor changes caller ownership.
#[no_mangle]
pub unsafe extern "C" fn syscall_policy_do_syscall2_bridge(
    number: CInt,
    arg0: CULong,
    arg1: CULong,
) -> CLong {
    let mut request = MaybeUninit::<SyscallRequest>::zeroed();
    let cpu = unsafe { crate::x86_local::ihk_mc_get_processor_id() };
    // SAFETY: The complete stack slot and current CPU satisfy the existing
    // builder/provider contract. Only a raw pointer crosses the blocking call.
    unsafe {
        crate::syscall_policy::syscall_generic_forwarding_body_result(
            request.as_mut_ptr(), number, arg0, arg1, 0, 0, 0, 0, cpu,
            Some(do_syscall),
        )
    }
}

const _: unsafe extern "C" fn(CInt, CULong, CULong) -> CLong =
    syscall_policy_do_syscall2_bridge;
const _: () = {
    assert!(size_of::<CInt>() == 4);
    assert!(size_of::<CLong>() == 8 && size_of::<CULong>() == 8);
    assert!(size_of::<SyscallRequest>() == 72 && align_of::<SyscallRequest>() == 8);
    assert!(offset_of!(SyscallRequest, rtid) == 0);
    assert!(offset_of!(SyscallRequest, ttid) == 4);
    assert!(offset_of!(SyscallRequest, valid) == 8);
    assert!(offset_of!(SyscallRequest, number) == 16);
    assert!(offset_of!(SyscallRequest, args) == 24);
};
