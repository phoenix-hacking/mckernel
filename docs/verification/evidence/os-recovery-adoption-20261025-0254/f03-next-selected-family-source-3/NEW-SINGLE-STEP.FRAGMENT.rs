// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
#[cfg(f03_ptrace_entry_candidate)]
mod ptrace_wakeup_step_callback {
    use crate::abi::{CULong, Thread};
    use super::{set_single_step, PtraceSetSingleStepFn};

    /// Forward the existing integer-address callback to the selected Rust provider.
    ///
    /// # Safety
    /// The original ptrace caller owns thread/context lifetime and exclusion.
    /// Null is passed through to the existing provider, which retains its checks.
    #[no_mangle]
    pub unsafe extern "C" fn ptrace_wakeup_set_single_step_bridge(thread_addr: CULong) {
        // SAFETY: Preserve the original address cast; no direct context access here.
        unsafe { set_single_step(thread_addr as *mut Thread) };
    }
    const _: PtraceSetSingleStepFn = ptrace_wakeup_set_single_step_bridge;
}
