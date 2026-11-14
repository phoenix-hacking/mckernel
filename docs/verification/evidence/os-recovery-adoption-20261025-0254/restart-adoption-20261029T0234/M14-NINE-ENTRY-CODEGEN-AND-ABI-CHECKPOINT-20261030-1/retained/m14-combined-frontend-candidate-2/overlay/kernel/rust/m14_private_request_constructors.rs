//! Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
//! Experimental declared-arity wire constructors; default selection stays disabled.
use core::mem::{align_of, offset_of, size_of, MaybeUninit};
use core::ptr::addr_of_mut;
use crate::abi::{CInt, CLong, CULong, SyscallRequest};

// The selected x86 request has its own natural C type alignment.
const _: () = {
    assert!(size_of::<SyscallRequest>() == 72 && align_of::<SyscallRequest>() == 8);
    assert!(offset_of!(SyscallRequest, number) == 16 && offset_of!(SyscallRequest, args) == 24);
    assert!(align_of::<MaybeUninit<SyscallRequest>>() == 8);
};

/// Construct only the approved wire fields; IDs and valid belong to the callee.
///
/// # Safety
/// The existing synchronous do_syscall contract, request/response lifetime,
/// endpoint and caller-specific number/argument preconditions must all hold.
/// The current CPU and helper must be usable in the calling context.
unsafe fn forward(number: CInt, args: [CULong; 6]) -> CLong {
    let mut storage = MaybeUninit::<SyscallRequest>::uninit();
    let request = storage.as_mut_ptr();
    // SAFETY: Aligned live storage. Raw field pointers never form a reference to
    // the incomplete request. Only approved number and six wire slots are set;
    // the existing helper owns sender IDs and valid before their first read.
    unsafe {
        addr_of_mut!((*request).number).write(number as CULong);
        let slots = addr_of_mut!((*request).args).cast::<CULong>();
        slots.add(0).write(args[0]);
        slots.add(1).write(args[1]);
        slots.add(2).write(args[2]);
        slots.add(3).write(args[3]);
        slots.add(4).write(args[4]);
        slots.add(5).write(args[5]);
        super::do_syscall(request, super::ihk_mc_get_processor_id())
    }
}

/// # Safety
/// Caller meets the approved two-argument wire and existing do_syscall contracts.
pub unsafe extern "C" fn syscall_do_syscall2_bridge(number: CInt, arg0: CULong, arg1: CULong) -> CLong {
    unsafe { forward(number, [arg0, arg1, 0, 0, 0, 0]) }
}
/// # Safety
/// Same contract as the two-argument callback; its wire values are unchanged.
pub unsafe extern "C" fn syscall_policy_do_syscall2_bridge(number: CInt, arg0: CULong, arg1: CULong) -> CLong {
    unsafe { forward(number, [arg0, arg1, 0, 0, 0, 0]) }
}
/// # Safety
/// Caller meets the approved three-argument wire and existing do_syscall contracts.
pub unsafe extern "C" fn syscall_do_syscall3_bridge(number: CInt, arg0: CULong, arg1: CULong, arg2: CULong) -> CLong {
    unsafe { forward(number, [arg0, arg1, arg2, 0, 0, 0]) }
}
/// # Safety
/// Same contract as the three-argument callback; its wire values are unchanged.
pub unsafe extern "C" fn syscall_policy_do_syscall3_bridge(number: CInt, arg0: CULong, arg1: CULong, arg2: CULong) -> CLong {
    unsafe { forward(number, [arg0, arg1, arg2, 0, 0, 0]) }
}
/// # Safety
/// Caller meets the original wait4 process and do_syscall lifetime contracts.
pub unsafe extern "C" fn wait_host_wait4_bridge(pid: CInt, options: CInt) -> CInt {
    const SYS_WAIT4: CInt = 61;
    unsafe { forward(SYS_WAIT4, [pid as CULong, 0, options as CULong, 0, 0, 0]) as CInt }
}

type Two = unsafe extern "C" fn(CInt, CULong, CULong) -> CLong;
type Three = unsafe extern "C" fn(CInt, CULong, CULong, CULong) -> CLong;
const _: Two = syscall_do_syscall2_bridge;
const _: Two = syscall_policy_do_syscall2_bridge;
const _: Three = syscall_do_syscall3_bridge;
const _: Three = syscall_policy_do_syscall3_bridge;
const _: unsafe extern "C" fn(CInt, CInt) -> CInt = wait_host_wait4_bridge;
