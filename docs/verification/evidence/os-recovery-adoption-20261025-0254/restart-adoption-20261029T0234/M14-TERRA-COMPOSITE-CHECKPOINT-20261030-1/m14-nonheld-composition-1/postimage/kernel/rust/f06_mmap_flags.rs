// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
// Exact existing flag providers: no logger, special-register or lock code copied.
// cfg(f06_use_nocache_mmap) mirrors the genuine C USE_NOCACHE_MMAP definition.
use crate::abi::CInt;

use super::{
    MAP_ANONYMOUS, MAP_FIXED, MAP_HUGETLB, MAP_HUGE_MASK, MAP_LOCKED, MAP_POPULATE,
    MAP_PRIVATE, MAP_SHARED,
};

const F06_MAP_32BIT: CInt = 0x40;
const F06_MAP_GROWSDOWN: CInt = 0x100;
const F06_MAP_DENYWRITE: CInt = 0x800;
const F06_MAP_EXECUTABLE: CInt = 0x1000;
const F06_MAP_NORESERVE: CInt = 0x4000;
const F06_MAP_NONBLOCK: CInt = 0x10000;
const F06_MAP_STACK: CInt = 0x20000;

#[no_mangle]
pub extern "C" fn arch_mmap_supported_flags_bridge() -> CInt {
    MAP_SHARED | MAP_PRIVATE | MAP_FIXED | MAP_ANONYMOUS | MAP_LOCKED
        | MAP_POPULATE | MAP_HUGETLB | MAP_HUGE_MASK
}

#[no_mangle]
pub extern "C" fn arch_mmap_ignored_flags_bridge() -> CInt {
    let ignored = F06_MAP_DENYWRITE | F06_MAP_NORESERVE | F06_MAP_STACK;
    #[cfg(f06_use_nocache_mmap)]
    { ignored | F06_MAP_32BIT }
    #[cfg(not(f06_use_nocache_mmap))]
    { ignored }
}

#[no_mangle]
pub extern "C" fn arch_mmap_error_flags_bridge() -> CInt {
    let errors = F06_MAP_GROWSDOWN | F06_MAP_EXECUTABLE | F06_MAP_NONBLOCK;
    #[cfg(not(f06_use_nocache_mmap))]
    { errors | F06_MAP_32BIT }
    #[cfg(f06_use_nocache_mmap)]
    { errors }
}
