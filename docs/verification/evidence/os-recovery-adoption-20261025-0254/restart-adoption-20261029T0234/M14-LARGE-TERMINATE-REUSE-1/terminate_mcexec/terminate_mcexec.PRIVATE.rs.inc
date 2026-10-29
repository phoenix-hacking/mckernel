// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
// Source-only proposal. This is unselected until the real C guard, provider
// binding, request initialization/ownership and exact target ABI are reviewed.
#[cfg(all(f03_terminate_mcexec_whole_candidate, target_arch = "x86_64"))]
mod f03_terminate_mcexec_whole {
    use core::mem::{offset_of, MaybeUninit};
    use crate::abi::{CInt, Process, SyscallRequest};

    // kernel/include/syscall.h defines __NR_exit_group = 231 on this profile.
    const EXIT_GROUP_NR: CInt = 231;

    /// Execute only the existing terminate_mcexec C entry's adapter.
    ///
    /// # Safety
    /// Current CPU/thread/process and group status obey the existing body and
    /// atomic provider contracts. The existing synchronous do_syscall provider
    /// may use the request only while this stack frame lives. Before any field
    /// is read or copied, the existing body and provider must initialize it.
    /// This wrapper establishes no request ownership, publication or host ACK.
    #[export_name = "terminate_mcexec"]
    pub unsafe extern "C" fn f03_terminate_mcexec_v1(rc: CInt, sig: CInt) {
        let mut request = MaybeUninit::<SyscallRequest>::uninit();
        // SAFETY: The unchanged current-CPU and process contracts match C;
        // request is passed as raw uninitialized storage, never as a reference.
        unsafe {
            let current = (*crate::cls::get_this_cpu_local_var()).current;
            let process = (*current).proc;
            let _ = super::terminate_mcexec_body_result(
                process.cast(), request.as_mut_ptr(), rc, sig,
                super::ihk_mc_get_processor_id(), EXIT_GROUP_NR,
                offset_of!(Process, group_exit_status), offset_of!(Process, nohost),
                Some(crate::atomic_helpers::atomic_cmpxchg_ulong),
                Some(super::do_syscall),
            );
        }
    }
}
