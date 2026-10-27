// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
// Exact existing private adapter; actual do_mmap retains every mapping ownership effect.
use core::ffi::c_void;

use crate::abi::{CInt, CLong, CULong, SizeT};

unsafe extern "C" {
    #[link_name = "do_mmap"]
    fn f06_mapping_do_mmap(
        addr: CULong, len: SizeT, prot: CInt, flags: CInt,
        fd: CInt, off: CLong, vrf0: CInt, private_data: *mut c_void,
    ) -> CLong;
}

/// # Safety
/// Existing do_mmap current VM/locks/memobj/private-data ownership contract.
/// This adapter neither adopts private_data nor rolls back partial effects.
#[no_mangle]
pub unsafe extern "C" fn arch_do_mmap_bridge(
    addr: CULong, len: SizeT, prot: CInt, flags: CInt,
    fd: CInt, off: CLong, vrf0: CInt, private_data: *mut c_void,
) -> CLong {
    // SAFETY: exact eight arguments and intptr_t result, including negative errors.
    unsafe { f06_mapping_do_mmap(addr, len, prot, flags, fd, off, vrf0, private_data) }
}
