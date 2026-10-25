// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
#[cfg(f03_io_diagnostic_callbacks_candidate)]
mod f03_io_diagnostic_callbacks_v1 {
    use core::ffi::c_void;
    use core::ptr::{addr_of, read_volatile};

    use crate::abi::{CInt, CLong, CULong, SizeT};

    use super::{ihk_mc_get_processor_id, kprintf};

    unsafe extern "C" {
        static mut f03_swapout_callback_debug_v1: crate::debug::Ddebug;
    }

    /// Emit the original gated swapout diagnostic before its existing body.
    ///
    /// # Safety
    /// The static debug record and formatter must be live. Debug-flag updates
    /// require the original dynamic-debug synchronization contract. Pointer values
    /// are formatted numerically and are never dereferenced by this callback.
    #[export_name = "syscall_swapout_log_bridge"]
    pub unsafe extern "C" fn swapout(
        filename: *const c_void,
        workarea: *mut c_void,
        size: SizeT,
        flag: CInt,
    ) {
        // SAFETY: This is the actual aligned static record, read without creating
        // a reference. Match the C macro's nonzero eight-bit flags test.
        let flags = unsafe {
            read_volatile(addr_of!(f03_swapout_callback_debug_v1.line_flags)) >> 24
        };
        if flags != 0 {
            // SAFETY: Original format, argument order and promoted scalar widths.
            // CPU lookup remains conditional, as in the original dkprintf macro.
            unsafe {
                kprintf(
                    c"[%d]swapout(%lx,%lx,%lx,%ld)\n".as_ptr().cast(),
                    ihk_mc_get_processor_id(),
                    filename as CULong,
                    workarea as CULong,
                    size as CULong,
                    flag as CLong,
                );
            }
        }
    }

    /// Emit the original unconditional Linux-mlock diagnostic.
    ///
    /// # Safety
    /// The genuine kernel formatter must be available in this context. The address
    /// is only formatted as a pointer; this callback does not access user memory.
    #[export_name = "syscall_linux_mlock_log_bridge"]
    pub unsafe extern "C" fn linux_mlock(address: CULong, length: SizeT) {
        // SAFETY: Match the original pointer and signed-long variadic slots;
        // converting length preserves all bits, including its signed presentation.
        unsafe {
            kprintf(
                c"linux_mlock: %p %ld\n".as_ptr().cast(),
                address as *const c_void,
                length as CLong,
            );
        }
    }
}
