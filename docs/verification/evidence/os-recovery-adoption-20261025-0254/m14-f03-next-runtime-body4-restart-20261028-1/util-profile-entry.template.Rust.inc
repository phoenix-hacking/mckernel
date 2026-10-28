// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
mod f03_util_profile_v1 {
    use core::ptr;
    use crate::abi::{CInt as c_int, CLong as c_long, CULong as c_ulong};

    // Exact existing project Rust ABI declarations, reused without field edits.
    // SOURCE_GENERATOR_INSERTS_EXACT_REUSED_UTI_ABI_HERE

    /// Print the original two ordered syscall-counter tables.
    ///
    /// # Safety
    /// The original caller supplies a live, aligned, initialized UtiDesc at the
    /// captured uti_desc address for the entire call. It retains the existing
    /// foreign-memory synchronization/lifetime contract. No borrowed whole
    /// descriptor reference is formed and no descriptor byte is written.
    #[no_mangle]
    pub unsafe extern "C" fn util_show_syscall_profile() -> c_int {
        // SAFETY: Same one-time global descriptor capture before the first log.
        let desc = unsafe { super::uti_desc as *const UtiDesc };
        unsafe {
            super::kprintf(b"Syscall stats for offloaded thread:\n\0".as_ptr().cast());
            for i in 0..UTI_SYSCALL_PROFILE_SLOTS {
                let slot = ptr::addr_of!((*desc).syscalls).cast::<c_long>().add(i);
                if ptr::read(slot) != 0 {
                    super::kprintf(b"nr=%d #called=%ld\n\0".as_ptr().cast(), i as c_int, ptr::read(slot));
                }
            }
            super::kprintf(b"Syscall stats for other threads:\n\0".as_ptr().cast());
            for i in 0..UTI_SYSCALL_PROFILE_SLOTS {
                let slot = ptr::addr_of!((*desc).syscalls2).cast::<c_long>().add(i);
                if ptr::read(slot) != 0 {
                    super::kprintf(b"nr=%d #called=%ld\n\0".as_ptr().cast(), i as c_int, ptr::read(slot));
                }
            }
        }
        0
    }
}
