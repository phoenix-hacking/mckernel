//! Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
//! Full reachable set_host_vma prefix, then the existing qualified Rust body.

use crate::abi::{CInt, CULong, SizeT, X86UserContext};
use crate::x86_cpu_helpers::{
    ihk_mc_syscall_set_arg0, ihk_mc_syscall_set_arg1, ihk_mc_syscall_set_arg2,
};
use super::{get_this_cpu_local_var, set_host_vma_body_result};
use core::mem::{offset_of, size_of, MaybeUninit};

type SetArgFn = unsafe extern "C" fn(*mut X86UserContext, CULong);
type HostVmaFn = unsafe extern "C" fn(CULong, SizeT, CInt, CInt) -> CInt;
const _: SetArgFn = ihk_mc_syscall_set_arg0;
const _: SetArgFn = ihk_mc_syscall_set_arg1;
const _: SetArgFn = ihk_mc_syscall_set_arg2;
const _: HostVmaFn = set_host_vma_body_result;
const _: HostVmaFn = mprotect_set_host_vma_bridge;
const _: () = {
    assert!(size_of::<X86UserContext>() == 224);
    assert!(offset_of!(X86UserContext, gpr) == 56);
    assert!(size_of::<CULong>() == 8 && size_of::<SizeT>() == 8);
    assert!(size_of::<CInt>() == 4);
};

/// Preserve the original callback's complete reachable prefix and return.
///
/// # Safety
/// The existing CPU-local pointer remains valid/readable for its current slot;
/// the original body's current/thread/VM and borrowed lock/endpoint prerequisites
/// are unchanged. The unused current-thread value may be null as before. No new
/// lifetime, ownership, locking or null/errno policy is introduced here.
#[no_mangle]
pub(super) unsafe extern "C" fn mprotect_set_host_vma_bridge(
    start: CULong, len: SizeT, prot: CInt, holding_lock: CInt,
) -> CInt {
    // Private scratch only. X86UserContext and its nested register structs contain
    // only u64/u8 fields, so zero is valid. Initializing these otherwise unused
    // local bytes prevents references to uninitialized fields in existing setters.
    // The scratch pointer never escapes those setters; no context is read back.
    let mut ctx = MaybeUninit::<X86UserContext>::zeroed();
    // SAFETY: Exactly the original reachable current-slot read before setters.
    let _thread = unsafe { (*get_this_cpu_local_var()).current };
    // SAFETY: Naturally aligned, live, zero-initialized private224B scratch; each
    // unchanged setter performs its original volatile register write in order.
    // C size_t/unsigned long are64-bit here. C int prot converts to unsigned long
    // modulo2^64; Rust's direct signed-i32→u64 cast has that exact defined value.
    unsafe {
        ihk_mc_syscall_set_arg0(ctx.as_mut_ptr(), start);
        ihk_mc_syscall_set_arg1(ctx.as_mut_ptr(), len as CULong);
        ihk_mc_syscall_set_arg2(ctx.as_mut_ptr(), prot as CULong);
    }
    set_host_vma_body_result(start, len, prot, holding_lock)
}
