// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
#[cfg(f03_ptrace_entry_candidate)]
mod ptrace_wakeup_state_callbacks {
    use core::ffi::c_void;

    use crate::abi::{CInt, CULong};
    use crate::process_helpers;

    use super::{
        PtracePendingSignalTakeFn, PtraceSavedContextClearFn, PtraceTraceSyscallUpdateFn,
    };

    /// Forward the original saved-context clear through its integer-address ABI.
    ///
    /// # Safety
    /// A nonzero thread address names live storage with an aligned writable C int
    /// at offset. The ptrace caller retains the original exclusion and lifetime.
    #[no_mangle]
    pub unsafe extern "C" fn ptrace_wakeup_clear_saved_bridge(
        thread_addr: CULong,
        offset: CULong,
    ) -> CInt {
        // SAFETY: Preserve the C address cast and pass through null to the provider.
        unsafe {
            process_helpers::process_thread_ptrace_saved_context_clear_result(
                thread_addr as *mut c_void,
                offset,
            )
        }
    }

    /// Forward the trace-syscall update under the caller's existing update lock.
    ///
    /// # Safety
    /// A nonzero thread address names live storage with an aligned writable C int
    /// at ptrace_offset. The caller holds the original update-lock exclusion.
    #[no_mangle]
    pub unsafe extern "C" fn ptrace_wakeup_trace_syscall_bridge(
        thread_addr: CULong,
        ptrace_offset: CULong,
        trace_syscall: CInt,
    ) -> CInt {
        // SAFETY: Forward the unchanged address, offset and signed flag once.
        unsafe {
            process_helpers::process_thread_ptrace_trace_syscall_update_result(
                thread_addr as *mut c_void,
                ptrace_offset,
                trace_syscall,
            )
        }
    }

    /// Return the existing provider's taken node through the unsigned-long ABI.
    ///
    /// # Safety
    /// A nonzero thread address remains live under the original ptrace exclusion.
    /// The selected offset names an aligned writable pointer slot. The caller
    /// retains the original delivery/free responsibility for the returned node.
    #[no_mangle]
    pub unsafe extern "C" fn ptrace_wakeup_pending_take_bridge(
        thread_addr: CULong,
        sendsig_offset: CULong,
        recvsig_offset: CULong,
        source: CInt,
    ) -> CULong {
        // SAFETY: Preserve source/offset routing and the original pointer-to-long cast.
        unsafe {
            process_helpers::process_thread_ptrace_pending_signal_take_result(
                thread_addr as *mut c_void,
                sendsig_offset,
                recvsig_offset,
                source,
            ) as CULong
        }
    }

    const _: PtraceSavedContextClearFn = ptrace_wakeup_clear_saved_bridge;
    const _: PtraceTraceSyscallUpdateFn = ptrace_wakeup_trace_syscall_bridge;
    const _: PtracePendingSignalTakeFn = ptrace_wakeup_pending_take_bridge;
}
