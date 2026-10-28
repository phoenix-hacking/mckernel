// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
mod f03_setresuid_entry_v1 {
    use core::mem::{offset_of, MaybeUninit};
    use crate::abi::{CInt, Process, Thread};
    use super::{getcred, syscall_refresh_cred_fields_body_result};

    /// Refresh the original four UID fields through the existing credential body.
    ///
    /// # Safety
    /// Current CPU/thread/process and synchronous credential-provider lifetimes
    /// retain their original contracts. The provider must initialize each of the
    /// four consumed response values before returning a non-null pointer. Its
    /// existing ignored-offload-error/uninitialized-response limitation remains;
    /// this entry supplies no new acknowledgement, error handling or zero-fill.
    #[no_mangle]
    pub unsafe extern "C" fn do_setresuid() {
        let mut scratch = MaybeUninit::<[CInt; 16]>::uninit();
        // SAFETY: Same original live CPU-local lookup and borrowed thread pointer.
        let cpu = unsafe { crate::cls::get_this_cpu_local_var() };
        let thread = unsafe { (*cpu).current };
        // SAFETY: Sixteen properly aligned writable C ints are available until
        // the synchronous provider returns. Only initialized provider values are
        // read. Existing body preserves provider order and null/error branches.
        let _ = unsafe {
            syscall_refresh_cred_fields_body_result(
                thread.cast(), scratch.as_mut_ptr().cast(),
                offset_of!(Thread, proc),
                offset_of!(Process, ruid), offset_of!(Process, euid),
                offset_of!(Process, suid), offset_of!(Process, fsuid),
                0, 1, 2, 3, Some(getcred),
            )
        };
    }
}
