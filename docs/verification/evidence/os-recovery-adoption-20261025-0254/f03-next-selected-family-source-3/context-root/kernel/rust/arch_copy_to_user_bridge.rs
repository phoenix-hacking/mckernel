// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
use core::ffi::c_void;
use crate::abi::{CLong, CULong, SizeT};

/// # Safety
/// Identical public copy_to_user preconditions: destination address is checked by
/// the actual user-copy provider; source covers bytes in live kernel memory.
/// This adapter retains no address or borrow and preserves int-to-long extension.
#[no_mangle]
pub unsafe extern "C" fn arch_copy_to_user_bridge(
    dst_addr: CULong,
    source: *const c_void,
    bytes: SizeT,
) -> CLong {
    // SAFETY: exact original pointer bits and length delegated to the existing
    // selected Rust user-copy mechanism, including its native fault fixups.
    let result = unsafe {
        crate::x86_memory_helpers::copy_to_user(dst_addr as *mut c_void, source, bytes)
    };
    result as CLong
}
