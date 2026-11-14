// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
// Exact existing private adapter, with original provider ownership retained.
use crate::abi::{CInt, CLong, SizeT};

unsafe extern "C" {
    #[link_name = "do_shmget"]
    fn f06_mapping_do_shmget(key: CInt, size: SizeT, flags: CInt) -> CInt;
}

/// # Safety
/// Existing do_shmget resource-set/IPC/exclusion contract. key_t is genuine
/// signed int32; preserve C's narrowing from long before the provider call.
#[no_mangle]
pub unsafe extern "C" fn arch_do_shmget_bridge(key: CLong, size: SizeT, flags: CInt) -> CInt {
    // SAFETY: existing public IPC body owns all allocations/refs/error policy.
    unsafe { f06_mapping_do_shmget(key as CInt, size, flags) }
}
