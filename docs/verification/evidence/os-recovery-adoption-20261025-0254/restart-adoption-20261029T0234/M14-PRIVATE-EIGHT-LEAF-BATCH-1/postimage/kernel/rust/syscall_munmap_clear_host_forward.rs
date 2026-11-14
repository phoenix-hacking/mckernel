//! Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
//! Existing do_munmap callback forwarding to the qualified Rust clear_host_pte.

use crate::abi::{CInt, CLong, CULong, SizeT};
use super::f03_clear_host_pte_entry_v1::clear_host_pte;

type ClearHostFn = unsafe extern "C" fn(CULong, SizeT, CInt) -> CLong;
const _: ClearHostFn = clear_host_pte;
const _: ClearHostFn = do_munmap_clear_host_bridge;
const _: () = {
    assert!(core::mem::size_of::<CULong>() == 8);
    assert!(core::mem::size_of::<SizeT>() == 8);
    assert!(core::mem::size_of::<CInt>() == 4);
    assert!(core::mem::size_of::<CLong>() == 8);
};

/// Retain the original scalar callback ABI and exact signed long return.
///
/// # Safety
/// The caller retains all existing clear_host_pte current CPU/thread/VM lifetime,
/// original memory-range-lock state and synchronous forwarding prerequisites.
/// The qualified Rust provider owns the existing request/endpoint/flag/logging
/// protocol; this callback adds no access, validation, lock, retry or cleanup.
#[no_mangle]
pub(super) unsafe extern "C" fn do_munmap_clear_host_bridge(
    addr: CULong, len: SizeT, holding_lock: CInt,
) -> CLong {
    // SAFETY: Unchanged exact original provider and argument order. No casts,
    // normalization or null/errno policy is introduced by this forwarding leaf.
    unsafe { clear_host_pte(addr, len, holding_lock) }
}
