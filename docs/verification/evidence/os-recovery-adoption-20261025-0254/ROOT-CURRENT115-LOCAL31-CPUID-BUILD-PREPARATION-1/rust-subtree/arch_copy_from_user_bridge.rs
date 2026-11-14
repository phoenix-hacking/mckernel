// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
use core::ffi::c_void;
use crate::abi::{CLong, CULong, SizeT};

/// # Safety
/// Identical public copy_from_user preconditions: destination covers bytes in
/// live kernel memory; user source address is checked by the genuine provider.
#[no_mangle]
pub unsafe extern "C" fn arch_copy_from_user_bridge(
    destination: *mut c_void,
    src_addr: CULong,
    bytes: SizeT,
) -> CLong {
    // SAFETY: original pointer/integer conversion and synchronous provider call;
    // no unchecked copy or new all-or-nothing policy is introduced here.
    let result = unsafe {
        crate::x86_memory_helpers::copy_from_user(destination, src_addr as *const c_void, bytes)
    };
    result as CLong
}
