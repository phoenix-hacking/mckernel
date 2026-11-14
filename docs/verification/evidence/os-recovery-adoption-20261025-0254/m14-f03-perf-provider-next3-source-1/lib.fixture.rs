#![no_std]
// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
mod abi { include!("retained-abi-types.Rust.inc"); }
mod x86_perfctr {
    use crate::abi::CInt;
    #[repr(C)] pub struct McPerfEvent { _opaque: [u8; 0] }
    unsafe extern "C" {
        #[link_name="fixture_extra_provider"]
        pub fn ihk_mc_perfctr_set_extra(event: *mut McPerfEvent) -> CInt;
        #[link_name="fixture_init_provider"]
        pub fn ihk_mc_perfctr_init_raw(counter: CInt, code: u32, mode: CInt) -> CInt;
    }
}
mod atomic_helpers {
    use core::sync::atomic::AtomicI64;
    use crate::abi::CLong;
    #[repr(C)] pub struct IhkAtomic64 { counter64: AtomicI64 }
    pub const COUNTER_OFFSET: usize = core::mem::offset_of!(IhkAtomic64, counter64);
    unsafe extern "C" {
        // Inert mock: the real retained provider remains SeqCst and is not run.
        #[link_name="fixture_atomic_provider"]
        pub fn ihk_atomic64_read(value: *const IhkAtomic64) -> CLong;
    }
}
mod policy {
    use core::ffi::c_void;
    use crate::abi::{CInt, CLong, CULong};
    include!("selected-bridges.Rust.inc");
    // Exact unchanged canonical wrapper, reused instead of porting it again.
    include!("retained-syscall-atomic64-read-bridge.Rust.inc");
    #[no_mangle] pub static F03_NEXT3_ABI: [CULong; 16] = [
        core::mem::size_of::<CInt>() as _, core::mem::align_of::<CInt>() as _,
        core::mem::size_of::<CULong>() as _, core::mem::align_of::<CULong>() as _,
        core::mem::size_of::<CLong>() as _, core::mem::align_of::<CLong>() as _,
        core::mem::size_of::<u32>() as _, core::mem::align_of::<u32>() as _,
        core::mem::size_of::<*mut c_void>() as _, core::mem::align_of::<*mut c_void>() as _,
        core::mem::size_of::<unsafe extern "C" fn(*mut c_void)->CInt>() as _,
        core::mem::size_of::<unsafe extern "C" fn(CInt,CULong,CInt)->CInt>() as _,
        core::mem::size_of::<unsafe extern "C" fn(*mut c_void)->CLong>() as _,
        core::mem::size_of::<crate::atomic_helpers::IhkAtomic64>() as _,
        core::mem::align_of::<crate::atomic_helpers::IhkAtomic64>() as _,
        crate::atomic_helpers::COUNTER_OFFSET as _,
    ];
}
