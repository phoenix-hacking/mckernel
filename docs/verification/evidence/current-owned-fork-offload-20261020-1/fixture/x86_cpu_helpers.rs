use crate::abi::CULong;
use core::ptr::read_volatile;
pub unsafe extern "C" fn cpu_pause() {
    core::arch::asm!("pause", options(nomem, nostack, preserves_flags));
}
pub unsafe extern "C" fn arch_barrier() {
    core::arch::asm!("", options(nostack, preserves_flags));
}
pub unsafe extern "C" fn smp_load_acquire_ulong(p: *const CULong) -> CULong {
    let value = unsafe { read_volatile(p) };
    unsafe { arch_barrier() };
    value
}