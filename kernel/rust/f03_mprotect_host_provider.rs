//! Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
//! Genuine shared mprotect/shmat host-VMA callback; reuse the qualified Rust body.
use core::mem::{align_of, size_of};
use crate::abi::{CInt, CULong, SizeT};

#[cfg(any(not(target_arch = "x86_64"), not(native_linux_irq_work_v6_12),
    not(enable_profile), not(enable_perf), not(enable_rusage), enable_tofu,
    enable_fugaku_hacks, f03_forward_adapters_candidate,
    not(f03_memory_host_offload_candidate)))]
compile_error!("mprotect host provider requires its paired qualified memory-host profile");

/// Preserve the original synchronous host-VMA callback used by mprotect and shmat.
///
/// # Safety
/// The original current thread and VM must remain live. The complete caller owns
/// the original VM/list/range locks and references, including the range lock when
/// holding_lock is nonzero. The qualified provider retains the current-thread
/// lookup, initialized private context and three real argument-setter calls,
/// native PFN invalidation, borrowed flag restoration and exact signed-int result.
/// This endpoint adds no argument conversion, lock, reference, log or stored borrow.
#[no_mangle]
pub unsafe extern "C" fn mprotect_set_host_vma_bridge(
    start: CULong, len: SizeT, prot: CInt, holding_lock: CInt,
) -> CInt {
    unsafe {
        crate::f03_memory_host_offload::do_munmap_set_host_bridge(
            start, len, prot, holding_lock,
        )
    }
}

const _: unsafe extern "C" fn(CULong, SizeT, CInt, CInt) -> CInt =
    mprotect_set_host_vma_bridge;
const _: unsafe extern "C" fn(CULong, SizeT, CInt, CInt) -> CInt =
    crate::f03_memory_host_offload::do_munmap_set_host_bridge;
const _: () = {
    assert!(size_of::<CInt>() == 4 && align_of::<CInt>() == 4);
    assert!(size_of::<CULong>() == 8 && align_of::<CULong>() == 8);
    assert!(size_of::<SizeT>() == 8 && align_of::<SizeT>() == 8);
};
